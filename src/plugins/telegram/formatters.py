"""
Telegram Output Formatters
==========================
Pure functions: data → HTML-formatted Telegram message strings.
No I/O, no controller calls. Just formatting.

Design principles:
  - Card-style layouts with clear visual hierarchy
  - Contextual inline keyboards (relevant actions per screen)
  - USD values alongside token amounts everywhere
  - Compact monospace blocks for data-heavy views
  - Consistent emoji vocabulary for status at a glance
  - App-like navigation: buttons drive everything, typing is optional
"""

from typing import Dict, Any, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
# Line drawing characters for card-style formatting
# ═══════════════════════════════════════════════════════════════════

_DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━"
_THIN_SEP = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"

# Tradeable tokens available for swap/send (order matters for display)
TRADEABLE_TOKENS = [
    {"sym": "HBAR",     "id": "0.0.0",         "emoji": "⟐"},
    {"sym": "USDC",     "id": "0.0.456858",     "emoji": "💵"},
    {"sym": "USDC[hts]","id": "0.0.1055459",    "emoji": "💲"},
    {"sym": "SAUCE",    "id": "0.0.731861",     "emoji": "🍕"},
    {"sym": "WBTC",     "id": "0.0.10082597",   "emoji": "₿"},
    {"sym": "WETH",     "id": "0.0.9470869",    "emoji": "Ξ"},
    {"sym": "HBARX",    "id": "0.0.834116",     "emoji": "🔷"},
]

# Amount presets per token (common trade sizes)
AMOUNT_PRESETS: Dict[str, List[str]] = {
    "HBAR":      ["10", "25", "50", "100"],
    "USDC":      ["1", "5", "10", "25"],
    "USDC[hts]": ["1", "5", "10", "25"],
    "SAUCE":     ["10", "50", "100", "500"],
    "WBTC":      ["0.0001", "0.0005", "0.001", "0.005"],
    "WETH":      ["0.001", "0.005", "0.01", "0.05"],
    "HBARX":     ["10", "50", "100", "500"],
}


# ═══════════════════════════════════════════════════════════════════
# Main menu — 4×2 action grid
# ═══════════════════════════════════════════════════════════════════

def format_buttons() -> Dict[str, Any]:
    """Return the main 4×2 InlineKeyboardMarkup."""
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "💱 Swap",      "callback_data": "swap"},
            ],
            [
                {"text": "📤 Send",      "callback_data": "send"},
                {"text": "📊 Prices",    "callback_data": "price"},
            ],
            [
                {"text": "🤖 Robot",     "callback_data": "robot"},
                {"text": "⛽ Gas",       "callback_data": "gas"},
            ],
            [
                {"text": "📋 History",   "callback_data": "history"},
                {"text": "🏥 Status",    "callback_data": "health"},
            ],
        ]
    }


# ═══════════════════════════════════════════════════════════════════
# Contextual keyboards
# ═══════════════════════════════════════════════════════════════════

def _portfolio_actions() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💱 Swap Tokens", "callback_data": "swap"},
                {"text": "📤 Send Tokens", "callback_data": "send"},
            ],
            [
                {"text": "📊 Prices", "callback_data": "price"},
                {"text": "🔄 Refresh", "callback_data": "portfolio"},
            ],
            [{"text": "⬅️ Main Menu", "callback_data": "menu"}],
        ]
    }


def _price_actions(token: str = "") -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💱 Swap Tokens", "callback_data": "swap"},
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
            ],
            [
                {"text": "🔄 Refresh", "callback_data": "price"},
                {"text": "⬅️ Main Menu", "callback_data": "menu"},
            ],
        ]
    }


def _post_swap_actions() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Check Balance", "callback_data": "portfolio"},
                {"text": "💱 Swap Again", "callback_data": "swap"},
            ],
            [
                {"text": "📋 History", "callback_data": "history"},
                {"text": "⬅️ Main Menu", "callback_data": "menu"},
            ],
        ]
    }


def _post_send_actions() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Check Balance", "callback_data": "portfolio"},
                {"text": "📤 Send Again", "callback_data": "send"},
            ],
            [
                {"text": "📋 History", "callback_data": "history"},
                {"text": "⬅️ Main Menu", "callback_data": "menu"},
            ],
        ]
    }


