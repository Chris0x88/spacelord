"""
Telegram Output Formatters
==========================
Pure functions: data → HTML-formatted Telegram message strings.
No I/O, no controller calls. Just formatting.
"""

from typing import Dict, Any, List, Optional


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
# Swap flow — Phase 2
# ---------------------------------------------------------------------------

def format_swap_prompt() -> str:
    """Prompt the user to type their swap command."""
    return (
        "\U0001f4b1 <b>Swap Tokens</b>\n\n"
        "Type your swap command:\n\n"
        "<code>swap 5 USDC for HBAR</code>\n"
        "<code>swap 100 HBAR for USDC</code>\n"
        "<code>buy 5 HBAR</code> \u2014 buys with USDC\n"
        "<code>sell 10 HBAR</code> \u2014 sells for USDC"
    )


def format_swap_confirm(
    amount: float,
    from_symbol: str,
    to_symbol: str,
    from_id: str,
    to_id: str,
    mode: str,
    fee_pct: float,
    gas_hbar: float,
    route_steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a swap confirmation message with Confirm/Cancel inline keyboard.

    Returns a dict: {text, reply_markup}
    """
    callback_confirm = f"confirm_swap:{amount}:{from_id}:{to_id}:{mode}"

    if mode == "exact_in":
        direction = (
            f"<b>{_fmt_amount(amount)} {_escape(from_symbol)}</b>"
            f" \u2192 {_escape(to_symbol)}"
        )
    else:
        direction = (
            f"{_escape(from_symbol)}"
            f" \u2192 <b>{_fmt_amount(amount)} {_escape(to_symbol)}</b>"
        )

    lines = ["\U0001f4b1 <b>Confirm Swap</b>", "", direction, ""]

    for step in route_steps:
        if step.get("type") == "swap":
            lines.append(
                f"  \u21b3 {_escape(step['from'])} \u2192 {_escape(step['to'])}"
                f" ({step['fee_pct']:.2f}%)"
            )

    if route_steps:
        lines.append("")

    lines += [
        f"LP fee: <code>{fee_pct * 100:.2f}%</code>",
        f"Est. gas: <code>~{gas_hbar:.3f} HBAR</code>",
        "",
        "\u26a0\ufe0f <i>Real trade. No simulation. Tap Confirm to proceed.</i>",
    ]

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "\u2705 Confirm", "callback_data": callback_confirm},
                {"text": "\u274c Cancel",  "callback_data": "cancel:swap"},
            ]
        ]
    }
    return {"text": "\n".join(lines), "reply_markup": keyboard}


def format_swap_receipt(
    tx_hash: str,
    amount_in: float,
    amount_out: float,
    from_symbol: str,
    to_symbol: str,
    gas_cost_hbar: float = 0.0,
    gas_cost_usd: float = 0.0,
    lp_fee: float = 0.0,
) -> str:
    """HTML receipt shown after a successful swap."""
    lines = [
        "\u2705 <b>Swap Successful!</b>",
        "",
        (
            f"<b>{_fmt_amount(amount_in)} {_escape(from_symbol)}</b>"
            f" \u2192 <b>{_fmt_amount(amount_out)} {_escape(to_symbol)}</b>"
        ),
        "",
    ]

    if tx_hash:
        lines.append(f"Tx: <code>{_escape(tx_hash)}</code>")
    if gas_cost_hbar:
        if gas_cost_usd:
            lines.append(
                f"Gas: <code>{gas_cost_hbar:.4f} HBAR"
                f" (${gas_cost_usd:.4f})</code>"
            )
        else:
            lines.append(f"Gas: <code>{gas_cost_hbar:.4f} HBAR</code>")
    if lp_fee:
        lines.append(
            f"LP fee paid: <code>{lp_fee:.6f} {_escape(from_symbol)}</code>"
        )

    return "\n".join(lines)


def format_swap_error(
    error_msg: str,
    from_symbol: str = "",
    to_symbol: str = "",
    amount: float = 0.0,
) -> str:
    """Swap error message with contextual recovery hints."""
    text = f"\u274c <b>Swap Failed</b>\n\n{_escape(error_msg)}"

    if from_symbol and to_symbol:
        text += f"\n\nPair: {_escape(from_symbol)} \u2192 {_escape(to_symbol)}"
    if amount:
        text += f"\nAmount: <code>{_fmt_amount(amount)}</code>"

    hints: List[str] = []
    err_lower = error_msg.lower()
    if "route" in err_lower or "no route" in err_lower or "no liquidity" in err_lower:
        hints.append("No path found \u2014 pair may have low liquidity.")
    if "slippage" in err_lower or "price" in err_lower:
        hints.append("Price moved. Try a smaller amount.")
    if "balance" in err_lower or "insufficient" in err_lower:
        hints.append("Check /balance to verify your funds.")
    if "limit" in err_lower or "exceed" in err_lower:
        hints.append("Max $100 per swap (governance limit).")
    if not hints:
        hints.append("Try /balance to verify funds.")

    text += "\n\n<i>\U0001f4a1 " + " | ".join(hints) + "</i>"
    return text


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


def _fmt_amount(amount: float) -> str:
    """Format a token amount for compact display."""
    if amount >= 1_000:
        return f"{amount:,.2f}"
    elif amount >= 1:
        return f"{amount:.4f}"
    elif amount >= 0.001:
        return f"{amount:.6f}"
    else:
        return f"{amount:.8f}"
