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
"""

from typing import Dict, Any, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
# Line drawing characters for card-style formatting
# ═══════════════════════════════════════════════════════════════════

_THIN_SEP = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"
_DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━"


# ═══════════════════════════════════════════════════════════════════
# Main menu — 4×2 action grid (persistent keyboard)
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
# Contextual keyboards — shown INSTEAD of main menu where relevant
# ═══════════════════════════════════════════════════════════════════

def _portfolio_actions() -> Dict[str, Any]:
    """Actions relevant after viewing portfolio."""
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
            [
                {"text": "⬅️ Menu", "callback_data": "menu"},
            ],
        ]
    }


def _price_actions(token: str = "") -> Dict[str, Any]:
    """Actions after viewing prices."""
    rows = [
        [
            {"text": "💱 Swap Tokens", "callback_data": "swap"},
            {"text": "💰 Portfolio", "callback_data": "portfolio"},
        ],
        [
            {"text": "🔄 Refresh Prices", "callback_data": "price"},
        ],
        [
            {"text": "⬅️ Menu", "callback_data": "menu"},
        ],
    ]
    return {"inline_keyboard": rows}


def _post_swap_actions() -> Dict[str, Any]:
    """After a swap completes."""
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Check Balance", "callback_data": "portfolio"},
                {"text": "💱 Swap Again", "callback_data": "swap"},
            ],
            [
                {"text": "📋 History", "callback_data": "history"},
                {"text": "⬅️ Menu", "callback_data": "menu"},
            ],
        ]
    }


def _post_send_actions() -> Dict[str, Any]:
    """After a send completes."""
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Check Balance", "callback_data": "portfolio"},
                {"text": "📤 Send Again", "callback_data": "send"},
            ],
            [
                {"text": "📋 History", "callback_data": "history"},
                {"text": "⬅️ Menu", "callback_data": "menu"},
            ],
        ]
    }


def _back_to_menu() -> Dict[str, Any]:
    """Simple back button."""
    return {
        "inline_keyboard": [
            [{"text": "⬅️ Menu", "callback_data": "menu"}],
        ]
    }


# ═══════════════════════════════════════════════════════════════════
# Welcome / Help
# ═══════════════════════════════════════════════════════════════════

def format_welcome() -> str:
    return (
        "🟢 <b>Pacman Wallet</b>\n"
        f"{_DIVIDER}\n\n"
        "Self-custody Hedera wallet.\n"
        "Live trades. No simulation.\n\n"
        "<b>Quick Actions</b>\n"
        "├ 💰 <b>Portfolio</b> — balances + USD values\n"
        "├ 💱 <b>Swap</b> — trade tokens instantly\n"
        "├ 📤 <b>Send</b> — transfer to whitelisted wallets\n"
        "├ 📊 <b>Prices</b> — live token prices\n"
        "├ 🤖 <b>Robot</b> — BTC rebalancer status\n"
        "├ ⛽ <b>Gas</b> — HBAR reserve check\n"
        "├ 📋 <b>History</b> — recent transactions\n"
        "└ 🏥 <b>Status</b> — system health\n\n"
        "<i>Tap a button below or type a command.</i>"
    )


# ═══════════════════════════════════════════════════════════════════
# Portfolio / Balance
# ═══════════════════════════════════════════════════════════════════

def format_balance(
    balances: Dict[str, float],
    account_id: str = "",
    prices: Optional[Dict[str, float]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Render portfolio with USD values.

    Returns:
        (html_text, reply_markup) tuple
    """
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

    # Sort: HBAR first, USDC second, then alphabetical
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
    """Render multiple token prices. Returns (text, reply_markup)."""
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
    """Single token price. Returns (text, reply_markup)."""
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
# Swap flow
# ═══════════════════════════════════════════════════════════════════