def _back_to_menu() -> Dict[str, Any]:
    return {"inline_keyboard": [[{"text": "⬅️ Main Menu", "callback_data": "menu"}]]}


# ═══════════════════════════════════════════════════════════════════
# Welcome / Help
# ═══════════════════════════════════════════════════════════════════

def format_welcome() -> str:
    return (
        "🟢 <b>Pacman Wallet</b>\n"
        f"{_DIVIDER}\n\n"
        "Self-custody Hedera wallet.\n"
        "Live trades · No simulation · SaucerSwap V2\n\n"
        "<b>Quick Actions</b>\n"
        "┌─────────────────────────┐\n"
        "│ 💰 <b>Portfolio</b>  balances + USD    │\n"
        "│ 💱 <b>Swap</b>       trade instantly    │\n"
        "│ 📤 <b>Send</b>       whitelisted only   │\n"
        "│ 📊 <b>Prices</b>     live token prices  │\n"
        "│ 🤖 <b>Robot</b>      BTC rebalancer     │\n"
        "│ ⛽ <b>Gas</b>        HBAR reserve       │\n"
        "│ 📋 <b>History</b>    recent txns        │\n"
        "│ 🏥 <b>Status</b>     system health      │\n"
        "└─────────────────────────┘\n\n"
        "<i>Tap a button below to get started.</i>"
    )


# ═══════════════════════════════════════════════════════════════════
# Portfolio / Balance
# ═══════════════════════════════════════════════════════════════════

def format_balance(
    balances: Dict[str, float],
    account_id: str = "",
    prices: Optional[Dict[str, float]] = None,
) -> Tuple[str, Dict[str, Any]]:
    if not balances:
        text = (
            "💰 <b>Portfolio</b>\n"
            f"{_DIVIDER}\n\n"
            "<i>No token balances found.</i>\n\n"
            "Fund your wallet to get started."
        )
        return text, _portfolio_actions()

    lines = ["💰 <b>Portfolio</b>"]
    if account_id:
        lines.append(f"<code>{account_id}</code>")
    lines.append(_DIVIDER)
    lines.append("")

    def sort_key(sym):
        if sym == "HBAR": return (0, sym)
        if sym == "USDC": return (1, sym)
        return (2, sym)

    total_usd = 0.0
    has_prices = prices and any(v and v > 0 for v in prices.values())

    for sym in sorted(balances.keys(), key=sort_key):
        amount = balances[sym]
        if amount <= 0:
            continue
        formatted = _fmt_amount(amount)

        if has_prices and prices.get(sym):
            usd_val = amount * prices[sym]
            total_usd += usd_val
            lines.append(
                f"  <b>{sym}</b>\n"
                f"  <code>{formatted}</code>  ≈  <b>${usd_val:,.2f}</b>"
            )
        else:
            lines.append(f"  <b>{sym}</b>  <code>{formatted}</code>")
        lines.append("")

    if has_prices and total_usd > 0:
        lines.append(f"{_THIN_SEP}")
        lines.append(f"  📈 <b>Total</b>  ≈  <b>${total_usd:,.2f}</b>")

    return "\n".join(lines), _portfolio_actions()


# ═══════════════════════════════════════════════════════════════════
# Prices
# ═══════════════════════════════════════════════════════════════════

