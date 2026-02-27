#!/usr/bin/env python3
"""
CLI Commands: Limit Orders
===========================

Wall Street-style limit order interface.
Uses conventional "limit buy" / "limit sell" terminology.

  Limit Buy  = Buy the asset when price drops TO or BELOW your target
  Limit Sell = Sell the asset when price rises TO or ABOVE your target
"""

from cli.display import C
from src.logger import logger


def cmd_order(app, args):
    """
    Main dispatcher for limit order subcommands.

    Usage:
        order buy  <token> at <price> size <amount>
        order sell <token> at <price> size <amount>
        order list / order book
        order cancel <id>
        order history / order fills
        order interval <time>
        order on / order off / order status
    """
    if not args:
        _show_help()
        return

    sub = args[0].lower()

    if sub == "buy":
        _cmd_buy(app, args[1:])
    elif sub == "sell":
        _cmd_sell(app, args[1:])
    elif sub in ("list", "ls", "book"):
        _cmd_list(app)
    elif sub == "cancel":
        _cmd_cancel(app, args[1:])
    elif sub in ("history", "fills"):
        _cmd_history(app)
    elif sub == "interval":
        _cmd_interval(app, args[1:])
    elif sub == "on":
        _cmd_daemon_on(app)
    elif sub == "off":
        _cmd_daemon_off(app)
    elif sub == "status":
        _cmd_daemon_status(app)
    else:
        print(f"  {C.ERR}✗{C.R} Unknown subcommand: {sub}")
        _show_help()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_current_price(app, token_symbol: str) -> float:
    """Fetch the current USD price of a token."""
    from lib.prices import price_manager
    price_manager.reload()
    if token_symbol.upper() in ("HBAR", "ℏ"):
        return price_manager.get_hbar_price()
    token_id = app.resolve_token_id(token_symbol)
    if token_id:
        return price_manager.get_price(token_id)
    return 0.0


def _side_label(condition: str) -> str:
    """Map internal condition to Wall Street side label."""
    return "BUY" if condition == "below" else "SELL"


def _side_color(condition: str) -> str:
    """Green for buy, red/yellow for sell."""
    return C.OK if condition == "below" else C.WARN


def _format_pair(order) -> str:
    """Show pair as BASE/QUOTE with base = watched token."""
    parts = order.action_string.split(":")
    if parts[0] == "swap" and len(parts) >= 5:
        # For buys (below): action is swap:USDC:TOKEN, but pair should be TOKEN/USDC
        # For sells (above): action is swap:TOKEN:USDC, pair is TOKEN/USDC
        if order.condition == "below":
            return f"{parts[2]}/{parts[1]}"
        else:
            return f"{parts[1]}/{parts[2]}"
    return order.token_symbol + "/USDC"


def _format_size(order) -> str:
    """Extract size from the action string."""
    parts = order.action_string.split(":")
    if parts[0] == "swap" and len(parts) >= 4:
        amt = parts[3]
        if order.condition == "below":
            # BUY: spending USDC (parts[1]) to get token (parts[2])
            return f"{amt} {parts[1]}"
        else:
            # SELL: selling token (parts[1]) for USDC (parts[2])
            return f"{amt} {parts[1]}"
    elif parts[0] == "transfer" and len(parts) >= 3:
        return f"{parts[2]} {parts[1]}"
    return "—"


# ---------------------------------------------------------------------------
# Buy / Sell Commands
# ---------------------------------------------------------------------------

def _cmd_buy(app, args):
    """
    Limit Buy: Buy a token when it drops to your target price.

    order buy <token> at <price> size <amount>
    order buy HBAR at 0.08 size 100

    This creates a swap: <amount> USDC → <token> when <token> ≤ <price>
    """
    stop_words = {"AT", "FOR", "WHEN", "WITH", "→", "->"}
    clean = [a for a in args if a.upper() not in stop_words]

    if len(clean) < 3:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}order buy <token> at <price> size <amount>{C.R}")
        print(f"  Example: {C.TEXT}order buy HBAR at 0.08 size 100{C.R}")
        print(f"  {C.MUTED}→ Buys 100 USDC worth of HBAR when price drops to $0.08{C.R}")
        return

    token = clean[0].upper()
    try:
        target_price = float(clean[1])
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid price: {clean[1]}")
        return

    # Size defaults to what's after "size" keyword, or the 3rd arg
    size = None
    for i, a in enumerate(clean):
        if a.upper() == "SIZE" and i + 1 < len(clean):
            try:
                size = float(clean[i + 1])
            except ValueError:
                pass
            break
    if size is None and len(clean) >= 3:
        try:
            size = float(clean[2])
        except ValueError:
            pass
    if size is None:
        print(f"  {C.ERR}✗{C.R} Missing size. Usage: {C.TEXT}order buy HBAR at 0.08 size 100{C.R}")
        return

    # Resolve token
    token_id = app.resolve_token_id(token)
    if not token_id and token in ("HBAR", "ℏ"):
        token_id = "0.0.0"
    if not token_id:
        print(f"  {C.ERR}✗{C.R} Unknown token: {token}")
        return

    # LIMIT BUY = swap USDC → TOKEN when price drops below target
    action_string = f"swap:USDC:{token}:{size}:exact_in"
    description = f"Buy {token} with {size} USDC"
    pair = f"{token}/USDC"

    _create_order(app, token, token_id, "below", target_price, "swap",
                  action_string, description, pair, size, "BUY")


