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
    Usage: stake [node_id] (Default: 5 - Google)
    """
    try:
        from lib.staking import StakingManager
    except ImportError:
        print(f"  {C.WARN}⚠ Staking Plugin not installed.{C.R}")
        print(f"  {C.MUTED}Missing lib/staking.py{C.R}")
        return

    # default to Google (Node 5)
    try:
        node_id = int(args[0]) if args else 5
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid Node ID. Must be an integer.")
        return

    if not app.config.private_key:
        print(f"  {C.ERR}✗{C.R} Staking requires a configured Private Key.")
        print(f"  {C.MUTED}Run 'setup' to configure.{C.R}")
        return

    # Initialize Manager
    try:
        manager = StakingManager(network=app.config.network)
        # Validate and Force-Reload Account ID from .env
        env_id = None
        try:
            env_path = Path(__file__).resolve().parent.parent.parent / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.strip().startswith("HEDERA_ACCOUNT_ID="):
                            env_id = line.strip().split("=")[1].strip()
                            break
        except Exception:
            pass

        # Prefer .env value if found, otherwise stick to config
        active_account_id = env_id if env_id else app.config.hedera_account_id
        
        if not active_account_id:
             print(f"  {C.ERR}✗{C.R} Account ID not configured.")
             return

        # Set Operator
        pk = app.config.private_key.reveal()
        manager.set_operator(active_account_id, pk)
        del pk  # Cleanup

        if node_id == 5:
            print(f"\n  {C.ACCENT}⟳{C.R} Staking for Account {C.BOLD}{active_account_id}{C.R}...")
            print(f"  {C.ACCENT}⟳{C.R} To {C.BOLD}Google Council Node (5){C.R}...")
        else:
            print(f"\n  {C.ACCENT}⟳{C.R} Staking for Account {C.BOLD}{active_account_id}{C.R}...")
            print(f"  {C.ACCENT}⟳{C.R} To Node {C.BOLD}{node_id}{C.R}...")
        
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

        if res.get("success"):
            status_icon = "✅" if not is_sim else "⚠️ [SIM]"
            print(f"  {C.OK}{status_icon} Successfully staked to Node {node_id}!{C.R}")
            if not is_sim:
                 print(f"  {C.MUTED}Tx ID: {res.get('tx_id')}{C.R}")
            print(f"  {C.MUTED}Rewards will begin accruing automatically.{C.R}")
            
            # Record History
            try:
                app.executor._record_staking_transaction(
                    mode="STAKE", 
                    node_id=node_id, 
                    tx_id=res.get('tx_id'), 
                    success=True
                )
            except Exception as e:
                if app.config.debug: print(f"  {C.WARN}History save failed: {e}{C.R}")
        else:
             print(f"  {C.ERR}✗{C.R} Staking Failed: {res.get('error')}")

    except Exception as e:
         print(f"  {C.ERR}✗{C.R} Plugin Error: {e}")


def cmd_unstake(app, args):
    """
    Unstake your account to stop earning rewards.
    Usage: unstake
    """
    try:
        from lib.staking import StakingManager
    except ImportError:
         print(f"  {C.WARN}⚠ Staking Plugin not installed.{C.R}")
         return

    if not app.config.private_key:
        print(f"  {C.ERR}✗{C.R} Unstaking requires a configured Private Key.")
        return

    try:
        manager = StakingManager(network=app.config.network)
        
        # Validate and Force-Reload Account ID from .env
        env_id = None
        try:
            env_path = Path(__file__).resolve().parent.parent.parent / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.strip().startswith("HEDERA_ACCOUNT_ID="):
                            env_id = line.strip().split("=")[1].strip()
                            break
        except Exception:
            pass
        
        active_account_id = env_id if env_id else app.config.hedera_account_id
        
        if not active_account_id:
             print(f"  {C.ERR}✗{C.R} Account ID not configured.")
             return

        pk = app.config.private_key.reveal()
        manager.set_operator(active_account_id, pk)
        del pk

        print(f"\n  {C.ACCENT}⟳{C.R} Unstaking for Account {C.BOLD}{active_account_id}{C.R}...")
        
        # Safety Check (Address Verification)
        try:
            derived_evm = manager.get_operator_evm_address()
            expected_evm = app.executor.eoa
            if derived_evm and expected_evm and derived_evm.lower() != expected_evm.lower():
                 print(f"  {C.ERR}✗{C.R} SAFETY STOP: Key derivation mismatch.")
                 return
        except: pass

        is_sim = app.config.simulate_mode
        if is_sim:
             print(f"  {C.WARN}⚠ Simulation Mode: Transaction will not be broadcast.{C.R}")

        # Node ID -1 triggers Unstake
        res = manager.stake_to_node(-1, simulate=is_sim)

        if res.get("success"):
            status_icon = "✅" if not is_sim else "⚠️ [SIM]"
            print(f"  {C.OK}{status_icon} Successfully Unstaked!{C.R}")
            
            # Record History
            try:
                app.executor._record_staking_transaction(
                    mode="UNSTAKE", 
                    node_id=-1, 
                    tx_id=res.get('tx_id'), 
                    success=True
                )
            except Exception as e:
                if app.config.debug: print(f"  {C.WARN}History save failed: {e}{C.R}")
        else:
             print(f"  {C.ERR}✗{C.R} Unstaking Failed: {res.get('error')}")

    except Exception as e:
         print(f"  {C.ERR}✗{C.R} Plugin Error: {e}")