def format_prices(prices: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
    lines = [
        "📊 <b>Live Prices</b>",
        _DIVIDER,
        "",
    ]
    for sym, price in prices.items():
        if price and price > 0:
            lines.append(f"  <b>{_escape(sym)}</b>  <code>{_fmt_price(price)}</code>")
        else:
            lines.append(f"  <b>{_escape(sym)}</b>  <i>—</i>")
    lines.append("")
    lines.append(f"<i>Source: SaucerSwap V2</i>")
    return "\n".join(lines), _price_actions()


def format_price(token: str, price_usd: float) -> Tuple[str, Dict[str, Any]]:
    if price_usd and price_usd > 0:
        text = (
            f"📊 <b>{_escape(token)}</b>\n"
            f"{_THIN_SEP}\n\n"
            f"  Price: <code>{_fmt_price(price_usd)}</code>"
        )
    else:
        text = f"📊 <b>{_escape(token)}</b> — <i>price unavailable</i>"
    return text, _price_actions(token)


# ═══════════════════════════════════════════════════════════════════
# Swap flow — Interactive button-driven
# ═══════════════════════════════════════════════════════════════════

def format_swap_entry() -> Tuple[str, Dict[str, Any]]:
    """Top-level swap screen: pick 'From' token."""
    text = (
        "💱 <b>Swap Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        "Select the token you want to <b>sell</b>:"
    )
    rows = []
    row = []
    for t in TRADEABLE_TOKENS:
        row.append({"text": f"{t['emoji']} {t['sym']}", "callback_data": f"sf:{t['id']}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "⬅️ Main Menu", "callback_data": "menu"}])
    return text, {"inline_keyboard": rows}


def format_swap_pick_to(from_sym: str, from_id: str) -> Tuple[str, Dict[str, Any]]:
    """After picking 'From', pick 'To' token."""
    text = (
        "💱 <b>Swap Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        f"  Selling: <b>{_escape(from_sym)}</b>\n\n"
        "Select the token you want to <b>buy</b>:"
    )
    rows = []
    row = []
    for t in TRADEABLE_TOKENS:
        if t["id"] == from_id:
            continue  # Can't swap to same token
        row.append({"text": f"{t['emoji']} {t['sym']}", "callback_data": f"st:{from_id}:{t['id']}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        {"text": "⬅️ Change From", "callback_data": "swap"},
        {"text": "⬅️ Main Menu", "callback_data": "menu"},
    ])
    return text, {"inline_keyboard": rows}


def format_swap_pick_amount(
    from_sym: str, to_sym: str, from_id: str, to_id: str,
    from_balance: float = 0.0, from_price: float = 0.0,
) -> Tuple[str, Dict[str, Any]]:
    """After picking both tokens, pick an amount."""
    text = (
        "💱 <b>Swap Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        f"  {_escape(from_sym)}  →  {_escape(to_sym)}\n"
    )
    if from_balance > 0:
        bal_str = _fmt_amount(from_balance)
        text += f"  Balance: <code>{bal_str} {_escape(from_sym)}</code>"
        if from_price > 0:
            text += f" ≈ ${from_balance * from_price:,.2f}"
        text += "\n"
    text += "\nSelect amount to sell:"

    presets = AMOUNT_PRESETS.get(from_sym, ["1", "5", "10", "50"])

    rows = []
    row = []
    for amt in presets:
        label = f"{amt} {from_sym}"
        # Show USD estimate if we have price
        if from_price > 0:
            usd = float(amt) * from_price
            if usd >= 1:
                label = f"{amt} ≈${usd:.0f}"
            else:
                label = f"{amt} ≈${usd:.2f}"
        row.append({"text": label, "callback_data": f"sa:{from_id}:{to_id}:{amt}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # Max button (use full balance minus gas reserve if HBAR)
    if from_balance > 0:
        if from_sym == "HBAR":
            max_amt = max(from_balance - 5.0, 0)  # Keep 5 HBAR gas reserve
        else:
            max_amt = from_balance
        if max_amt > 0:
            max_label = f"MAX ({_fmt_amount(max_amt)})"
            rows.append([{"text": max_label, "callback_data": f"sa:{from_id}:{to_id}:{max_amt:.8f}"}])

    rows.append([
        {"text": "⬅️ Change Pair", "callback_data": "swap"},
        {"text": "⬅️ Main Menu", "callback_data": "menu"},
    ])
    return text, {"inline_keyboard": rows}


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
    estimated_out: float = 0.0,
) -> Dict[str, Any]:
    """Build a swap confirmation card with Confirm/Cancel."""
    callback_confirm = f"confirm_swap:{amount}:{from_id}:{to_id}:{mode}"

    lines = [
        "💱 <b>Confirm Swap</b>",
        _DIVIDER,
        "",
        f"  <b>{_fmt_amount(amount)} {_escape(from_symbol)}</b>  →  <b>{_escape(to_symbol)}</b>",
        "",
    ]

    # Estimated output
    if estimated_out > 0:
        lines.append(f"  Est. receive: <code>~{_fmt_amount(estimated_out)} {_escape(to_symbol)}</code>")
        if amount > 0:
            rate = estimated_out / amount
            lines.append(f"  Rate: <code>1 {_escape(from_symbol)} ≈ {_fmt_amount(rate)} {_escape(to_symbol)}</code>")
        lines.append("")

    # Route path
    if route_steps:
        lines.append("  <b>Route</b>")
        for i, step in enumerate(route_steps):
            if step.get("type") == "swap":
                prefix = "└" if i == len(route_steps) - 1 else "├"
                lines.append(
                    f"  {prefix} {_escape(step['from'])} → {_escape(step['to'])}"
                    f"  ({step['fee_pct']:.2f}% fee)"
                )
        lines.append("")

    lines.append(f"{_THIN_SEP}")
    lines.append(f"  LP Fee: <code>{fee_pct * 100:.2f}%</code>")
    lines.append(f"  Est. Gas: <code>~{gas_hbar:.3f} HBAR</code>")
    lines.append("")
    lines.append("⚡ <i>Live trade on Hedera mainnet.</i>")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm Swap", "callback_data": callback_confirm},
                {"text": "❌ Cancel",       "callback_data": "cancel:swap"},
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
) -> Tuple[str, Dict[str, Any]]:
    lines = [
        "✅ <b>Swap Complete</b>",
        _DIVIDER,
        "",
        f"  <b>{_fmt_amount(amount_in)} {_escape(from_symbol)}</b>"
        f"  →  <b>{_fmt_amount(amount_out)} {_escape(to_symbol)}</b>",
        "",
    ]

    if amount_in > 0 and amount_out > 0:
        rate = amount_out / amount_in
        lines.append(f"  Rate: <code>1 {_escape(from_symbol)} = {_fmt_amount(rate)} {_escape(to_symbol)}</code>")

    if gas_cost_hbar:
        gas_str = f"{gas_cost_hbar:.4f} HBAR"
        if gas_cost_usd:
            gas_str += f" (${gas_cost_usd:.4f})"
        lines.append(f"  Gas: <code>{gas_str}</code>")

    if lp_fee:
        lines.append(f"  LP Fee: <code>{lp_fee:.6f} {_escape(from_symbol)}</code>")

    if tx_hash:
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        short_hash = tx_hash[:16] + "…" if len(tx_hash) > 20 else tx_hash
        lines.append(f"  Tx: <code>{_escape(short_hash)}</code>")

    return "\n".join(lines), _post_swap_actions()


def format_swap_error(
    error_msg: str,
    from_symbol: str = "",
    to_symbol: str = "",
    amount: float = 0.0,
) -> str:
    lines = [
        "❌ <b>Swap Failed</b>",
        _DIVIDER,
        "",
        f"  {_escape(error_msg)}",
    ]

    if from_symbol and to_symbol:
        lines.append(f"\n  Pair: {_escape(from_symbol)} → {_escape(to_symbol)}")
    if amount:
        lines.append(f"  Amount: <code>{_fmt_amount(amount)}</code>")

    hints: List[str] = []
    err_lower = error_msg.lower()
    if "route" in err_lower or "no route" in err_lower or "no liquidity" in err_lower:
        hints.append("No path found — pair may lack liquidity")
    if "slippage" in err_lower or "price" in err_lower:
        hints.append("Price moved — try a smaller amount")
    if "balance" in err_lower or "insufficient" in err_lower:
        hints.append("Check /balance to verify your funds")
    if "limit" in err_lower or "exceed" in err_lower:
        hints.append("Max $100 per swap (governance limit)")
    if not hints:
        hints.append("Check /balance and try again")

    lines.append("")
    lines.append(f"{_THIN_SEP}")
    for hint in hints:
        lines.append(f"💡 <i>{hint}</i>")

    return "\n".join(lines)


def format_swap_prompt() -> str:
    """Fallback text-based swap prompt (for typed commands)."""
    return (
        "💱 <b>Swap Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        "Or type your swap:\n\n"
        "  <code>swap 5 USDC for HBAR</code>\n"
        "  <code>buy 100 HBAR</code>\n"
        "  <code>sell 10 HBAR</code>\n\n"
        f"{_THIN_SEP}\n"
        f"📏 Max $100 per swap  •  Max 5% slippage"
    )


# ═══════════════════════════════════════════════════════════════════
# Send flow — Interactive button-driven
# ═══════════════════════════════════════════════════════════════════

def format_send_entry() -> Tuple[str, Dict[str, Any]]:
    """Top-level send screen: pick token to send."""
    text = (
        "📤 <b>Send Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        "Select the token to send:"
    )
    rows = []
    row = []
    for t in TRADEABLE_TOKENS:
        row.append({"text": f"{t['emoji']} {t['sym']}", "callback_data": f"send_tok:{t['id']}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "⬅️ Main Menu", "callback_data": "menu"}])
    return text, {"inline_keyboard": rows}


def format_send_pick_recipient(
    token_sym: str, token_id: str,
    whitelist: List[Dict[str, str]],
    balance: float = 0.0,
) -> Tuple[str, Dict[str, Any]]:
    """After picking token, pick recipient from whitelist."""
    text = (
        "📤 <b>Send Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        f"  Token: <b>{_escape(token_sym)}</b>\n"
    )
    if balance > 0:
        text += f"  Balance: <code>{_fmt_amount(balance)}</code>\n"
    text += "\nSelect recipient:"

    rows = []
    if whitelist:
        for entry in whitelist:
            addr = entry.get("address", "")
            name = entry.get("name", entry.get("nickname", addr[:12]))
            rows.append([{"text": f"👤 {name}  ({addr[-8:]})", "callback_data": f"send_to:{token_id}:{addr}"}])
    else:
        text += "\n\n⚠️ <i>No whitelisted recipients found.</i>\n<i>Add recipients via CLI first.</i>"

    rows.append([
        {"text": "⬅️ Change Token", "callback_data": "send"},
        {"text": "⬅️ Main Menu", "callback_data": "menu"},
    ])
    return text, {"inline_keyboard": rows}


def format_send_pick_amount(
    token_sym: str, token_id: str, recipient: str,
    recipient_name: str = "",
    balance: float = 0.0, price: float = 0.0,
) -> Tuple[str, Dict[str, Any]]:
    """After picking recipient, pick amount."""
    display_to = recipient_name or recipient
    text = (
        "📤 <b>Send Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        f"  Token: <b>{_escape(token_sym)}</b>\n"
        f"  To: <b>{_escape(display_to)}</b>\n"
        f"       <code>{_escape(recipient)}</code>\n"
    )
    if balance > 0:
        bal_str = _fmt_amount(balance)
        text += f"  Balance: <code>{bal_str}</code>"
        if price > 0:
            text += f" ≈ ${balance * price:,.2f}"
        text += "\n"
    text += "\nSelect amount:"

    presets = AMOUNT_PRESETS.get(token_sym, ["1", "5", "10", "50"])
    rows = []
    row = []
    for amt in presets:
        label = f"{amt} {token_sym}"
        if price > 0:
            usd = float(amt) * price
            if usd >= 1:
                label = f"{amt} ≈${usd:.0f}"
            else:
                label = f"{amt} ≈${usd:.2f}"
        row.append({"text": label, "callback_data": f"send_amt:{token_id}:{recipient}:{amt}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # Max button
    if balance > 0:
        max_amt = balance
        if token_sym == "HBAR":
            max_amt = max(balance - 5.0, 0)
        if max_amt > 0:
            rows.append([{"text": f"MAX ({_fmt_amount(max_amt)})", "callback_data": f"send_amt:{token_id}:{recipient}:{max_amt:.8f}"}])

    rows.append([
        {"text": "⬅️ Change Recipient", "callback_data": f"send_tok:{token_id}"},
        {"text": "⬅️ Main Menu", "callback_data": "menu"},
    ])
    return text, {"inline_keyboard": rows}


def format_send_confirm(
    amount: float,
    token: str,
    recipient: str,
    remaining_balance: Optional[float] = None,
    recipient_name: str = "",
) -> Dict[str, Any]:
    callback_confirm = f"confirm_send:{amount}:{token}:{recipient}"
    display_to = recipient_name or recipient
    lines = [
        "📤 <b>Confirm Transfer</b>",
        _DIVIDER,
        "",
        f"  Amount: <b>{_fmt_amount(amount)} {_escape(token)}</b>",
        f"  To: <b>{_escape(display_to)}</b>",
        f"       <code>{_escape(recipient)}</code>",
    ]
    if remaining_balance is not None:
        lines.append(f"  Remaining: <code>{_fmt_amount(remaining_balance)} {_escape(token)}</code>")
    lines += [
        "",
        f"{_THIN_SEP}",
        "🔒 Whitelisted recipient",
        "⚡ <i>Live transfer on Hedera mainnet.</i>",
    ]
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm Send", "callback_data": callback_confirm},
                {"text": "❌ Cancel",       "callback_data": "cancel:send"},
            ]
        ]
    }
    return {"text": "\n".join(lines), "reply_markup": keyboard}


def format_send_receipt(
    amount: float, token: str, recipient: str, tx_hash: str = ""
) -> Tuple[str, Dict[str, Any]]:
    lines = [
        "✅ <b>Transfer Complete</b>",
        _DIVIDER,
        "",
        f"  <b>{_fmt_amount(amount)} {_escape(token)}</b>  →  <code>{_escape(recipient)}</code>",
    ]
    if tx_hash:
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        short_hash = tx_hash[:16] + "…" if len(tx_hash) > 20 else tx_hash
        lines.append(f"  Tx: <code>{_escape(short_hash)}</code>")
    return "\n".join(lines), _post_send_actions()


def format_send_error(
    error_msg: str, amount: float = 0, token: str = "", recipient: str = ""
) -> str:
    lines = [
        "❌ <b>Transfer Failed</b>",
        _DIVIDER,
        "",
        f"  {_escape(error_msg)}",
    ]
    if amount and token:
        lines.append(f"\n  Amount: <code>{_fmt_amount(amount)} {_escape(token)}</code>")
    if recipient:
        lines.append(f"  To: <code>{_escape(recipient)}</code>")
    if "whitelist" in error_msg.lower() or "safety" in error_msg.lower():
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        lines.append("💡 <i>Add recipient to whitelist first via CLI</i>")
    return "\n".join(lines)


def format_send_prompt() -> str:
    return (
        "📤 <b>Send Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        "Or type your transfer:\n\n"
        "  <code>send 5 USDC to 0.0.XXXXXXX</code>\n"
        "  <code>send 100 HBAR to 0.0.XXXXXXX</code>\n\n"
        f"{_THIN_SEP}\n"
        "🔒 Only whitelisted recipients allowed.\n"
        "📏 Hedera IDs only (0.0.xxx) — no EVM."
    )


# ═══════════════════════════════════════════════════════════════════
# Status / Health
# ═══════════════════════════════════════════════════════════════════

def format_status(
    balances: Dict[str, float],
    account_id: str,
    network: str,
    prices: Optional[Dict[str, float]] = None,
) -> Tuple[str, Dict[str, Any]]:
    lines = [
        "🏥 <b>System Status</b>",
        _DIVIDER,
        "",
        f"  Account: <code>{_escape(account_id)}</code>",
        f"  Network: <code>{_escape(network)}</code>",
        f"  Engine:  <code>online ✓</code>",
        "",
    ]

    if balances:
        lines.append(f"  <b>Holdings</b>")
        total_usd = 0.0
        has_prices = prices and any(v and v > 0 for v in prices.values())
        for sym in sorted(balances.keys(), key=lambda s: (0 if s == "HBAR" else 1, s)):
            amount = balances[sym]
            if amount <= 0:
                continue
            if has_prices and prices.get(sym):
                usd_val = amount * prices[sym]
                total_usd += usd_val
                lines.append(f"  ├ {sym}: <code>{_fmt_amount(amount)}</code> ≈ ${usd_val:,.2f}")
            else:
                lines.append(f"  ├ {sym}: <code>{_fmt_amount(amount)}</code>")
        if has_prices and total_usd > 0:
            lines.append(f"  └ <b>Total ≈ ${total_usd:,.2f}</b>")
    else:
        lines.append("  <i>No balances found.</i>")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "⛽ Gas", "callback_data": "gas"},
            ],
            [
                {"text": "🤖 Robot", "callback_data": "robot"},
                {"text": "⬅️ Main Menu", "callback_data": "menu"},
            ],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Gas status
# ═══════════════════════════════════════════════════════════════════

def format_gas_status(hbar_balance: float, min_reserve: float = 5.0) -> Tuple[str, Dict[str, Any]]:
    if hbar_balance >= min_reserve * 3:
        icon, status = "🟢", "Healthy"
        bar = "█████████░"
    elif hbar_balance >= min_reserve * 1.5:
        icon, status = "🟡", "Adequate"
        bar = "██████░░░░"
    elif hbar_balance >= min_reserve:
        icon, status = "🟠", "Low"
        bar = "███░░░░░░░"
    else:
        icon, status = "🔴", "CRITICAL"
        bar = "█░░░░░░░░░"

    text = (
        f"⛽ <b>Gas Reserve</b>\n"
        f"{_DIVIDER}\n\n"
        f"  HBAR: <code>{_fmt_amount(hbar_balance)}</code>\n"
        f"  Reserve: <code>{min_reserve} HBAR</code>\n\n"
        f"  {icon} <b>{status}</b>\n"
        f"  <code>[{bar}]</code>"
    )

    if hbar_balance < min_reserve:
        text += f"\n\n⚠️ <i>Need {min_reserve - hbar_balance:.2f} more HBAR for gas.</i>"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "💱 Buy HBAR", "callback_data": "swap"},
            ],
            [{"text": "⬅️ Main Menu", "callback_data": "menu"}],
        ]
    }
    return text, keyboard


