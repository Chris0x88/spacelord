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
    cmd_whitelist, cmd_associate, cmd_status, cmd_fund, cmd_backup_keys,
    check_wallet_setup, check_saucerswap_api_key
)
from cli.commands.nfts import cmd_nfts
from cli.commands.trading import handle_natural_language, cmd_swap_v1, cmd_slippage, cmd_lp_padding
from cli.commands.staking import cmd_stake, cmd_unstake
from cli.commands.liquidity import cmd_pool_deposit, cmd_pool_withdraw, cmd_lp_positions
from cli.commands.info import (
    cmd_help, cmd_tokens, cmd_sources, cmd_price,
    cmd_pools, cmd_history, cmd_verbose, cmd_refresh,
    cmd_install_service, cmd_uninstall_service, cmd_service_status,
    cmd_docs
)
from cli.commands.orders import cmd_order
from cli.commands.hcs import cmd_hcs
from cli.commands.hcs10 import cmd_hcs10
from cli.commands.robot import cmd_robot
from cli.commands.agent_sync import cmd_agent_sync
from cli.commands.doctor import cmd_doctor
from cli.commands.telegram import cmd_telegram
from cli.commands.discord import cmd_discord

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

def cmd_logs(app, args):
    """Show recent agent interaction logs and failure summary."""
    import json as _json
    from src.agent_log import get_recent, get_failure_summary
    clean = [a for a in args if a not in ("--yes", "-y", "--json")]
    n = int(clean[0]) if clean and clean[0].isdigit() else 20

    if "--json" in args:
        print(_json.dumps({"recent": get_recent(n), "failures": get_failure_summary()}, indent=2, default=str))
        return

    entries = get_recent(n)
    if not entries:
        print(f"  {C.MUTED}No interactions logged yet.{C.R}")
        return

    failures = get_failure_summary()
    if failures:
        print(f"\n  {C.ERR}Recurring Failures:{C.R}")
        for err, info in failures.items():
            print(f"  {C.WARN}{info['count']}x{C.R} {err}")
            print(f"      {C.MUTED}Last: {info['last_ts']} | Example: {info['example_command']}{C.R}")
        print()

    print(f"  {C.BOLD}Last {len(entries)} Interactions:{C.R}")
    for e in entries:
        status = f"{C.OK}OK{C.R}" if e.get("result") == "success" else f"{C.ERR}FAIL{C.R}"
        ts = e.get("ts", "")[:19]
        cmd = e.get("command", "?")[:60]
        ms = e.get("duration_ms", 0)
        print(f"  {C.MUTED}{ts}{C.R} [{status}] {cmd} {C.MUTED}({ms:.0f}ms){C.R}")
        if e.get("error"):
            print(f"           {C.ERR}{e['error'][:80]}{C.R}")


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def _cmd_swap(app, args):
    """Route swap commands through the NLP handler for natural language parsing."""
    handle_natural_language(app, "swap " + " ".join(args))

COMMANDS = {
    # --- Trading ---
    "swap": _cmd_swap, "buy": _cmd_swap, "sell": _cmd_swap, "trade": _cmd_swap,
    "swap-v1": cmd_swap_v1, "v1": cmd_swap_v1,
    "slippage": cmd_slippage,
    "price": cmd_price,
    # --- Portfolio ---
    "balance": cmd_balance,
    "status": cmd_status, "whoami": cmd_status, "info": cmd_status,
    "history": cmd_history,
    "tokens": cmd_tokens, "t": cmd_tokens,
    "sources": cmd_sources,
    "nfts": cmd_nfts,
    # --- Transfers ---
    "send": cmd_send,
    "receive": cmd_receive,
    "whitelist": cmd_whitelist,
    # --- Account ---
    "account": cmd_account, "accounts": cmd_account,
    "associate": cmd_associate, "assoc": cmd_associate,
    "setup": cmd_setup,
    "fund": cmd_fund, "faucet": cmd_fund,
    "backup-keys": cmd_backup_keys, "export-keys": cmd_backup_keys,
    # --- Staking ---
    "stake": cmd_stake,
    "unstake": cmd_unstake,
    # --- Liquidity ---
    "pool-deposit": cmd_pool_deposit,
    "pool-withdraw": cmd_pool_withdraw,
    "lp": cmd_lp_positions, "positions": cmd_lp_positions,
    "pools": cmd_pools, "pool": cmd_pools,
    "lp-padding": cmd_lp_padding,
    # --- Orders ---
    "order": cmd_order, "orders": cmd_order,
    # --- Robot ---
    "robot": cmd_robot, "bot": cmd_robot,
    # --- Messaging ---
    "hcs": cmd_hcs,
    "hcs10": cmd_hcs10,
    # --- Telegram Fast Lane ---
    "tg": cmd_telegram, "telegram": cmd_telegram,
    # --- Discord Fast Lane ---
    "dc": cmd_discord, "discord": cmd_discord,
    # --- System ---
    "doctor": cmd_doctor,
    "refresh": cmd_refresh, "sync": cmd_refresh,
    "verbose": cmd_verbose,
    "logs": cmd_logs, "log": cmd_logs,
    "docs": cmd_docs, "doc": cmd_docs,
    "help": cmd_help, "?": cmd_help, "-h": cmd_help,
    # --- Agent ---
    "agent-sync": cmd_agent_sync,
    # --- Services ---
    "install-service": cmd_install_service,
    "uninstall-service": cmd_uninstall_service,
    "status-service": cmd_service_status,
}

