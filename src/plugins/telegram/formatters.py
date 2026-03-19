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
        "/price [TOKEN] \u2014 token prices\n"
        "/status \u2014 full dashboard\n"
        "/history \u2014 recent transactions\n"
        "/send \u2014 transfer tokens\n"
        "/tokens \u2014 supported tokens\n"
        "/gas \u2014 HBAR gas reserve\n"
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
# Price
# ---------------------------------------------------------------------------

def format_prices(prices: Dict[str, float]) -> str:
    """Render a dict of {symbol: usd_price} as an HTML price list."""
    lines = ["\U0001f4ca <b>Token Prices</b>", ""]
    for sym, price in prices.items():
        if price and price > 0:
            if price >= 1000:
                formatted = f"${price:,.2f}"
            elif price >= 1:
                formatted = f"${price:.4f}"
            elif price >= 0.0001:
                formatted = f"${price:.6f}"
            else:
                formatted = f"${price:.8f}"
            lines.append(f"  <b>{_escape(sym)}</b>: <code>{formatted}</code>")
        else:
            lines.append(f"  <b>{_escape(sym)}</b>: <i>unavailable</i>")
    lines.append("")
    lines.append("<i>Prices from SaucerSwap V2 pools.</i>")
    return "\n".join(lines)


def format_price(token: str, price_usd: float) -> str:
    """Render a single token price."""
    if price_usd and price_usd > 0:
        if price_usd >= 1000:
            formatted = f"${price_usd:,.2f}"
        elif price_usd >= 1:
            formatted = f"${price_usd:.4f}"
        else:
            formatted = f"${price_usd:.6f}"
        return f"\U0001f4ca <b>{_escape(token)}</b>: <code>{formatted}</code>"
    return f"\U0001f4ca <b>{_escape(token)}</b>: <i>price unavailable</i>"


# ---------------------------------------------------------------------------
# Status dashboard
# ---------------------------------------------------------------------------