# ═══════════════════════════════════════════════════════════════════
# History
# ═══════════════════════════════════════════════════════════════════

def format_history(records: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    if not records:
        text = (
            "📋 <b>Transaction History</b>\n"
            f"{_DIVIDER}\n\n"
            "<i>No recent transactions.</i>"
        )
        return text, _back_to_menu()

    lines = [
        "📋 <b>Recent Transactions</b>",
        _DIVIDER,
        "",
    ]
    for r in records:
        ts = r.get("timestamp", r.get("time", ""))[:16] if r.get("timestamp") or r.get("time") else "?"
        from_tok = r.get("from_token", r.get("token_in", "?"))
        to_tok = r.get("to_token", r.get("token_out", ""))
        amount = r.get("amount_in", r.get("amount", 0))
        success = r.get("success", True)
        icon = "✅" if success else "❌"
        if to_tok:
            desc = f"{_fmt_amount(amount)} {_escape(from_tok)} → {_escape(to_tok)}"
        else:
            desc = f"{_fmt_amount(amount)} {_escape(from_tok)}"
        lines.append(f"  {icon} <code>{_escape(ts)}</code>")
        lines.append(f"     {desc}")
        lines.append("")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "💱 Swap", "callback_data": "swap"},
            ],
            [{"text": "⬅️ Main Menu", "callback_data": "menu"}],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Tokens list