def format_swap_prompt() -> str:
    """Prompt the user to type their swap command."""
    return (
        "💱 <b>Swap Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        "Type your swap:\n\n"
        "  <code>swap 5 USDC for HBAR</code>\n"
        "  <code>swap 100 HBAR for USDC</code>\n"
        "  <code>buy 5 HBAR</code>\n"
        "  <code>sell 10 HBAR</code>\n\n"
        f"{_THIN_SEP}\n"
        "⚡ Trades execute on Hedera mainnet.\n"
        f"📏 Max ${'{:.0f}'.format(100)} per swap  •  Max 5% slippage"
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
    Build a swap confirmation card with Confirm/Cancel.

    Returns a dict: {text, reply_markup}
    """
    callback_confirm = f"confirm_swap:{amount}:{from_id}:{to_id}:{mode}"

    if mode == "exact_in":
        direction = (
            f"<b>{_fmt_amount(amount)} {_escape(from_symbol)}</b>"
            f"  →  {_escape(to_symbol)}"
        )
    else:
        direction = (
            f"{_escape(from_symbol)}  →  "
            f"<b>{_fmt_amount(amount)} {_escape(to_symbol)}</b>"
        )

    lines = [
        "💱 <b>Confirm Swap</b>",
        _DIVIDER,
        "",
        f"  {direction}",
        "",
    ]

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
    """HTML receipt after a successful swap. Returns (text, reply_markup)."""
    lines = [
        "✅ <b>Swap Complete</b>",
        _DIVIDER,
        "",
        f"  <b>{_fmt_amount(amount_in)} {_escape(from_symbol)}</b>"
        f"  →  <b>{_fmt_amount(amount_out)} {_escape(to_symbol)}</b>",
        "",
    ]

    # Rate
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
    """Swap error message with contextual recovery hints."""
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


# ═══════════════════════════════════════════════════════════════════
# Send flow
# ═══════════════════════════════════════════════════════════════════

def format_send_prompt() -> str:
    return (
        "📤 <b>Send Tokens</b>\n"
        f"{_DIVIDER}\n\n"
        "Type your transfer:\n\n"
        "  <code>send 5 USDC to 0.0.XXXXXXX</code>\n"
        "  <code>send 100 HBAR to 0.0.XXXXXXX</code>\n\n"
        f"{_THIN_SEP}\n"
        "🔒 Only whitelisted recipients allowed.\n"
        "📏 Hedera IDs only (0.0.xxx) — no EVM."
    )


def format_send_confirm(
    amount: float,
    token: str,
    recipient: str,
    remaining_balance: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a send confirmation card."""
    callback_confirm = f"confirm_send:{amount}:{token}:{recipient}"
    lines = [
        "📤 <b>Confirm Transfer</b>",
        _DIVIDER,
        "",
        f"  Amount: <b>{_fmt_amount(amount)} {_escape(token)}</b>",
        f"  To: <code>{_escape(recipient)}</code>",
    ]
    if remaining_balance is not None:
        lines.append(f"  Remaining: <code>{_fmt_amount(remaining_balance)} {_escape(token)}</code>")
    lines += [
        "",
        f"{_THIN_SEP}",
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
    """Returns (text, reply_markup)."""
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


# ═══════════════════════════════════════════════════════════════════
# Status / Health
# ═══════════════════════════════════════════════════════════════════

def format_status(
    balances: Dict[str, float],
    account_id: str,
    network: str,
    prices: Optional[Dict[str, float]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Full system dashboard. Returns (text, reply_markup)."""
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
                {"text": "⬅️ Menu", "callback_data": "menu"},
            ],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Gas status
# ═══════════════════════════════════════════════════════════════════

def format_gas_status(hbar_balance: float, min_reserve: float = 5.0) -> Tuple[str, Dict[str, Any]]:
    """Gas reserve card. Returns (text, reply_markup)."""
    if hbar_balance >= min_reserve * 3:
        icon = "🟢"
        status = "Healthy"
        bar = "█████████░"
    elif hbar_balance >= min_reserve * 1.5:
        icon = "🟡"
        status = "Adequate"
        bar = "██████░░░░"
    elif hbar_balance >= min_reserve:
        icon = "🟠"
        status = "Low"
        bar = "███░░░░░░░"
    else:
        icon = "🔴"
        status = "CRITICAL"
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
            [{"text": "⬅️ Menu", "callback_data": "menu"}],
        ]
    }
    return text, keyboard


# ═══════════════════════════════════════════════════════════════════
# History
# ═══════════════════════════════════════════════════════════════════

def format_history(records: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """Render recent transactions. Returns (text, reply_markup)."""
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
            [{"text": "⬅️ Menu", "callback_data": "menu"}],
        ]
    }
    return "\n".join(lines), keyboard


# ═══════════════════════════════════════════════════════════════════
# Tokens list
# ═══════════════════════════════════════════════════════════════════

def format_tokens(tokens_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Supported tokens card. Returns (text, reply_markup)."""
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
    lines.append("<i>Use symbols in commands:</i> <code>swap 5 USDC for HBAR</code>")

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💱 Swap", "callback_data": "swap"},
                {"text": "📊 Prices", "callback_data": "price"},
            ],
            [{"text": "⬅️ Menu", "callback_data": "menu"}],
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
    """Robot/rebalancer status card. Returns (text, reply_markup)."""
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
            [{"text": "⬅️ Menu", "callback_data": "menu"}],
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


def _fmt_price(price: float) -> str:
    """Format a USD price."""
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    elif price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"
