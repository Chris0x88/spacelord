#!/usr/bin/env python3
"""
CLI Commands: Wallet & Account Management
==========================================

Handles: setup, account, balance, send, receive, whitelist.
Also contains the _update_env helper and startup checks.
"""

import sys
from pathlib import Path
from src.logger import logger
from cli.display import (
    C, show_balance, show_account, print_transfer_receipt
)


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
        acc = temp_w3.eth.account.from_key(clean_key)
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
    existing_id = __import__('os').getenv("HEDERA_ACCOUNT_ID")
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


def cmd_account(app, args):
    """
    View account info or manage sub-accounts.
    Usage:
      account                        → view current wallet info
      account --new                  → create a new sub-account (same key)
      account rename <0.0.xxx> <name> → rename a known account
    """
    # Handle 'rename' sub-command: account rename 0.0.xxx My Label
    if args and args[0].lower() == "rename":
        if len(args) < 3:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}account rename <0.0.xxx> <nickname>{C.R}")
            return
        target_id = args[1]
        new_name = " ".join(args[2:])
        success = app.rename_account(target_id, new_name)
        if success:
            print(f"  {C.OK}✅ Renamed {target_id} → '{C.ACCENT}{new_name}{C.R}'")
        else:
            print(f"  {C.ERR}✗{C.R} Account {target_id} not found in local registry.")
        return

    known = app.account_manager.get_known_accounts()
    show_account(app.executor, known_accounts=known)

    # Sub-account creation only on explicit --new flag
    if "--new" not in args and "-n" not in args:
        print(f"  {C.MUTED}To create a sub-account (same key), run: {C.ACCENT}account --new{C.R}")
        print(f"  {C.MUTED}To rename an account: {C.ACCENT}account rename <0.0.xxx> <label>{C.R}")
        print()
        return

    print(f"\n  {C.TEXT}Sub-account creation:{C.R}")
    print(f"  {C.WARN}⚠  This creates a new Hedera ID funded from your current account.{C.R}")
    confirm = input(f"  Continue? {C.MUTED}(y/n){C.R} ").strip().lower()
    if confirm not in ["y", "yes"]:
        print(f"  {C.MUTED}Cancelled.{C.R}")
        return

    # Prompt for nickname
    try:
        nickname = input(f"  Nickname for this account {C.MUTED}(optional, press enter to skip){C.R}: ").strip()
    except (KeyboardInterrupt, EOFError):
        nickname = ""

    print(f"\n  {C.MUTED}Creating sub-account on {app.network}...{C.R}")
    new_id = app.create_sub_account(initial_balance=1.0, nickname=nickname)
    if not new_id:
        print(f"  {C.ERR}✗{C.R} Creation failed.")
        return

    label = f" '{C.ACCENT}{nickname}{C.R}'" if nickname else ""
    print(f"  {C.OK}✅ Created Sub-account{label}: {C.BOLD}{new_id}{C.R}")
    print(f"  {C.MUTED}This account uses your existing Private Key.{C.R}")

    confirm = input(f"\n  Switch .env to this new ID? {C.MUTED}(y/n){C.R} ").strip().lower()
    if confirm in ["y", "yes"]:
        _update_env("HEDERA_ACCOUNT_ID", new_id, force=True)
        app.config.hedera_account_id = new_id
        print(f"  {C.OK}✅ Active account switched to {new_id}.{C.R}")
    print()



def cmd_balance(app, args):
    token = args[0] if args else None
    
    lp_positions = []
    try:
        lp_positions = app.get_liquidity_positions()
    except Exception as e:
        logger.debug(f"Failed to fetch LPs: {e}")
        
    show_balance(app.executor, single_token=token, lp_positions=lp_positions)


