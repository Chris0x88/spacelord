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
    
    # Sub-account creation option
    print(f"\n  {C.TEXT}Sub-account management:{C.R}")
    print(f"  {C.ACCENT}[S]{C.R} Create new Sub-account (same key)")
    
    while True:
        choice = input(f"\n  Choice {C.MUTED}(s or enter to exit){C.R}: ").strip().lower()
        if not choice:
            break
        if choice == 's':
            print(f"\n  {C.MUTED}Creating sub-account on {app.network}...{C.R}")
            new_id = app.create_sub_account(initial_balance=1.0)
            if not new_id:
                print(f"  {C.ERR}✗{C.R} Creation failed.")
                return
                
            print(f"  {C.OK}✅ Created Sub-account: {C.BOLD}{new_id}{C.R}")
            print(f"  {C.MUTED}This account uses your existing Private Key.{C.R}")
            
            confirm = input(f"\n  Switch .env to this new ID? {C.MUTED}(y/n){C.R} ").strip().lower()
            if confirm in ["y", "yes"]:
                _update_env("HEDERA_ACCOUNT_ID", new_id, force=True)
                app.config.hedera_account_id = new_id
                print(f"  {C.OK}✅ Account ID updated to {new_id}.{C.R}")
            break
        else:
            print(f"  {C.MUTED}Invalid choice. Type 's' or press enter.{C.R}")

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
        print(f"  {C.MUTED}Flags: -1 (V1), -2 (V2). Default: V2{C.R}")
        print()
        return

    # 1. Robust Flag Extraction (Any position, various aliases)
    v1_aliases = ["--v1", "-v1", "--1", "-1"]
    v2_aliases = ["--v2", "-v2", "--2", "-2", "v--2", "--v2"] # Added user's typo for safety
    
    v1_flag = any(f in args for f in v1_aliases)
    v2_flag = any(f in args for f in v2_aliases)
    
    # Clean args from flags
    clean_args = [a for a in args if a not in v1_aliases and a not in v2_aliases]
    
    if not clean_args:
        return cmd_pools(app, []) # Show help if no action left

    action = clean_args[0].lower()
    sub_args = clean_args[1:]
    
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
        # If no protocol specifically requested, try both
        if not (v1_flag or v2_flag):
            _pools_delete(app, sub_args[0], "both")
        else:
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
        print(f"\n  {C.BOLD}{p_type.upper()} Liquidity Sources{C.R}")
        print(f"  {C.CHROME}{'ID':<12} {'PAIR':<25} {'FEE':<8}{C.R}")
        print(f"  {C.CHROME}{'─' * 50}{C.R}")
        
        for r in results[:10]: # Cap at 10 for readability
            cid = r.get("contractId", "N/A")
            tA = r.get("tokenA", {}).get("symbol", "???")
            tB = r.get("tokenB", {}).get("symbol", "???")
            idA = r.get("tokenA", {}).get("id", "???")
            idB = r.get("tokenB", {}).get("id", "???")
            
            # Fee handling
            fee = r.get("fee")
            if p_type == "v1" and fee is None:
                fee = 3000
            fee_str = f"{fee/10000:.2f}%" if fee is not None else "N/A"
            
            print(f"  {C.TEXT}{cid:<12} {tA}/{tB:<24} {fee_str:<8}{C.R}")
            print(f"               {C.MUTED}{idA} / {idB}{C.R}")
            
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
    if protocol == "both":
        success = app.remove_pool(pool_id, protocol="v1")
        if not success:
            success = app.remove_pool(pool_id, protocol="v2")
            if success:
                print(f"  {C.OK}✅ Removed V2 pool {pool_id} from registry.{C.R}")
            else:
                print(f"  {C.WARN}⚠ Pool {pool_id} not found in V1 or V2 registries.{C.R}")
        else:
            print(f"  {C.OK}✅ Removed V1 pool {pool_id} from registry.{C.R}")
    else:
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

    logger.debug(f"NLP Interpretation: {intent} (Tokens: {tokens}, Amt: {amt})")
    
    if intent == "swap":
        _do_swap(app, req)
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