def _cmd_sell(app, args):
    """
    Limit Sell: Sell a token when it rises to your target price.

    order sell <token> at <price> size <amount>
    order sell HBAR at 0.12 size 50

    This creates a swap: <amount> <token> → USDC when <token> ≥ <price>
    """
    stop_words = {"AT", "FOR", "WHEN", "WITH", "→", "->"}
    clean = [a for a in args if a.upper() not in stop_words]

    if len(clean) < 3:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}order sell <token> at <price> size <amount>{C.R}")
        print(f"  Example: {C.TEXT}order sell HBAR at 0.12 size 50{C.R}")
        print(f"  {C.MUTED}→ Sells 50 HBAR for USDC when price rises to $0.12{C.R}")
        return

    token = clean[0].upper()
    try:
        target_price = float(clean[1])
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid price: {clean[1]}")
        return

    size = None
    for i, a in enumerate(clean):
        if a.upper() == "SIZE" and i + 1 < len(clean):
            try:
                size = float(clean[i + 1])
            except ValueError:
                pass
            break
    if size is None and len(clean) >= 3:
        try:
            size = float(clean[2])
        except ValueError:
            pass
    if size is None:
        print(f"  {C.ERR}✗{C.R} Missing size. Usage: {C.TEXT}order sell HBAR at 0.12 size 50{C.R}")
        return

    # Resolve token
    token_id = app.resolve_token_id(token)
    if not token_id and token in ("HBAR", "ℏ"):
        token_id = "0.0.0"
    if not token_id:
        print(f"  {C.ERR}✗{C.R} Unknown token: {token}")
        return

    # LIMIT SELL = swap TOKEN → USDC when price rises above target
    action_string = f"swap:{token}:USDC:{size}:exact_in"
    description = f"Sell {size} {token} for USDC"
    pair = f"{token}/USDC"

    _create_order(app, token, token_id, "above", target_price, "swap",
                  action_string, description, pair, size, "SELL")


def _create_order(app, token, token_id, condition, target_price, action_type,
                  action_string, description, pair, size, side_label):
    """Shared order creation logic with exchange-style confirmation."""
    try:
        current_price = _get_current_price(app, token)
        engine = app.limit_engine
        order_id = engine.add_order(
            token_symbol=token,
            token_id=token_id,
            condition=condition,
            target_price=target_price,
            action_type=action_type,
            action_string=action_string,
            description=description,
            account_id=app.account_id,
        )

        side_col = C.OK if side_label == "BUY" else C.WARN
        print(f"\n  {C.BOLD}ORDER PLACED{C.R}")
        print(f"  {C.CHROME}{'─' * 44}{C.R}")
        print(f"  {C.MUTED}ID{C.R}             {C.TEXT}{order_id}{C.R}")
        print(f"  {C.MUTED}Side{C.R}           {side_col}{side_label}{C.R}")
        print(f"  {C.MUTED}Pair{C.R}           {C.ACCENT}{pair}{C.R}")
        print(f"  {C.MUTED}Trigger Price{C.R}  {C.TEXT}${target_price:.6f}{C.R}")
        if current_price > 0:
            diff = ((target_price - current_price) / current_price) * 100
            diff_str = f"{diff:+.2f}%"
            print(f"  {C.MUTED}Current Price{C.R}  {C.TEXT}${current_price:.6f}{C.R}  {C.MUTED}({diff_str}){C.R}")
        print(f"  {C.MUTED}Size{C.R}           {C.TEXT}{size}{C.R}")
        print(f"  {C.MUTED}Action{C.R}         {description}")
        print(f"  {C.CHROME}{'─' * 44}{C.R}")

        if not engine.is_running:
            print(f"  {C.WARN}⚠{C.R} Daemon OFF — run {C.TEXT}order on{C.R} to start monitoring")

    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Failed: {e}")


# ---------------------------------------------------------------------------
# Order Book (List)
# ---------------------------------------------------------------------------

