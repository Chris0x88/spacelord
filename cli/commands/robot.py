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


# Module-level bot instance (for interactive/one-shot use within this process)
_bot_instance = None
PID_FILE = "data/robot.pid"


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
    elif subcmd == "run-internal":
        _cmd_run_internal(app)
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
        
    print(f"\n  {C.BOLD}🤖 Power Law Robot Deployment{C.R}")
    print(f"  {C.CHROME}{'─' * 45}{C.R}")
    
    # Check if a robot account is already configured in .env
    robot_id = app.config.robot_account_id
    if not robot_id:
        # Check local account registry for "Robot"
        try:
            from pathlib import Path
            acc_path = Path("data/accounts.json")
            if acc_path.exists():
                with open(acc_path) as f:
                    accs = _json.load(f)
                    if isinstance(accs, list):
                        for acc in accs:
                            if acc.get("nickname") == "Robot":
                                robot_id = acc.get("id")
                                break
                    elif isinstance(accs, dict):
                        for aid, meta in accs.items():
                            if meta.get("nickname") == "Robot":
                                robot_id = aid
                                break
        except: pass
    
    if robot_id:
        if app.config.hedera_account_id != robot_id:
            # Hands-free: auto-link and persist
            if not app.config.robot_account_id:
                app.config.robot_account_id = robot_id
                print(f"  {C.OK}✓{C.R} Hands-free: Auto-linked Dedicated Robot account: {C.BOLD}{robot_id}{C.R}")
                
                # Persist to robot_state.json so it's sticky
                try:
                    import json
                    from pathlib import Path
                    state_path = Path("data/robot_state.json")
                    state_data = {}
                    if state_path.exists():
                        with open(state_path) as f:
                            state_data = json.load(f)
                    state_data["robot_account_id"] = robot_id
                    with open(state_path, "w") as f:
                        json.dump(state_data, f, indent=2)
                except Exception as e:
                    logger.debug(f"Failed to persist robot_account_id: {e}")
    else:
        # No robot account found anywhere
        print(f"  {C.MUTED}Security Best Practice: Run the robot in an isolated child account{C.R}")
        print(f"  {C.MUTED}so your daily transactions don't disturb its target thresholds.{C.R}")
        confirm = input(f"\n  Would you like to create a dedicated Child Account now? {C.MUTED}(y/N){C.R} ").strip().lower()
        
        if confirm in ["y", "yes"]:
            print(f"\n  {C.MUTED}Creating isolated sub-account...{C.R}")
            # Use AccountManager plugin logic
            try:
                # Check current HBAR for initial funding
                cur_bal = app.executor.get_balances().get("HBAR", 0)
                init_bal = 1.0 if cur_bal > 1.5 else 0.1
                
                # Use the AccountManager if available via discovery
                # In CLI, we might need direct import if PM isn't fully active
                from src.plugins.account_manager import AccountManager
                am = AccountManager(app)
                new_id = am.create_sub_account(initial_balance=init_bal, nickname="Robot")
                
                if new_id:
                    print(f"  {C.OK}✅ Created Robot Sub-account: {C.BOLD}{new_id}{C.R}")
                    
                    # Persist immediately
                    try:
                        import json
                        from pathlib import Path
                        state_path = Path("data/robot_state.json")
                        state_data = {}
                        if state_path.exists():
                            with open(state_path) as f:
                                state_data = json.load(f)
                        state_data["robot_account_id"] = new_id
                        with open(state_path, "w") as f:
                            json.dump(state_data, f, indent=2)
                        app.config.robot_account_id = new_id
                        print(f"  {C.OK}✓{C.R} Auto-linked and persisted to robot_state.json")
                    except Exception as e:
                        logger.debug(f"Persistence failed: {e}")

                    print(f"  {C.MUTED}Note: This account is derived from your primary key.{C.R}")
                    print(f"  {C.MUTED}Please transfer your WBTC/USDC allocation to this ID to begin.{C.R}")
            except Exception as e:
                print(f"  {C.ERR}✗{C.R} Failed to create sub-account: {e}")
                return
    
    import subprocess
    import os
    import sys
    
    # Check if already running via PID file
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0) # Check if process exists
            print(f"  {C.ACCENT}ℹ{C.R} Robot is already running (PID: {pid})")
            return
        except (ProcessLookupError, ValueError, OverflowError):
            os.remove(PID_FILE)
    
    sim_tag = f" {C.ACCENT}(SIMULATION MODE){C.R}" if bot.config.simulate else ""
    print(f"\n  {C.OK}🤖{C.R} Starting Power Law rebalancer...{sim_tag}")
    print(f"  {C.MUTED}   Threshold: {bot.config.threshold_percent}% | "
          f"Interval: {bot.config.interval_seconds}s{C.R}")
    
    if not bot.config.simulate:
        print(f"  {C.ERR}⚠️  LIVE TRADING MODE — real transactions will execute!{C.R}")
    
    # Spawn detached process
    try:
        # We use the same command line as 'daemon' mode but filtered for robot
        # This ensures the bot runs in a clean environment.
        cmd = [sys.executable, "-m", "cli.main", "robot", "run-internal"]
        
        # Log to daemon_output.log
        log_file = open("daemon_output.log", "a")
        
        # Start detached
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
            cwd=os.getcwd()
        )
        
        # Write PID
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
            
        print(f"  {C.OK}✓{C.R} Robot daemon started in background (PID: {proc.pid})")
    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Failed to start robot daemon: {e}")