def cmd_setup(app, args):
    """
    Securely configure your Hedera wallet credentials.
    Usage: setup
    """
    import getpass
    import os
    from lib.saucerswap import SaucerSwapV2
    from web3 import Web3

    print(f"\n{C.BOLD}{C.TEXT}  SECURE WALLET SETUP{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.MUTED}This will update your .env file.{C.R}")
    print(f"  {C.MUTED}Type 'x' or 'cancel' to exit at any time.{C.R}")

    # 0. Selection
    print(f"\n  {C.TEXT}How would you like to start?{C.R}")
    print(f"  {C.ACCENT}[P]{C.R} Paste existing Private Key")
    print(f"  {C.ACCENT}[C]{C.R} Create completely fresh Account")
    
    choice = input(f"\n  Choice {C.MUTED}(p/c){C.R}: ").strip().lower()
    if choice in ["x", "cancel"]:
        print(f"  {C.MUTED}Setup cancelled.{C.R}\n")
        return
        
    if choice == 'c':
        print(f"\n  {C.MUTED}Creating fresh ECDSA account on {app.network}...{C.R}")
        new_id, new_key = app.create_new_account(initial_balance=1.0)
        if not new_id:
            print(f"  {C.ERR}✗{C.R} Creation failed. Check your network or funding account.")
            return
        
        print(f"  {C.OK}✅ Created Account: {C.BOLD}{new_id}{C.R}")
        print(f"  {C.WARN}⚠  IMPORTANT: Write down your Private Key!{C.R}")
        print(f"  {C.TEXT}{new_key}{C.R}")
        
        # Save to .env
        _update_env("PRIVATE_KEY", new_key)
        _update_env("HEDERA_ACCOUNT_ID", new_id)
        
        # Immediate config update
        from src.config import SecureString
        app.config.private_key = SecureString(new_key)
        app.config.hedera_account_id = new_id
        
        print(f"\n  {C.OK}✅ Wallet setup complete!{C.R}")
        return

    # 1. Private Key Entry (Existing Flow)
    print(f"\n  {C.BOLD}Step 1: Enter your Private Key{C.R}")
    print(f"  {C.MUTED}(Masked input, will be saved to .env as PRIVATE_KEY){C.R}")
    
    while True:
        key_input = getpass.getpass(f"  {C.ACCENT}Private Key:{C.R} ").strip()
        if key_input.lower() in ['x', 'cancel', 'exit']:
            print(f"  {C.MUTED}Setup cancelled.{C.R}")
            return

        clean_key = key_input.replace("0x", "")
        if len(clean_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in clean_key):
             break
        print(f"  {C.ERR}✗{C.R} Invalid format. Must be 64 hex characters.")

    # Update .env
    _update_env("PRIVATE_KEY", clean_key)
    
    # 2. Account ID Discovery
    print(f"\n  {C.BOLD}Step 2: Account ID Discovery{C.R}")
    try:
        temp_w3 = Web3()
        acc = temp_w3.eth.account.from_key(clean_key) # Use clean_key here
        eoa = acc.address
        print(f"  {C.MUTED}EVM Address: {C.TEXT}{eoa}{C.R}")
    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Failed to derive address: {e}")
        return

    print(f"  {C.MUTED}Discovering Hedera ID via Mirror Node...{C.R}")
    hedera_id = app.resolve_account_id(eoa)
    
    if not hedera_id:
        from src.utils import is_valid_account_id
        print(f"\n  {C.WARN}⚠  Account Not Linked{C.R}")
        print(f"  {C.TEXT}Your address {C.BOLD}{eoa}{C.R} is not yet indexed on Hedera.{C.R}")
        print(f"  {C.MUTED}This usually means the account is brand new or has no HBAR.{C.R}")
        
        choice = input(f"\n  Enter Account ID manually? (0.0.xxx) {C.MUTED}(y/n){C.R} ").strip().lower()
        if choice in ["y", "yes"]:
            while True:
                hedera_id = input(f"  Hedera ID: ").strip()
                if not hedera_id:
                    print(f"  {C.MUTED}Setup aborted.{C.R}")
                    return
                if hedera_id.lower() in ["x", "cancel"]:
                    print(f"  {C.MUTED}Setup aborted.{C.R}")
                    return
                
                if is_valid_account_id(hedera_id):
                    break
                else:
                    print(f"  {C.ERR}✗{C.R} Invalid format. Expected {C.BOLD}0.0.xxx{C.R}")
        else:
            print(f"  {C.MUTED}Setup aborted.{C.R}")
            return
    else:
        print(f"  {C.OK}✅ Found Account ID: {C.BOLD}{hedera_id}{C.R}")

    # 3. Confirmation and Save
    existing_id = os.getenv("HEDERA_ACCOUNT_ID")
    if existing_id and existing_id != hedera_id:
        print(f"\n  {C.WARN}⚠  WARNING: Overwriting Existing ID{C.R}")
        print(f"  Existing: {C.BOLD}{existing_id}{C.R}")
        print(f"  New:      {C.BOLD}{hedera_id}{C.R}")
        confirm = input(f"  Are you sure? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Setup aborted. Existing values kept.{C.R}")
            return

    _update_env("PRIVATE_KEY", clean_key, force=True)
    _update_env("HEDERA_ACCOUNT_ID", hedera_id, force=True)
    
    # Immediate config update for active session
    from src.config import SecureString
    app.config.private_key = SecureString(clean_key)
    app.config.hedera_account_id = hedera_id
    
    print(f"\n  {C.OK}✅ Wallet setup complete!{C.R}")
    print(f"  {C.MUTED}You can now use 'pools search' or check your 'balance'.{C.R}\n")

