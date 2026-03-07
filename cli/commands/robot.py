#!/usr/bin/env python3
"""
CLI Commands: Robot (Power Law Rebalancer)
==========================================

Commands:
    robot signal  → Show today's heartbeat model signal (no trading)
    robot start   → Start the rebalancer daemon (background)
    robot stop    → Stop the daemon
    robot status  → Show bot status, portfolio, and last signal
"""

from cli.display import C
from src.logger import logger


# Module-level bot instance (persists across commands)
_bot_instance = None


def _get_or_create_bot(app):
    """Get or create the bot singleton."""
    global _bot_instance
    if _bot_instance is None:
        from src.plugins.power_law.bot import PowerLawBot
        _bot_instance = PowerLawBot(app)
    return _bot_instance


def cmd_robot(app, args):
    """Robot command dispatcher."""
    import json as _json
    
    # Strip --json flag before routing
    json_mode = "--json" in args
    args = [a for a in args if a != "--json"]
    
    if not args:
        _print_robot_help()
        return
    
    subcmd = args[0].lower()
    
    if subcmd == "signal":
        _cmd_signal(app)
    elif subcmd == "start":
        _cmd_start(app)
    elif subcmd == "stop":
        _cmd_stop(app)
    elif subcmd == "status":
        _cmd_status(app, json_mode=json_mode)
    elif subcmd in ("help", "?"):
        _print_robot_help()
    else:
        print(f"  {C.ERR}✗{C.R} Unknown robot command: {subcmd}")
        _print_robot_help()



def _cmd_signal(app):
    """Show today's heartbeat model signal without trading."""
    print(f"\n  {C.BOLD}🧠 Bitcoin Heartbeat Model Signal{C.R}")
    print(f"  {'─' * 45}")
    
    bot = _get_or_create_bot(app)
    signal = bot.get_signal()
    
    if not signal:
        print(f"  {C.ERR}✗{C.R} Could not compute signal (check BTC price feed)")
        return
    
    alloc = signal.get("allocation_pct", 0)
    floor_price = signal.get("floor", 0)
    ceiling = signal.get("ceiling", 0)
    model_price = signal.get("model_price", 0)
    band_pos = signal.get("position_in_band_pct", 0)
    valuation = signal.get("valuation", "unknown")
    stance = signal.get("stance", "unknown")
    cycle = signal.get("cycle", 0)
    cycle_pct = signal.get("cycle_progress_pct", 0)
    phase = signal.get("phase", "unknown")
    tagline = signal.get("tagline", "")
    
    # Color the allocation based on stance
    if alloc >= 70:
        alloc_color = C.OK  # Green — accumulate
    elif alloc >= 40:
        alloc_color = C.ACCENT  # Yellow — balanced
    else:
        alloc_color = C.ERR  # Red — trim/protect
    
    print(f"  {C.BOLD}Target BTC Allocation:{C.R}  {alloc_color}{alloc:.0f}%{C.R}")
    print(f"  {C.BOLD}Valuation:{C.R}              {valuation.replace('_', ' ').title()}")
    print(f"  {C.BOLD}Stance:{C.R}                 {stance.replace('_', ' ').title()}")
    print()
    print(f"  {C.MUTED}Floor Price:{C.R}           ${floor_price:,.0f}")
    print(f"  {C.MUTED}Model Fair Value:{C.R}      ${model_price:,.0f}")
    print(f"  {C.MUTED}Ceiling Price:{C.R}         ${ceiling:,.0f}")
    print(f"  {C.MUTED}Band Position:{C.R}         {band_pos:.1f}%")
    print()
    print(f"  {C.MUTED}Cycle:{C.R}                 {cycle} ({cycle_pct:.1f}% complete)")
    print(f"  {C.MUTED}Phase:{C.R}                 {phase.replace('_', ' ').title()}")
    
    if tagline:
        print(f"\n  {C.ACCENT}💬{C.R} {tagline}")


def _cmd_start(app):
    """Start the rebalancer daemon."""
    bot = _get_or_create_bot(app)
    
    if bot.running:
        print(f"  {C.ACCENT}ℹ{C.R} Robot is already running")
        return
    
    sim_tag = f" {C.ACCENT}(SIMULATION MODE){C.R}" if bot.config.simulate else ""
    print(f"  {C.OK}🤖{C.R} Starting Power Law rebalancer...{sim_tag}")
    print(f"  {C.MUTED}   Threshold: {bot.config.threshold_percent}% | "
          f"Interval: {bot.config.interval_seconds}s{C.R}")
    
    if not bot.config.simulate:
        print(f"  {C.ERR}⚠️  LIVE TRADING MODE — real transactions will execute!{C.R}")
    
    bot.start()
    print(f"  {C.OK}✓{C.R} Robot daemon started in background")


def _cmd_stop(app):
    """Stop the rebalancer daemon."""
    global _bot_instance
    
    if _bot_instance is None or not _bot_instance.running:
        print(f"  {C.MUTED}Robot is not running.{C.R}")
        return
    
    _bot_instance.stop()
    print(f"  {C.OK}✓{C.R} Robot stopped. Trades executed this session: {_bot_instance.trades_executed}")


