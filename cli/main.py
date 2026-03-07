#!/usr/bin/env python3
"""
Pacman CLI - Operational Trading Interface
==========================================

Thin dispatcher. All command handlers live in cli/commands/*.
Responsible ONLY for:
1. Banner display
2. Building the COMMANDS dict
3. The process_input() dispatcher
4. The main() entry point loop
"""
import os
import sys
import time
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from src.controller import PacmanController
from src.errors import PacmanError, ConfigurationError
from src.logger import logger
from cli.display import C, print_security_warning

# Import command handlers from modules
from cli.commands.wallet import (
    cmd_setup, cmd_account, cmd_balance, cmd_send, cmd_receive,
    cmd_whitelist, cmd_associate, check_wallet_setup, check_saucerswap_api_key
)
from cli.commands.trading import handle_natural_language, cmd_swap_v1, cmd_slippage, cmd_lp_padding
from cli.commands.staking import cmd_stake, cmd_unstake
from cli.commands.liquidity import cmd_pool_deposit, cmd_pool_withdraw, cmd_lp_positions
from cli.commands.info import (
    cmd_help, cmd_tokens, cmd_sources, cmd_price,
    cmd_pools, cmd_history, cmd_verbose, cmd_refresh,
    cmd_install_service, cmd_uninstall_service, cmd_service_status
)
from cli.commands.orders import cmd_order
from cli.commands.robot import cmd_robot

# Load banner from cli.text_content
try:
    from cli.text_content import PACMAN_BANNER_TEMPLATE
    import socket
    hostname = socket.gethostname()
    PACMAN_BANNER = PACMAN_BANNER_TEMPLATE.format(
        ACCENT=C.ACCENT, CHROME=C.CHROME, MUTED=C.MUTED, 
        OK=C.OK, TEXT=C.TEXT, BRAND=C.BRAND, R=C.R
    )
except Exception:
    PACMAN_BANNER = f"{C.ACCENT}╔══════════════════════════════════════════╗{C.R}\n{C.ACCENT}║           PACMAN TRADING CLI           ║{C.R}\n{C.ACCENT}╚══════════════════════════════════════════╝{C.R}"

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

COMMANDS = {
    "setup": cmd_setup,
    "account": cmd_account,
    "balance": cmd_balance,
    "tokens": cmd_tokens, "t": cmd_tokens,
    "pools": cmd_pools, "pool": cmd_pools,
    "pool-deposit": cmd_pool_deposit,
    "pool-withdraw": cmd_pool_withdraw,
    "lp": cmd_lp_positions,
    "positions": cmd_lp_positions,
    "price": cmd_price,
    "history": cmd_history,
    "send": cmd_send,
    "receive": cmd_receive,
    "associate": cmd_associate, "assoc": cmd_associate,
    "swap-v1": cmd_swap_v1,
    "v1": cmd_swap_v1,
    "whitelist": cmd_whitelist,
    "stake": cmd_stake,
    "unstake": cmd_unstake,
    "sources": cmd_sources, "source": cmd_sources,
    "accounts": cmd_account,
    "verbose": cmd_verbose,
    "slippage": cmd_slippage,
    "lp-padding": cmd_lp_padding,
    "order": cmd_order, "orders": cmd_order,
    "robot": cmd_robot, "bot": cmd_robot,
    "refresh": cmd_refresh, "sync": cmd_refresh,
    "install-service": cmd_install_service,
    "uninstall-service": cmd_uninstall_service,
    "status-service": cmd_service_status,
    "help": cmd_help, "?": cmd_help, "-h": cmd_help,
}