def _is_auto_yes(args: list) -> bool:
    """Check if --yes flag is present or stdin is non-interactive (OpenClaw/pipe)."""
    return "--yes" in args or "-y" in args or not sys.stdin.isatty()

def _safe_input(prompt: str, args: list = None, default: str = "y") -> str:
    """
    Safe input() wrapper for AI agent compatibility.
    If --yes is in args or stdin is non-interactive, returns default without prompting.
    Prevents EOFError crashes when driven by OpenClaw exec or pipes.
    """
    if args and _is_auto_yes(args):
        return default
    if not sys.stdin.isatty():
        return default
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return default

def process_input(app, text):
    logger.info(f"User Input: {text}")
    parts = text.strip().split()
    if not parts: return

    # Strip --yes / -y flag (used by AI agents to skip confirmation)
    explicit_yes = "--yes" in parts or "-y" in parts
    parts = [p for p in parts if p not in ("--yes", "-y")]
    if not parts: return

    cmd = parts[0].lower()
    args = parts[1:]

    # Only inject --yes into args if the caller explicitly passed it.
    # Non-interactive auto-yes is handled by _safe_input() which checks isatty() directly.
    # Injecting --yes on every non-TTY call breaks positional args (e.g. `balance HBAR`).
    if explicit_yes and "--yes" not in args:
        args = args + ["--yes"]

    # Agent interaction logging — capture every command's input, output, errors
    from src.agent_log import log_interaction, capture_output
    import traceback as _tb
    _t0 = time.time()
    _result = "success"
    _error = None
    _stack = None
    _source = "oneshot" if len(sys.argv) > 1 else "interactive"
    _account_id = getattr(getattr(app, 'executor', None), 'hedera_account_id', None)

    with capture_output() as _cap:
        if cmd in COMMANDS:
            try:
                COMMANDS[cmd](app, args)
            except PacmanError as e:
                _result, _error = "error", str(e)
                print(f"  {C.ERR}✗{C.R} {e}")
            except Exception as e:
                _result, _error = "error", str(e)
                _stack = _tb.format_exc()
                logger.error(f"Command Error ({cmd}): {e}", exc_info=True)
                print(f"  {C.ERR}✗{C.R} Unexpected Error: {e}")
        else:
            # Fallback to NLP
            try:
                handle_natural_language(app, text)
            except PacmanError as e:
                _result, _error = "error", str(e)
                print(f"  {C.ERR}✗{C.R} {e}")
            except Exception as e:
                _result, _error = "error", str(e)
                _stack = _tb.format_exc()

    _duration = (time.time() - _t0) * 1000
    log_interaction(command=text, result=_result, error=_error,
                    duration_ms=_duration, source=_source,
                    output=_cap.get_output(), stack_trace=_stack,
                    account_id=_account_id)

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
        
        for p_name in pm.plugins:
            print(f"  {C.OK}✓{C.R} Plugin started: {p_name}")

        # 4. Attach PluginManager to the controller for memory-bridged API
        app.pm = pm
        
        # 5. Start Secure API bridge (Daemon Thread)
        start_api(app)
        
        print(f"\n  {C.MUTED}Daemon alive. Ctrl-C or kill PID to stop.{C.R}")
        print(f"  {C.MUTED}PID: {os.getpid()}{C.R}")
        
        # Stay alive — sleep loop
        import json
        last_sync = time.time()
        start_time = time.time()
        app.start_time = start_time
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