def check_wallet_setup(app):
    """Check for wallet keys on startup and guide onboarding."""
    import os
    
    # Don't prompt if running a one-shot command unrelated to trading
    if len(sys.argv) > 1 and sys.argv[1] in ["help", "pools", "tokens", "price"]:
        return

    key = os.getenv("PRIVATE_KEY")
    acc_id = os.getenv("HEDERA_ACCOUNT_ID")

    if not key or not acc_id:
        print(f"\n  {C.WARN}⚠  Wallet Not Configured{C.R}")
        print(f"  {C.TEXT}To execute live swaps, you need to set your Secure Private Key.{C.R}")
        print(f"  {C.MUTED}Note: Pacman will automatically resolve your Hedera ID.{C.R}")
        
        try:
            choice = input(f"  Configure now? {C.MUTED}(y/n){C.R} ").strip().lower()
            if choice in ["y", "yes"]:
                cmd_setup(app, [])
        except (KeyboardInterrupt, EOFError):
            print()
            return

def check_saucerswap_api_key(app):
    """Check if SaucerSwap API key is set, and prompt if missing."""
    import os
    
    # Skip if specifically requested or in help
    if len(sys.argv) > 1 and sys.argv[1] in ["help"]:
        return

    key = os.getenv("SAUCERSWAP_API_KEY_MAINNET")
    if key:
        return

    print(f"\n  {C.WARN}⚠ SaucerSwap API Key Missing{C.R}")
    print(f"  {C.TEXT}It is recommended to set your own SaucerSwap API key for better accuracy.{C.R}")
    
    try:
        choice = input(f"  Set Key now? {C.MUTED}(y/n) [n]{C.R} ").strip().lower()
        if choice in ["y", "yes"]:
            new_key = input(f"  Enter Your API Key: ").strip()
            if new_key:
                _update_env("SAUCERSWAP_API_KEY_MAINNET", new_key)
                os.environ["SAUCERSWAP_API_KEY_MAINNET"] = new_key
                print(f"  {C.OK}✅ API Key saved.{C.R}")
    except (KeyboardInterrupt, EOFError):
        print()

def _update_env(key, value, force=False):
    """Update or add a key-value pair in the .env file."""
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    
    # Create file if missing
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write("# Pacman .env\n")
    
    lines = []
    found = False
    current_value = None
    
    with open(env_path, "r") as f:
        for line in f:
            if line.strip().startswith(f"{key}="):
                current_value = line.split("=", 1)[1].strip()
                if not force and current_value and current_value != value:
                    print(f"\n  {C.WARN}⚠  Warning: {key} already has a value.{C.R}")
                    confirm = input(f"  Overwrite? {C.MUTED}(y/n){C.R} ").strip().lower()
                    if confirm not in ["y", "yes"]:
                        print(f"  {C.MUTED}Update skipped.{C.R}")
                        return False
                
                lines.append(f"{key}={value}\n")
                found = True
            else:
                lines.append(line)
    
    if not found:
        # Add newline if needed
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{key}={value}\n")
        
    with open(env_path, "w") as f:
        f.writelines(lines)

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

COMMANDS = {
    "setup": cmd_setup,
    "account": cmd_account,
    "balance": cmd_balance,
    "tokens": cmd_tokens, "t": cmd_tokens,
    "pools": cmd_pools, "pool": cmd_pools,
    "price": cmd_price,
    "history": cmd_history,
    "send": cmd_send,
    "receive": cmd_receive,
    "sources": cmd_sources, "source": cmd_sources,
    "verbose": cmd_verbose,
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