def _cmd_stop(app):
    """Stop the rebalancer daemon."""
    import os
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            
            print(f"  {C.MUTED}Stopping robot (PID: {pid})...{C.R}")
            os.kill(pid, 15) # SIGTERM
            
            # Wait a bit then force if needed?
            import time
            for _ in range(5):
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                except ProcessLookupError:
                    break
            else:
                os.kill(pid, 9) # SIGKILL
            
            os.remove(PID_FILE)
            print(f"  {C.OK}✓{C.R} Robot stopped.")
            return
        except Exception as e:
            print(f"  {C.ERR}✗{C.R} Error stopping robot: {e}")
            if os.path.exists(PID_FILE): os.remove(PID_FILE)
    
    print(f"  {C.MUTED}Robot is not running.{C.R}")


def _cmd_run_internal(app):
    """Internal use only: starts bot thread and keeps process alive."""
    bot = _get_or_create_bot(app)
    # Reset running state for the new process
    bot.stop_plugin() 
    bot.start_plugin()
    
    try:
        # Keep process alive while bot is running
        while bot.running:
            import time
            time.sleep(1)
            # If the thread actually died but 'running' is still true, exit
            if not bot.is_alive():
                logger.error("[Robot] Thread died unexpectedly.")
                break
    except KeyboardInterrupt:
        bot.stop_plugin()

def _cmd_status(app, json_mode=False):
    """Show comprehensive bot status."""
    import json as _json
    import os
    bot = _get_or_create_bot(app)
    status = bot.get_status()
    
    is_running = False
    pid = None
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            is_running = True
        except (ProcessLookupError, ValueError):
            pass

    if json_mode:
        # Emit clean structured output for AI parsing  
        out = {
            "running": is_running,
            "pid": pid if is_running else None,
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
    
    import os
    is_running = False
    pid = None
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            is_running = True
        except (ProcessLookupError, ValueError):
            if os.path.exists(PID_FILE): os.remove(PID_FILE)

    running_str = f"{C.OK}RUNNING{C.R}" if is_running else f"{C.MUTED}STOPPED{C.R}"
    pid_str = f" (PID: {pid})" if pid and is_running else ""
    sim_str = f" {C.ACCENT}(sim){C.R}" if status["simulate"] else f" {C.ERR}(LIVE){C.R}"
    print(f"  {C.BOLD}State:{C.R}      {running_str}{sim_str}{pid_str}")
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
    print(f"  {C.MUTED}  ROBOT_ACCOUNT_ID=(0.0.x)      (dedicated child account){C.R}")
    print(f"  {C.MUTED}  ROBOT_THRESHOLD_PERCENT=15.0  (15% = optimal){C.R}")
    print(f"  {C.MUTED}  ROBOT_SIMULATE=true           (default: safe mode){C.R}")
    print()
    print(f"  {C.BOLD}OpenClaw Integration:{C.R}")
    print(f"  {C.MUTED}To pull the latest Power Law chart into OpenClaw or an AI Agent:{C.R}")
    print(f"  {C.ACCENT}GET http://127.0.0.1:8088/chart.png?secret=YOUR_PACMAN_API_SECRET{C.R}")
    print()
    print(f"  {C.BOLD}Startup Explainer:{C.R}")
    print(f"  {C.MUTED}1. Run 'robot start' to initiate background monitoring.{C.R}")
    print(f"  {C.MUTED}2. If prompted, create a Child Account to isolate trading.{C.R}")
    print(f"  {C.MUTED}3. Ensure the Parent Account has >1 HBAR to fund gas fees.{C.R}")
    print(f"  {C.MUTED}4. Dashboard: http://127.0.0.1:8088 (Glassmorphism UI){C.R}")
