"""
Telegram Output Formatters  [SHARED — used by both wallet bot AND agent fast-lane]
==========================
Pure functions: data → HTML-formatted Telegram message strings.
No I/O, no controller calls. Just formatting.

Design principles (matching Trojan/BONKbot standards):
  - Clean visual hierarchy with thin line separators (not heavy dividers)
  - Compact data display: token + amount + USD value on minimal lines
  - Smart amount presets: USD-denominated ($5, $10, $20, etc.)
  - Custom amount buttons on every amount picker
  - Professional emoji vocabulary (minimal, focused)
  - Monospace numbers and addresses for clarity
  - Status indicators with color dots and progress bars
  - Compact navigation: ↩ Back, 🏠 Menu, minimal button text
  - Exchange rates prominently displayed in swap screens
  - HashScan links for all transactions
"""

from typing import Dict, Any, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
# Separators: thin lines for visual hierarchy, not heavy dividers
# ═══════════════════════════════════════════════════════════════════

_HEADER_SEP = "┌─────────────────────────"
_THIN_SEP = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"

# Tradeable tokens available for swap/send (order matters for display)
TRADEABLE_TOKENS = [
    {"sym": "HBAR",     "id": "0.0.0",         "emoji": "⟐"},
    {"sym": "USDC",     "id": "0.0.456858",     "emoji": "💵"},
    {"sym": "USDC[hts]","id": "0.0.1055459",    "emoji": "💲"},
    {"sym": "SAUCE",    "id": "0.0.731861",     "emoji": "🍕"},
    {"sym": "WBTC",     "id": "0.0.10082597",   "emoji": "₿"},
    {"sym": "WETH",     "id": "0.0.9770617",    "emoji": "Ξ"},
    {"sym": "HBARX",    "id": "0.0.834116",     "emoji": "⬟"},
]

# Quick lookup: symbol → emoji
_SYM_EMOJI = {t["sym"]: t["emoji"] for t in TRADEABLE_TOKENS}
_SYM_EMOJI["HBAR"] = "⟐"  # ensure native HBAR covered

# Amount presets: USD-denominated for stablecoins, token amounts for others
# Users think in USD, so show what they think in
AMOUNT_PRESETS: Dict[str, List[str]] = {
    "HBAR":      ["5", "15", "30", "50"],      # ~$0.40, $1.20, $2.40, $4 at ~$0.08
    "USDC":      ["5", "10", "20", "50"],      # Direct USD amounts
    "USDC[hts]": ["5", "10", "20", "50"],      # Direct USD amounts
    "SAUCE":     ["10", "50", "100", "500"],
    "WBTC":      ["0.0001", "0.0005", "0.001", "0.005"],
    "WETH":      ["0.01", "0.05", "0.1", "0.25"],
    "HBARX":     ["10", "50", "100", "500"],
}

# HashScan base URL for transaction links
_HASHSCAN_TX = "https://hashscan.io/mainnet/transaction/"


# ═══════════════════════════════════════════════════════════════════
# Main menu — compact action grid
# ═══════════════════════════════════════════════════════════════════

def format_buttons() -> Dict[str, Any]:
    """Return the main action grid InlineKeyboardMarkup."""
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "💱 Swap",      "callback_data": "swap"},
                {"text": "📤 Send",      "callback_data": "send"},
            ],
            [
                {"text": "📊 Prices",    "callback_data": "price"},
                {"text": "⛽ Gas",       "callback_data": "gas"},
                {"text": "🤖 Robot",     "callback_data": "robot"},
            ],
            [
                {"text": "📋 History",   "callback_data": "history"},
                {"text": "🏥 Status",    "callback_data": "health"},
                {"text": "🔐 Setup",     "callback_data": "setup"},
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
                {"text": "💱 Swap", "callback_data": "swap"},
                {"text": "📤 Send", "callback_data": "send"},
            ],
            [
                {"text": "📊 Prices", "callback_data": "price"},
                {"text": "🔄 Refresh", "callback_data": "portfolio"},
            ],
            [{"text": "🏠 Menu", "callback_data": "menu"}],
        ]
    }


def _price_actions(token: str = "") -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💱 Swap", "callback_data": "swap"},
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
            ],
            [
                {"text": "🔄 Refresh", "callback_data": "price"},
                {"text": "🏠 Menu", "callback_data": "menu"},
            ],
        ]
    }