def process_input(app, text):
    logger.info(f"User Input: {text}")
    parts = text.strip().split()
    if not parts: return

    # Strip --yes / -y flag (used by AI agents to skip confirmation)
    yes_flag = "--yes" in parts or "-y" in parts
    parts = [p for p in parts if p not in ("--yes", "-y")]
    if not parts: return

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in COMMANDS:
        try:
            # Pass yes_flag to commands that support it
            if yes_flag and cmd in ("swap", "swap-v1", "v1"):
                # Trading commands get yes_flag injected into args
                COMMANDS[cmd](app, args + ["--yes"])
            else:
                COMMANDS[cmd](app, args)
        except PacmanError as e:
            print(f"  {C.ERR}✗{C.R} {e}")
        except Exception as e:
            logger.error(f"Command Error ({cmd}): {e}", exc_info=True)
            print(f"  {C.ERR}✗{C.R} Unexpected Error: {e}")
    else:
        # Fallback to NLP
        try:
            handle_natural_language(app, text)
        except PacmanError as e:
            print(f"  {C.ERR}✗{C.R} {e}")

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    from src.logger import setup_mirror
    setup_mirror()

    # Verbose Mode Detection (CLI Override)
    verbose_requested = False
    if "--verbose" in sys.argv or "-v" in sys.argv:
        verbose_requested = True
        if "--verbose" in sys.argv: sys.argv.remove("--verbose")
        if "-v" in sys.argv: sys.argv.remove("-v")

    # Determine run mode
    has_args = len(sys.argv) > 1
    is_oneshot = has_args  # Any args = one-shot (agent/subprocess mode)
    is_daemon = has_args and sys.argv[1].lower() == "daemon"

    # Banner: ONLY in interactive mode (no args). Agents never see it.
    if not is_oneshot:
        print(PACMAN_BANNER)
        print_security_warning()

    # Initialize App (Logic)
    try:
        if verbose_requested:
            os.environ["PACMAN_VERBOSE"] = "true"
            
        app = PacmanController()
        
        # Wallet/API checks only in interactive mode (they use input() which breaks pipes)
        if not is_oneshot:
            check_wallet_setup(app)
            check_saucerswap_api_key(app)
        
        
        if not is_oneshot:
            print(f"\n  {C.BOLD}{C.ACCENT}System Online{C.R}")
    except ConfigurationError as e:
        print(f"  {C.ERR}✗{C.R} Config Error: {e}")
        return

    # ── DAEMON MODE ──────────────────────────────────────────────
    # Persistent headless mode: starts robot + order daemons, stays alive.
    # Usage: ./launch.sh daemon
    #        nohup ./launch.sh daemon &
    #        ./launch.sh daemon 2>&1 | tee daemon.log
    if is_daemon:
        import signal as _signal
        import time
        
        print(f"  {C.BOLD}🤖 Pacman Daemon Mode{C.R}")
        print(f"  {'─' * 45}")
        
        # Initialize and start Plugin Manager
        from src.core.plugin_manager import PluginManager
        pm = PluginManager(app)
        pm.discover_and_load()
        pm.start_all()
        
        # Start Secure API
        from src.core.api import start_api
        start_api(app)
        
        for p_name in pm.plugins:
            print(f"  {C.OK}✓{C.R} Plugin started: {p_name}")
        
        print(f"\n  {C.MUTED}Daemon alive. Ctrl-C or kill PID to stop.{C.R}")
        print(f"  {C.MUTED}PID: {os.getpid()}{C.R}")
        
        # Stay alive — sleep loop
        import json
        last_sync = time.time()
        start_time = time.time()
        status_file = root_dir / "data/status.json"
        
        try:
            while True:
                # 1. Heartbeat
                status = {
                    "pid": os.getpid(),
                    "uptime_sec": int(time.time() - start_time),
                    "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "plugins": pm.get_all_statuses(),
                    "last_pool_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_sync))
                }
                with open(status_file, "w") as f:
                    json.dump(status, f, indent=2)
                
                # 2. Periodic Refresh (24h = 86400s)
                if time.time() - last_sync > 86400:
                    try:
                        from scripts.refresh_data import refresh
                        print(f"\n  {C.BOLD}📡 Periodic pool refresh...{C.R}")
                        refresh(force=True)
                        app.router.load_pools()
                        last_sync = time.time()
                        print(f"  {C.OK}✓{C.R} Pools updated.")
                    except Exception as e:
                        print(f"  {C.ERR}✗{C.R} Periodic refresh failed: {e}")
                
                time.sleep(2)
        except KeyboardInterrupt:
            print(f"\n  {C.MUTED}Daemon shutting down.{C.R}")
            if status_file.exists():
                status_file.unlink()
        return

    # ── ONE-SHOT MODE ────────────────────────────────────────────
    # Agent / subprocess: run one command and exit.
    if is_oneshot:
        process_input(app, " ".join(sys.argv[1:]))
        return

    # ── INTERACTIVE MODE ─────────────────────────────────────────
    # Human TUI: banner already shown, show help, enter REPL.
    cmd_help(app, [])
    
    import select
    while True:
        try:
            # Print prompt safely
            sys.stdout.write(f"\n  {C.ACCENT}ᗧ{C.R} ")
            sys.stdout.flush()
            
            # Wait for input with a timeout so background prints don't permanently lock the terminal
            user_input = None
            while True:
                r, _, _ = select.select([sys.stdin], [], [], 0.5)
                if r:
                    user_input = sys.stdin.readline()
                    break
                    
            if not user_input:
                continue
                
            user_input = user_input.strip()
            if not user_input: 
                continue
                
            if user_input.lower() in ["exit", "quit", "q"]:
                print(f"  {C.MUTED}Shutting down.{C.R}")
                break

            process_input(app, user_input)

        except KeyboardInterrupt:
            print(f"\n  {C.MUTED}Interrupted.{C.R}")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()


# CLI entry point for compatibility
cli = main