def _cmd_list(app):
    """Show active orders in exchange-style order book format."""
    engine = app.limit_engine
    orders = engine.list_orders(status="active", account_id=app.account_id)

    if not orders:
        print(f"\n  {C.MUTED}No open orders.{C.R}")
        return

    # Get live prices
    current_prices = {}
    for o in orders:
        if o.token_symbol not in current_prices:
            current_prices[o.token_symbol] = _get_current_price(app, o.token_symbol)

    # Separate into buys and sells
    buys = [o for o in orders if o.condition == "below"]
    sells = [o for o in orders if o.condition == "above"]

    print(f"\n  {C.BOLD}OPEN ORDERS ({len(orders)}){C.R}")
    print(f"  {C.CHROME}{'─' * 68}{C.R}")
    print(f"  {C.MUTED}{'ID':<10} {'SIDE':<6} {'PAIR':<12} {'TRIGGER':>12} {'MARK':>12} {'SIZE':>12}{C.R}")
    print(f"  {C.CHROME}{'─' * 68}{C.R}")

    for o in sells:
        pair = _format_pair(o)
        size = _format_size(o)
        mark = current_prices.get(o.token_symbol, 0)
        mark_str = f"${mark:.6f}" if mark > 0 else "—"
        print(
            f"  {C.TEXT}{o.id:<10}{C.R}"
            f"{C.WARN}{'SELL':<6}{C.R}"
            f"{C.ACCENT}{pair:<12}{C.R}"
            f"{C.TEXT}{'${:.6f}'.format(o.target_price):>12}{C.R}"
            f"{C.MUTED}{mark_str:>12}{C.R}"
            f"{C.TEXT}{size:>12}{C.R}"
        )

    for o in buys:
        pair = _format_pair(o)
        size = _format_size(o)
        mark = current_prices.get(o.token_symbol, 0)
        mark_str = f"${mark:.6f}" if mark > 0 else "—"
        print(
            f"  {C.TEXT}{o.id:<10}{C.R}"
            f"{C.OK}{'BUY':<6}{C.R}"
            f"{C.ACCENT}{pair:<12}{C.R}"
            f"{C.TEXT}{'${:.6f}'.format(o.target_price):>12}{C.R}"
            f"{C.MUTED}{mark_str:>12}{C.R}"
            f"{C.TEXT}{size:>12}{C.R}"
        )

    print(f"  {C.CHROME}{'─' * 68}{C.R}")

    # Daemon status footer
    from src.limit_orders import format_interval
    interval_str = format_interval(engine.poll_interval)
    if engine.is_running:
        print(f"  {C.OK}●{C.R} Daemon {C.OK}ON{C.R} — polling every {interval_str}")
    else:
        print(f"  {C.ERR}●{C.R} Daemon {C.ERR}OFF{C.R} — {C.TEXT}order on{C.R} to start")


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

def _cmd_cancel(app, args):
    """Cancel an order by ID (prefix match)."""
    if not args:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}order cancel <id>{C.R}")
        return

    order_id = args[0]
    engine = app.limit_engine

    if engine.cancel_order(order_id, account_id=app.account_id):
        print(f"  {C.OK}✓{C.R} Order {C.TEXT}{order_id}{C.R} cancelled.")
    else:
        print(f"  {C.ERR}✗{C.R} No active order matching '{order_id}'")


# ---------------------------------------------------------------------------
# History / Fills
# ---------------------------------------------------------------------------

def _cmd_history(app):
    """Show order fills and cancellations."""
    engine = app.limit_engine
    history = [o for o in engine.list_orders(account_id=app.account_id) if o.status != "active"]

    if not history:
        print(f"\n  {C.MUTED}No order history.{C.R}")
        return

    print(f"\n  {C.BOLD}ORDER HISTORY{C.R}")
    print(f"  {C.CHROME}{'─' * 72}{C.R}")
    print(f"  {C.MUTED}{'ID':<10} {'STATUS':<10} {'SIDE':<6} {'PAIR':<12} {'TRIGGER':>12} {'TIME'}{C.R}")
    print(f"  {C.CHROME}{'─' * 72}{C.R}")

    status_colors = {
        "triggered": C.OK,
        "cancelled": C.MUTED,
        "failed": C.ERR,
    }
    status_labels = {
        "triggered": "FILLED",
        "cancelled": "CANCELLED",
        "failed": "FAILED",
    }

    for o in history:
        sc = status_colors.get(o.status, C.TEXT)
        label = status_labels.get(o.status, o.status.upper())
        side = _side_label(o.condition)
        side_col = _side_color(o.condition)
        pair = _format_pair(o)
        ts = o.triggered_at or o.created_at

        print(
            f"  {C.TEXT}{o.id:<10}{C.R}"
            f"{sc}{label:<10}{C.R}"
            f"{side_col}{side:<6}{C.R}"
            f"{C.ACCENT}{pair:<12}{C.R}"
            f"{C.TEXT}{'${:.6f}'.format(o.target_price):>12}{C.R}"
            f"  {C.MUTED}{ts}{C.R}"
        )
        if o.error:
            print(f"  {'':10}{C.ERR}└ {o.error}{C.R}")


