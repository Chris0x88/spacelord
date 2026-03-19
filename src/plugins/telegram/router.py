"""
Telegram Inbound Router
=======================
Traffic cop: decides whether an incoming update goes to the fast lane
(direct PacmanController call) or the AI lane (Phase 2+, LLM round-trip).

Fast-lane commands (Phase 1):
  /balance, /portfolio → get_balances()
  /price               → placeholder (Phase 2)
  /status, /health     → system status
  callback_query       → same mapping as slash commands

Swap lane (Phase 2):
  Free-text swap commands  → parse → confirm keyboard
  confirm_swap:* callback  → execute_swap_callback() (called from async thread)
  cancel:swap callback     → cancel message

AI lane:
  Everything else → placeholder response for now.

Returns a response dict:
  {
    "text": str,
    "reply_markup": dict | None,   # Telegram InlineKeyboardMarkup
    "parse_mode": str,             # "HTML"
  }
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.plugins.telegram import formatters

logger = logging.getLogger("pacman.telegram")

# Repo root — used for data file access
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATA_DIR = _REPO_ROOT / "data"

# Commands handled in the fast lane (no LLM)
FAST_LANE_COMMANDS = {
    "/balance", "/portfolio",
    "/price",
    "/status", "/health",
    "/start", "/help",
}

# callback_data values → treated as equivalent slash command
CALLBACK_MAP = {
    "portfolio": "/portfolio",
    "balance":   "/balance",
    "price":     "/price",
    "gas":       "/health",
    "health":    "/health",
    "status":    "/status",
    # Phase 2+ — handled explicitly below
    "swap":      "/swap",
    "send":      "/send",
    "orders":    "/orders",
    "robot":     "/robot",
}

# Words that indicate a swap intent in free-text messages
SWAP_TRIGGER_WORDS = frozenset({"swap", "buy", "sell", "trade", "exchange", "convert"})


class InboundRouter:
    def __init__(self, controller):
        """
        Args:
            controller: PacmanController instance (shared, already initialised)
        """
        self._ctrl = controller

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def handle_message(self, text: str, user_id: int) -> Dict[str, Any]:
        """Route a text message (slash command or free text)."""
        cmd = self._extract_command(text)
        if cmd and cmd in FAST_LANE_COMMANDS:
            return self._fast_lane(cmd, user_id)

        # Check if the first word is a swap trigger
        first_word = text.strip().lower().split()[0] if text.strip() else ""
        if first_word in SWAP_TRIGGER_WORDS:
            return self._cmd_swap_parse(text)

        # AI lane placeholder
        return self._ai_lane_placeholder(text)

    def handle_callback(self, callback_data: str, user_id: int) -> Dict[str, Any]:
        """Route a callback_query (inline button press)."""
        # confirm_swap:AMOUNT:FROM_ID:TO_ID:MODE — execution is done by the
        # interceptor asynchronously; this path is never reached for that prefix.
        if callback_data.startswith("confirm_swap:"):
            # Fallback: should be handled by interceptor async path
            return _reply("\u23f3 Processing swap\u2026", with_buttons=False)

        # Cancel swap
        if callback_data == "cancel:swap":
            return _reply("\U0001f6ab Swap cancelled.", with_buttons=True)

        # "swap" button in the main menu → show prompt
        if callback_data == "swap":
            return self._cmd_swap_prompt()

        cmd = CALLBACK_MAP.get(callback_data)
        if cmd and cmd in FAST_LANE_COMMANDS:
            return self._fast_lane(cmd, user_id)

        # Unmapped callback or unimplemented Phase 2+ command
        return self._ai_lane_placeholder(callback_data)

    def execute_swap_callback(self, callback_data: str) -> Dict[str, Any]:
        """
        Execute a confirmed swap.  Called from an asyncio thread pool so
        blocking Hedera RPC calls are fine here.

        callback_data format: confirm_swap:AMOUNT:FROM_ID:TO_ID:MODE
        """
        try:
            parts = callback_data.split(":")
            # Parts: ["confirm_swap", "AMOUNT", "FROM_ID", "TO_ID", "MODE"]
            # Token IDs like "0.0.456858" contain dots, NOT colons, so the
            # split is unambiguous.
            if len(parts) != 5:
                return _error("Malformed swap callback — please try again.")
            _, amount_str, from_id, to_id, mode = parts
            amount = float(amount_str)
        except Exception as exc:
            return _error(f"Could not parse swap request: {exc}")

        from_sym = self._id_to_symbol(from_id)
        to_sym = self._id_to_symbol(to_id)

        try:
            result = self._ctrl.swap(from_id, to_id, amount, mode=mode)
        except Exception as exc:
            logger.error(f"[Telegram] swap() raised: {exc}", exc_info=True)
            return {
                "text": formatters.format_swap_error(
                    str(exc), from_sym, to_sym, amount
                ),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        if not result.success:
            return {
                "text": formatters.format_swap_error(
                    result.error or "Unknown error", from_sym, to_sym, amount
                ),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        # Decode raw amounts using token decimals
        try:
            from_dec = self._ctrl.executor._get_token_decimals(from_id)
            to_dec   = self._ctrl.executor._get_token_decimals(to_id)
        except Exception:
            from_dec, to_dec = 8, 8  # Safe fallback

        amount_in  = result.amount_in_raw  / (10 ** from_dec) if result.amount_in_raw  else amount
        amount_out = result.amount_out_raw / (10 ** to_dec)   if result.amount_out_raw else 0.0

        text = formatters.format_swap_receipt(
            tx_hash=result.tx_hash,
            amount_in=amount_in,
            amount_out=amount_out,
            from_symbol=from_sym,
            to_symbol=to_sym,
            gas_cost_hbar=result.gas_cost_hbar,
            gas_cost_usd=result.gas_cost_usd,
            lp_fee=result.lp_fee_amount,
        )
        return {"text": text, "reply_markup": formatters.format_buttons(), "parse_mode": "HTML"}

    # ------------------------------------------------------------------
    # Fast lane
    # ------------------------------------------------------------------

    def _fast_lane(self, cmd: str, user_id: int) -> Dict[str, Any]:
        """Execute command directly via PacmanController — no LLM."""
        try:
            if cmd in ("/balance", "/portfolio"):
                return self._cmd_balance()
            elif cmd in ("/status", "/health", "/gas"):
                return self._cmd_health()
            elif cmd in ("/start", "/help"):
                return self._cmd_help()
            elif cmd == "/price":
                return self._cmd_price()
            else:
                return _not_implemented(cmd)
        except Exception as exc:
            return _error(str(exc), hint="Try again in a moment.")

    # ------------------------------------------------------------------
    # Fast-lane command implementations
    # ------------------------------------------------------------------

    def _cmd_balance(self) -> Dict[str, Any]:
        balances = self._ctrl.get_balances()
        account_id = getattr(self._ctrl, "account_id", "")
        text = formatters.format_balance(balances, account_id=account_id)
        return _reply(text, with_buttons=True)

    def _cmd_health(self) -> Dict[str, Any]:
        account_id = getattr(self._ctrl, "account_id", "unknown")
        network = getattr(self._ctrl, "network", "mainnet")
        text = (
            "\U0001f7e2 <b>System Status</b>\n\n"
            f"Account: <code>{account_id}</code>\n"
            f"Network: <code>{network}</code>\n"
            "Controller: <code>online</code>"
        )
        return _reply(text, with_buttons=True)

    def _cmd_help(self) -> Dict[str, Any]:
        text = formatters.format_welcome()
        return _reply(text, with_buttons=True)

    def _cmd_price(self) -> Dict[str, Any]:
        # Phase 1: minimal price info — just HBAR price from the price manager
        try:
            from lib.prices import price_manager
            hbar = price_manager.get_hbar_price()
            text = (
                "\U0001f4ca <b>Token Prices</b>\n\n"
                f"HBAR: <code>${hbar:.4f}</code>\n\n"
                "<i>More prices coming in Phase 2.</i>"
            )
        except Exception as exc:
            text = formatters.format_error(f"Could not fetch prices: {exc}")
        return _reply(text, with_buttons=True)

    # ------------------------------------------------------------------
    # Swap lane — Phase 2
    # ------------------------------------------------------------------

    def _cmd_swap_prompt(self) -> Dict[str, Any]:
        """Return the 'What do you want to swap?' prompt."""
        return {"text": formatters.format_swap_prompt(), "reply_markup": None, "parse_mode": "HTML"}

    def _cmd_swap_parse(self, text: str) -> Dict[str, Any]:
        """
        Parse a free-text swap command, check governance limits, get route,
        and return a confirmation keyboard for the user to review before executing.
        """
        from src.translator import translate_command

        req = translate_command(text)
        if not req or req.get("intent") != "swap":
            return _reply(
                "\u2753 <b>Couldn\u2019t parse that.</b>\n\nExamples:\n"
                "<code>swap 5 USDC for HBAR</code>\n"
                "<code>buy 100 HBAR</code>\n"
                "<code>sell 10 HBAR</code>",
                with_buttons=True,
            )

        from_id = req["from_token"]
        to_id   = req["to_token"]
        amount  = req["amount"]
        mode    = req.get("mode", "exact_in")

        # "swap all" is not supported via Telegram — needs real-time balance query
        if amount == -1:
            return _reply(
                "\u2139\ufe0f <b>Swap All</b> isn\u2019t supported via Telegram.\n\n"
                "Specify an amount:\n<code>swap 100 HBAR for USDC</code>",
                with_buttons=True,
            )

        from_sym = self._id_to_symbol(from_id)
        to_sym   = self._id_to_symbol(to_id)

        # --- Balance check ---
        try:
            balances = self._ctrl.get_balances()
            from_bal = balances.get(from_sym, balances.get(from_id, 0.0))
            if isinstance(from_bal, dict):
                from_bal = from_bal.get("balance", 0.0)
            if mode == "exact_in" and from_bal < amount:
                return {
                    "text": formatters.format_swap_error(
                        f"Insufficient balance: have {formatters._fmt_amount(from_bal)}"
                        f" {from_sym}, need {formatters._fmt_amount(amount)}.",
                        from_sym, to_sym, amount,
                    ),
                    "reply_markup": formatters.format_buttons(),
                    "parse_mode": "HTML",
                }
        except Exception as exc:
            logger.warning(f"[Telegram] balance pre-check failed: {exc}")
            # Non-fatal: proceed and let the executor catch it

        # --- Governance limits ---
        limit_err = self._check_swap_limits(from_id, to_id, amount, mode)
        if limit_err:
            return {
                "text": formatters.format_swap_error(limit_err, from_sym, to_sym, amount),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        # --- Route ---
        try:
            route = self._ctrl.get_route(from_id, to_id, amount, mode=mode)
        except Exception as exc:
            return {
                "text": formatters.format_swap_error(
                    f"Routing failed: {exc}", from_sym, to_sym, amount
                ),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        if not route or route.output_format == "ERROR" or not route.steps:
            return {
                "text": formatters.format_swap_error(
                    "No liquidity route found for this pair.",
                    from_sym, to_sym, amount,
                ),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        # Build step list for display
        steps: List[Dict[str, Any]] = []
        for step in route.steps:
            if step.step_type == "swap":
                steps.append({
                    "type": "swap",
                    "from": step.from_token,
                    "to":   step.to_token,
                    "fee_pct": step.fee_percent * 100,
                })

        confirm = formatters.format_swap_confirm(
            amount=amount,
            from_symbol=from_sym,
            to_symbol=to_sym,
            from_id=from_id,
            to_id=to_id,
            mode=mode,
            fee_pct=route.total_fee_percent,
            gas_hbar=route.total_gas_hbar,
            route_steps=steps,
        )
        return {**confirm, "parse_mode": "HTML"}

    # ------------------------------------------------------------------
    # Governance limit enforcement
    # ------------------------------------------------------------------

    def _check_swap_limits(
        self, from_id: str, to_id: str, amount: float, mode: str
    ) -> Optional[str]:
        """
        Validate against governance.json safety limits.
        Returns an error string if a limit is violated, None otherwise.
        """
        max_swap_usd     = getattr(self._ctrl.config, "max_swap_amount_usd", 100.0)
        min_hbar_reserve = 5.0  # Governance default

        try:
            gov_path = _DATA_DIR / "governance.json"
            if gov_path.exists():
                with open(gov_path) as f:
                    gov = json.load(f)
                min_hbar_reserve = gov.get("safety_limits", {}).get(
                    "min_hbar_reserve", 5.0
                )
        except Exception:
            pass

        # USD value check
        try:
            from lib.prices import price_manager

            if mode == "exact_in":
                basis_id = from_id
                basis_amt = amount
            else:
                basis_id = to_id
                basis_amt = amount

            if basis_id in ("0.0.0", "HBAR"):
                price = price_manager.get_hbar_price()
            else:
                price = price_manager.get_price(basis_id)

            if price and price > 0:
                swap_usd = basis_amt * price
                if swap_usd > max_swap_usd:
                    return (
                        f"Swap value ~${swap_usd:.2f} exceeds the"
                        f" ${max_swap_usd:.0f} per-swap limit."
                    )
        except Exception:
            pass  # Skip USD check if price data unavailable

        # HBAR gas reserve check (only when selling HBAR exact_in)
        if from_id in ("0.0.0", "HBAR") and mode == "exact_in":
            try:
                balances = self._ctrl.get_balances()
                hbar_bal = balances.get("HBAR", balances.get("hbar", 0.0))
                if isinstance(hbar_bal, dict):
                    hbar_bal = hbar_bal.get("balance", 0.0)
                remaining = hbar_bal - amount
                if remaining < min_hbar_reserve:
                    return (
                        f"Must keep {min_hbar_reserve} HBAR as gas reserve."
                        f" Balance: {hbar_bal:.2f} HBAR;"
                        f" after swap: {remaining:.2f} HBAR."
                    )
            except Exception:
                pass

        return None

    # ------------------------------------------------------------------
    # AI lane placeholder
    # ------------------------------------------------------------------

    def _ai_lane_placeholder(self, text: str) -> Dict[str, Any]:
        reply = (
            "\U0001f916 <b>AI Lane</b>\n\n"
            "Natural language trading is coming in Phase 2.\n\n"
            "Use slash commands or the buttons below for now."
        )
        return _reply(reply, with_buttons=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _id_to_symbol(self, token_id: str) -> str:
        """Reverse-lookup a token ID (or symbol key) to its display symbol."""
        if not token_id:
            return "???"
        if token_id in ("0.0.0", "HBAR"):
            return "HBAR"
        try:
            tokens_path = _DATA_DIR / "tokens.json"
            if tokens_path.exists():
                with open(tokens_path) as f:
                    tokens = json.load(f)
                # tokens.json is {symbol: {id, symbol, decimals, name}}
                # If token_id is already a key (e.g. "USDC"), return its symbol field
                if token_id in tokens:
                    return tokens[token_id].get("symbol", token_id)
                # Otherwise scan for a matching id
                for sym, meta in tokens.items():
                    if isinstance(meta, dict) and meta.get("id") == token_id:
                        return meta.get("symbol", sym)
        except Exception:
            pass
        return token_id  # Fallback: return the raw ID

    @staticmethod
    def _extract_command(text: str) -> Optional[str]:
        """Extract /command from message text (strips @BotName suffix)."""
        if not text or not text.startswith("/"):
            return None
        word = text.split()[0].lower()
        # Strip @botname suffix: /balance@MyBot → /balance
        if "@" in word:
            word = word.split("@")[0]
        return word


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _reply(text: str, with_buttons: bool = False) -> Dict[str, Any]:
    return {
        "text": text,
        "reply_markup": formatters.format_buttons() if with_buttons else None,
        "parse_mode": "HTML",
    }


def _error(msg: str, hint: str = "") -> Dict[str, Any]:
    return _reply(formatters.format_error(msg, hint=hint))


def _not_implemented(cmd: str) -> Dict[str, Any]:
    return _reply(formatters.format_not_implemented(cmd))
