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

import sys
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
    cmd_pools, cmd_history, cmd_verbose
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
    "help": cmd_help, "?": cmd_help, "-h": cmd_help,
}

def process_input(app, text):
    logger.info(f"User Input: {text}")
    parts = text.strip().split()
    if not parts: return

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in COMMANDS:
        try:
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

    print(PACMAN_BANNER)
    print_security_warning()

    # Initialize App (Logic)
    try:
        if verbose_requested:
            import os
            os.environ["PACMAN_VERBOSE"] = "true"
            
        app = PacmanController()
        
        # Check for API Key and Wallet Setup
        check_wallet_setup(app)
        check_saucerswap_api_key(app)
        
        # Auto-start Limit Order Daemon if enabled in settings
        if app.limit_engine._daemon_enabled:
            app.limit_engine.start_monitor(app)
        
        print(f"\n  {C.BOLD}{C.ACCENT}System Online{C.R}")
    except ConfigurationError as e:
        print(f"  {C.ERR}✗{C.R} Config Error: {e}")
        return

    # One-Shot Mode
    if len(sys.argv) > 1:
        process_input(app, " ".join(sys.argv[1:]))
        return

    # Interactive Mode
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
