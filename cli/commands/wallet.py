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


# ---------------------------------------------------------------------------
# Agent-Safe Input Helpers
# ---------------------------------------------------------------------------

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

def _clean_args(args: list) -> list:
    """Remove control flags (--yes, --json) from args for parsing."""
    return [a for a in args if a not in ("--yes", "-y", "--json")]

def _print_account_context(app):
    """Print a one-line account context header so agents always know which account is active."""
    account_id = getattr(app, 'account_id', None) or 'Unknown'
    # Look up nickname
    nickname = ""
    try:
        known = app.account_manager.get_known_accounts()
        for acc in known:
            if acc.get("id") == account_id:
                nickname = acc.get("nickname", "")
                break
    except Exception:
        pass
    label = f" ({nickname})" if nickname else ""
    network = getattr(app, 'network', 'mainnet')
    print(f"  {C.MUTED}[{network} | {account_id}{label}]{C.R}")


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

    # Guard: warn if wallet already configured
    existing_key = os.getenv("PRIVATE_KEY")
    existing_id = os.getenv("HEDERA_ACCOUNT_ID")
    if existing_key and existing_id:
        print(f"\n  {C.WARN}⚠  Wallet Already Configured{C.R}")
        print(f"  {C.TEXT}Active account: {C.BOLD}{existing_id}{C.R}")
        print(f"  {C.MUTED}Running setup again will replace your current credentials.{C.R}")
        print(f"  {C.MUTED}Your existing key will be automatically backed up in .env.{C.R}")
        confirm = _safe_input(f"  Continue with new setup? {C.MUTED}(y/n){C.R} ", default="n").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Setup cancelled. Existing wallet unchanged.{C.R}\n")
            return

    # 1. Credentials
    print(f"\n  {C.BOLD}[1/3] IDENTITY & SECURITY{C.R}")
    print(f"  {C.MUTED}How would you like to provide your main private key?{C.R}")
    print(f"  {C.ACCENT}[P]{C.R} Paste existing Private Key")
    print(f"  {C.ACCENT}[C]{C.R} Create completely fresh Account")
    
    choice = _safe_input(f"\n  Choice {C.MUTED}(p/c){C.R}: ", default="p").strip().lower()
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
             do_sponsor = _safe_input(f"  Sponsor now? {C.MUTED}(y/n){C.R} ").strip().lower()
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
            hedera_id = _safe_input(f"  Enter Account ID manually (0.0.xxx): ", default="").strip()

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
    
    do_robot = _safe_input(f"\n  Create dedicated rebalancer account? {C.MUTED}(y/n){C.R} ", default="n").strip().lower()
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
    
    do_hcs = _safe_input(f"\n  Create a new HCS signal topic now? {C.MUTED}(y/n){C.R} ", default="n").strip().lower()
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
      account                          → view current wallet info
      account --new [--purpose robot]  → create a new sub-account (unique key)
      account rename <0.0.xxx> <name>  → rename a known account
      account switch <nickname_or_id>  → switch active account
      account --json                   → JSON output for agents
    """
    import json as _json

    json_mode = "--json" in args
    auto_yes = _is_auto_yes(args)
    clean = _clean_args(args)

    # Handle 'rename' sub-command
    if clean and clean[0].lower() == "rename":
        if len(clean) < 3:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}account rename <0.0.xxx> <nickname>{C.R}")
            return
        target_id = clean[1]
        new_name = " ".join(clean[2:])
        success = app.rename_account(target_id, new_name)
        if json_mode:
            print(_json.dumps({"success": success, "account": target_id, "nickname": new_name}))
        elif success:
            print(f"  {C.OK}✅ Renamed {target_id} → '{C.ACCENT}{new_name}{C.R}'")
        else:
            print(f"  {C.ERR}✗{C.R} Account {target_id} not found in local registry.")
        return

    # Handle 'switch' sub-command
    if clean and clean[0].lower() == "switch":
        if len(clean) < 2:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}account switch <nickname_or_id>{C.R}")
            return

        target = " ".join(clean[1:]).lower()
        known = app.account_manager.get_known_accounts()

        # Find match by ID or nickname (also support partial match)
        match_id = None
        match_name = None
        for acc in known:
            acc_id = acc.get("id", "")
            nick = acc.get("nickname", "").lower()
            if target == acc_id.lower() or target == nick or target in nick:
                match_id = acc_id
                match_name = acc.get("nickname", acc_id)
                break

        if not match_id:
            msg = f"Account '{target}' not found in known accounts."
            if json_mode:
                print(_json.dumps({"error": msg}))
            else:
                print(f"  {C.ERR}✗{C.R} {msg}")
            return

        if match_id == app.executor.hedera_account_id:
            if json_mode:
                print(_json.dumps({"success": True, "account": match_id, "nickname": match_name, "note": "already active"}))
            else:
                print(f"  {C.OK}✅ Already using account {C.ACCENT}{match_name}{C.R}")
            return

        # Perform switch — update account ID, then reload (key resolution in controller)
        _update_env("HEDERA_ACCOUNT_ID", match_id, force=True)
        app.reload_wallet()
        if json_mode:
            print(_json.dumps({"success": True, "account": match_id, "nickname": match_name}))
        else:
            print(f"  {C.OK}✅ Switched active account to {C.ACCENT}{match_name}{C.R} ({match_id})")
        return

    # Default: show account info
    known = app.account_manager.get_known_accounts()

    if json_mode:
        # Structured JSON output for agents
        result = {
            "active_account": app.account_id,
            "network": app.network,
            "evm_address": app.executor.eoa,
            "robot_account": getattr(app.config, 'robot_account_id', None),
            "known_accounts": known,
            "simulate_mode": app.config.simulate_mode,
        }
        print(_json.dumps(result, indent=2))
        return

    show_account(app.executor, known_accounts=known)

    # Sub-account creation only on explicit --new flag
    if "--new" not in args and "-n" not in args:
        print(f"  {C.MUTED}To create a sub-account: {C.ACCENT}account --new{C.R}")
        print(f"  {C.MUTED}To switch accounts:      {C.ACCENT}account switch <name>{C.R}")
        print(f"  {C.MUTED}To rename an account:    {C.ACCENT}account rename <0.0.xxx> <label>{C.R}")
        print()
        return

    # --- New Sub-Account Creation (with unique key) ---
    # Parse optional purpose flag
    purpose = None
    for i, a in enumerate(clean):
        if a.lower() == "--purpose" and i + 1 < len(clean):
            purpose = clean[i + 1].lower()

    print(f"\n  {C.TEXT}Sub-account creation:{C.R}")
    print(f"  {C.TEXT}This generates a NEW private key and creates a funded Hedera account.{C.R}")
    print(f"  {C.WARN}⚠  The new key will be displayed ONCE. Back it up immediately.{C.R}")

    confirm = _safe_input(f"  Continue? {C.MUTED}(y/n){C.R} ", args)
    if confirm.lower() not in ["y", "yes"]:
        print(f"  {C.MUTED}Cancelled.{C.R}")
        return

    # Prompt for nickname (or use purpose)
    if purpose == "robot" or purpose == "rebalancer":
        nickname = "Bitcoin Rebalancer Daemon"
        purpose = "rebalancer"
    else:
        nickname = _safe_input(
            f"  Nickname for this account {C.MUTED}(optional, press enter to skip){C.R}: ",
            args, default=""
        )

    # Determine safe initial balance
    try:
        cur_bal = app.executor.w3.eth.get_balance(app.executor.eoa) / 10**18
        init_bal = 2.0 if cur_bal > 3.0 else 1.0 if cur_bal > 1.5 else 0.5
    except Exception:
        init_bal = 1.0

    print(f"\n  {C.MUTED}Creating account on {app.network} (funding: {init_bal} HBAR)...{C.R}")

    # Create with UNIQUE key (not sub-account with same key)
    new_id, new_private_key = app.create_new_account(initial_balance=init_bal)
    if not new_id:
        print(f"  {C.ERR}✗{C.R} Creation failed.")
        return

    # Save to registry
    app.account_manager._save_account(new_id, type="independent", nickname=nickname, purpose=purpose)

    label = f" '{C.ACCENT}{nickname}{C.R}'" if nickname else ""
    print(f"  {C.OK}✅ Created Account{label}: {C.BOLD}{new_id}{C.R}")

    # --- AUTOMATIC KEY BACKUP ---
    # Keys are saved to local files automatically (~/Downloads + backups/).
    # In agent mode, the key is NEVER printed to stdout (prevents API leakage).
    if new_private_key:
        # Derive EVM address for the backup file
        evm_addr = ""
        try:
            from hiero_sdk_python.crypto.private_key import PrivateKey as _PK
            _pk = _PK.from_bytes_ecdsa(bytes.fromhex(new_private_key.replace("0x", "")))
            evm_addr = f"0x{_pk.public_key().to_evm_address()}"
        except Exception:
            pass

        backup_result = _auto_backup_new_key(new_id, new_private_key, nickname, evm_addr)
        saved_files = backup_result.get("files", [])

        if sys.stdin.isatty() and not _is_auto_yes(args):
            # Human at keyboard — show the key on screen
            print(f"\n  {C.WARN}{'═' * 56}{C.R}")
            print(f"  {C.WARN}⚠  PRIVATE KEY — BACKED UP AUTOMATICALLY{C.R}")
            print(f"  {C.WARN}{'═' * 56}{C.R}")
            print(f"  {C.ACCENT}{new_private_key}{C.R}")
            print(f"  {C.WARN}{'═' * 56}{C.R}")
            print(f"  {C.TEXT}Account ID: {new_id}{C.R}")
            print(f"  {C.TEXT}Key Type:   ECDSA (secp256k1){C.R}")
            if evm_addr:
                print(f"  {C.TEXT}EVM Addr:   {evm_addr}{C.R}")
        else:
            # Agent mode — NEVER show the key, only the backup file paths
            print(f"\n  {C.TEXT}Account ID: {new_id}{C.R}")
            print(f"  {C.TEXT}Key Type:   ECDSA (secp256k1){C.R}")
            if evm_addr:
                print(f"  {C.TEXT}EVM Addr:   {evm_addr}{C.R}")

        if saved_files:
            for fp in saved_files:
                print(f"  {C.OK}✅ Key saved:{C.R} {fp}")
            # Open email draft with backup file attached (macOS: auto-attaches via AppleScript)
            _try_open_email_draft(
                f"Pacman Key Backup — {new_id}",
                f"New Pacman account created.\n\nAccount: {new_id}\nNickname: {nickname or '(none)'}\nKey Type: ECDSA (secp256k1)\nEVM: {evm_addr}\n\nKey backup file is attached.",
                attachment_path=saved_files[0]
            )
        else:
            print(f"  {C.WARN}⚠  Could not auto-save key backup. Copy from .env manually.{C.R}")

    # If this is a robot account, store its key in .env
    if purpose == "rebalancer":
        _update_env("ROBOT_ACCOUNT_ID", new_id, force=True)
        if new_private_key:
            _update_env("ROBOT_PRIVATE_KEY", new_private_key, force=True)
        print(f"\n  {C.OK}✅ Robot account configured in .env{C.R}")

        # Auto-associate base tokens on the new account
        print(f"\n  {C.MUTED}Auto-associating base tokens on new account...{C.R}")
        try:
            # Temporarily set operator to the new account for association
            app.account_manager.set_operator(new_id, new_private_key)
            summary = app.account_manager.auto_associate_base_tokens()
            associated = summary.get("associated", [])
            if associated:
                print(f"  {C.OK}✅ Associated:{C.R} {', '.join(s for s, _ in associated)}")
            # Restore operator to main account
            pk = app.config.private_key.reveal()
            app.account_manager.set_operator(app.account_id, pk)
            del pk
        except Exception as e:
            print(f"  {C.WARN}⚠  Auto-association skipped: {e}{C.R}")
    else:
        # Ask if user wants to switch to the new account
        switch = _safe_input(f"\n  Switch .env to this new ID? {C.MUTED}(y/n){C.R} ", args, default="n")
        if switch.lower() in ["y", "yes"]:
            if new_private_key:
                _update_env("PRIVATE_KEY", new_private_key, force=True)
            _update_env("HEDERA_ACCOUNT_ID", new_id, force=True)
            app.reload_wallet(hard_reset=True)
            print(f"  {C.OK}✅ Active account switched to {new_id}{C.R}")

    print()



def cmd_associate(app, args):
    """
    Manually associate a token with your account.
    Usage: associate <token_id|symbol> [--json] [--yes]
    """
    import json as _json

    json_mode = "--json" in args
    clean = _clean_args(args)

    if not clean:
        msg = "Usage: associate <token_id> (e.g. associate 0.0.456858)"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    token_id = clean[0]

    # Try to resolve symbol if not in 0.0.xxx format
    if not token_id.startswith("0.0."):
        # Try the app's token resolver first, then fallback to hardcoded
        resolved = app.resolve_token_id(token_id)
        if resolved:
            token_id = resolved
        else:
            symbols = {
                "USDC": "0.0.456858",
                "SAUCE": "0.0.731861",
                "WBTC": "0.0.10082597",
                "WETH": "0.0.9470869",
                "USDT": "0.0.1055472",
            }
            if token_id.upper() in symbols:
                token_id = symbols[token_id.upper()]
            else:
                msg = f"Unknown token symbol '{token_id}'. Use Hedera ID (0.0.xxx)"
                if json_mode:
                    print(_json.dumps({"error": msg}))
                else:
                    print(f"  {C.ERR}✗{C.R} {msg}")
                return

    if not json_mode:
        _print_account_context(app)
        print(f"  {C.MUTED}Associating {C.ACCENT}{token_id}{C.MUTED} to your account...{C.R}")

    success = app.associate_token(token_id)

    if json_mode:
        print(_json.dumps({"success": success, "token_id": token_id, "account": app.account_id}))
    elif success:
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
            
            from cli.pacman_filter import ui_filter
            tokens_data = ui_filter.get_token_metadata()

            for token_key, bal in balances.items():
                # Skip HBAR (already in result["hbar"])
                if token_key in ("HBAR", "0.0.0"):
                    continue
                try:
                    meta = tokens_data.get(token_key, {})
                    if not meta:
                        for k, m in tokens_data.items():
                            if m.get("symbol") == token_key:
                                meta = m
                                break
                    token_id = meta.get("id", token_key)
                    if ui_filter.is_blacklisted(token_id):
                        continue
                    display_name = meta.get("symbol", token_key)
                    price = price_manager.get_price(token_id) if token_id else 0
                    val = round(bal * price, 2)
                    result["tokens"][display_name] = {"balance": bal, "price_usd": price, "value_usd": val}
                    total += val
                except Exception:
                    result["tokens"][token_key] = {"balance": bal, "price_usd": 0, "value_usd": 0}
            
            result["total_usd"] = round(total, 2)
            print(_json.dumps(result, indent=2))
            return
        except Exception as e:
            print(_json.dumps({"error": str(e)}))
            return
    
    _print_account_context(app)
    lp_positions = []
    try:
        lp_positions = app.get_liquidity_positions()
    except Exception as e:
        logger.debug(f"Failed to fetch LPs: {e}")

    show_balance(app.executor, single_token=token, lp_positions=lp_positions)



def cmd_send(app, args):
    import json as _json

    json_mode = "--json" in args
    auto_yes = _is_auto_yes(args)
    clean = _clean_args(args)

    # Syntax: send <amount> <token> to <recipient> [memo "your message"]
    if len(clean) < 4 or clean[2].lower() != "to":
        msg = "Usage: send <amount> <token> to <recipient> [memo <message>]"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    try:
        amount = float(clean[0])
    except ValueError:
        msg = f"Invalid amount: {clean[0]}"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    symbol = clean[1].upper()
    recipient = clean[3]

    # 1. Parse optional memo
    memo = None
    if len(clean) > 4:
        if clean[4].lower() in ["memo", "message", "msg"]:
            memo = " ".join(clean[5:])
        else:
            memo = " ".join(clean[4:])

    if not json_mode:
        _print_account_context(app)
        print(f"\n  {C.ACCENT}↗{C.R} Transfer: {C.TEXT}{amount} {symbol}{C.R} → {C.TEXT}{recipient}{C.R}")
        if memo:
            print(f"  {C.MUTED}Memo: {memo}{C.R}")

    if app.config.require_confirmation and not auto_yes:
        confirm = _safe_input(f"  Confirm? {C.MUTED}(y/n){C.R} ", args)
        if confirm.lower() not in ["y", "yes"]:
            if json_mode:
                print(_json.dumps({"error": "Cancelled by user"}))
            else:
                print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    if not json_mode:
        print(f"  {C.MUTED}Submitting...{C.R}")
    res = app.transfer(symbol, amount, recipient, memo=memo)

    if json_mode:
        print(_json.dumps(res, indent=2))
    elif res["success"]:
        print_transfer_receipt(res)
    else:
        err_msg = res.get('error', 'Unknown error')
        print(f"\n  {C.ERR}✗{C.R} FAILED: {err_msg}")
        raise RuntimeError(f"Transfer failed: {err_msg}")


def cmd_receive(app, args):
    """
    Show wallet address and check token associations.
    Usage: receive [token_symbol] [--json]
    """
    import json as _json

    json_mode = "--json" in args
    clean = _clean_args(args)

    if not app.executor:
        if json_mode:
            print(_json.dumps({"error": "Engine not initialized"}))
        else:
            print(f"  {C.ERR}✗{C.R} Engine not initialized.")
        return

    account_id = app.executor.hedera_account_id
    eoa = app.executor.eoa

    if json_mode:
        result = {"account": account_id, "evm_address": eoa}
        if clean:
            token_symbol = clean[0].upper()
            token_id = app.resolve_token_id(token_symbol) if token_symbol not in ["HBAR"] else "0.0.0"
            is_associated = True if token_symbol == "HBAR" else app.executor.check_token_association(token_id) if token_id else False
            result["token"] = token_symbol
            result["token_id"] = token_id
            result["associated"] = is_associated
        print(_json.dumps(result, indent=2))
        return

    # 1. Show Address
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

        if app.config.require_confirmation and not _is_auto_yes(args):
            confirm = _safe_input(f"\n  Associate now? (cost ~0.05 HBAR) {C.MUTED}(y/n){C.R} ", args)
            if confirm.lower() not in ["y", "yes"]:
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
    import json as _json
    json_mode = "--json" in args
    clean = [a for a in args if a not in ("--json", "--yes", "-y")]
    action = clean[0].lower() if clean else "view"

    if json_mode and action in ["view", "list", "ls"]:
        print(_json.dumps({"whitelist": app.get_whitelist()}, indent=2))
        return

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
            nickname = _safe_input(
                f"  Nickname for {address} {C.MUTED}(optional, press enter to skip){C.R}: ",
                args, default=""
            )

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
            choice = _safe_input(f"  Configure now? {C.MUTED}(y/n){C.R} ", default="n").strip().lower()
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
        choice = _safe_input(f"  Set Key now? {C.MUTED}(y/n) [n]{C.R} ", default="n").strip().lower()
        if choice in ["y", "yes"]:
            new_key = _safe_input(f"  Enter Your API Key: ", default="").strip()
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
# Status / Fund Commands
# ---------------------------------------------------------------------------

def cmd_status(app, args):
    """
    Combined account + balance snapshot in one call.
    Usage: status [--json]
    """
    import json as _json

    json_mode = "--json" in args

    account_id = getattr(app, 'account_id', None) or app.executor.hedera_account_id
    network = getattr(app, 'network', 'mainnet')
    eoa = app.executor.eoa
    robot_id = getattr(app.config, 'robot_account_id', None)
    simulate = app.config.simulate_mode

    # Get balances
    hbar_bal = 0.0
    hbar_price = 0.0
    tokens_out = {}
    total_usd = 0.0

    try:
        from lib.prices import price_manager
        price_manager.reload()
        balances = app.executor.get_balances()
        hbar_raw = app.executor.w3.eth.get_balance(app.executor.eoa)
        hbar_bal = hbar_raw / (10**18)
        hbar_price = price_manager.get_hbar_price()
        total_usd = hbar_bal * hbar_price

        from cli.pacman_filter import ui_filter
        tokens_data = ui_filter.get_token_metadata()

        for token_key, bal in balances.items():
            # Skip HBAR variants (already handled above)
            if token_key in ("HBAR", "0.0.0"):
                continue
            try:
                # Look up metadata: token_key is a token ID like "0.0.456858"
                meta = tokens_data.get(token_key, {})
                if not meta:
                    # Fallback: search by symbol match
                    for k, m in tokens_data.items():
                        if m.get("symbol") == token_key:
                            meta = m
                            break
                token_id = meta.get("id", token_key)
                # Skip blacklisted tokens (e.g., WHBAR)
                if ui_filter.is_blacklisted(token_id):
                    continue
                display_name = meta.get("symbol", token_key)
                price = price_manager.get_price(token_id) if token_id else 0
                val = round(bal * price, 2)
                tokens_out[display_name] = {"balance": bal, "price_usd": price, "value_usd": val}
                total_usd += val
            except Exception:
                tokens_out[token_key] = {"balance": bal, "price_usd": 0, "value_usd": 0}
    except Exception as e:
        if json_mode:
            print(_json.dumps({"error": f"Balance fetch failed: {e}"}))
            return

    # Known accounts
    known = []
    try:
        known = app.account_manager.get_known_accounts()
    except Exception:
        pass

    if json_mode:
        result = {
            "active_account": account_id,
            "network": network,
            "evm_address": eoa,
            "robot_account": robot_id,
            "simulate_mode": simulate,
            "known_accounts": known,
            "hbar": {
                "balance": round(hbar_bal, 6),
                "price_usd": round(hbar_price, 6),
                "value_usd": round(hbar_bal * hbar_price, 2),
            },
            "tokens": tokens_out,
            "total_usd": round(total_usd, 2),
        }
        print(_json.dumps(result, indent=2))
        return

    # Pretty display
    _print_account_context(app)
    print(f"\n  {C.BOLD}Account & Portfolio Snapshot{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.TEXT}Account:{C.R}     {C.BOLD}{account_id}{C.R}")
    print(f"  {C.TEXT}EVM:{C.R}         {C.MUTED}{eoa}{C.R}")
    print(f"  {C.TEXT}Network:{C.R}     {network}")
    print(f"  {C.TEXT}Simulate:{C.R}    {'Yes' if simulate else 'No (LIVE)'}")
    if robot_id:
        print(f"  {C.TEXT}Robot:{C.R}       {robot_id}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.BOLD}HBAR:{C.R}        {hbar_bal:.4f} (${hbar_bal * hbar_price:.2f})")
    for sym, data in tokens_out.items():
        if data["balance"] > 0:
            print(f"  {C.BOLD}{sym}:{C.R}        {data['balance']:.6f} (${data['value_usd']:.2f})")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.BOLD}Total:{C.R}       ${total_usd:.2f}")
    print()


def cmd_fund(app, args):
    """
    Fund your account with HBAR.
    - Mainnet: generates a MoonPay buy link pre-filled with your address.
    - Testnet: requests HBAR from the Hedera testnet faucet.
    Usage: fund [--json]
    """
    import json as _json

    json_mode = "--json" in args
    account_id = getattr(app, 'account_id', None) or app.executor.hedera_account_id
    network = getattr(app, 'network', 'mainnet')

    if not account_id or account_id == "Unknown":
        msg = "No active account. Run 'setup' first."
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    if network == "testnet":
        # Testnet faucet
        if not json_mode:
            print(f"\n  {C.BOLD}Testnet Faucet{C.R}")
            print(f"  {C.CHROME}{'─' * 56}{C.R}")
            print(f"  {C.MUTED}Requesting HBAR from Hedera testnet faucet...{C.R}")

        try:
            import requests
            resp = requests.post(
                "https://faucet.testnet.hedera.com/api/v1/address",
                json={"address": account_id},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                if json_mode:
                    print(_json.dumps({
                        "success": True,
                        "network": "testnet",
                        "account": account_id,
                        "message": "Testnet HBAR dispensed",
                    }))
                else:
                    print(f"  {C.OK}✅ Testnet HBAR dispensed to {account_id}{C.R}")
                    print(f"  {C.MUTED}Run 'balance' to check your updated balance.{C.R}")
            else:
                msg = f"Faucet returned status {resp.status_code}: {resp.text[:100]}"
                if json_mode:
                    print(_json.dumps({"error": msg}))
                else:
                    print(f"  {C.ERR}✗{C.R} {msg}")
        except Exception as e:
            msg = f"Faucet request failed: {e}"
            if json_mode:
                print(_json.dumps({"error": msg}))
            else:
                print(f"  {C.ERR}✗{C.R} {msg}")
        return

    # Mainnet — check if user has swappable tokens before suggesting fiat
    # MoonPay should only be primary when wallet is nearly empty (< $1 total)
    has_swappable = False
    swappable_hint = ""
    try:
        balances = app.get_balances()
        # Sum non-HBAR token values to find swappable assets
        from lib.prices import PriceManager
        pm = PriceManager.instance()
        total_usd = 0.0
        best_token = None
        best_val = 0.0
        for sym, bal in balances.items():
            if bal > 0 and sym != "HBAR":
                price = pm.get_price(sym) or 0.0
                val = bal * price
                total_usd += val
                if val > best_val:
                    best_val = val
                    best_token = sym
        # Also count HBAR value
        hbar_bal = balances.get("HBAR", 0.0)
        hbar_price = pm.get_price("HBAR") or 0.0
        total_usd += hbar_bal * hbar_price

        if total_usd >= 1.0 and best_token:
            has_swappable = True
            swappable_hint = f"You have ${total_usd:.2f} in tokens. Swap to HBAR: swap {best_token} for HBAR"
    except Exception:
        pass  # If balance check fails, just show MoonPay normally

    buy_url = f"https://www.moonpay.com/buy/hbar?walletAddress={account_id}"

    # Also offer Transak as alternative
    transak_url = f"https://global.transak.com/?cryptoCurrencyCode=HBAR&walletAddress={account_id}"

    if json_mode:
        result = {
            "network": "mainnet",
            "account": account_id,
            "has_swappable_tokens": has_swappable,
        }
        if has_swappable:
            result["swap_suggestion"] = swappable_hint
            result["note"] = "You already have tokens to swap. Use the swap command for HBAR. MoonPay is for purchasing with fiat when your wallet is empty."
        result["buy_url"] = buy_url
        result["alternative_url"] = transak_url
        result["provider"] = "MoonPay"
        result["alternative_provider"] = "Transak"
        result["instructions"] = "Open the URL to purchase HBAR with credit/debit card." if not has_swappable else "Swap existing tokens first. Use MoonPay only if you need to add new fiat funds."
        print(_json.dumps(result))
        return

    print(f"\n  {C.BOLD}Fund Your Account{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.TEXT}Account:{C.R}  {C.BOLD}{account_id}{C.R}")
    print(f"  {C.TEXT}Network:{C.R}  mainnet")
    print()

    if has_swappable:
        print(f"  {C.OK}You already have swappable tokens!{C.R}")
        print(f"  {C.TEXT}{swappable_hint}{C.R}")
        print()
        print(f"  {C.MUTED}If you still want to buy HBAR with fiat:{C.R}")
    else:
        print(f"  {C.BOLD}Buy HBAR with Credit/Debit Card:{C.R}")

    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print()
    print(f"  {C.OK}MoonPay{C.R} (Official HBAR Foundation partner):")
    print(f"  {C.ACCENT}{buy_url}{C.R}")
    print()
    print(f"  {C.MUTED}Alternative — Transak:{C.R}")
    print(f"  {C.MUTED}{transak_url}{C.R}")
    print()
    print(f"  {C.MUTED}HBAR will be delivered directly to your account.{C.R}")
    print(f"  {C.MUTED}No intermediary — MoonPay handles KYC and payment.{C.R}")
    print()


# ---------------------------------------------------------------------------
# Key Backup Helpers
# ---------------------------------------------------------------------------

def _auto_backup_new_key(account_id, private_key, nickname="", evm_address=""):
    """
    Automatically save a new account's private key to TWO locations:
    1. backups/ folder in the project (gitignored)
    2. ~/Downloads/ so the user sees it immediately

    Returns a dict with the file paths (no key content — safe for stdout).
    """
    from pathlib import Path
    import time
    import os

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_id = account_id.replace(".", "_")
    filename = f"pacman_key_{safe_id}_{timestamp}.txt"

    content = (
        f"PACMAN KEY BACKUP\n"
        f"{'=' * 50}\n"
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Account ID:  {account_id}\n"
        f"Nickname:    {nickname or '(none)'}\n"
        f"Key Type:    ECDSA (secp256k1)\n"
        f"Private Key: {private_key}\n"
    )
    if evm_address:
        content += f"EVM Address: {evm_address}\n"
    content += (
        f"\n{'=' * 50}\n"
        f"IMPORTANT: Save this to a password manager,\n"
        f"then delete this file. This key controls real\n"
        f"funds on Hedera. If lost, funds are gone forever.\n"
    )

    saved_paths = []

    # 1. Save to backups/ in project
    try:
        backup_dir = Path(__file__).resolve().parent.parent.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        path1 = backup_dir / filename
        with open(path1, "w") as f:
            f.write(content)
        saved_paths.append(str(path1))
    except Exception:
        pass

    # 2. Save to ~/Downloads (user will see it)
    try:
        downloads = Path.home() / "Downloads"
        if downloads.exists() and downloads.is_dir():
            path2 = downloads / filename
            with open(path2, "w") as f:
                f.write(content)
            saved_paths.append(str(path2))
    except Exception:
        pass

    return {"files": saved_paths, "filename": filename}


def _try_open_email_draft(subject, body_text, attachment_path=None):
    """
    Open the user's local email client with a draft containing the backup.

    On macOS: Uses AppleScript to create a Mail.app draft with the backup
    file attached. User just hits Send.
    On Linux/Windows: Falls back to mailto: URI (no attachment support).

    All execution is LOCAL via subprocess — nothing touches stdout or APIs.

    Returns True if opened, False if not available.
    """
    import subprocess
    import platform

    system = platform.system()

    # macOS: Use AppleScript to create a Mail.app draft WITH attachment
    if system == "Darwin" and attachment_path:
        try:
            import os
            abs_path = os.path.abspath(attachment_path)
            escaped_body = body_text.replace(chr(10), "\\n").replace('"', '\\"')
            applescript = f'''
            tell application "Mail"
                set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{escaped_body}"}}
                tell newMessage
                    make new attachment with properties {{file name:POSIX file "{abs_path}"}} at after the last paragraph
                    set visible to true
                end tell
                activate
            end tell
            '''
            subprocess.Popen(["osascript", "-e", applescript],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass

    # Fallback: mailto: URI (no attachment, but includes body text)
    try:
        import urllib.parse
        if len(body_text) > 1500:
            body_text = body_text[:1400] + "\n\n[Full backup in attached file or ~/Downloads]"
        mailto = f"mailto:?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body_text)}"

        if system == "Darwin":
            subprocess.Popen(["open", mailto], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif system == "Linux":
            subprocess.Popen(["xdg-open", mailto], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif system == "Windows":
            subprocess.Popen(["start", mailto], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Key Backup Command
# ---------------------------------------------------------------------------

def cmd_backup_keys(app, args):
    """
    Display key inventory and export to a secure local file.

    SECURITY MODEL: Private keys NEVER appear in stdout when --json is used.
    This prevents keys from flowing through agent APIs (OpenClaw, LLM pipes).
    Full keys are ONLY written to local files that the user accesses directly.

    Usage:
      backup-keys                → show key inventory (redacted on screen) + export options
      backup-keys --file         → export full keys to backups/key_backup_<date>.txt
      backup-keys --json         → structured JSON (keys REDACTED — safe for agents)
    """
    import json as _json
    import time
    import requests
    from pathlib import Path

    json_mode = "--json" in args
    file_mode = "--file" in args

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        msg = "No .env file found. Run 'setup' first."
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    # 1. Read all private keys from .env
    keys = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            # Collect private keys (not API keys or secrets)
            if "KEY" in k.upper() and "API" not in k.upper() and "SECRET" not in k.upper():
                if len(v) >= 60:  # Private keys are 64 hex chars
                    keys[k] = v

    if not keys:
        msg = "No private keys found in .env"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.MUTED}No private keys found in .env{C.R}")
        return

    # 2. Derive ECDSA public key and EVM address for each key
    inventory = []
    try:
        from hiero_sdk_python.crypto.private_key import PrivateKey as _PK
    except ImportError:
        _PK = None

    mirror = "https://mainnet-public.mirrornode.hedera.com"
    network = getattr(app, 'network', 'mainnet')
    if network == "testnet":
        mirror = "https://testnet.mirrornode.hedera.com"

    for name, hex_key in keys.items():
        entry = {
            "env_name": name,
            "key_hex_redacted": f"{hex_key[:4]}...{hex_key[-4:]}",
            "key_type": "ECDSA (secp256k1)",
            "ecdsa_pub": None,
            "evm_address": None,
            "account_id": None,
            "account_nickname": None,
            "is_active": name in ("PRIVATE_KEY", "ROBOT_PRIVATE_KEY", "MAIN_OPERATOR_KEY"),
            "is_backup": "BACKUP" in name,
        }

        if _PK:
            try:
                clean_hex = hex_key.replace("0x", "")
                pk = _PK.from_bytes_ecdsa(bytes.fromhex(clean_hex))
                pub = pk.public_key()
                evm = pub.to_evm_address()
                entry["ecdsa_pub"] = pub.to_string()
                entry["evm_address"] = f"0x{evm}"

                # Look up on-chain account — only for active keys (skip archived to save API calls)
                if entry["is_active"]:
                    try:
                        r = requests.get(f"{mirror}/api/v1/accounts?account.publickey={pub.to_string()}&limit=1", timeout=5)
                        if r.status_code == 200:
                            accts = r.json().get("accounts", [])
                            if accts:
                                entry["account_id"] = accts[0].get("account")
                    except Exception:
                        pass
            except Exception:
                pass

        inventory.append(entry)

    # 3. File export — handle --file first (can combine with --json)
    backup_file_path = None
    downloads_path = None
    email_opened = False

    if file_mode:
        backup_dir = Path(__file__).resolve().parent.parent.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"key_backup_{timestamp}.txt"

        file_content = (
            f"PACMAN KEY BACKUP — {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'=' * 60}\n"
            f"IMPORTANT: Save to a password manager, then delete this file.\n"
            f"These keys control real funds on Hedera mainnet.\n"
            f"{'=' * 60}\n\n"
        )
        for entry in inventory:
            file_content += f"{'─' * 60}\n"
            file_content += f"Name:        {entry['env_name']}\n"
            file_content += f"Status:      {'ACTIVE' if entry['is_active'] else 'ARCHIVED'}\n"
            file_content += f"Key Type:    {entry['key_type']}\n"
            file_content += f"Private Key: {keys[entry['env_name']]}\n"
            if entry.get("evm_address"):
                file_content += f"EVM Address: {entry['evm_address']}\n"
            if entry.get("account_id"):
                acct_str = entry['account_id']
                if entry.get("account_nickname"):
                    acct_str += f" ({entry['account_nickname']})"
                file_content += f"Account ID:  {acct_str}\n"
            file_content += "\n"

        # Write to backups/
        with open(backup_file, "w") as f:
            f.write(file_content)
        backup_file_path = str(backup_file)

        # Also write to ~/Downloads so user sees it immediately
        try:
            dl_dir = Path.home() / "Downloads"
            if dl_dir.exists() and dl_dir.is_dir():
                dl_file = dl_dir / f"key_backup_{timestamp}.txt"
                with open(dl_file, "w") as f:
                    f.write(file_content)
                downloads_path = str(dl_file)
        except Exception:
            pass

        # Try to open email client with a SHORT summary (not full keys — too long for mailto:)
        email_subject = f"Pacman Key Backup — {time.strftime('%Y-%m-%d')}"
        active_keys = [e for e in inventory if e["is_active"]]
        email_summary = f"Pacman key backup saved to:\n{backup_file_path}\n"
        if downloads_path:
            email_summary += f"{downloads_path}\n"
        email_summary += f"\n{len(active_keys)} active key(s), {len(inventory)} total.\n\n"
        for e in active_keys:
            email_summary += f"- {e['env_name']}: {e.get('account_id', 'unknown')} ({e['key_hex_redacted']})\n"
        email_summary += "\nAttach the backup file from Downloads to this email for safekeeping."
        email_opened = _try_open_email_draft(email_subject, email_summary, attachment_path=backup_file_path)

    # 4. Output
    if json_mode:
        result = {
            "count": len(inventory),
            "keys": inventory,
            "security_note": "Private keys are redacted. Full keys saved to local files only.",
        }
        if backup_file_path:
            result["backup_file"] = backup_file_path
            result["downloads_file"] = downloads_path
            result["email_draft_opened"] = email_opened
            result["success"] = True
        print(_json.dumps(result, indent=2))
        return

    # Pretty display (keys redacted on screen too)
    print(f"\n  {C.BOLD}Key Inventory{C.R}")
    print(f"  {C.CHROME}{'═' * 60}{C.R}")
    print(f"  {C.MUTED}Found {len(inventory)} key(s) in .env{C.R}")
    print()

    for entry in inventory:
        is_active = entry["is_active"]
        is_backup = entry["is_backup"]
        status = f"{C.OK}ACTIVE{C.R}" if is_active else f"{C.MUTED}ARCHIVE{C.R}"

        print(f"  {C.BOLD}{entry['env_name']}{C.R}  [{status}]")
        print(f"    Key:     {C.ACCENT}{entry['key_hex_redacted']}{C.R}")
        if entry.get("evm_address"):
            print(f"    EVM:     {entry['evm_address']}")
        if entry.get("account_id"):
            nick = f" ({entry['account_nickname']})" if entry.get("account_nickname") else ""
            print(f"    Account: {C.OK}{entry['account_id']}{nick}{C.R}")
        elif not is_backup:
            print(f"    Account: {C.WARN}No on-chain match found{C.R}")
        print()

    # Show file export results (file was already written above if --file)
    if file_mode and backup_file_path:
        print(f"  {C.OK}✅ Key backup saved:{C.R}")
        print(f"    {C.ACCENT}{backup_file_path}{C.R}")
        if downloads_path:
            print(f"    {C.ACCENT}{downloads_path}{C.R}")
        if email_opened:
            print(f"  {C.OK}✓{C.R} Email draft opened in your mail client.")
        print(f"\n  {C.WARN}⚠  Save to a password manager, then delete the files.{C.R}")
        return

    # Default: show options
    print(f"  {C.BOLD}Backup Options:{C.R}")
    print(f"  {C.CHROME}{'─' * 60}{C.R}")
    print(f"  {C.ACCENT}backup-keys --file{C.R}   Save full backup to ~/Downloads + backups/")
    print(f"  {C.ACCENT}backup-keys --json{C.R}   Key inventory (redacted, safe for agents)")
    print()
    print(f"  {C.MUTED}Keys are automatically backed up when new accounts are created.{C.R}")
    print(f"  {C.WARN}⚠  Private keys never appear in agent output or API traffic.{C.R}")
    print()


# ---------------------------------------------------------------------------
# .env Helpers
# ---------------------------------------------------------------------------

def _update_env(key, value, force=False):
    """
    Update or add a key-value pair in the .env file.

    SAFETY: If the key contains 'KEY' (but not 'API'), and the old value differs,
    a timestamped backup line is automatically appended BEFORE overwriting.
    This ensures private keys are NEVER lost — they are the only copy of
    self-custody funds.
    """
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

    for line in existing_lines:
        if line.strip().startswith(f"{key}="):
            current_val = line.split("=", 1)[1].strip()

            # SAFETY: Archive the old value if it's a private key
            # Never lose a key — it may be the only copy of self-custody funds
            is_sensitive = "KEY" in key.upper() and "API" not in key.upper() and "SECRET" not in key.upper()
            if is_sensitive and current_val and current_val != value:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_key = f"{key}_BACKUP_{timestamp}"
                lines.append(f"# Archived by _update_env on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                lines.append(f"{backup_key}={current_val}\n")

            if not force and current_val and current_val != value:
                print(f"\n  {C.WARN}⚠  Warning: {key} already has a value.{C.R}")
                confirm = _safe_input(f"  Overwrite? {C.MUTED}(y/n){C.R} ")
                if confirm.lower() not in ["y", "yes"]:
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