# ═══════════════════════════════════════════════════════════════════

def format_tokens(tokens_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    lines = [
        "📋 <b>Supported Tokens</b>",
        _DIVIDER,
        "",
    ]
    priority = ["HBAR", "USDC", "WBTC", "WETH", "SAUCE", "HBARX"]
    shown = set()
    for sym in priority:
        meta = tokens_data.get(sym)
        if meta is None:
            for tid, m in tokens_data.items():
                if isinstance(m, dict) and m.get("symbol") == sym:
                    meta = m
                    break
        if meta and isinstance(meta, dict):
            tid = meta.get("id", sym)
            lines.append(f"  <b>{_escape(sym)}</b>  <code>{_escape(tid)}</code>")
            shown.add(sym)
    if "HBAR" not in shown:
        lines.insert(3, "  <b>HBAR</b>  <code>0.0.0</code>  (native)")
    lines.append("")
    lines.append(f"{_THIN_SEP}")
    lines.append("<i>Tap Swap to trade any of these tokens.</i>")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💱 Swap", "callback_data": "swap"},
                {"text": "📊 Prices", "callback_data": "price"},
            ],
            [{"text": "⬅️ Main Menu", "callback_data": "menu"}],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Robot status
# ═══════════════════════════════════════════════════════════════════

def format_robot_status(
    robot_account: str = "",
    funded: bool = False,
    portfolio_usd: float = 0.0,
    btc_pct: float = 0.0,
    target_pct: float = 0.0,
    last_rebalance: str = "",
    status: str = "unknown",
) -> Tuple[str, Dict[str, Any]]:
    if status == "running":
        icon = "🟢"
    elif status == "idle":
        icon = "🟡"
    else:
        icon = "⚪"

    lines = [
        "🤖 <b>BTC Rebalancer</b>",
        _DIVIDER,
        "",
        f"  Status: {icon} <b>{_escape(status.title())}</b>",
    ]

    if robot_account:
        lines.append(f"  Account: <code>{_escape(robot_account)}</code>")

    if not funded or portfolio_usd < 5.0:
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        lines.append("⚠️ <i>Robot needs funding (min $5 USDC + WBTC)</i>")
        lines.append("<i>Fund the robot account to enable auto-rebalancing.</i>")
    else:
        lines.append(f"  Portfolio: <b>${portfolio_usd:,.2f}</b>")
        if btc_pct > 0:
            lines.append(f"  BTC allocation: <code>{btc_pct:.1f}%</code> (target: {target_pct:.1f}%)")
        if last_rebalance:
            lines.append(f"  Last rebalance: <code>{_escape(last_rebalance[:16])}</code>")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "🏥 Status", "callback_data": "health"},
            ],
            [{"text": "⬅️ Main Menu", "callback_data": "menu"}],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Ghost Tunnel — Secure key setup