def _post_swap_actions() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "💱 Swap Again", "callback_data": "swap"},
            ],
            [
                {"text": "📋 History", "callback_data": "history"},
                {"text": "🏠 Menu", "callback_data": "menu"},
            ],
        ]
    }


def _post_send_actions() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "📤 Send Again", "callback_data": "send"},
            ],
            [
                {"text": "📋 History", "callback_data": "history"},
                {"text": "🏠 Menu", "callback_data": "menu"},
            ],
        ]
    }


def _back_to_menu() -> Dict[str, Any]:
    return {"inline_keyboard": [[{"text": "🏠 Menu", "callback_data": "menu"}]]}


# ═══════════════════════════════════════════════════════════════════
# Home screen (replaces old format_welcome)
# ═══════════════════════════════════════════════════════════════════

def format_home(
    total_usd: float = 0.0,
    hbar_balance: float = 0.0,
    hbar_reserve: float = 5.0,
) -> str:
    """Home screen with optional balance summary."""
    lines = [
        "🏠 <b>Space Lord Wallet</b>",
        _THIN_SEP,
        "",
    ]

    # Balance summary if available
    if total_usd > 0:
        lines.append(f"  💼 Portfolio Value")
        lines.append(f"  <code>${total_usd:,.2f}</code>")
        lines.append("")

    if hbar_balance > 0:
        if hbar_balance >= hbar_reserve * 3:
            gas_icon = "🟢"
            status = "Healthy"
        elif hbar_balance >= hbar_reserve:
            gas_icon = "🟡"
            status = "Adequate"
        else:
            gas_icon = "🔴"
            status = "Low"
        lines.append(f"  {gas_icon} Gas Reserve")
        lines.append(f"  <code>{_fmt_amount(hbar_balance)} HBAR</code> — {status}")
        lines.append("")

    lines.append(f"{_THIN_SEP}")
    lines.append("  <i>Self-custody · Hedera Mainnet</i>")
    lines.append("")
    return "\n".join(lines)


def format_welcome() -> str:
    """Legacy wrapper — returns home screen without balance data."""
    return format_home()


# ═══════════════════════════════════════════════════════════════════
# Portfolio / Balance
# ═══════════════════════════════════════════════════════════════════

def _format_account_section(
    balances: Dict[str, float],
    account_id: str,
    nickname: str,
    icon: str,
    prices: Optional[Dict[str, float]] = None,
) -> Tuple[List[str], float]:
    """Format one account's holdings. Returns (lines, total_usd)."""

    def sort_key(sym):
        if sym == "HBAR": return (0, sym)
        if sym == "USDC": return (1, sym)
        return (2, sym)

    lines = [f"  {icon} <b>{nickname}</b> — <code>{account_id}</code>"]
    total_usd = 0.0
    has_prices = prices and any(v and v > 0 for v in prices.values())
    has_tokens = False

    for sym in sorted(balances.keys(), key=sort_key):
        amount = balances[sym]
        if amount <= 0:
            continue
        has_tokens = True
        formatted = _fmt_amount(amount)
        emoji = _SYM_EMOJI.get(sym, "·")

        if has_prices and prices.get(sym):
            usd_val = amount * prices[sym]
            total_usd += usd_val
            lines.append(f"    {emoji} {sym:<6} <code>{formatted:>12}</code>  ≈ ${usd_val:>8,.2f}")
        else:
            lines.append(f"    {emoji} {sym:<6} <code>{formatted:>12}</code>")

    if not has_tokens:
        lines.append("    <i>No balances</i>")
    elif has_prices and total_usd > 0:
        lines.append(f"    💼 Subtotal  <b>${total_usd:,.2f}</b>")

    return lines, total_usd


def format_balance(
    balances: Dict[str, float],
    account_id: str = "",
    prices: Optional[Dict[str, float]] = None,
) -> Tuple[str, Dict[str, Any]]:
    if not balances:
        text = (
            "💰 <b>Portfolio</b>\n"
            f"{_THIN_SEP}\n\n"
            "<i>No balances yet. Deposit to get started.</i>"
        )
        return text, _portfolio_actions()

    lines = ["💰 <b>Portfolio</b>"]
    if account_id:
        lines.append(f"<code>{account_id}</code>")
    lines.append(_THIN_SEP)

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
        emoji = _SYM_EMOJI.get(sym, "·")

        if has_prices and prices.get(sym):
            usd_val = amount * prices[sym]
            total_usd += usd_val
            lines.append(f"  {emoji} {sym:<6} <code>{formatted:>12}</code>  ≈ ${usd_val:>8,.2f}")
        else:
            lines.append(f"  {emoji} {sym:<6} <code>{formatted:>12}</code>")

    if has_prices and total_usd > 0:
        lines.append(_THIN_SEP)
        lines.append(f"  💼 <b>Total</b>  <b>${total_usd:,.2f}</b>")

    return "\n".join(lines), _portfolio_actions()


