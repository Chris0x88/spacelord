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

AI lane:
  Everything else → placeholder response for now.

Returns a response dict:
  {
    "text": str,
    "reply_markup": dict | None,   # Telegram InlineKeyboardMarkup
    "parse_mode": str,             # "HTML"
  }
"""

from typing import Dict, Any, Optional

from src.plugins.telegram import formatters


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
    # Phase 2+ commands — placeholder for now
    "swap":      "/swap",
    "send":      "/send",
    "orders":    "/orders",
    "robot":     "/robot",
}


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
        # AI lane placeholder
        return self._ai_lane_placeholder(text)

    def handle_callback(self, callback_data: str, user_id: int) -> Dict[str, Any]:
        """Route a callback_query (inline button press)."""
        cmd = CALLBACK_MAP.get(callback_data)
        if cmd and cmd in FAST_LANE_COMMANDS:
            return self._fast_lane(cmd, user_id)
        # Unmapped callback or Phase 2+ command
        return self._ai_lane_placeholder(callback_data)

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
