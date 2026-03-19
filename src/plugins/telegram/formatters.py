"""
Telegram Output Formatters
==========================
Pure functions: data → HTML-formatted Telegram message strings.
No I/O, no controller calls. Just formatting.
"""

from typing import Dict, Any


# ---------------------------------------------------------------------------
# Inline keyboard — 4x2 grid matching SOUL.md
# ---------------------------------------------------------------------------

def format_buttons() -> Dict[str, Any]:
    """Return a Telegram InlineKeyboardMarkup dict (ready for Bot.send_message)."""
    return {
        "inline_keyboard": [
            [
                {"text": "\U0001f4b0 Portfolio", "callback_data": "portfolio"},
                {"text": "\U0001f4b1 Swap",      "callback_data": "swap"},
            ],
            [
                {"text": "\U0001f4e4 Send",       "callback_data": "send"},
                {"text": "\U0001f4ca Prices",     "callback_data": "price"},
            ],
            [
                {"text": "\U0001f4cb Orders",     "callback_data": "orders"},
                {"text": "\U0001f916 Robot",      "callback_data": "robot"},
            ],
            [
                {"text": "\u26fd Gas",            "callback_data": "gas"},
                {"text": "\U0001f3e5 Health",     "callback_data": "health"},
            ],
        ]
    }


# ---------------------------------------------------------------------------
# Portfolio / balance
# ---------------------------------------------------------------------------

def format_balance(balances: Dict[str, float], account_id: str = "") -> str:
    """
    Render a balance dict as an HTML portfolio table.

    Args:
        balances: {symbol: amount}  (already price-resolved by controller)
        account_id: Hedera account ID for display header

    Returns:
        HTML string safe for Telegram parse_mode=HTML
    """
    if not balances:
        return (
            "<b>\U0001f4b0 Portfolio</b>\n\n"
            "<i>No token balances found.</i>\n\n"
            "Fund your wallet to get started."
        )

    lines = [f"<b>\U0001f4b0 Portfolio</b>"]
    if account_id:
        lines.append(f"<code>{account_id}</code>")
    lines.append("")

    # Sort: HBAR first, then alphabetical
    def sort_key(sym):
        return (0 if sym == "HBAR" else 1, sym)

    for sym in sorted(balances.keys(), key=sort_key):
        amount = balances[sym]
        if amount <= 0:
            continue
        # Format numbers cleanly
        if amount >= 1_000:
            formatted = f"{amount:,.2f}"
        elif amount >= 1:
            formatted = f"{amount:.4f}"
        else:
            formatted = f"{amount:.8f}"
        lines.append(f"  <b>{sym}</b>: <code>{formatted}</code>")

    lines.append("")
    lines.append("<i>Use the buttons below to act on your portfolio.</i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def format_error(error_msg: str, hint: str = "") -> str:
    """
    User-friendly error message with optional recovery hint.
    """
    text = f"\u274c <b>Error</b>\n\n{_escape(error_msg)}"
    if hint:
        text += f"\n\n<i>\U0001f4a1 {_escape(hint)}</i>"
    return text


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------

def format_not_implemented(feature: str) -> str:
    return (
        f"\U0001f6a7 <b>{_escape(feature)}</b>\n\n"
        "This feature is coming in a future update.\n"
        "Use the CLI for now: <code>./launch.sh</code>"
    )


def format_unauthorized() -> str:
    return (
        "\U0001f512 <b>Access Denied</b>\n\n"
        "Your Telegram ID is not authorized to use this bot.\n"
        "Contact the wallet owner to request access."
    )


def format_welcome() -> str:
    return (
        "\U0001f44b <b>Welcome to Pacman</b>\n\n"
        "Your self-custody Hedera wallet assistant.\n\n"
        "Use the buttons below or type a slash command:\n"
        "/balance \u2014 portfolio overview\n"
        "/price \u2014 token prices\n"
        "/status \u2014 system status\n"
        "/health \u2014 connectivity check"
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    """Minimal HTML escaping for user-facing strings."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
