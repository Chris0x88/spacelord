#!/usr/bin/env python3
"""
CLI Commands: Staking
=====================

Handles: stake, unstake (HIP-406 native staking via Hedera SDK).
"""

import os
from pathlib import Path
from cli.display import C


def cmd_stake(app, args):
    """
    Stake your account to a consensus node for HBAR rewards.
    Usage: stake [node_id] [--json] (Default: 5 - Google)
    """
    import json as _json
    json_mode = "--json" in args
    clean = [a for a in args if a not in ("--json", "--yes", "-y")]

    try:
        from lib.staking import StakingManager
    except ImportError:
        msg = "Staking Plugin not installed. Missing lib/staking.py"
        if json_mode:
            print(_json.dumps({"success": False, "error": msg}))
        else:
            print(f"  {C.WARN}⚠ {msg}{C.R}")
        return

    # default to Google (Node 5)
    try:
        node_id = int(clean[0]) if clean else 5
    except ValueError:
        msg = f"Invalid Node ID: {clean[0]}. Must be an integer."
        if json_mode:
            print(_json.dumps({"success": False, "error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    if not app.config.private_key:
        print(f"  {C.ERR}✗{C.R} Staking requires a configured Private Key.")
        print(f"  {C.MUTED}Run 'setup' to configure.{C.R}")
        return

    # Initialize Manager
    try:
        manager = StakingManager(network=app.config.network)

        active_account_id = app.executor.hedera_account_id
        if not active_account_id:
             print(f"  {C.ERR}✗{C.R} Account ID not configured.")
             return

        # Staking uses AccountUpdateTransaction which requires the account's ADMIN key,
        # not the EVM signing key. On Hedera these can be different keys.
        # MAIN_OPERATOR_KEY is the admin key; PRIVATE_KEY is the EVM signing key.
        admin_key = os.getenv("MAIN_OPERATOR_KEY", "").strip()
        if admin_key:
            manager.set_operator(active_account_id, admin_key)
        else:
            # Fallback to PRIVATE_KEY (works if admin key == signing key)
            pk = app.config.private_key.reveal()
            manager.set_operator(active_account_id, pk)
            del pk

        if not json_mode:
            node_name = "Google Council Node (5)" if node_id == 5 else f"Node {node_id}"
            print(f"\n  {C.ACCENT}⟳{C.R} Staking for Account {C.BOLD}{active_account_id}{C.R}...")
            print(f"  {C.ACCENT}⟳{C.R} To {C.BOLD}{node_name}{C.R}...")
            print(f"  {C.MUTED}ℹ This stakes your {C.BOLD}full liquid balance{C.R}{C.MUTED}.{C.R}")
            print(f"  {C.MUTED}ℹ Funds remain available for use immediately.{C.R}")
        
        # SAFETY CHECK: Verify Key Derivation
        try:
            derived_evm = manager.get_operator_evm_address()
            expected_evm = app.executor.eoa
            
            if derived_evm and expected_evm:
                if derived_evm.lower() != expected_evm.lower():
                    print(f"  {C.ERR}✗{C.R} SAFETY STOP: Key derivation mismatch.")
                    print(f"  {C.MUTED}Derived:  {derived_evm}{C.R}")
                    print(f"  {C.MUTED}Expected: {expected_evm}{C.R}")
                    print(f"  {C.WARN}Aborting to prevent INVALID_SIGNATURE.{C.R}")
                    return
        except Exception as e:
            if app.config.debug:
                 print(f"  {C.WARN}⚠ Verification skipped: {e}{C.R}")

        # Execute (or Simulate)
        is_sim = app.config.simulate_mode
        if is_sim:
             print(f"  {C.WARN}⚠ Simulation Mode: Transaction will not be broadcast.{C.R}")

        res = manager.stake_to_node(node_id, simulate=is_sim)

        if json_mode:
            print(_json.dumps({"success": res.get("success", False), "node_id": node_id,
                              "tx_id": res.get("tx_id"), "error": res.get("error")}))
        elif res.get("success"):
            status_icon = "✅" if not is_sim else "⚠️ [SIM]"
            print(f"  {C.OK}{status_icon} Successfully staked to Node {node_id}!{C.R}")
            if not is_sim:
                 print(f"  {C.MUTED}Tx ID: {res.get('tx_id')}{C.R}")
            print(f"  {C.MUTED}Rewards will begin accruing automatically.{C.R}")
        else:
             print(f"  {C.ERR}✗{C.R} Staking Failed: {res.get('error')}")

        if res.get("success"):
            try:
                app.executor._record_staking_transaction(
                    mode="STAKE", node_id=node_id, tx_id=res.get('tx_id'), success=True)
            except Exception:
                pass

    except Exception as e:
        if json_mode:
            print(_json.dumps({"success": False, "error": str(e)}))
        else:
            print(f"  {C.ERR}✗{C.R} Plugin Error: {e}")


def cmd_unstake(app, args):
    """
    Unstake your account to stop earning rewards.
    Usage: unstake [--json]
    """
    import json as _json
    json_mode = "--json" in args

    try:
        from lib.staking import StakingManager
    except ImportError:
        msg = "Staking Plugin not installed."
        if json_mode: print(_json.dumps({"success": False, "error": msg}))
        else: print(f"  {C.WARN}⚠ {msg}{C.R}")
        return

    if not app.config.private_key:
        msg = "Unstaking requires a configured Private Key."
        if json_mode: print(_json.dumps({"success": False, "error": msg}))
        else: print(f"  {C.ERR}✗{C.R} {msg}")
        return

    try:
        manager = StakingManager(network=app.config.network)
        active_account_id = app.executor.hedera_account_id
        if not active_account_id:
            msg = "Account ID not configured."
            if json_mode: print(_json.dumps({"success": False, "error": msg}))
            else: print(f"  {C.ERR}✗{C.R} {msg}")
            return

        admin_key = os.getenv("MAIN_OPERATOR_KEY", "").strip()
        if admin_key:
            manager.set_operator(active_account_id, admin_key)
        else:
            pk = app.config.private_key.reveal()
            manager.set_operator(active_account_id, pk)
            del pk

        if not json_mode:
            print(f"\n  {C.ACCENT}⟳{C.R} Unstaking for Account {C.BOLD}{active_account_id}{C.R}...")

        res = manager.stake_to_node(-1, simulate=app.config.simulate_mode)

        if json_mode:
            print(_json.dumps({"success": res.get("success", False),
                              "tx_id": res.get("tx_id"), "error": res.get("error")}))
        elif res.get("success"):
            print(f"  {C.OK}✅ Successfully Unstaked!{C.R}")
        else:
            print(f"  {C.ERR}✗{C.R} Unstaking Failed: {res.get('error')}")

        if res.get("success"):
            try:
                app.executor._record_staking_transaction(
                    mode="UNSTAKE", node_id=-1, tx_id=res.get('tx_id'), success=True)
            except Exception: pass

    except Exception as e:
        if json_mode: print(_json.dumps({"success": False, "error": str(e)}))
        else: print(f"  {C.ERR}✗{C.R} Plugin Error: {e}")
