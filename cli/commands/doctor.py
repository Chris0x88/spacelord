"""
Pacman Doctor - System Health & AI Safety Diagnostics
====================================================
Validates environment, accounts, and file permissions.
Helps prevent AI agents from getting stuck in loops due to bad config.
"""
import os
import json
from pathlib import Path
from cli.display import C

def cmd_doctor(app, args):
    """Run system health check."""
    print(f"\n  {C.BOLD}👨‍⚕️ Pacman Doctor Diagnostics{C.R}")
    print(f"  {'─' * 45}")
    
    root_dir = Path(__file__).resolve().parent.parent.parent
    errors = 0
    warnings = 0

    # 1. Environment Check
    env_path = root_dir / ".env"
    print(f"  {C.BOLD}[1] Environment File{C.R}")
    if not env_path.exists():
        print(f"  {C.ERR}✗{C.R} .env file missing! Run 'pacman setup'")
        errors += 1
    else:
        print(f"  {C.OK}✓{C.R} .env file found.")
        
        # Check specific keys
        from src.config import PacmanConfig
        config = app.config
        
        if not config.private_key:
            print(f"  {C.ERR}✗{C.R} PRIVATE_KEY not found in .env")
            errors += 1
        else:
            print(f"  {C.OK}✓{C.R} PRIVATE_KEY is configured.")
            
        # Strip literal quotes that sometimes appear if .env is not parsed by a library
        main_id = (config.hedera_account_id or "").strip("'\"")
        robot_id = (config.robot_account_id or "").strip("'\"")

        if not main_id:
            print(f"  {C.WARN}⚠{C.R} HEDERA_ACCOUNT_ID missing (Main account)")
            warnings += 1
        else:
            print(f"  {C.OK}✓{C.R} Main Account: {main_id}")
            
        if not robot_id:
            print(f"  {C.MUTED}-  ROBOT_ACCOUNT_ID not set (Daemon account){C.R}")
        else:
            print(f"  {C.OK}✓{C.R} Robot Account: {robot_id}")

    # 2. Registry Check
    print(f"\n  {C.BOLD}[2] Account Registry{C.R}")
    accounts_path = root_dir / "data" / "accounts.json"
    if not accounts_path.exists():
        print(f"  {C.ERR}✗{C.R} data/accounts.json missing!")
        errors += 1
    else:
        try:
            with open(accounts_path) as f:
                accounts = json.load(f)
            print(f"  {C.OK}✓{C.R} {len(accounts)} accounts in registry.")
            
            # Cross-check IDs
            known_ids = [a.get("id") for a in accounts]
            if main_id and main_id not in known_ids:
                print(f"  {C.WARN}⚠{C.R} Main ID {main_id} not in registry!")
                warnings += 1
            
            # Only warn if robot ID is configured but missing from registry
            if robot_id and robot_id not in known_ids:
                print(f"  {C.WARN}⚠{C.R} Robot ID {robot_id} not in registry!")
                warnings += 1
        except Exception as e:
            print(f"  {C.ERR}✗{C.R} Failed to parse accounts.json: {e}")
            errors += 1

    # 3. Directory Permissions
    print(f"\n  {C.BOLD}[3] Permissions & Data{C.R}")
    dirs_to_check = ["data", "logs", "backups", "execution_records"]
    for d in dirs_to_check:
        d_path = root_dir / d
        if not d_path.exists():
            print(f"  {C.WARN}⚠{C.R} Directory '{d}' missing.")
            warnings += 1
        elif not os.access(d_path, os.W_OK):
            print(f"  {C.ERR}✗{C.R} Directory '{d}' is not writable!")
            errors += 1
        else:
            print(f"  {C.OK}✓{C.R} Directory '{d}' is OK.")

    # Summary
    print(f"\n  {'─' * 45}")
    if errors > 0:
        print(f"  {C.ERR}{C.BOLD}SYSTEM UNHEALTHY:{C.R} {errors} errors, {warnings} warnings.")
    elif warnings > 0:
        print(f"  {C.WARN}{C.BOLD}SYSTEM CAUTION:{C.R} {warnings} warnings found.")
    else:
        print(f"  {C.OK}{C.BOLD}SYSTEM HEALTHY:{C.R} All checks passed.")
    print(f"  {'─' * 45}\n")