# ═══════════════════════════════════════════════════════════════════

def format_setup_prompt() -> str:
    return (
        "🔐 <b>Secure Key Setup</b>\n"
        f"{_DIVIDER}\n\n"
        "Tap the button below to open the secure input panel.\n\n"
        "  🔒 Sent over HTTPS directly to your server\n"
        "  🔒 Written to <code>.env</code> — never in chat\n"
        "  🔒 Telegram identity verified via HMAC\n\n"
        f"{_THIN_SEP}\n"
        "<i>Your key is never stored in Telegram history.</i>"
    )


def format_key_saved(field: str) -> str:
    return (
        f"✅ <b>{_escape(field)} saved</b>\n"
        f"{_DIVIDER}\n\n"
        "Key written to <code>.env</code> successfully.\n\n"
        "<i>Restart the bot for the new key to take effect.</i>"
    )


# ═══════════════════════════════════════════════════════════════════
# Error / Generic
# ═══════════════════════════════════════════════════════════════════

def format_error(error_msg: str, hint: str = "") -> str:
    text = f"❌ <b>Error</b>\n{_THIN_SEP}\n\n{_escape(error_msg)}"
    if hint:
        text += f"\n\n💡 <i>{_escape(hint)}</i>"
    return text


def format_not_implemented(feature: str) -> str:
    return (
        f"🚧 <b>{_escape(feature)}</b>\n"
        f"{_THIN_SEP}\n\n"
        "This feature is coming soon.\n"
        "Use the CLI for now: <code>./launch.sh</code>"
    )


def format_unauthorized() -> str:
    return (
        "🔒 <b>Access Denied</b>\n"
        f"{_THIN_SEP}\n\n"
        "Your Telegram ID is not authorized.\n"
        "Contact the wallet owner to request access."
    )


# ═══════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════

def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _fmt_amount(amount: float) -> str:
    if amount >= 1_000:
        return f"{amount:,.2f}"
    elif amount >= 1:
        return f"{amount:.4f}"
    elif amount >= 0.001:
        return f"{amount:.6f}"
    else:
        return f"{amount:.8f}"


def _fmt_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    elif price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"