def cmd_send(app, args):
    # Syntax: send <amount> <token> to <recipient> [memo "your message"]
    if len(args) < 4 or args[2].lower() != "to":
        print(f"  {C.ERR}✗{C.R} Usage: {C.BOLD}send <amount> <token> to <recipient> [memo <message>]{C.R}")
        return

    try:
        amount = float(args[0])
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid amount: {args[0]}")
        return

    symbol = args[1].upper()
    recipient = args[3]
    
    # 1. Parse optional memo
    memo = None
    if len(args) > 4:
        if args[4].lower() in ["memo", "message", "msg"]:
            memo = " ".join(args[5:])
        else:
            memo = " ".join(args[4:])

    print(f"\n  {C.ACCENT}↗{C.R} Transfer: {C.TEXT}{amount} {symbol}{C.R} → {C.TEXT}{recipient}{C.R}")
    if memo:
        print(f"  {C.MUTED}Memo: {memo}{C.R}")

    if app.config.require_confirmation:
        confirm = input(f"  Confirm? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    print(f"  {C.MUTED}Submitting...{C.R}")
    res = app.transfer(symbol, amount, recipient, memo=memo)

    if res["success"]:
        print_transfer_receipt(res)
    else:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {res.get('error')}")


def cmd_receive(app, args):
    """
    Show wallet address and check token associations.
    Usage: receive [token_symbol]
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


def cmd_whitelist(app, args):
    """
    Manage trusted transfer recipients.
    Usage:
      whitelist                          → view list
      whitelist add <0.0.xxx> [nickname] → add address with optional label
      whitelist remove <0.0.xxx>         → remove address
    """
    action = args[0].lower() if args else "view"

    if action in ["view", "list", "ls"]:
        whitelist = app.get_whitelist()
        print(f"\n{C.BOLD}{C.TEXT}  WHITELISTED ADDRESSES{C.R}")
        print(f"  {C.CHROME}{'─' * 60}{C.R}")
        print(f"  {C.MUTED}{'ADDRESS':<16} {'NICKNAME'}{C.R}")
        print(f"  {C.CHROME}{'─' * 60}{C.R}")

        if not whitelist:
            print(f"  {C.MUTED}No addresses whitelisted.{C.R}")
            print(f"  {C.WARN}⚠ All live transfers will be blocked.{C.R}")
        else:
            for entry in whitelist:
                addr = entry.get("address", entry) if isinstance(entry, dict) else entry
                nick = entry.get("nickname", "") if isinstance(entry, dict) else ""
                nick_display = f"{C.ACCENT}{nick}{C.R}" if nick else f"{C.MUTED}—{C.R}"
                print(f"  {C.TEXT}{addr:<16}{C.R} {nick_display}")
        print()
        return

    if action == "add":
        if len(args) < 2:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}whitelist add <0.0.xxx> [nickname]{C.R}")
            return

        address = args[1]
        nickname = " ".join(args[2:]) if len(args) > 2 else ""
        if not nickname:
            try:
                nickname = input(f"  Nickname for {address} {C.MUTED}(optional, press enter to skip){C.R}: ").strip()
            except (KeyboardInterrupt, EOFError):
                nickname = ""

        success = app.add_to_whitelist(address, nickname=nickname)
        if success:
            label = f" as '{C.ACCENT}{nickname}{C.R}'" if nickname else ""
            print(f"  {C.OK}✅ Added {address}{label} to whitelist.{C.R}")
        else:
            print(f"  {C.ERR}✗{C.R} Failed to add. Check format (0.0.xxx).")

    elif action in ["remove", "delete", "rm"]:
        if len(args) < 2:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}whitelist remove <0.0.xxx>{C.R}")
            return

        address = args[1]
        success = app.remove_from_whitelist(address)
        if success:
            print(f"  {C.OK}✅ Removed {address} from whitelist.{C.R}")
        else:
            print(f"  {C.WARN}⚠ Address not found in whitelist.{C.R}")
    else:
        print(f"  {C.ERR}✗{C.R} Unknown action '{action}'. Try: view, add, remove")


# ---------------------------------------------------------------------------
# Startup Checks
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# .env Helpers
# ---------------------------------------------------------------------------

def _update_env(key, value, force=False):
    """Update or add a key-value pair in the .env file."""
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    
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