def format_status(balances: Dict[str, float], account_id: str, network: str) -> str:
    """Full dashboard: account info + portfolio summary."""
    lines = [
        "\U0001f7e2 <b>System Status</b>",
        "",
        f"Account: <code>{_escape(account_id)}</code>",
        f"Network: <code>{_escape(network)}</code>",
        f"Controller: <code>online</code>",
        "",
        "<b>Portfolio</b>",
    ]
    if not balances:
        lines.append("  <i>No balances found.</i>")
    else:
        def sort_key(sym):
            return (0 if sym == "HBAR" else 1, sym)
        for sym in sorted(balances.keys(), key=sort_key):
            amount = balances[sym]
            if amount <= 0:
                continue
            if amount >= 1_000:
                formatted = f"{amount:,.2f}"
            elif amount >= 1:
                formatted = f"{amount:.4f}"
            else:
                formatted = f"{amount:.8f}"
            lines.append(f"  <b>{_escape(sym)}</b>: <code>{formatted}</code>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def format_history(records: List[Dict[str, Any]]) -> str:
    """Render recent execution records as a compact list."""
    if not records:
        return (
            "\U0001f4dc <b>Transaction History</b>\n\n"
            "<i>No recent transactions found.</i>"
        )
    lines = ["\U0001f4dc <b>Recent Transactions</b>", ""]
    for r in records:
        ts = r.get("timestamp", r.get("time", ""))[:16] if r.get("timestamp") or r.get("time") else "?"
        from_tok = r.get("from_token", r.get("token_in", "?"))
        to_tok = r.get("to_token", r.get("token_out", ""))
        amount = r.get("amount_in", r.get("amount", 0))
        success = r.get("success", True)
        status_icon = "\u2705" if success else "\u274c"
        if to_tok:
            desc = f"{_fmt_amount(amount)} {_escape(from_tok)} \u2192 {_escape(to_tok)}"
        else:
            desc = f"{_fmt_amount(amount)} {_escape(from_tok)}"
        lines.append(f"{status_icon} <code>{_escape(ts)}</code> {desc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Send flow
# ---------------------------------------------------------------------------

def format_send_prompt() -> str:
    return (
        "\U0001f4e4 <b>Send Tokens</b>\n\n"
        "Type your send command:\n\n"
        "<code>send 5 USDC to 0.0.7949179</code>\n"
        "<code>send 100 HBAR to 0.0.7949179</code>\n\n"
        "\u26a0\ufe0f Only whitelisted recipients are allowed."
    )


def format_send_confirm(
    amount: float,
    token: str,
    recipient: str,
    remaining_balance: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a send confirmation message with Confirm/Cancel inline keyboard."""
    callback_confirm = f"confirm_send:{amount}:{token}:{recipient}"
    lines = [
        "\U0001f4e4 <b>Confirm Send</b>",
        "",
        f"Amount: <b>{_fmt_amount(amount)} {_escape(token)}</b>",
        f"To: <code>{_escape(recipient)}</code>",
    ]
    if remaining_balance is not None:
        lines.append(f"Remaining balance: <code>{_fmt_amount(remaining_balance)} {_escape(token)}</code>")
    lines += [
        "",
        "\u26a0\ufe0f <i>Real transfer. No simulation. Tap Confirm to proceed.</i>",
    ]
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "\u2705 Confirm", "callback_data": callback_confirm},
                {"text": "\u274c Cancel",  "callback_data": "cancel:send"},
            ]
        ]
    }
    return {"text": "\n".join(lines), "reply_markup": keyboard}


def format_send_receipt(amount: float, token: str, recipient: str, tx_hash: str = "") -> str:
    lines = [
        "\u2705 <b>Send Successful!</b>",
        "",
        f"<b>{_fmt_amount(amount)} {_escape(token)}</b> \u2192 <code>{_escape(recipient)}</code>",
    ]
    if tx_hash:
        lines.append(f"Tx: <code>{_escape(tx_hash)}</code>")
    return "\n".join(lines)


def format_send_error(error_msg: str, amount: float = 0, token: str = "", recipient: str = "") -> str:
    text = f"\u274c <b>Send Failed</b>\n\n{_escape(error_msg)}"
    if amount and token:
        text += f"\n\nAmount: <code>{_fmt_amount(amount)} {_escape(token)}</code>"
    if recipient:
        text += f"\nTo: <code>{_escape(recipient)}</code>"
    if "whitelist" in error_msg.lower() or "safety" in error_msg.lower():
        text += "\n\n<i>\U0001f4a1 Add the recipient to your whitelist first: <code>./launch.sh whitelist add 0.0.xxx</code></i>"
    return text


# ---------------------------------------------------------------------------
# Tokens list
# ---------------------------------------------------------------------------

def format_tokens(tokens_data: Dict[str, Any]) -> str:
    """Render supported tokens as a list."""
    lines = ["\U0001f4cb <b>Supported Tokens</b>", ""]
    # Priority symbols first
    priority = ["HBAR", "USDC", "WBTC", "WETH", "SAUCE", "HBARX"]
    shown = set()
    for sym in priority:
        # Find by symbol or key
        meta = tokens_data.get(sym)
        if meta is None:
            for tid, m in tokens_data.items():
                if isinstance(m, dict) and m.get("symbol") == sym:
                    meta = m
                    break
        if meta and isinstance(meta, dict):
            tid = meta.get("id", sym)
            name = meta.get("name", sym)
            lines.append(f"  <b>{_escape(sym)}</b> — <code>{_escape(tid)}</code>")
            shown.add(sym)
    # Add HBAR manually if not in tokens.json
    if "HBAR" not in shown:
        lines.insert(2, "  <b>HBAR</b> — <code>0.0.0</code> (native)")
    lines.append("")
    lines.append("<i>Use symbols in swap commands, e.g. <code>swap 5 USDC for HBAR</code></i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gas status
# ---------------------------------------------------------------------------

def format_gas_status(hbar_balance: float, min_reserve: float = 5.0) -> str:
    """Show HBAR balance and gas reserve status."""
    if hbar_balance >= min_reserve * 3:
        icon = "\u26fd"
        status = "Healthy"
    elif hbar_balance >= min_reserve:
        icon = "\u26a0\ufe0f"
        status = "Adequate"
    else:
        icon = "\U0001f534"
        status = f"LOW — minimum {min_reserve} HBAR required"
    return (
        f"{icon} <b>Gas Status</b>\n\n"
        f"HBAR balance: <code>{_fmt_amount(hbar_balance)}</code>\n"
        f"Min reserve: <code>{min_reserve} HBAR</code>\n"
        f"Status: <b>{status}</b>"
    )


# ---------------------------------------------------------------------------
# Ghost Tunnel — Phase 4
# ---------------------------------------------------------------------------

def format_setup_prompt() -> str:
    """Prompt shown when user runs /setup — opens the Ghost Tunnel Mini App."""
    return (
        "\U0001f510 <b>Secure Key Setup</b>\n\n"
        "Tap the button below to open the secure input panel.\n\n"
        "Your key is sent directly to your server over HTTPS and written "
        "to <code>.env</code>. It is <b>never</b> stored in Telegram chat history.\n\n"
        "<i>\U0001f512 The tunnel validates your Telegram identity before accepting any value.</i>"
    )


def format_key_saved(field: str) -> str:
    """Confirmation message after a key is successfully saved via Ghost Tunnel."""
    safe_field = _escape(field)
    return (
        f"\u2705 <b>{safe_field} saved</b>\n\n"
        "Your key has been written to <code>.env</code>.\n\n"
        "<i>Restart the bot for the new key to take effect: "
        "<code>./launch.sh telegram-start</code></i>"
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