def format_multi_account_balance(
    accounts: List[Dict[str, Any]],
    prices: Optional[Dict[str, float]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Format portfolio across ALL accounts in one view.

    Each entry in *accounts*:
        {"account_id": "0.0.xxx", "nickname": "...", "icon": "👤",
         "balances": {"HBAR": 55.0, "USDC": 6.5, ...}}
    """
    if not accounts:
        text = (
            "💰 <b>Portfolio</b>\n"
            f"{_THIN_SEP}\n\n"
            "<i>No accounts configured.</i>"
        )
        return text, _portfolio_actions()

    lines = ["💰 <b>Portfolio — All Accounts</b>", _THIN_SEP]
    grand_total = 0.0

    for acct in accounts:
        section_lines, subtotal = _format_account_section(
            balances=acct.get("balances", {}),
            account_id=acct.get("account_id", ""),
            nickname=acct.get("nickname", "Account"),
            icon=acct.get("icon", "💼"),
            prices=prices,
        )
        lines.extend(section_lines)
        lines.append("")  # spacer between accounts
        grand_total += subtotal

    has_prices = prices and any(v and v > 0 for v in prices.values())
    if has_prices and grand_total > 0:
        lines.append(_THIN_SEP)
        lines.append(f"  💼 <b>Total (all accounts)</b>  <b>${grand_total:,.2f}</b>")

    return "\n".join(lines), _portfolio_actions()


# ═══════════════════════════════════════════════════════════════════
# Prices
# ═══════════════════════════════════════════════════════════════════

def format_prices(prices: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
    lines = [
        "📊 <b>Live Prices</b>",
        _THIN_SEP,
    ]

    def sort_prices(sym):
        if sym == "HBAR": return (0, sym)
        if sym == "USDC": return (1, sym)
        return (2, sym)

    for sym in sorted(prices.keys(), key=sort_prices):
        price = prices[sym]
        emoji = _SYM_EMOJI.get(sym, "·")
        if price and price > 0:
            lines.append(f"  {emoji} {sym:<6} <code>{_fmt_price(price):>10}</code>")
        else:
            lines.append(f"  {emoji} {sym:<6} <i>—</i>")

    lines.append(_THIN_SEP)
    lines.append("  <i>SaucerSwap V2 · Real-time</i>")
    return "\n".join(lines), _price_actions()


def format_price(token: str, price_usd: float) -> Tuple[str, Dict[str, Any]]:
    emoji = _SYM_EMOJI.get(token, "📊")
    if price_usd and price_usd > 0:
        text = (
            f"{emoji} <b>{_escape(token)}</b>\n"
            f"{_THIN_SEP}\n"
            f"  Current Price\n"
            f"  <code>{_fmt_price(price_usd)}</code>\n\n"
            f"{_THIN_SEP}\n"
            "<i>SaucerSwap V2</i>"
        )
    else:
        text = f"{emoji} <b>{_escape(token)}</b>\n{_THIN_SEP}\n<i>Price unavailable</i>"
    return text, _price_actions(token)


# ═══════════════════════════════════════════════════════════════════
# Swap flow — Interactive button-driven
# ═══════════════════════════════════════════════════════════════════

def format_swap_entry() -> Tuple[str, Dict[str, Any]]:
    """Top-level swap screen: pick 'From' token."""
    text = (
        "💱 <b>Swap</b>  <i>Step 1/4</i>\n"
        f"{_THIN_SEP}\n\n"
        "<b>Sell token:</b>"
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
    rows.append([{"text": "🏠 Menu", "callback_data": "menu"}])
    return text, {"inline_keyboard": rows}


def format_swap_pick_to(from_sym: str, from_id: str) -> Tuple[str, Dict[str, Any]]:
    """After picking 'From', pick 'To' token."""
    from_emoji = _SYM_EMOJI.get(from_sym, "")
    text = (
        "💱 <b>Swap</b>  <i>Step 2/4</i>\n"
        f"{_THIN_SEP}\n\n"
        f"  Selling: {from_emoji} <b>{_escape(from_sym)}</b>\n\n"
        "<b>Buy token:</b>"
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
        {"text": "↩ Back", "callback_data": "swap"},
        {"text": "🏠 Menu", "callback_data": "menu"},
    ])
    return text, {"inline_keyboard": rows}


def format_swap_pick_amount(
    from_sym: str, to_sym: str, from_id: str, to_id: str,
    from_balance: float = 0.0, from_price: float = 0.0,
    to_price: float = 0.0,
) -> Tuple[str, Dict[str, Any]]:
    """After picking both tokens, pick an amount."""
    from_emoji = _SYM_EMOJI.get(from_sym, "")
    to_emoji = _SYM_EMOJI.get(to_sym, "")
    text = (
        "💱 <b>Swap</b>  <i>Step 3/4</i>\n"
        f"{_THIN_SEP}\n\n"
        f"  {from_emoji} {_escape(from_sym)} → {to_emoji} {_escape(to_sym)}\n"
    )

    # Show exchange rate prominently if we have both prices
    if from_price > 0 and to_price > 0:
        rate = to_price / from_price
        text += f"\n  <b>Rate</b>  <code>1 {_escape(from_sym)} = {_fmt_amount(rate)} {_escape(to_sym)}</code>"

    if from_balance > 0:
        bal_str = _fmt_amount(from_balance)
        bal_usd = ""
        if from_price > 0:
            bal_usd = f" ≈ ${from_balance * from_price:,.2f}"
        text += f"\n  <b>Balance</b>  <code>{bal_str}</code>{bal_usd}"

    text += "\n\n<b>Select amount:</b>"

    presets = AMOUNT_PRESETS.get(from_sym, ["1", "5", "10", "50"])

    rows = []
    row = []
    for amt in presets:
        try:
            amt_float = float(amt)
        except ValueError:
            continue

        # For USD pairs, show $ directly; for others show token amount
        if from_sym in ["USDC", "USDC[hts]"]:
            label = f"${amt}"
        elif from_price > 0:
            usd = amt_float * from_price
            if usd >= 1:
                label = f"${usd:.0f}"
            else:
                label = f"${usd:.2f}"
        else:
            label = f"{amt}"

        row.append({"text": label, "callback_data": f"sa:{from_id}:{to_id}:{amt}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # Add buttons: MAX and Custom
    button_row = []
    if from_balance > 0:
        if from_sym == "HBAR":
            max_amt = max(from_balance - 5.0, 0)  # Keep 5 HBAR gas reserve
        else:
            max_amt = from_balance
        if max_amt > 0:
            button_row.append({"text": f"📊 MAX", "callback_data": f"sa:{from_id}:{to_id}:{max_amt:.8f}"})

    button_row.append({"text": "✏️ Custom", "callback_data": f"custom_swap:{from_id}:{to_id}"})
    rows.append(button_row)

    rows.append([
        {"text": "↩ Back", "callback_data": f"st:{from_id}"},
        {"text": "🏠 Menu", "callback_data": "menu"},
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
    from_emoji = _SYM_EMOJI.get(from_symbol, "")
    to_emoji = _SYM_EMOJI.get(to_symbol, "")

    lines = [
        "💱 <b>Confirm Swap</b>  <i>Step 4/4</i>",
        _THIN_SEP,
        "",
        f"  {from_emoji} <b>{_fmt_amount(amount)}</b> {_escape(from_symbol)}",
        f"      ↓",
        f"  {to_emoji} <b>~{_fmt_amount(estimated_out)}</b> {_escape(to_symbol)}",
        "",
    ]

    # Rate
    if amount > 0 and estimated_out > 0:
        rate = estimated_out / amount
        lines.append(f"  <b>Price</b>  <code>1 {_escape(from_symbol)} = {_fmt_amount(rate)} {_escape(to_symbol)}</code>")

    # Route path
    if route_steps:
        lines.append("")
        lines.append(f"  <b>Route</b>")
        for i, step in enumerate(route_steps):
            if step.get("type") == "swap":
                prefix = "└" if i == len(route_steps) - 1 else "├"
                lines.append(
                    f"  {prefix} {_escape(step['from'])} → {_escape(step['to'])}"
                    f"  ({step['fee_pct']:.2f}%)"
                )

    lines.append("")
    lines.append(f"{_THIN_SEP}")
    lines.append(f"  💰 LP Fee: <code>{fee_pct:.3%}</code>")
    lines.append(f"  ⛽ Est. Gas: <code>~{gas_hbar:.3f} HBAR</code>")
    lines.append("")
    lines.append("⚡ <i>Live on Hedera mainnet</i>")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm", "callback_data": callback_confirm},
                {"text": "❌ Cancel",  "callback_data": "cancel:swap"},
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
    from_emoji = _SYM_EMOJI.get(from_symbol, "")
    to_emoji = _SYM_EMOJI.get(to_symbol, "")
    lines = [
        "✅ <b>Swap Complete</b>",
        _THIN_SEP,
        "",
        f"  {from_emoji} <code>{_fmt_amount(amount_in)}</code> {_escape(from_symbol)}",
        f"  {to_emoji} <code>{_fmt_amount(amount_out)}</code> {_escape(to_symbol)}",
        "",
    ]

    if amount_in > 0 and amount_out > 0:
        rate = amount_out / amount_in
        lines.append(f"  <b>Rate</b>  <code>1 {_escape(from_symbol)} = {_fmt_amount(rate)} {_escape(to_symbol)}</code>")

    if gas_cost_hbar or lp_fee:
        lines.append("")
        if gas_cost_hbar:
            gas_str = f"{gas_cost_hbar:.4f} HBAR"
            if gas_cost_usd:
                gas_str += f" (${gas_cost_usd:.4f})"
            lines.append(f"  ⛽ Gas: <code>{gas_str}</code>")
        if lp_fee:
            lines.append(f"  💰 LP Fee: <code>{lp_fee:.6f}</code>")

    if tx_hash:
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        short_hash = tx_hash[:12] + "…" if len(tx_hash) > 16 else tx_hash
        lines.append(f'  <a href="{_HASHSCAN_TX}{_escape(tx_hash)}">🔗 View on HashScan</a>')
        lines.append(f"  <code>{_escape(short_hash)}</code>")

    return "\n".join(lines), _post_swap_actions()


def format_swap_error(
    error_msg: str,
    from_symbol: str = "",
    to_symbol: str = "",
    amount: float = 0.0,
) -> str:
    lines = [
        "❌ <b>Swap Failed</b>",
        _THIN_SEP,
        "",
        f"  {_escape(error_msg)}",
    ]

    if from_symbol and to_symbol:
        lines.append(f"\n  {_escape(from_symbol)} → {_escape(to_symbol)}")
    if amount:
        lines.append(f"  Amount: <code>{_fmt_amount(amount)}</code>")

    hints: List[str] = []
    err_lower = error_msg.lower()
    if "route" in err_lower or "no route" in err_lower or "no liquidity" in err_lower:
        hints.append("No path found — this pair may lack liquidity")
    if "slippage" in err_lower or "price" in err_lower:
        hints.append("Price moved too fast — try a smaller amount")
    if "balance" in err_lower or "insufficient" in err_lower:
        hints.append("Insufficient balance — check portfolio")
    if "limit" in err_lower or "exceed" in err_lower:
        hints.append("Max $100 per swap (safety limit)")
    if not hints:
        hints.append("Try a different pair or amount")

    lines.append("")
    lines.append(f"{_THIN_SEP}")
    for hint in hints:
        lines.append(f"💡 <i>{hint}</i>")

    return "\n".join(lines)


def format_swap_prompt() -> str:
    """Fallback text-based swap prompt (for typed commands)."""
    return (
        "💱 <b>Swap</b>\n"
        f"{_THIN_SEP}\n\n"
        "Type your swap:\n\n"
        "  <code>swap 5 USDC for HBAR</code>\n"
        "  <code>buy 100 HBAR</code>\n"
        "  <code>sell 10 HBAR</code>\n\n"
        f"{_THIN_SEP}\n"
        "  📏 Max $100  ·  Max 5% slippage"
    )


# ═══════════════════════════════════════════════════════════════════
# Send flow — Interactive button-driven
# ═══════════════════════════════════════════════════════════════════

def format_send_entry() -> Tuple[str, Dict[str, Any]]:
    """Top-level send screen: pick token to send."""
    text = (
        "📤 <b>Send</b>  <i>Step 1/4</i>\n"
        f"{_THIN_SEP}\n\n"
        "<b>Select token:</b>"
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
    rows.append([{"text": "🏠 Menu", "callback_data": "menu"}])
    return text, {"inline_keyboard": rows}


def format_send_pick_recipient(
    token_sym: str, token_id: str,
    whitelist: List[Dict[str, str]],
    balance: float = 0.0,
) -> Tuple[str, Dict[str, Any]]:
    """After picking token, pick recipient from whitelist."""
    emoji = _SYM_EMOJI.get(token_sym, "")
    text = (
        "📤 <b>Send</b>  <i>Step 2/4</i>\n"
        f"{_THIN_SEP}\n\n"
        f"  Token: {emoji} <b>{_escape(token_sym)}</b>\n"
    )
    if balance > 0:
        text += f"  Balance: <code>{_fmt_amount(balance)}</code>\n"
    text += "\n<b>Recipient:</b>"

    rows = []
    if whitelist:
        for entry in whitelist:
            addr = entry.get("address", "")
            name = entry.get("name", entry.get("nickname", addr[:12]))
            rows.append([{"text": f"👤 {name}", "callback_data": f"send_to:{token_id}:{addr}"}])
    else:
        text += "\n\n⚠️ <i>No recipients whitelisted.</i>\n<i>Add via CLI first.</i>"

    rows.append([
        {"text": "↩ Back", "callback_data": "send_tok:" + token_id},
        {"text": "🏠 Menu", "callback_data": "menu"},
    ])
    return text, {"inline_keyboard": rows}


def format_send_pick_amount(
    token_sym: str, token_id: str, recipient: str,
    recipient_name: str = "",
    balance: float = 0.0, price: float = 0.0,
) -> Tuple[str, Dict[str, Any]]:
    """After picking recipient, pick amount."""
    display_to = recipient_name or recipient
    emoji = _SYM_EMOJI.get(token_sym, "")
    text = (
        "📤 <b>Send</b>  <i>Step 3/4</i>\n"
        f"{_THIN_SEP}\n\n"
        f"  Token: {emoji} <b>{_escape(token_sym)}</b>\n"
        f"  To: <b>{_escape(display_to)}</b>\n"
    )
    if balance > 0:
        bal_str = _fmt_amount(balance)
        text += f"  Balance: <code>{bal_str}</code>"
        if price > 0:
            text += f" ≈ ${balance * price:,.2f}"
        text += "\n"
    text += "\n<b>Select amount:</b>"

    presets = AMOUNT_PRESETS.get(token_sym, ["1", "5", "10", "50"])
    rows = []
    row = []
    for amt in presets:
        try:
            amt_float = float(amt)
        except ValueError:
            continue

        # For USD pairs, show $ directly; for others show token amount
        if token_sym in ["USDC", "USDC[hts]"]:
            label = f"${amt}"
        elif price > 0:
            usd = amt_float * price
            if usd >= 1:
                label = f"${usd:.0f}"
            else:
                label = f"${usd:.2f}"
        else:
            label = f"{amt}"

        row.append({"text": label, "callback_data": f"send_amt:{token_id}:{recipient}:{amt}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # Add buttons: MAX and Custom
    button_row = []
    if balance > 0:
        max_amt = balance
        if token_sym == "HBAR":
            max_amt = max(balance - 5.0, 0)
        if max_amt > 0:
            button_row.append({"text": "📊 MAX", "callback_data": f"send_amt:{token_id}:{recipient}:{max_amt:.8f}"})

    button_row.append({"text": "✏️ Custom", "callback_data": f"custom_send:{token_id}:{recipient}"})
    rows.append(button_row)

    rows.append([
        {"text": "↩ Back", "callback_data": f"send_tok:{token_id}"},
        {"text": "🏠 Menu", "callback_data": "menu"},
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
    emoji = _SYM_EMOJI.get(token, "")
    lines = [
        "📤 <b>Confirm Transfer</b>  <i>Step 4/4</i>",
        _THIN_SEP,
        "",
        f"  {emoji} <b>{_fmt_amount(amount)} {_escape(token)}</b>",
        "",
        f"  → <b>{_escape(display_to)}</b>",
    ]
    if remaining_balance is not None:
        lines.append(f"  After: <code>{_fmt_amount(remaining_balance)} {_escape(token)}</code>")
    lines += [
        "",
        f"{_THIN_SEP}",
        "🔒 Whitelisted recipient",
        "⚡ <i>Live on Hedera mainnet</i>",
    ]
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm", "callback_data": callback_confirm},
                {"text": "❌ Cancel",  "callback_data": "cancel:send"},
            ]
        ]
    }
    return {"text": "\n".join(lines), "reply_markup": keyboard}


def format_send_receipt(
    amount: float, token: str, recipient: str, tx_hash: str = ""
) -> Tuple[str, Dict[str, Any]]:
    emoji = _SYM_EMOJI.get(token, "")
    lines = [
        "✅ <b>Transfer Complete</b>",
        _THIN_SEP,
        "",
        f"  {emoji} <code>{_fmt_amount(amount)}</code> {_escape(token)}",
        f"  → <code>{_escape(recipient)}</code>",
    ]
    if tx_hash:
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        short_hash = tx_hash[:12] + "…" if len(tx_hash) > 16 else tx_hash
        lines.append(f'  <a href="{_HASHSCAN_TX}{_escape(tx_hash)}">🔗 View on HashScan</a>')
        lines.append(f"  <code>{_escape(short_hash)}</code>")
    return "\n".join(lines), _post_send_actions()


def format_send_error(
    error_msg: str, amount: float = 0, token: str = "", recipient: str = ""
) -> str:
    lines = [
        "❌ <b>Transfer Failed</b>",
        _THIN_SEP,
        "",
        f"  {_escape(error_msg)}",
    ]
    if amount and token:
        lines.append(f"\n  <code>{_fmt_amount(amount)} {_escape(token)}</code>")
    if recipient:
        lines.append(f"  To: <code>{_escape(recipient)}</code>")
    if "whitelist" in error_msg.lower() or "safety" in error_msg.lower():
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        lines.append("💡 <i>Add recipient to whitelist via CLI</i>")
    return "\n".join(lines)


def format_send_prompt() -> str:
    return (
        "📤 <b>Send</b>\n"
        f"{_THIN_SEP}\n\n"
        "Type your transfer:\n\n"
        "  <code>send 5 USDC to 0.0.XXXXXXX</code>\n"
        "  <code>send 100 HBAR to 0.0.XXXXXXX</code>\n\n"
        f"{_THIN_SEP}\n"
        "  🔒 Whitelisted only  ·  Hedera IDs"
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
        _THIN_SEP,
        "",
        f"  Account: <code>{_escape(account_id)}</code>",
        f"  Network: <code>{_escape(network)}</code>",
        f"  ✓ <b>Online</b>",
        "",
    ]

    if balances:
        lines.append("  <b>Holdings</b>")
        total_usd = 0.0
        has_prices = prices and any(v and v > 0 for v in prices.values())
        for sym in sorted(balances.keys(), key=lambda s: (0 if s == "HBAR" else 1, s)):
            amount = balances[sym]
            if amount <= 0:
                continue
            emoji = _SYM_EMOJI.get(sym, "·")
            if has_prices and prices.get(sym):
                usd_val = amount * prices[sym]
                total_usd += usd_val
                lines.append(f"  {emoji} {sym:<6} <code>{_fmt_amount(amount):>12}</code>  ≈ ${usd_val:>8,.2f}")
            else:
                lines.append(f"  {emoji} {sym:<6} <code>{_fmt_amount(amount):>12}</code>")
        if has_prices and total_usd > 0:
            lines.append("")
            lines.append(f"  💼 <b>Total  ${total_usd:,.2f}</b>")
    else:
        lines.append("  <i>No balances.</i>")

    lines.append("")
    lines.append(f"{_THIN_SEP}")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "⛽ Gas", "callback_data": "gas"},
            ],
            [
                {"text": "🤖 Robot", "callback_data": "robot"},
                {"text": "🏠 Menu", "callback_data": "menu"},
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
        pct = 100
    elif hbar_balance >= min_reserve * 1.5:
        icon, status = "🟡", "Adequate"
        pct = int((hbar_balance / (min_reserve * 3)) * 100)
    elif hbar_balance >= min_reserve:
        icon, status = "🟠", "Low"
        pct = int((hbar_balance / (min_reserve * 3)) * 100)
    else:
        icon, status = "🔴", "Critical"
        pct = int((hbar_balance / (min_reserve * 3)) * 100)

    # Build progress bar
    filled = min(int(pct / 10), 10)
    bar = "█" * filled + "░" * (10 - filled)

    text = (
        f"⛽ <b>Gas Reserve</b>\n"
        f"{_THIN_SEP}\n\n"
        f"  Balance: <code>{_fmt_amount(hbar_balance)} HBAR</code>\n"
        f"  Min Reserve: <code>{min_reserve} HBAR</code>\n\n"
        f"  {icon} <b>{status}</b>\n"
        f"  <code>[{bar}]</code>  {pct}%"
    )

    if hbar_balance < min_reserve:
        needed = min_reserve - hbar_balance
        text += f"\n\n⚠️ Need <code>{needed:.2f} HBAR</code> more for trading"

    text += f"\n\n{_THIN_SEP}"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "💱 Swap",      "callback_data": "swap"},
            ],
            [{"text": "🏠 Menu", "callback_data": "menu"}],
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
            f"{_THIN_SEP}\n\n"
            "<i>No transactions yet.</i>"
        )
        return text, _back_to_menu()

    lines = [
        "📋 <b>Recent Transactions</b>",
        _THIN_SEP,
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
        lines.append(f"  {icon} {_escape(ts)}")
        lines.append(f"  {desc}")

    lines.append("")
    lines.append(f"{_THIN_SEP}")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "💱 Swap", "callback_data": "swap"},
            ],
            [{"text": "🏠 Menu", "callback_data": "menu"}],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Tokens list
# ═══════════════════════════════════════════════════════════════════

def format_tokens(tokens_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    lines = [
        "📖 <b>Supported Tokens</b>",
        _THIN_SEP,
        "",
    ]
    priority = ["HBAR", "USDC", "WBTC", "WETH", "SAUCE", "HBARX"]
    shown = set()
    for sym in priority:
        emoji = _SYM_EMOJI.get(sym, "·")
        meta = tokens_data.get(sym)
        if meta is None:
            for tid, m in tokens_data.items():
                if isinstance(m, dict) and m.get("symbol") == sym:
                    meta = m
                    break
        if meta and isinstance(meta, dict):
            tid = meta.get("id", sym)
            lines.append(f"  {emoji} <b>{_escape(sym):<6}</b> <code>{_escape(tid)}</code>")
            shown.add(sym)
    if "HBAR" not in shown:
        lines.insert(3, "  ⟐ <b>HBAR  <code>0.0.0</code>")

    lines.append("")
    lines.append(f"{_THIN_SEP}")
    lines.append("<i>Available for swap</i>")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💱 Swap", "callback_data": "swap"},
                {"text": "📊 Prices", "callback_data": "price"},
            ],
            [{"text": "🏠 Menu", "callback_data": "menu"}],
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
        _THIN_SEP,
        "",
        f"  {icon} <b>{_escape(status.title())}</b>",
    ]

    if robot_account:
        lines.append(f"  Account: <code>{_escape(robot_account)}</code>")

    if not funded or portfolio_usd < 5.0:
        lines.append("")
        lines.append(f"{_THIN_SEP}")
        lines.append("⚠️ <i>Needs funding (min $5)</i>")
        lines.append("<i>Fund robot account to enable auto-rebalancing</i>")
    else:
        lines.append(f"  💼 Portfolio: <b>${portfolio_usd:,.2f}</b>")
        if btc_pct > 0:
            lines.append(f"  ₿ BTC: <code>{btc_pct:.1f}%</code> (target: {target_pct:.1f}%)")
        if last_rebalance:
            lines.append(f"  📅 Last: <code>{_escape(last_rebalance[:16])}</code>")

    lines.append("")
    lines.append(f"{_THIN_SEP}")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Portfolio", "callback_data": "portfolio"},
                {"text": "🏥 Status", "callback_data": "health"},
            ],
            [{"text": "🏠 Menu", "callback_data": "menu"}],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Ghost Tunnel — Secure key setup
# ═══════════════════════════════════════════════════════════════════

def format_setup_prompt() -> str:
    return (
        "🔐 <b>Secure Key Setup</b>\n"
        f"{_THIN_SEP}\n\n"
        "Tap below to open secure input.\n\n"
        "  🔒 HTTPS direct to server\n"
        "  🔒 Stored in <code>.env</code> only\n"
        "  🔒 HMAC-verified\n\n"
        f"{_THIN_SEP}\n"
        "<i>Never stored in chat history.</i>"
    )


def format_key_saved(field: str) -> str:
    return (
        f"✅ <b>{_escape(field)}</b> saved\n"
        f"{_THIN_SEP}\n\n"
        "Written to <code>.env</code>.\n\n"
        "<i>Restart bot for changes.</i>"
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
        "<i>Coming soon</i>"
    )


def format_unauthorized() -> str:
    return (
        "🔒 <b>Access Denied</b>\n"
        f"{_THIN_SEP}\n\n"
        "Telegram ID not authorized.\n"
        "<i>Request access from wallet owner.</i>"
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
