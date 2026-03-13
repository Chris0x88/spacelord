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
    Securely configure your Hedera wallet credentials with a premium onboarding.
    Usage: setup
    """
    import getpass
    import os
    import time
    from lib.saucerswap import SaucerSwapV2
    from web3 import Web3

    print(f"\n{C.BOLD}{C.ACCENT}  ᗧ  PACMAN | WELCOME TO THE FUTURE OF HEDERA{C.R}")
    print(f"  {C.CHROME}{'═' * 56}{C.R}")
    print(f"  {C.TEXT}The AI-native toolkit for serious Hedera builders.{C.R}")
    print(f"  {C.MUTED}This wizard will set up your keys, accounts, and HCS signals.{C.R}")
    print(f"  {C.MUTED}{'─' * 56}{C.R}")

    # 1. Credentials
    print(f"\n  {C.BOLD}[1/3] IDENTITY & SECURITY{C.R}")
    print(f"  {C.MUTED}How would you like to provide your main private key?{C.R}")
    print(f"  {C.ACCENT}[P]{C.R} Paste existing Private Key")
    print(f"  {C.ACCENT}[C]{C.R} Create completely fresh Account")
    
    choice = input(f"\n  Choice {C.MUTED}(p/c){C.R}: ").strip().lower()
    if choice in ["x", "cancel"]:
        print(f"  {C.MUTED}Setup cancelled.{C.R}\n")
        return

    raw_key = None
    hedera_id = None

    if choice == 'c':
        print(f"\n  {C.BOLD}Locally Generating Secure Key Pair...{C.R}")
        from hiero_sdk_python.crypto.private_key import PrivateKey
        new_key = PrivateKey.generate_ecdsa()
        raw_key = new_key.to_string()
        
        # Derive EVM Address
        temp_w3 = Web3()
        acc = temp_w3.eth.account.from_key(raw_key)
        eoa = acc.address
        
        print(f"  {C.OK}✅ Generated!{C.R}")
        print(f"  {C.WARN}⚠  PRIVATE KEY (BACKUP THIS PRIVATELY):{C.R}")
        print(f"  {C.ACCENT}{raw_key}{C.R}")
        print(f"  {C.MUTED}Address: {eoa}{C.R}")

        # Sponsorship
        sponsor_id = os.getenv("HEDERA_ACCOUNT_ID")
        if sponsor_id:
             print(f"\n  {C.BOLD}Instant Activation?{C.R}")
             print(f"  Pacman can sponsor this new account from {C.BOLD}{sponsor_id}{C.R}.")
             do_sponsor = input(f"  Sponsor now? {C.MUTED}(y/n){C.R} ").strip().lower()
             if do_sponsor in ['y', 'yes']:
                 new_id, _ = app.create_new_account(initial_balance=1.0, alias_key=raw_key)
                 if new_id:
                     hedera_id = new_id
                     print(f"  {C.OK}✅ ACTIVATED: {C.BOLD}{hedera_id}{C.R}")
                 else:
                     print(f"  {C.ERR}✗{C.R} Sponsorship failed. Please activate manually.")
    else:
        while True:
            key_input = getpass.getpass(f"\n  {C.ACCENT}Enter Private Key:{C.R} ").strip()
            if key_input.lower() in ['x', 'cancel']: return
            raw_key = key_input.replace("0x", "")
            if len(raw_key) == 64: break
            print(f"  {C.ERR}✗{C.R} Invalid format. Need 64 hex chars.")
        
        print(f"  {C.MUTED}Discovering Hedera ID via Mirror Node...{C.R}")
        from web3 import Web3
        temp_w3 = Web3()
        acc = temp_w3.eth.account.from_key(raw_key)
        hedera_id = app.resolve_account_id(acc.address)
        
        if not hedera_id:
            print(f"\n  {C.WARN}⚠  Account Not Found{C.R}")
            hedera_id = input(f"  Enter Account ID manually (0.0.xxx): ").strip()

    if not raw_key or not hedera_id:
        print(f"  {C.ERR}✗{C.R} Setup incomplete.")
        return

    _update_env("PRIVATE_KEY", raw_key, force=True)
    _update_env("HEDERA_ACCOUNT_ID", hedera_id, force=True)
    app.reload_wallet(hard_reset=True)

    # 2. Account Isolation
    print(f"\n  {C.BOLD}[2/3] ACCOUNT ISOLATION (ROBOTS){C.R}")
    print(f"  {C.TEXT}Pacman recommends using a dedicated sub-account for AI agents{C.R}")
    print(f"  {C.TEXT}to keep your main funds and rebalancer logic separate.{C.R}")
    
    do_robot = input(f"\n  Create dedicated rebalancer account? {C.MUTED}(y/n){C.R} ").strip().lower()
    if do_robot in ['y', 'yes']:
        print(f"  {C.MUTED}Creating sub-account 'Bitcoin Rebalancer Daemon'...{C.R}")
        robot_id = app.create_sub_account(initial_balance=2.0, purpose="rebalancer")
        if robot_id:
             _update_env("ROBOT_ACCOUNT_ID", robot_id, force=True)
             print(f"  {C.OK}✅ CREATED: {C.BOLD}{robot_id}{C.R}")
        else:
             print(f"  {C.ERR}✗{C.R} Failed to create robot account.")

    # 3. HCS Signals
    print(f"\n  {C.BOLD}[3/3] HCS MESSAGING & SIGNALS{C.R}")
    print(f"  {C.TEXT}Broadcast signals to other Pacman instances via HCS.{C.R}")
    
    do_hcs = input(f"\n  Create a new HCS signal topic now? {C.MUTED}(y/n){C.R} ").strip().lower()
    if do_hcs in ['y', 'yes']:
        print(f"  {C.MUTED}Creating HCS topic...{C.R}")
        topic_id = app.hcs_manager.create_topic(memo="Pacman Signals")
        if topic_id:
             print(f"  {C.OK}✅ TOPIC ACTIVE: {C.BOLD}{topic_id}{C.R}")
        else:
             print(f"  {C.ERR}✗{C.R} HCS Topic creation failed.")

    print(f"\n  {C.OK}{C.BOLD}✨ SETUP COMPLETE!{C.R}")
    print(f"  {C.MUTED}{'═' * 56}{C.R}")
    print(f"  {C.TEXT}Main Account:  {C.BOLD}{hedera_id}{C.R}")
    if os.getenv("ROBOT_ACCOUNT_ID"):
        print(f"  {C.TEXT}Robot Account: {C.BOLD}{os.getenv('ROBOT_ACCOUNT_ID')}{C.R}")
    if os.getenv("HCS_TOPIC_ID"):
        print(f"  {C.TEXT}HCS Topic:     {C.BOLD}{os.getenv('HCS_TOPIC_ID')}{C.R}")
    
    print(f"\n  {C.ACCENT}Next Step:{C.R} Run {C.BOLD}balance{C.R} or {C.BOLD}robot start{C.R}")
    print()
    _auto_associate_after_setup(app)


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

    # Handle 'switch' sub-command: account switch <nickname>
    if args and args[0].lower() == "switch":
        if len(args) < 2:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}account switch <nickname_or_id>{C.R}")
            return
            
        target = " ".join(args[1:]).lower()
        known = app.account_manager.get_known_accounts()
        
        # Find match by ID or nickname
        match_id = None
        match_name = None
        for acc in known:
            acc_id = acc.get("id", "")
            nick = acc.get("nickname", "").lower()
            if target == acc_id.lower() or target == nick:
                match_id = acc_id
                match_name = acc.get("nickname", acc_id)
                break
                
        if not match_id:
            print(f"  {C.ERR}✗{C.R} Account '{target}' not found in known sub-accounts.")
            return
            
        if match_id == app.executor.hedera_account_id:
            print(f"  {C.OK}✅ Already using account {C.ACCENT}{match_name}{C.R}")
            return
            
        # Perform switch
        _update_env("HEDERA_ACCOUNT_ID", match_id, force=True)
        app.reload_wallet()
        print(f"  {C.OK}✅ Switched active account to {C.ACCENT}{match_name}{C.R} ({match_id})")
        return

    known = app.account_manager.get_known_accounts()
    show_account(app.executor, known_accounts=known)

    # Sub-account creation only on explicit --new flag
    if "--new" not in args and "-n" not in args:
        print(f"  {C.MUTED}To create a sub-account (same key), run: {C.ACCENT}account --new{C.R}")
        print(f"  {C.MUTED}To switch active accounts, run: {C.ACCENT}account switch <name>{C.R}")
        print(f"  {C.MUTED}To rename an account, run: {C.ACCENT}account rename <0.0.xxx> <label>{C.R}")
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

    # Determine safe initial balance
    try:
        cur_bal = app.executor.w3.eth.get_balance(app.executor.eoa) / 10**18
        init_bal = 1.0 if cur_bal > 1.5 else 0.1
    except:
        init_bal = 1.0

    print(f"\n  {C.MUTED}Creating sub-account on {app.network} (funding: {init_bal} HBAR)...{C.R}")
    new_id = app.create_sub_account(initial_balance=init_bal, nickname=nickname)
    if not new_id:
        print(f"  {C.ERR}✗{C.R} Creation failed.")
        return

    label = f" '{C.ACCENT}{nickname}{C.R}'" if nickname else ""
    print(f"  {C.OK}✅ Created Sub-account{label}: {C.BOLD}{new_id}{C.R}")
    print(f"  {C.MUTED}This account uses your existing Private Key.{C.R}")

    confirm = input(f"\n  Switch .env to this new ID? {C.MUTED}(y/n){C.R} ").strip().lower()
    if confirm in ["y", "yes"]:
        _update_env("HEDERA_ACCOUNT_ID", new_id, force=True)
        app.reload_wallet()
        print(f"  {C.OK}✅ Active account switched to {new_id} — no restart needed.{C.R}")
    print()



def cmd_associate(app, args):
    """
    Manually associate a token with your account.
    Usage: associate <token_id|symbol>
    """
    if not args:
        print(f"  {C.ERR}✗{C.R} Usage: {C.BOLD}associate <token_id>{C.R} (e.g. associate 0.0.456858)")
        return

    token_id = args[0]
    
    # Try to resolve symbol if not in 0.0.xxx format
    if not token_id.startswith("0.0."):
        # Check against common symbols
        symbols = {
            "USDC": "0.0.456858",
            "SAUCE": "0.0.731861",
        }
        if token_id.upper() in symbols:
            token_id = symbols[token_id.upper()]
        else:
             print(f"  {C.ERR}✗{C.R} Unknown token symbol. Please use Hedera ID (0.0.xxx)")
             return

    print(f"  {C.MUTED}Associating {C.ACCENT}{token_id}{C.MUTED} to your account...{C.R}")
    success = app.associate_token(token_id)
    if success:
        print(f"  {C.OK}✅ Successfully associated {C.BOLD}{token_id}{C.R}")
    else:
        print(f"  {C.ERR}✗{C.R} Association failed. Check your balance or token ID.")


def cmd_balance(app, args):
    import json as _json
    
    # AI-agent flag: --json emits parseable structure
    json_mode = "--json" in args
    args = [a for a in args if a != "--json"]
    token = args[0] if args else None
    
    if json_mode:
        # Emit structured JSON for AI agents
        try:
            from lib.prices import price_manager
            price_manager.reload()
            balances = app.executor.get_balances()
            hbar_raw = app.executor.w3.eth.get_balance(app.executor.eoa)
            hbar_bal = hbar_raw / (10**18)
            hbar_price = price_manager.get_hbar_price()
            
            result = {
                "account": app.executor.hedera_account_id,
                "network": app.executor.network,
                "hbar": {"balance": round(hbar_bal, 6), "price_usd": round(hbar_price, 6), 
                         "value_usd": round(hbar_bal * hbar_price, 2)},
                "tokens": {},
                "total_usd": 0,
            }
            total = hbar_bal * hbar_price
            
            for sym, bal in balances.items():
                if sym == "HBAR": continue
                try:
                    from cli.pacman_filter import ui_filter
                    meta = ui_filter.get_token_metadata().get(sym, {})
                    token_id = meta.get("id", "")
                    price = price_manager.get_price(token_id) if token_id else 0
                    val = round(bal * price, 2)
                    result["tokens"][sym] = {"balance": bal, "price_usd": price, "value_usd": val}
                    total += val
                except Exception:
                    result["tokens"][sym] = {"balance": bal, "price_usd": 0, "value_usd": 0}
            
            result["total_usd"] = round(total, 2)
            print(_json.dumps(result, indent=2))
            return
        except Exception as e:
            print(_json.dumps({"error": str(e)}))
            return
    
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
    account_id = app.executor.hedera_account_id
    eoa = app.executor.eoa
    print(f"\n  {C.BOLD}{C.TEXT}RECEIVE HBAR / TOKENS{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.TEXT}Hedera Native ID:{C.R} {C.BOLD}{C.OK}{account_id}{C.R}")
    print(f"  {C.TEXT}EVM Address:    {C.R} {C.MUTED}{eoa}{C.R}")
    print(f"  {C.MUTED}{'─' * 56}{C.R}")
    
    # Check max auto-associations
    try:
        url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{account_id}"
        import requests
        resp = requests.get(url, timeout=5).json()
        max_assoc = resp.get("max_automatic_token_associations", 0)
        if max_assoc == -1:
            print(f"  {C.OK}✅ Unlimited Auto-Association Enabled{C.R}")
        else:
            print(f"  {C.WARN}⚠  Auto-Association Slots: {max_assoc}{C.R}")
    except: pass
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
    import sys
    
    # Don't prompt if running a one-shot command unrelated to trading
    if len(sys.argv) > 1 and sys.argv[1] in ["help", "pools", "tokens", "price"]:
        return

    if not app.config.private_key:
        print(f"\n  {C.BOLD}{C.TEXT}Welcome to Pacman!{C.R}")
        print(f"  {C.MUTED}To start trading, you'll need to configure your Hedera wallet.{C.R}")
        print(f"  Run {C.BOLD}{C.ACCENT}setup{C.R} to get started.")
        print()
        return

    # Check activation
    if not app.executor.hedera_account_id or app.executor.hedera_account_id == "Unknown":
        print(f"\n  {C.WARN}⚠  WALLET NOT ACTIVATED{C.R}")
        print(f"  Your key is set, but your Hedera ID (0.0.xxx) is missing.")
        print(f"  Run {C.BOLD}{C.ACCENT}setup{C.R} and choose {C.BOLD}[P]{C.R} to discover your ID.")
        print()
        
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

def _auto_associate_after_setup(app):
    """
    Batch-associate the base token set after a new wallet is activated.
    Runs silently, prints a clean summary.
    """
    print(f"\n  {C.BOLD}Auto-Associating Base Tokens...{C.R}")
    print(f"  {C.MUTED}(Linking top V2 pool tokens so you can receive them){C.R}")
    try:
        summary = app.account_manager.auto_associate_base_tokens()
        associated  = summary.get("associated", [])
        already     = summary.get("already_associated", [])
        failed      = summary.get("failed", [])

        if associated:
            print(f"  {C.OK}✅ Associated:{C.R} {', '.join(s for s, _ in associated)}")
        if already:
            print(f"  {C.MUTED}⬡  Already linked:{C.R} {', '.join(s for s, _ in already)}")
        if failed:
            print(f"  {C.WARN}⚠  Skipped (retry with 'associate'):{C.R} {', '.join(s for s, _, __ in failed)}")
        if not associated and not already and not failed:
            print(f"  {C.MUTED}No base tokens to associate.{C.R}")
    except Exception as e:
        print(f"  {C.WARN}⚠  Auto-association skipped (non-fatal): {e}{C.R}")
    print()


# ---------------------------------------------------------------------------
# .env Helpers
# ---------------------------------------------------------------------------

def _update_env(key, value, force=False):

    """Update or add a key-value pair in the .env file with archival safety."""
    from pathlib import Path
    import time
    import os
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    
    # Create file if missing
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write("# Pacman .env\n")
    
    lines = []
    found = False
    
    with open(env_path, "r") as f:
        existing_lines = f.readlines()

    # 2. Update/Append logic
    for line in existing_lines:
        if line.strip().startswith(f"{key}="):
            current_val = line.split("=", 1)[1].strip()
            if not force and current_val and current_val != value:
                # This prompt is usually handled by the caller, but keep it as a safety valve
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
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{key}={value}\n")
        
    with open(env_path, "w") as f:
        f.writelines(lines)
    return True