def _cmd_status(app, json_mode=False):
    """Show comprehensive bot status."""
    import json as _json
    bot = _get_or_create_bot(app)
    status = bot.get_status()
    
    if json_mode:
        # Emit clean structured output for AI parsing  
        out = {
            "running": status.get("running", False),
            "simulate": status.get("simulate", True),
            "model": status.get("model", "HEARTBEAT"),
            "threshold_pct": status.get("threshold", 15.0),
            "interval_seconds": status.get("interval_seconds", 3600),
            "trades_executed": status.get("trades_executed", 0),
            "last_check": status.get("last_check"),
            "last_rebalance": status.get("last_rebalance"),
            "portfolio": None,
            "signal": None,
        }
        port = status.get("portfolio")
        if port:
            out["portfolio"] = {
                "wbtc_balance": port.get("wbtc_balance", 0),
                "wbtc_percent": round(port.get("wbtc_percent", 0), 2),
                "usdc_balance": port.get("usdc_balance", 0),
                "hbar_balance": round(port.get("hbar_balance", 0), 6),
                "total_usd": round(port.get("total_value_usd", 0), 2),
            }
        sig = status.get("signal")
        if sig:
            out["signal"] = {
                "allocation_pct": sig.get("allocation_pct", 0),
                "valuation": sig.get("valuation"),
                "stance": sig.get("stance"),
                "phase": sig.get("phase"),
                "price_floor": sig.get("floor"),
                "price_ceiling": sig.get("ceiling"),
                "position_in_band_pct": sig.get("position_in_band_pct"),
            }
        print(_json.dumps(out, indent=2))
        return
    
    print(f"\n  {C.BOLD}🤖 Power Law Robot Status{C.R}")
    print(f"  {'─' * 45}")
    
    running_str = f"{C.OK}RUNNING{C.R}" if status["running"] else f"{C.MUTED}STOPPED{C.R}"
    sim_str = f" {C.ACCENT}(sim){C.R}" if status["simulate"] else f" {C.ERR}(LIVE){C.R}"
    print(f"  {C.BOLD}State:{C.R}      {running_str}{sim_str}")
    print(f"  {C.BOLD}Model:{C.R}      {status['model']}")
    print(f"  {C.BOLD}Threshold:{C.R}  {status['threshold']}%")
    print(f"  {C.BOLD}Trades:{C.R}     {status['trades_executed']}")
    
    if status.get("last_check"):
        print(f"  {C.BOLD}Last check:{C.R} {status['last_check']}")
    if status.get("last_rebalance"):
        print(f"  {C.BOLD}Last trade:{C.R} {status['last_rebalance']}")
    
    portfolio = status.get("portfolio")
    if portfolio:
        print(f"\n  {C.BOLD}Portfolio:{C.R}")
        print(f"    WBTC: {portfolio['wbtc_balance']:.8f} ({portfolio['wbtc_percent']:.1f}%)")
        print(f"    USDC: {portfolio['usdc_balance']:.2f}")
        print(f"    HBAR: {portfolio['hbar_balance']:.2f} (gas)")
        print(f"    Total: ${portfolio['total_value_usd']:,.2f}")
    
    signal = status.get("signal")
    if signal:
        print(f"\n  {C.BOLD}Signal:{C.R}")
        print(f"    Target: {signal.get('allocation_pct', 0):.0f}% BTC")
        print(f"    Stance: {signal.get('stance', 'unknown').replace('_', ' ').title()}")
    
    # Recent activity
    log = status.get("activity_log", [])
    if log:
        print(f"\n  {C.BOLD}Recent Activity:{C.R}")
        for entry in log[-5:]:
            ts = entry.get("timestamp", "")[:19]
            msg = entry.get("message", "")
            print(f"    {C.MUTED}{ts}{C.R} {msg}")



def _print_robot_help():
    """Print robot command help."""
    print(f"\n  {C.BOLD}🤖 Power Law Robot Commands{C.R}")
    print(f"  {'─' * 45}")
    print(f"  {C.ACCENT}robot signal{C.R}   Show today's heartbeat model signal")
    print(f"  {C.ACCENT}robot start{C.R}    Start rebalancer daemon (background)")
    print(f"  {C.ACCENT}robot stop{C.R}     Stop the daemon")
    print(f"  {C.ACCENT}robot status{C.R}   Show bot status and portfolio")
    print()
    print(f"  {C.MUTED}Configure via .env:{C.R}")
    print(f"  {C.MUTED}  ROBOT_THRESHOLD_PERCENT=15.0  (15% = optimal){C.R}")
    print(f"  {C.MUTED}  ROBOT_INTERVAL_SECONDS=3600   (check hourly){C.R}")
    print(f"  {C.MUTED}  ROBOT_SIMULATE=true           (safe mode){C.R}")
