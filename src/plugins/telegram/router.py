"""
Telegram Inbound Router
=======================
Traffic cop: decides whether an incoming update goes to the fast lane
(direct PacmanController call) or the AI lane (LLM round-trip, future).

Fast-lane commands (Phase 1–3):
  /balance, /portfolio → get_balances() + prices
  /price               → price lookups
  /status, /health     → system status
  /tokens, /gas        → token info, gas reserve
  /history             → recent tx records
  /send                → transfer flow
  /robot               → rebalancer status
  /setup               → Ghost Tunnel
  /menu, /start, /help → main menu

Swap lane (Phase 2):
  Free-text swap commands → parse → confirm keyboard
  confirm_swap:* callback → execute_swap_callback() (async thread)
  cancel:swap callback    → cancel message

Send lane (Phase 3):
  send/transfer commands  → parse → confirm keyboard
  confirm_send:* callback → execute_send_callback() (async thread)

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
    "/start", "/help", "/menu",
    "/tokens",
    "/gas",
    "/history",
    "/send",
    "/setup",
    "/robot",
    "/orders",
}

# callback_data values → treated as equivalent slash command
CALLBACK_MAP = {
    "portfolio": "/portfolio",
    "balance":   "/balance",
    "price":     "/price",
    "gas":       "/gas",
    "health":    "/health",
    "status":    "/status",
    "tokens":    "/tokens",
    "history":   "/history",
    "send":      "/send",
    "setup":     "/setup",
    "robot":     "/robot",
    "orders":    "/orders",
    "menu":      "/menu",
    # Phase 2+ — handled explicitly below
    "swap":      "/swap",
}

# Words that indicate a swap intent in free-text messages
SWAP_TRIGGER_WORDS = frozenset({"swap", "buy", "sell", "trade", "exchange", "convert"})

# Words that indicate a send/transfer intent
SEND_TRIGGER_WORDS = frozenset({"send", "transfer"})


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
            arg = text[len(cmd):].strip() if cmd else ""
            return self._fast_lane(cmd, user_id, arg=arg)

        # Check if the first word is a send trigger
        first_word = text.strip().lower().split()[0] if text.strip() else ""
        if first_word in SEND_TRIGGER_WORDS:
            return self._cmd_send_parse(text)

        # Check if the first word is a swap trigger
        if first_word in SWAP_TRIGGER_WORDS:
            return self._cmd_swap_parse(text)

        # AI lane placeholder
        return self._ai_lane_placeholder(text)

    def handle_web_app_data(self, data: str, user_id: int) -> Dict[str, Any]:
        """
        Handle web_app_data sent back by Telegram after Mini App submission.
        Ghost Tunnel uses direct POST /ghost instead, so this is belt-and-suspenders.
        """
        try:
            import json as _json
            payload = _json.loads(data)
            field = payload.get("field", "")
            if field:
                text = formatters.format_key_saved(field)
                return _reply(text, with_buttons=True)
        except Exception:
            pass
        return _reply("🔐 Key received.", with_buttons=True)

    def handle_callback(self, callback_data: str, user_id: int) -> Dict[str, Any]:
        """Route a callback_query (inline button press)."""
        # confirm_swap:* — handled by interceptor async path
        if callback_data.startswith("confirm_swap:"):
            return _reply("⏳ Processing swap…", with_buttons=False)

        # confirm_send:* — handled by interceptor async path
        if callback_data.startswith("confirm_send:"):
            return _reply("⏳ Processing transfer…", with_buttons=False)

        # Cancel
        if callback_data in ("cancel:swap", "cancel:send"):
            return _reply("🚫 Cancelled.", with_buttons=True)

        # "swap" button in the main menu → show prompt
        if callback_data == "swap":
            return self._cmd_swap_prompt()

        if callback_data == "swap_select_from":
            return self._cmd_swap_select_from()

        if callback_data == "swap_select_to":
            return self._cmd_swap_select_to()

        if callback_data == "swap_select_amount":
            return self._cmd_swap_select_amount()

        cmd = CALLBACK_MAP.get(callback_data)
        if cmd and cmd in FAST_LANE_COMMANDS:
            return self._fast_lane(cmd, user_id)

        # Unmapped callback
        return self._ai_lane_placeholder(callback_data)

    def execute_swap_callback(self, callback_data: str) -> Dict[str, Any]:
        """
        Execute a confirmed swap. Called from asyncio thread pool.
        callback_data format: confirm_swap:AMOUNT:FROM_ID:TO_ID:MODE
        """
        try:
            parts = callback_data.split(":")
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
            from_dec, to_dec = 8, 8

        amount_in  = result.amount_in_raw  / (10 ** from_dec) if result.amount_in_raw  else amount
        amount_out = result.amount_out_raw / (10 ** to_dec)   if result.amount_out_raw else 0.0

        text, reply_markup = formatters.format_swap_receipt(
            tx_hash=result.tx_hash,
            amount_in=amount_in,
            amount_out=amount_out,
            from_symbol=from_sym,
            to_symbol=to_sym,
            gas_cost_hbar=result.gas_cost_hbar,
            gas_cost_usd=result.gas_cost_usd,
            lp_fee=result.lp_fee_amount,
        )
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    # ------------------------------------------------------------------
    # Fast lane
    # ------------------------------------------------------------------

    def _fast_lane(self, cmd: str, user_id: int, arg: str = "") -> Dict[str, Any]:
        """Execute command directly via PacmanController — no LLM."""
        try:
            if cmd in ("/balance", "/portfolio"):
                return self._cmd_balance()
            elif cmd == "/status":
                return self._cmd_status()
            elif cmd in ("/health",):
                return self._cmd_health()
            elif cmd == "/gas":
                return self._cmd_gas()
            elif cmd in ("/start", "/help", "/menu"):
                return self._cmd_help()
            elif cmd == "/price":
                return self._cmd_price(arg.upper() if arg else None)
            elif cmd == "/tokens":
                return self._cmd_tokens()
            elif cmd == "/history":
                return self._cmd_history()
            elif cmd == "/send":
                return self._cmd_send_prompt()
            elif cmd == "/setup":
                return self._cmd_setup(arg)
            elif cmd == "/robot":
                return self._cmd_robot()
            elif cmd == "/orders":
                return self._cmd_orders()
            else:
                return _not_implemented(cmd)
        except Exception as exc:
            return _error(str(exc), hint="Try again in a moment.")

    # ------------------------------------------------------------------
    # Fast-lane command implementations
    # ------------------------------------------------------------------

    def _get_prices(self) -> Dict[str, float]:
        """Fetch USD prices for major tokens. Non-fatal on failure."""
        try:
            from lib.prices import price_manager
            MAJOR = {
                "HBAR": "0.0.0",
                "USDC": "0.0.456858",
                "WBTC": "0.0.10082597",
                "WETH": "0.0.9470869",
                "SAUCE": "0.0.731861",
            }
            prices = {}
            for sym, tid in MAJOR.items():
                if sym == "HBAR":
                    prices[sym] = price_manager.get_hbar_price()
                elif sym == "USDC":
                    prices[sym] = 1.0  # Stablecoin
                else:
                    prices[sym] = price_manager.get_price(tid)
            return prices
        except Exception:
            return {}

    def _cmd_balance(self) -> Dict[str, Any]:
        balances = self._ctrl.get_balances()
        account_id = getattr(self._ctrl, "account_id", "")
        prices = self._get_prices()
        text, reply_markup = formatters.format_balance(balances, account_id=account_id, prices=prices)
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_status(self) -> Dict[str, Any]:
        balances = self._ctrl.get_balances()
        account_id = getattr(self._ctrl, "account_id", "unknown")
        network = getattr(self._ctrl, "network", "mainnet")
        prices = self._get_prices()
        text, reply_markup = formatters.format_status(balances, account_id, network, prices=prices)
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_health(self) -> Dict[str, Any]:
        account_id = getattr(self._ctrl, "account_id", "unknown")
        network = getattr(self._ctrl, "network", "mainnet")
        balances = self._ctrl.get_balances()
        prices = self._get_prices()
        text, reply_markup = formatters.format_status(balances, account_id, network, prices=prices)
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_gas(self) -> Dict[str, Any]:
        try:
            gov_path = _DATA_DIR / "governance.json"
            min_reserve = 5.0
            if gov_path.exists():
                with open(gov_path) as f:
                    gov = json.load(f)
                min_reserve = gov.get("safety_limits", {}).get("min_hbar_reserve", 5.0)
            balances = self._ctrl.get_balances()
            hbar_bal = balances.get("HBAR", balances.get("hbar", 0.0))
            if isinstance(hbar_bal, dict):
                hbar_bal = hbar_bal.get("balance", 0.0)
            text, reply_markup = formatters.format_gas_status(hbar_bal, min_reserve)
        except Exception as exc:
            text = formatters.format_error(f"Could not fetch gas status: {exc}")
            reply_markup = formatters.format_buttons()
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_help(self) -> Dict[str, Any]:
        text = formatters.format_welcome()
        return _reply(text, with_buttons=True)

    def _cmd_price(self, token: Optional[str] = None) -> Dict[str, Any]:
        MAJOR_TOKENS = {
            "HBAR":  "0.0.0",
            "USDC":  "0.0.456858",
            "WBTC":  "0.0.10082597",
            "WETH":  "0.0.9470869",
            "SAUCE": "0.0.731861",
        }
        try:
            from lib.prices import price_manager
            if token:
                sym = token.upper()
                tid = MAJOR_TOKENS.get(sym)
                if sym == "HBAR":
                    price = price_manager.get_hbar_price()
                elif sym == "USDC":
                    price = 1.0
                elif tid:
                    price = price_manager.get_price(tid)
                else:
                    price = price_manager.get_price(sym)
                text, reply_markup = formatters.format_price(sym, price)
            else:
                prices = {}
                for sym, tid in MAJOR_TOKENS.items():
                    if sym == "HBAR":
                        prices[sym] = price_manager.get_hbar_price()
                    elif sym == "USDC":
                        prices[sym] = 1.0
                    else:
                        prices[sym] = price_manager.get_price(tid)
                text, reply_markup = formatters.format_prices(prices)
        except Exception as exc:
            text = formatters.format_error(f"Could not fetch prices: {exc}")
            reply_markup = formatters.format_buttons()
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_tokens(self) -> Dict[str, Any]:
        try:
            tokens_path = _DATA_DIR / "tokens.json"
            tokens_data = {}
            if tokens_path.exists():
                with open(tokens_path) as f:
                    tokens_data = json.load(f)
            text, reply_markup = formatters.format_tokens(tokens_data)
        except Exception as exc:
            text = formatters.format_error(f"Could not load tokens: {exc}")
            reply_markup = formatters.format_buttons()
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_history(self) -> Dict[str, Any]:
        try:
            records = []
            try:
                raw = self._ctrl.get_history(10)
                if raw:
                    records = raw if isinstance(raw, list) else []
            except Exception:
                pass

            if not records:
                exec_dir = _REPO_ROOT / "execution_records"
                if exec_dir.exists():
                    files = sorted(exec_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                    for fp in files[:10]:
                        try:
                            with open(fp) as f:
                                records.append(json.load(f))
                        except Exception:
                            continue
            text, reply_markup = formatters.format_history(records)
        except Exception as exc:
            text = formatters.format_error(f"Could not load history: {exc}")
            reply_markup = formatters.format_buttons()
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_robot(self) -> Dict[str, Any]:
        """Show BTC rebalancer daemon status."""
        try:
            gov_path = _DATA_DIR / "governance.json"
            robot_account = ""
            funded = False
            if gov_path.exists():
                with open(gov_path) as f:
                    gov = json.load(f)
                robot_info = gov.get("accounts", {}).get("robot", {})
                robot_account = robot_info.get("id", "")
                funded = robot_info.get("funded", False)

            # Try to read robot state
            portfolio_usd = 0.0
            btc_pct = 0.0
            target_pct = 50.0
            last_rebalance = ""
            status = "idle"

            state_path = _DATA_DIR / "robot_state.json"
            if state_path.exists():
                try:
                    with open(state_path) as f:
                        state = json.load(f)
                    portfolio_usd = state.get("portfolio_usd", 0.0)
                    btc_pct = state.get("btc_pct", 0.0)
                    target_pct = state.get("target_pct", 50.0)
                    last_rebalance = state.get("last_rebalance", "")
                    status = state.get("status", "idle")
                except Exception:
                    pass

            # Check if daemon PID is alive
            pid_path = _DATA_DIR / "robot.pid"
            if pid_path.exists():
                try:
                    import os
                    pid = int(pid_path.read_text().strip())
                    os.kill(pid, 0)  # Check if process exists
                    status = "running"
                except (ValueError, ProcessLookupError, PermissionError):
                    status = "stopped"

            text, reply_markup = formatters.format_robot_status(
                robot_account=robot_account,
                funded=funded,
                portfolio_usd=portfolio_usd,
                btc_pct=btc_pct,
                target_pct=target_pct,
                last_rebalance=last_rebalance,
                status=status,
            )
        except Exception as exc:
            text = formatters.format_error(f"Could not fetch robot status: {exc}")
            reply_markup = formatters.format_buttons()
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _cmd_orders(self) -> Dict[str, Any]:
        """Pending orders — placeholder for now."""
        text = formatters.format_not_implemented("Pending Orders")
        return _reply(text, with_buttons=True)

    # ------------------------------------------------------------------
    # Swap lane — Phase 2
    # ------------------------------------------------------------------

    def _cmd_swap_prompt(self) -> Dict[str, Any]:
        """Return the 'What do you want to swap?' prompt."""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "1️⃣ From token", "callback_data": "swap_select_from"},
                    {"text": "2️⃣ To token", "callback_data": "swap_select_to"},
                ],
                [
                    {"text": "3️⃣ Amount", "callback_data": "swap_select_amount"},
                ],
                [
                    {"text": "⬅️ Menu", "callback_data": "menu"},
                ],
            ]
        }
        return {"text": formatters.format_swap_prompt(), "reply_markup": keyboard, "parse_mode": "HTML"}

    def _cmd_swap_select_from(self) -> Dict[str, Any]:
        return _reply("💱 <b>Choose the token to swap from</b>\n\nUse a typed swap command for now:\n<code>swap 5 USDC for HBAR</code>", with_buttons=True)

    def _cmd_swap_select_to(self) -> Dict[str, Any]:
        return _reply("💱 <b>Choose the token to swap to</b>\n\nUse a typed swap command for now:\n<code>swap 5 USDC for HBAR</code>", with_buttons=True)

    def _cmd_swap_select_amount(self) -> Dict[str, Any]:
        return _reply("💱 <b>Choose an amount</b>\n\nUse a typed swap command for now:\n<code>swap 5 USDC for HBAR</code>", with_buttons=True)

    def _cmd_swap_parse(self, text: str) -> Dict[str, Any]:
        """
        Parse a free-text swap command, check governance limits, get route,
        and return a confirmation keyboard for the user to review before executing.
        """
        from src.translator import translate_command

        req = translate_command(text)
        if not req or req.get("intent") != "swap":
            return _reply(
                "❓ <b>Couldn't parse that.</b>\n\nExamples:\n"
                "<code>swap 5 USDC for HBAR</code>\n"
                "<code>buy 100 HBAR</code>\n"
                "<code>sell 10 HBAR</code>",
                with_buttons=True,
            )

        from_id = req["from_token"]
        to_id   = req["to_token"]
        amount  = req["amount"]
        mode    = req.get("mode", "exact_in")

        if amount == -1:
            return _reply(
                "ℹ️ <b>Swap All</b> isn't supported via Telegram.\n\n"
                "Specify an amount:\n<code>swap 100 HBAR for USDC</code>",
                with_buttons=True,
            )

        from_sym = self._id_to_symbol(from_id)
        to_sym   = self._id_to_symbol(to_id)

        # Balance check
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

        # Governance limits
        limit_err = self._check_swap_limits(from_id, to_id, amount, mode)
        if limit_err:
            return {
                "text": formatters.format_swap_error(limit_err, from_sym, to_sym, amount),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        # Route
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
    # Send lane — Phase 3
    # ------------------------------------------------------------------

    def _cmd_setup(self, field: str = "") -> Dict[str, Any]:
        """Return a WebApp button for secure key entry via the Ghost Tunnel."""
        try:
            from src.plugins.telegram.interceptor import build_webapp_button
            field = field.upper() if field else "PRIVATE_KEY"
            markup = build_webapp_button(field)
        except Exception:
            markup = None
        text = formatters.format_setup_prompt()
        return {"text": text, "reply_markup": markup, "parse_mode": "HTML"}

    def _cmd_send_prompt(self) -> Dict[str, Any]:
        keyboard = {
            "inline_keyboard": [
                [{"text": "⬅️ Menu", "callback_data": "menu"}],
            ]
        }
        return {"text": formatters.format_send_prompt(), "reply_markup": keyboard, "parse_mode": "HTML"}

    def _cmd_send_parse(self, text: str) -> Dict[str, Any]:
        """Parse a free-text send command, check whitelist and balance."""
        import re
        m = re.match(
            r"(?:send|transfer)\s+([\d.]+)\s+(\w+)\s+to\s+(0\.0\.\d+)",
            text.strip(), re.IGNORECASE
        )
        if not m:
            return _reply(
                "❓ <b>Couldn't parse that.</b>\n\n"
                "Format: <code>send 5 USDC to 0.0.7949179</code>",
                with_buttons=True,
            )

        amount = float(m.group(1))
        token = m.group(2).upper()
        recipient = m.group(3)

        if recipient.startswith("0x"):
            return _reply(
                "🔒 <b>EVM addresses blocked.</b>\n\nUse a Hedera ID: <code>0.0.xxx</code>",
                with_buttons=True,
            )

        # Whitelist check
        whitelist_err = self._check_send_whitelist(recipient)
        if whitelist_err:
            return {
                "text": formatters.format_send_error(whitelist_err, amount, token, recipient),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        # Balance check
        try:
            balances = self._ctrl.get_balances()
            bal = balances.get(token, 0.0)
            if isinstance(bal, dict):
                bal = bal.get("balance", 0.0)
            if bal < amount:
                return {
                    "text": formatters.format_send_error(
                        f"Insufficient balance: have {formatters._fmt_amount(bal)} {token}, need {formatters._fmt_amount(amount)}.",
                        amount, token, recipient,
                    ),
                    "reply_markup": formatters.format_buttons(),
                    "parse_mode": "HTML",
                }
            remaining = bal - amount
        except Exception:
            remaining = None

        confirm = formatters.format_send_confirm(amount, token, recipient, remaining)
        return {**confirm, "parse_mode": "HTML"}

    def execute_send_callback(self, callback_data: str) -> Dict[str, Any]:
        """Execute a confirmed send. Called from async thread pool."""
        try:
            parts = callback_data.split(":")
            if len(parts) != 4:
                return _error("Malformed send callback — please try again.")
            _, amount_str, token, recipient = parts
            amount = float(amount_str)
        except Exception as exc:
            return _error(f"Could not parse send request: {exc}")

        whitelist_err = self._check_send_whitelist(recipient)
        if whitelist_err:
            return {
                "text": formatters.format_send_error(whitelist_err, amount, token, recipient),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        try:
            result = self._ctrl.transfer(token, amount, recipient)
        except Exception as exc:
            logger.error(f"[Telegram] transfer() raised: {exc}", exc_info=True)
            return {
                "text": formatters.format_send_error(str(exc), amount, token, recipient),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        if not result.get("success"):
            err = result.get("error", "Unknown error")
            return {
                "text": formatters.format_send_error(err, amount, token, recipient),
                "reply_markup": formatters.format_buttons(),
                "parse_mode": "HTML",
            }

        tx_hash = result.get("tx_hash", "")
        text, reply_markup = formatters.format_send_receipt(amount, token, recipient, tx_hash)
        return {"text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}

    def _check_send_whitelist(self, recipient: str) -> Optional[str]:
        """Check transfer whitelist. Returns error string if blocked, None if OK."""
        try:
            settings_path = _DATA_DIR / "settings.json"
            if settings_path.exists():
                with open(settings_path) as f:
                    settings = json.load(f)
                whitelist = settings.get("transfer_whitelist", [])
                whitelist_addresses = [e.get("address") for e in whitelist]
                if recipient not in whitelist_addresses:
                    accounts_path = _DATA_DIR / "accounts.json"
                    if accounts_path.exists():
                        with open(accounts_path) as f:
                            accounts = json.load(f)
                        if any(a.get("id") == recipient for a in accounts):
                            return None  # Own account — allowed
                    return f"SAFETY: Recipient {recipient} is not in your transfer whitelist."
        except Exception as exc:
            return f"SAFETY: Whitelist check failed: {exc}"
        return None

    # ------------------------------------------------------------------
    # Governance limit enforcement
    # ------------------------------------------------------------------

    def _check_swap_limits(
        self, from_id: str, to_id: str, amount: float, mode: str
    ) -> Optional[str]:
        """Validate against governance.json safety limits."""
        max_swap_usd     = getattr(self._ctrl.config, "max_swap_amount_usd", 100.0)
        min_hbar_reserve = 5.0

        try:
            gov_path = _DATA_DIR / "governance.json"
            if gov_path.exists():
                with open(gov_path) as f:
                    gov = json.load(f)
                min_hbar_reserve = gov.get("safety_limits", {}).get("min_hbar_reserve", 5.0)
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
            pass

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
            "🤖 <b>AI Mode</b>\n\n"
            "Natural language trading is coming soon.\n\n"
            "Use the buttons or slash commands for now."
        )
        return _reply(reply, with_buttons=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _id_to_symbol(self, token_id: str) -> str:
        """Reverse-lookup a token ID to its display symbol."""
        if not token_id:
            return "???"
        if token_id in ("0.0.0", "HBAR"):
            return "HBAR"
        try:
            tokens_path = _DATA_DIR / "tokens.json"
            if tokens_path.exists():
                with open(tokens_path) as f:
                    tokens = json.load(f)
                if token_id in tokens:
                    return tokens[token_id].get("symbol", token_id)
                for sym, meta in tokens.items():
                    if isinstance(meta, dict) and meta.get("id") == token_id:
                        return meta.get("symbol", sym)
        except Exception:
            pass
        return token_id

    @staticmethod
    def _extract_command(text: str) -> Optional[str]:
        """Extract /command from message text (strips @BotName suffix)."""
        if not text or not text.startswith("/"):
            return None
        word = text.split()[0].lower()
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
    return _reply(formatters.format_error(msg, hint=hint), with_buttons=True)


def _not_implemented(cmd: str) -> Dict[str, Any]:
    return _reply(formatters.format_not_implemented(cmd), with_buttons=True)
