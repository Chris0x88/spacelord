#!/usr/bin/env python3
"""
Pacman CLI - Operational Trading Interface
==========================================

The View Layer.
Responsible ONLY for:
1. Handling User Input (Arguments, Interactive)
2. Displaying Output (Colors, Tables, Errors)
3. Calling the Logic Layer (PacmanApp)
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import json
from src.controller import PacmanController
from src.errors import PacmanError, ConfigurationError
from src.logger import logger
from cli.display import (
    C, print_security_warning,
    show_help, show_tokens, show_sources, show_price,
    show_balance, show_account, show_history,
    print_receipt, print_transfer_receipt
)
from src.translator import translate

# Load banner from data.text_content
try:
    from data.text_content import PACMAN_BANNER_TEMPLATE
    import socket
    hostname = socket.gethostname()
    PACMAN_BANNER = PACMAN_BANNER_TEMPLATE.format(
        ACCENT=C.ACCENT, CHROME=C.CHROME, MUTED=C.MUTED, 
        OK=C.OK, TEXT=C.TEXT, BRAND=C.BRAND, R=C.R
    )
except Exception:
    PACMAN_BANNER = f"{C.ACCENT}╔══════════════════════════════════════════╗{C.R}\n{C.ACCENT}║           PACMAN TRADING CLI           ║{C.R}\n{C.ACCENT}╚══════════════════════════════════════════╝{C.R}"

# ---------------------------------------------------------------------------
# Command Handlers (View Logic)
# ---------------------------------------------------------------------------

def cmd_help(app, args):
    topic = args[0] if args else None
    
    # Map Aliases
    aliases = {
        "trade": "swap",
        "buy":   "swap",
        "get":   "swap",
        "convert":"swap",
        "transfers": "send",
        "transfer": "send",
        "wallet": "balance",
        "prices": "price",
        "natural": "nlp",
        "rules":   "nlp",
        "grammar": "nlp"
    }
    
    if topic and topic.lower() in aliases:
        topic = aliases[topic.lower()]
        
    show_help(topic)

def cmd_tokens(app, args):
    show_tokens()

def cmd_sources(app, args):
    show_sources()

def cmd_price(app, args):
    if len(args) >= 1:
        show_price(args[0])
    else:
        # Show all
        from cli.display import show_all_prices
        show_all_prices()

def cmd_account(app, args):
    show_account(app.executor)

def cmd_balance(app, args):
    token = args[0] if args else None
    show_balance(app.executor, single_token=token)

def cmd_history(app, args):
    show_history(app.executor)

def cmd_send(app, args):
    # Syntax: send <amount> <token> to <recipient>
    # args: [100, HBAR, to, 0.0.123]
    if len(args) < 4 or args[2].lower() != "to":
        print(f"  {C.ERR}✗{C.R} Usage: {C.BOLD}send <amount> <token> to <recipient>{C.R}")
        return

    try:
        amount = float(args[0])
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid amount: {args[0]}")
        return

    symbol = args[1].upper()
    recipient = args[3]

    print(f"\n  {C.ACCENT}↗{C.R} Transfer: {C.TEXT}{amount} {symbol}{C.R} → {C.TEXT}{recipient}{C.R}")

    if app.config.require_confirmation:
        confirm = input(f"  Confirm? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    print(f"  {C.MUTED}Submitting...{C.R}")
    res = app.transfer(symbol, amount, recipient)

    if res["success"]:
        print_transfer_receipt(res)
    else:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {res.get('error')}")

def cmd_receive(app, args):
    """
    Show wallet address and check token associations.

    Usage: receive [token_symbol]
    If token provided, checks if account is associated (and offers to associate).
    """
    if not app.executor:
        print(f"  {C.ERR}✗{C.R} Engine not initialized.")
        return

    # 1. Show Address
    print(f"\n{C.BOLD}{C.TEXT}  RECEIVE FUNDS{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.MUTED}Hedera ID:{C.R}    {C.TEXT}{app.executor.hedera_account_id}{C.R}")
    print(f"  {C.MUTED}EVM Address:{C.R}  {C.TEXT}{app.executor.eoa}{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")

    # 2. Check Token Association (if requested)
    if not args:
        print(f"  {C.OK}✓{C.R} You can receive HBAR anytime.")
        print(f"  {C.MUTED}To check a token, run: {C.TEXT}receive <token>{C.R}")
        print()
        return

    token_symbol = args[0].upper()
    if token_symbol in ["HBAR", "HBARX"]:
        print(f"  {C.OK}✓{C.R} HBAR is native. No association needed.")
        print()
        return

    # Resolve ID
    token_id = app.resolve_token_id(token_symbol)
    if not token_id:
        print(f"  {C.WARN}⚠{C.R} Unknown token '{token_symbol}'.")
        print(f"  Ensure sender uses your Hedera ID or EVM Address.")
        print()
        return

    print(f"  Checking status for {C.BOLD}{token_symbol}{C.R} ({token_id})...")

    is_associated = app.executor.check_token_association(token_id)
    if is_associated:
        print(f"  {C.OK}✓{C.R} Associated. Ready to receive {token_symbol}.")
    else:
        print(f"  {C.WARN}⚠  NOT ASSOCIATED{C.R}")
        print(f"  You must associate {token_symbol} before receiving it.")

        if app.config.require_confirmation:
            confirm = input(f"\n  Associate now? (cost ~0.05 HBAR) {C.MUTED}(y/n){C.R} ").strip().lower()
            if confirm not in ["y", "yes"]:
                print(f"  {C.MUTED}Cancelled.{C.R}")
                return

        print(f"  {C.MUTED}Associating...{C.R}")
        success = app.executor.associate_token(token_id)
        if success:
            print(f"  {C.OK}✓{C.R} Successfully associated {token_symbol}!")
        else:
            print(f"  {C.ERR}✗{C.R} Association failed.")
    print()

def cmd_verbose(app, args):
    """Toggle or set verbose mode."""
    if not args:
        enabled = app.toggle_verbose()
    else:
        val = args[0].lower()
        if val in ["on", "true", "1"]:
            enabled = app.toggle_verbose(True)
        elif val in ["off", "false", "0"]:
            enabled = app.toggle_verbose(False)
        else:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}verbose [on/off]{C.R}")
            return
    
    from cli.display import C
    status = f"{C.OK}ON{C.R}" if enabled else f"{C.WARN}OFF{C.R}"
    print(f"  Verbose Mode: {status}")

def cmd_pools(app, args):
    """
    Manage pool registries (search, list, approve, delete).
    Usage: pools <action> [args] [--v1|--v2]
    """
    if not args:
        print(f"\n  {C.BOLD}POOLS COMMANDS{C.R}")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  {C.TEXT}pools list{C.R}             List all approved pools")
        print(f"  {C.TEXT}pools search <q>{C.R}       Search on-chain pools (symbol/ID)")
        print(f"  {C.TEXT}pools approve <id>{C.R}    Add pool to approved list")
        print(f"  {C.TEXT}pools delete <id>{C.R}     Remove pool from list")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  Use {C.MUTED}--v1{C.R} or {C.MUTED}--v2{C.R} to filter protocol (Default: V2)")
        print()
        return

    action = args[0].lower()
    sub_args = args[1:]
    
    # Extract flags
    v1_flag = "--v1" in sub_args
    v2_flag = "--v2" in sub_args
    if v1_flag: sub_args.remove("--v1")
    if v2_flag: sub_args.remove("--v2")
    
    protocol = "v1" if v1_flag else "v2"

    if action == "list":
        _pools_list(app)
    elif action == "search":
        if not sub_args:
            print(f"  {C.ERR}✗{C.R} Missing search query.")
            return
        _pools_search(app, sub_args[0], protocol if (v1_flag or v2_flag) else "both")
    elif action == "approve":
        if not sub_args:
            print(f"  {C.ERR}✗{C.R} Missing pool ID.")
            return
        _pools_approve(app, sub_args[0], protocol)
    elif action == "delete" or action == "remove":
        if not sub_args:
            print(f"  {C.ERR}✗{C.R} Missing pool ID.")
            return
        _pools_delete(app, sub_args[0], protocol)
    else:
        print(f"  {C.ERR}✗{C.R} Unknown action: {action}")

def _pools_list(app):
    """Show the currently approved pools from JSON files."""
    import json
    from pathlib import Path
    
    registries = [
        ("V2 (Direct)", "data/pools.json"),
        ("V1 (Legacy)", "data/v1_pools_approved.json")
    ]
    
    print(f"\n{C.BOLD}{C.TEXT}  APPROVED POOL REGISTRIES{C.R}")
    
    for label, path_str in registries:
        p = Path(path_str)
        print(f"\n  {C.ACCENT}■ {label}{C.R} {C.MUTED}({path_str}){C.R}")
        if not p.exists():
            print(f"    {C.MUTED}No file found.{C.R}")
            continue
            
        with open(p) as f:
            data = json.load(f)
            if not data:
                print(f"    {C.MUTED}Registry is empty.{C.R}")
            else:
                print(f"    {C.CHROME}{'ID':<12} {'LABEL':<20} {'FEE':<6}{C.R}")
                for entry in data:
                    cid = entry.get("contractId", "N/A")
                    lbl = entry.get("label", "Unknown")
                    fee = entry.get("fee")
                    fee_str = str(fee) if fee is not None else "N/A"
                    print(f"    {C.TEXT}{cid:<12} {lbl:<20} {fee_str:<6}{C.R}")
    print()

def _pools_search(app, query, protocol):
    """Perform on-chain discovery using the Sidecar module."""
    from src.discovery import DiscoveryManager
    discovery = DiscoveryManager()
    
    protocols = ["v1", "v2"] if protocol == "both" else [protocol]
    
    print(f"\n  {C.ACCENT}🔍 Searching on-chain...{C.R} (Query: {C.BOLD}{query}{C.R})")
    
    found_any = False
    for p_type in protocols:
        results = discovery.search_pools(query, protocol=p_type)
        if not results:
            continue
            
        found_any = True
        print(f"\n  {C.BOLD}{p_type.upper()} Results:{C.R}")
        print(f"  {C.CHROME}{'ID':<12} {'PAIR':<20} {'LIQUIDITY':<15}{C.R}")
        for r in results[:10]: # Cap at 10 for readability
            cid = r.get("contractId", "N/A")
            tA = r.get("tokenA", {}).get("symbol", "???")
            tB = r.get("tokenB", {}).get("symbol", "???")
            # Liquidity handling varies by protocol in API
            liq = r.get("tvlUsd") or r.get("liquidityUsd") or 0
            liq_str = f"${float(liq):,.0f}" if liq else "N/A"
            
            print(f"  {C.TEXT}{cid:<12} {tA}/{tB:<18} {liq_str:<15}{C.R}")
            
    if not found_any:
        print(f"  {C.WARN}⚠ No pools found matching query.{C.R}")
    else:
        print(f"\n  {C.MUTED}Type 'pools approve <ID>' to add a pool to your registry.{C.R}")
    print()

def _pools_approve(app, pool_id, protocol):
    """Fetch pool metadata and save to registry."""
    from src.discovery import DiscoveryManager
    discovery = DiscoveryManager()
    
    # We search specifically for this pool ID to get its metadata
    print(f"  Verifying pool {pool_id} metadata...")
    results = discovery.search_pools(pool_id, protocol=protocol)
    
    if not results:
        # Try the other protocol just in case
        other = "v1" if protocol == "v2" else "v2"
        results = discovery.search_pools(pool_id, protocol=other)
        if results:
            protocol = other
            
    if not results:
        print(f"  {C.ERR}✗{C.R} Could not find metadata for pool {pool_id}.")
        return

    # Find the exact match
    pool_data = None
    for r in results:
        if r.get("contractId") == pool_id:
            pool_data = r
            break
            
    if not pool_data:
        pool_data = results[0] # Fallback to first

    success = app.approve_pool(pool_data, protocol=protocol)
    if success:
        print(f"  {C.OK}✅ Approved {protocol.upper()} pool {pool_id}!{C.R}")
    else:
        print(f"  {C.WARN}⚠ Pool already in registry or error occurred.{C.R}")

def _pools_delete(app, pool_id, protocol):
    """Remove pool from registry."""
    success = app.remove_pool(pool_id, protocol=protocol)
    if success:
        print(f"  {C.OK}✅ Removed {protocol.upper()} pool {pool_id} from registry.{C.R}")
    else:
        print(f"  {C.WARN}⚠ Pool not found in {protocol.upper()} registry.{C.R}")

def handle_natural_language(app, text):
    """Process NLP commands like 'swap 10 HBAR for USDC'."""
    req = translate(text)
    if not req:
        print(f"  {C.ERR}✗{C.R} Unknown command. Type {C.TEXT}help{C.R} for options.")
        return

    intent = req.get("intent")

    if intent == "swap":
        _do_swap(app, req)
    elif intent == "convert":
        _do_swap(app, req) # Convert is handled by swap logic in App
    elif intent == "balance":
        cmd_balance(app, [])
    elif intent == "help":
        cmd_help(app, [])
    else:
        print(f"  {C.ERR}✗{C.R} Unhandled intent: {intent}")

def _do_swap(app, req):
    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]
    mode = req["mode"]

    if mode == "exact_in":
        print(f"\n  {C.ACCENT}⟳{C.R} Analyzing: {C.TEXT}{amount}{C.R} {from_token} → {to_token} ({mode})")
    else:
        print(f"\n  {C.ACCENT}⟳{C.R} Analyzing: {from_token} → {C.TEXT}{amount}{C.R} {to_token} ({mode})")

    try:
        route = app.get_route(from_token, to_token, amount)
        if not route:
            print(f"  {C.ERR}✗{C.R} No route found for {from_token} → {to_token}")
            return

        print(f"\n  {C.BOLD}Proposed Route:{C.R}")
        print(f"  {C.TEXT}{route.from_variant}{C.R} → {C.TEXT}{route.to_variant}{C.R}")
        print(route.explain())

        if app.config.require_confirmation:
            confirm = input(f"\n  Execute swap? {C.MUTED}(y/n){C.R} ").strip().lower()
            if confirm not in ["y", "yes"]:
                print(f"  {C.MUTED}Cancelled.{C.R}")
                return
        
        logger.debug("Confirmation received, starting execution phase...")

        res = app.executor.execute_swap(route, amount_usd=amount, mode=mode)

        if res.success:
            print_receipt(res, route, route.from_variant, route.to_variant, amount, mode, app.executor)
        else:
            print(f"\n  {C.ERR}✗{C.R} FAILED: {res.error}")

    except PacmanError as e:
        print(f"  {C.ERR}✗{C.R} Error: {e}")
    except Exception as e:
        print(f"\n  {C.ERR}✗{C.R} Critical System Error: {e}")
        import traceback
        logger.debug(traceback.format_exc())

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

COMMANDS = {
    "help": cmd_help, "?": cmd_help, "-h": cmd_help,
    "tokens": cmd_tokens, "t": cmd_tokens,
    "sources": cmd_sources, "source": cmd_sources, "s": cmd_sources, "price": cmd_price,
    "account": cmd_account,
    "balance": cmd_balance,
    "history": cmd_history,
    "send": cmd_send,
    "receive": cmd_receive,
    "verbose": cmd_verbose,
    "pools": cmd_pools, "pool": cmd_pools
}

def process_input(app, text):
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
            print(f"  {C.ERR}✗{C.R} Unexpected Error: {e}")
    else:
        # Fallback to NLP
        try:
            handle_natural_language(app, text)
        except PacmanError as e:
            print(f"  {C.ERR}✗{C.R} {e}")

def check_saucerswap_api_key(app):
    """Check if SaucerSwap API key is set, and prompt if missing."""
    import os
    from pathlib import Path
    
    # Check if we are in a one-shot command or interactive
    if len(sys.argv) > 1 and sys.argv[1] not in ["account", "balance"]:
        # Don't prompt during quick swap commands to avoid blocking
        return

    # We only care about Mainnet for now as it's the primary use case
    key = os.getenv("SAUCERSWAP_API_KEY_MAINNET")
    if key:
        return

    print(f"\n  {C.WARN}⚠ SaucerSwap API Key Missing{C.R}")
    print(f"  {C.TEXT}To get full pool liquidity depth and high-accuracy price discovery,{C.R}")
    print(f"  {C.TEXT}it is recommended to set your own SaucerSwap API key.{C.R}")
    print(f"  {C.MUTED}Public fallbacks (CoinGecko/Binance) will be used otherwise.{C.R}")
    print(f"  {C.MUTED}Warning: You will not have full visibility into high-liquidity depth.{C.R}")
    print(f"  {C.MUTED}See docs/SAUCERSWAP_API_GUIDE.md for details.{C.R}")
    
    try:
        choice = input(f"\n  {C.BOLD}1) Set Key now{C.R}\n  {C.BOLD}2) Use public fallbacks{C.R}\n  Selection [2]: ").strip()
        
        if choice == "1":
            new_key = input(f"  Enter your SaucerSwap Mainnet API Key: ").strip()
            if new_key:
                _update_env_api_key(new_key)
                os.environ["SAUCERSWAP_API_KEY_MAINNET"] = new_key
                print(f"  {C.OK}✅ API Key saved to .env and loaded.{C.R}")
        else:
            print(f"  {C.MUTED}Using public fallbacks with limited accuracy.{C.R}")
    except (KeyboardInterrupt, EOFError):
        print(f"\n  {C.MUTED}Proceeding with public fallbacks.{C.R}")

def _update_env_api_key(key):
    """Helper to update .env file with the API key."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    
    lines = []
    found = False
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("SAUCERSWAP_API_KEY_MAINNET="):
                lines.append(f"SAUCERSWAP_API_KEY_MAINNET={key}\n")
                found = True
            else:
                lines.append(line)
    
    if not found:
        lines.append(f"\nSAUCERSWAP_API_KEY_MAINNET={key}\n")
        
    with open(env_path, "w") as f:
        f.writelines(lines)

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
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
        
        # Check for API Key if not in simulation or if specifically needed
        check_saucerswap_api_key(app)
        
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
    while True:
        try:
            user_input = input(f"\n  {C.ACCENT}ᗧ{C.R} ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print(f"  {C.MUTED}Shutting down.{C.R}")
                break

            process_input(app, user_input)

        except KeyboardInterrupt:
            print(f"\n  {C.MUTED}Interrupted.{C.R}")
            break

if __name__ == "__main__":
    main()


# CLI entry point for compatibility
cli = main

