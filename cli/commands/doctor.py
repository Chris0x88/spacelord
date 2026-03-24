"""
Space Lord Doctor - System Health & AI Safety Diagnostics
====================================================
Validates environment, accounts, daemons, gas, keys, and connectivity.
Helps prevent AI agents from getting stuck in loops due to bad config.
"""
import os
import json
import sys
from pathlib import Path
from cli.display import C

PID_FILE = "data/robot.pid"


def cmd_doctor(app, args):
    """Run comprehensive system health check."""
    json_mode = "--json" in args

    print(f"\n  {C.BOLD}👨‍⚕️ Space Lord Doctor Diagnostics{C.R}")
    print(f"  {'─' * 45}")

    root_dir = Path(__file__).resolve().parent.parent.parent
    errors = 0
    warnings = 0
    checks = []

    def ok(msg, section=""):
        nonlocal checks
        print(f"  {C.OK}✓{C.R} {msg}")
        checks.append({"status": "ok", "message": msg, "section": section})

    def warn(msg, section=""):
        nonlocal warnings, checks
        warnings += 1
        print(f"  {C.WARN}⚠{C.R} {msg}")
        checks.append({"status": "warning", "message": msg, "section": section})

    def fail(msg, section=""):
        nonlocal errors, checks
        errors += 1
        print(f"  {C.ERR}✗{C.R} {msg}")
        checks.append({"status": "error", "message": msg, "section": section})

    # ── 1. Environment File ────────────────────────────────────
    env_path = root_dir / ".env"
    print(f"  {C.BOLD}[1] Environment{C.R}")
    if not env_path.exists():
        fail(".env file missing! Run 'setup'", "env")
    else:
        ok(".env file found.", "env")

        config = app.config
        if not config.private_key:
            fail("PRIVATE_KEY not set", "env")
        else:
            ok("PRIVATE_KEY configured", "env")

        main_id = (config.hedera_account_id or "").strip("'\"")
        robot_id = (config.robot_account_id or "").strip("'\"")

        if not main_id:
            warn("HEDERA_ACCOUNT_ID missing", "env")
        else:
            ok(f"Main Account: {main_id}", "env")

        if robot_id:
            ok(f"Robot Account: {robot_id}", "env")
            # Check ROBOT_PRIVATE_KEY
            if config.robot_private_key:
                ok("ROBOT_PRIVATE_KEY configured (independent key)", "env")
            else:
                warn("ROBOT_PRIVATE_KEY missing — robot uses main key (shared EVM address)", "env")
        else:
            print(f"  {C.MUTED}-  No robot account configured{C.R}")

        # Check MAIN_OPERATOR_KEY
        main_op = os.getenv("MAIN_OPERATOR_KEY")
        if main_op:
            ok("MAIN_OPERATOR_KEY set (Hedera SDK operator)", "env")
        else:
            print(f"  {C.MUTED}-  MAIN_OPERATOR_KEY not set (only needed for native Hedera SDK ops){C.R}")

    # ── 2. Account Registry ────────────────────────────────────
    print(f"\n  {C.BOLD}[2] Accounts{C.R}")
    accounts_path = root_dir / "data" / "accounts.json"
    if not accounts_path.exists():
        fail("data/accounts.json missing", "accounts")
    else:
        try:
            with open(accounts_path) as f:
                accounts = json.load(f)
            ok(f"{len(accounts)} account(s) in registry", "accounts")

            known_ids = [a.get("id") for a in accounts]
            if main_id and main_id not in known_ids:
                warn(f"Main ID {main_id} not in registry", "accounts")
            if robot_id and robot_id not in known_ids:
                warn(f"Robot ID {robot_id} not in registry", "accounts")
        except Exception as e:
            fail(f"accounts.json parse error: {e}", "accounts")

    # ── 3. Gas (HBAR Balance) ──────────────────────────────────
    print(f"\n  {C.BOLD}[3] Gas{C.R}")
    try:
        hbar_raw = app.executor.w3.eth.get_balance(app.executor.eoa)
        hbar_bal = hbar_raw / (10**18)
        if hbar_bal >= 5:
            ok(f"HBAR balance: {hbar_bal:.2f} (sufficient)", "gas")
        elif hbar_bal >= 1:
            warn(f"HBAR balance: {hbar_bal:.2f} — low, top up to >= 5", "gas")
        else:
            fail(f"HBAR balance: {hbar_bal:.2f} — critically low, transactions will fail", "gas")
    except Exception as e:
        warn(f"Could not check HBAR balance: {e}", "gas")

    # ── 4. Daemon Status ───────────────────────────────────────
    print(f"\n  {C.BOLD}[4] Daemons{C.R}")

    # Check for running daemon process
    daemon_running = False
    try:
        import subprocess
        result = subprocess.run(["pgrep", "-f", "cli.main daemon"],
                                capture_output=True, text=True, timeout=5)
        daemon_pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        if daemon_pids:
            daemon_running = True
            ok(f"Daemon process running (PID: {', '.join(daemon_pids)})", "daemon")
        else:
            print(f"  {C.MUTED}-  No daemon running (start with: ./launch.sh daemon-start){C.R}")
    except Exception:
        print(f"  {C.MUTED}-  Could not check daemon status{C.R}")

    # Check robot PID file
    pid_path = root_dir / PID_FILE
    if pid_path.exists():
        try:
            with open(pid_path) as f:
                pid = int(f.read().strip())
            # Check if the process is actually alive
            try:
                os.kill(pid, 0)
                ok(f"Robot process alive (PID: {pid})", "daemon")
            except ProcessLookupError:
                warn(f"Stale robot PID file (PID {pid} is dead) — cleaning up", "daemon")
                pid_path.unlink()
        except Exception:
            warn("Corrupt robot PID file — removing", "daemon")
            try:
                pid_path.unlink()
            except Exception:
                pass

    # Check if API port 8088 is responding
    if daemon_running:
        try:
            import requests
            secret = os.getenv("SPACELORD_API_SECRET", "")
            r = requests.get(f"http://127.0.0.1:8088/health", timeout=3)
            if r.status_code == 200:
                ok("API responding on :8088", "daemon")
            else:
                warn(f"API returned {r.status_code}", "daemon")
        except Exception:
            warn("Daemon running but API not responding on :8088", "daemon")

    # ── 5. Directories & Files ─────────────────────────────────
    print(f"\n  {C.BOLD}[5] Files{C.R}")
    dirs_to_check = ["data", "logs", "backups", "execution_records"]
    for d in dirs_to_check:
        d_path = root_dir / d
        if not d_path.exists():
            warn(f"Directory '{d}' missing", "files")
        elif not os.access(d_path, os.W_OK):
            fail(f"Directory '{d}' not writable", "files")
        else:
            ok(f"'{d}' OK", "files")

    # Check key backup status
    backup_dir = root_dir / "backups"
    backup_files = list(backup_dir.glob("key_backup_*.txt")) + list(backup_dir.glob("spacelord_key_*.txt")) if backup_dir.exists() else []
    if backup_files:
        latest = max(backup_files, key=lambda f: f.stat().st_mtime)
        ok(f"Key backup exists ({latest.name})", "files")
    else:
        warn("No key backup found — run 'backup-keys --file'", "files")

    # ── 6. Connectivity ───────────────────────────────────────
    print(f"\n  {C.BOLD}[6] Connectivity{C.R}")
    try:
        import requests
        r = requests.get("https://mainnet-public.mirrornode.hedera.com/api/v1/network/supply", timeout=5)
        if r.status_code == 200:
            ok("Hedera Mirror Node reachable", "network")
        else:
            warn(f"Mirror Node returned {r.status_code}", "network")
    except Exception:
        fail("Cannot reach Hedera Mirror Node", "network")

    try:
        import requests
        r = requests.get("https://mainnet.hashio.io/api", timeout=5)
        ok("Hashio RPC reachable", "network")
    except Exception:
        warn("Hashio RPC not responding", "network")

    # ── Summary ────────────────────────────────────────────────
    print(f"\n  {'─' * 45}")
    if errors > 0:
        print(f"  {C.ERR}{C.BOLD}UNHEALTHY:{C.R} {errors} error(s), {warnings} warning(s)")
        print(f"  {C.MUTED}Fix errors above before trading.{C.R}")
    elif warnings > 0:
        print(f"  {C.WARN}{C.BOLD}CAUTION:{C.R} {warnings} warning(s)")
    else:
        print(f"  {C.OK}{C.BOLD}SYSTEM HEALTHY:{C.R} All checks passed.")

    # Launch guidance
    if not daemon_running:
        print(f"\n  {C.BOLD}Quick Start:{C.R}")
        print(f"  {C.ACCENT}./launch.sh daemon-start{C.R}  Start background daemon (robot + API + dashboard)")
        print(f"  {C.ACCENT}./launch.sh dashboard{C.R}     Open dashboard at http://127.0.0.1:8088")
    print(f"  {'─' * 45}\n")

    if json_mode:
        import json as _json
        print(_json.dumps({
            "healthy": errors == 0,
            "errors": errors,
            "warnings": warnings,
            "checks": checks,
            "daemon_running": daemon_running,
        }, indent=2))