# ---------------------------------------------------------------------------
# Daemon Toggle
# ---------------------------------------------------------------------------

def _cmd_daemon_on(app):
    """Start the limit order monitor daemon."""
    engine = app.limit_engine
    if engine.start_monitor(app):
        count = engine.get_active_count(account_id=app.account_id)
        from src.limit_orders import format_interval
        interval_str = format_interval(engine.poll_interval)
        print(f"  {C.OK}✓{C.R} Daemon {C.OK}ON{C.R} — monitoring {count} order(s) every {interval_str}")
    else:
        print(f"  {C.MUTED}Daemon is already running.{C.R}")


def _cmd_daemon_off(app):
    """Stop the limit order monitor daemon."""
    engine = app.limit_engine
    if engine.is_running:
        engine.stop_monitor()
        print(f"  {C.OK}✓{C.R} Daemon {C.ERR}OFF{C.R}")
    else:
        print(f"  {C.MUTED}Daemon is not running.{C.R}")


def _cmd_daemon_status(app):
    """Show daemon status."""
    engine = app.limit_engine
    active = engine.get_active_count(account_id=app.account_id)
    from src.limit_orders import format_interval
    interval_str = format_interval(engine.poll_interval)

    if engine.is_running:
        print(f"\n  {C.OK}●{C.R} Daemon: {C.OK}RUNNING{C.R}")
    else:
        print(f"\n  {C.ERR}●{C.R} Daemon: {C.ERR}STOPPED{C.R}")

    print(f"  {C.MUTED}Open orders:{C.R}  {active}")
    print(f"  {C.MUTED}Poll interval:{C.R} {interval_str}")


def _cmd_interval(app, args):
    """Set the daemon polling interval."""
    if not args:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}order interval <time>{C.R}")
        print(f"  Examples: {C.TEXT}5m{C.R}, {C.TEXT}1h{C.R}, {C.TEXT}30s{C.R}, {C.TEXT}600{C.R}")
        return

    interval_str = " ".join(args)
    from src.limit_orders import parse_interval, format_interval
    
    seconds = parse_interval(interval_str)
    if seconds is None:
        print(f"  {C.ERR}✗{C.R} Invalid interval format: {interval_str}")
        print(f"  Use formats like: {C.TEXT}5m{C.R}, {C.TEXT}1h{C.R}, {C.TEXT}30s{C.R}")
        return
        
    if seconds < 60:
        print(f"  {C.WARN}⚠{C.R} Interval too low, enforcing minimum of 60 seconds (1m)")
        seconds = 60
        
    engine = app.limit_engine
    engine.set_interval(seconds)
    print(f"  {C.OK}✓{C.R} Poll interval set to {C.TEXT}{format_interval(seconds)}{C.R}")
    
    if engine.is_running:
        print(f"  {C.WARN}⚠{C.R} Restarting daemon to apply new interval...")
        engine.stop_monitor()
        engine.start_monitor(app)


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

def _show_help():
    """Print limit order help in exchange style."""
    print(f"\n  {C.BOLD}LIMIT ORDERS{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.TEXT}order buy{C.R}   <token> at <price> size <amount>")
    print(f"  {C.TEXT}order sell{C.R}  <token> at <price> size <amount>")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.TEXT}order list{C.R}    Open orders (order book)")
    print(f"  {C.TEXT}order cancel{C.R}  <id>")
    print(f"  {C.TEXT}order fills{C.R}   Filled / cancelled orders")
    print(f"  {C.TEXT}order interval{C.R} Set poll interval (e.g. 5m, 1h)")
    print(f"  {C.TEXT}order on{C.R}      Start monitoring daemon")
    print(f"  {C.TEXT}order off{C.R}     Stop monitoring daemon")
    print(f"  {C.TEXT}order status{C.R}  Daemon status")
    print()
    print(f"  {C.MUTED}Examples:{C.R}")
    print(f"  {C.OK}BUY{C.R}  {C.TEXT}order buy HBAR at 0.08 size 100{C.R}   {C.MUTED}Buy HBAR with 100 USDC when price ≤ $0.08{C.R}")
    print(f"  {C.WARN}SELL{C.R} {C.TEXT}order sell HBAR at 0.12 size 50{C.R}   {C.MUTED}Sell 50 HBAR for USDC when price ≥ $0.12{C.R}")
