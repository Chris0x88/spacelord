#!/usr/bin/env python3
"""
OpenClaw Agent Setup — One-command onboarding for Pacman + Hedera
=================================================================

Creates a fully configured OpenClaw agent with:
  - Hedera wallet (import existing key or generate fresh)
  - Telegram bot routing (dedicated bot via BotFather)
  - Daemon auto-start and heartbeat cron
  - Skill symlink to SKILL.md

Usage:
  ./launch.sh openclaw-setup          # Full guided setup
  python3 scripts/openclaw_setup.py   # Direct invocation
"""

import json
import os
import sys
import shutil
import getpass
import time
from pathlib import Path

# ─── Colors ───────────────────────────────────────────────────
class C:
    BOLD    = "\033[1m"
    MUTED   = "\033[2m"
    ACCENT  = "\033[36m"     # cyan
    OK      = "\033[32m"     # green
    WARN    = "\033[33m"     # yellow
    ERR     = "\033[31m"     # red
    R       = "\033[0m"      # reset

PACMAN_DIR = Path(__file__).resolve().parent.parent
OPENCLAW_DIR = PACMAN_DIR / "openclaw"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
ENV_FILE = PACMAN_DIR / ".env"
ENV_TEMPLATE = PACMAN_DIR / ".env.template"


def banner():
    print(f"""
  {C.BOLD}{C.ACCENT}ᗧ  PACMAN × OPENCLAW{C.R}
  {C.MUTED}{'═' * 52}{C.R}
  {C.BOLD}One-command setup for your AI Hedera trading agent.{C.R}
  {C.MUTED}This wizard will configure:{C.R}
  {C.MUTED}  1. Hedera wallet credentials{C.R}
  {C.MUTED}  2. OpenClaw agent workspace + skill linking{C.R}
  {C.MUTED}  3. Telegram bot routing (optional){C.R}
  {C.MUTED}{'─' * 52}{C.R}
""")


def safe_input(prompt, default=""):
    """Input that won't crash in pipes."""
    if not sys.stdin.isatty():
        return default
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n  {C.MUTED}Cancelled.{C.R}")
        sys.exit(0)


def check_prerequisites():
    """Verify OpenClaw is installed."""
    openclaw_bin = shutil.which("openclaw")
    if not openclaw_bin:
        print(f"  {C.ERR}✗ OpenClaw not found.{C.R}")
        print(f"  {C.MUTED}Install: https://openclaw.ai{C.R}")
        print(f"  {C.MUTED}Then re-run: ./launch.sh openclaw-setup{C.R}")
        return False

    if not OPENCLAW_CONFIG.exists():
        print(f"  {C.WARN}⚠  No openclaw.json found at {OPENCLAW_CONFIG}{C.R}")
        print(f"  {C.MUTED}Run 'openclaw doctor' first to initialize.{C.R}")
        return False

    print(f"  {C.OK}✓{C.R} OpenClaw found at {C.MUTED}{openclaw_bin}{C.R}")
    print(f"  {C.OK}✓{C.R} Config at {C.MUTED}{OPENCLAW_CONFIG}{C.R}")
    return True


# ─── Step 1: Hedera Wallet ───────────────────────────────────

def setup_hedera_wallet():
    """Configure Hedera credentials in .env — import or generate."""
    print(f"\n  {C.BOLD}[1/3] HEDERA WALLET{C.R}")

    # Check if already configured
    existing_key = None
    existing_id = None
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("PRIVATE_KEY=") and "your_private_key" not in line:
                val = line.split("=", 1)[1].strip()
                if len(val) >= 64:
                    existing_key = val
            if line.startswith("HEDERA_ACCOUNT_ID=") and "123456" not in line:
                val = line.split("=", 1)[1].strip()
                if val.startswith("0.0."):
                    existing_id = val

    if existing_key and existing_id:
        print(f"  {C.OK}✓{C.R} Wallet already configured: {C.BOLD}{existing_id}{C.R}")
        reuse = safe_input(f"  Keep this wallet? {C.MUTED}(Y/n){C.R} ", default="y").lower()
        if reuse in ["y", "yes", ""]:
            return existing_id
        print(f"  {C.MUTED}Backing up current .env to .env.backup...{C.R}")
        shutil.copy2(ENV_FILE, PACMAN_DIR / ".env.backup")

    print(f"  {C.MUTED}How would you like to set up your wallet?{C.R}")
    print(f"  {C.ACCENT}[I]{C.R} Import existing Private Key")
    print(f"  {C.ACCENT}[G]{C.R} Generate fresh key pair")

    choice = safe_input(f"\n  Choice {C.MUTED}(i/g){C.R}: ", default="i").lower()

    raw_key = None
    hedera_id = None

    if choice == "g":
        # Generate fresh key
        try:
            from hiero_sdk_python.crypto.private_key import PrivateKey
            from web3 import Web3
        except ImportError:
            print(f"  {C.ERR}✗{C.R} Dependencies not available. Run from: ./launch.sh openclaw-setup")
            return None

        new_key = PrivateKey.generate_ecdsa()
        raw_key = new_key.to_string()
        temp_w3 = Web3()
        acc = temp_w3.eth.account.from_key(raw_key)
        eoa = acc.address

        print(f"\n  {C.OK}✅ Key Generated!{C.R}")
        print(f"  {C.WARN}⚠  BACKUP THIS KEY PRIVATELY — it cannot be recovered:{C.R}")
        print(f"  {C.BOLD}{raw_key}{C.R}")
        print(f"  {C.MUTED}EVM address: {eoa}{C.R}")
        print(f"\n  {C.MUTED}This key needs a Hedera account. Options:{C.R}")
        print(f"  {C.MUTED}  • Transfer HBAR to the EVM address above from HashPack/another wallet{C.R}")
        print(f"  {C.MUTED}  • Use portal.hedera.com to create an account with this key{C.R}")
        hedera_id = safe_input(f"\n  Enter your Account ID once created {C.MUTED}(0.0.xxx){C.R}: ")

    else:
        # Import existing key
        print(f"\n  {C.MUTED}Your key is entered securely (hidden) and stored only in .env locally.{C.R}")
        raw_key = getpass.getpass(f"  {C.ACCENT}Private Key:{C.R} ").strip().replace("0x", "")

        if len(raw_key) != 64:
            print(f"  {C.ERR}✗{C.R} Invalid key (need 64 hex chars). Got {len(raw_key)}.")
            return None

        # Try to auto-discover Hedera ID
        print(f"  {C.MUTED}Looking up Hedera ID via Mirror Node...{C.R}")
        try:
            from web3 import Web3
            import urllib.request
            temp_w3 = Web3()
            acc = temp_w3.eth.account.from_key(raw_key)
            eoa = acc.address
            evm_no_prefix = eoa[2:].lower()
            url = f"https://mainnet.mirrornode.hedera.com/api/v1/accounts/{evm_no_prefix}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                hedera_id = data.get("account")
                if hedera_id:
                    print(f"  {C.OK}✓{C.R} Found: {C.BOLD}{hedera_id}{C.R}")
        except Exception:
            pass

        if not hedera_id:
            hedera_id = safe_input(f"  {C.WARN}Enter Account ID manually{C.R} {C.MUTED}(0.0.xxx){C.R}: ")

    if not raw_key or not hedera_id or not hedera_id.startswith("0.0."):
        print(f"  {C.ERR}✗{C.R} Wallet setup incomplete. Please try again.")
        return None

    # Write to .env
    if not ENV_FILE.exists():
        shutil.copy2(ENV_TEMPLATE, ENV_FILE)
        print(f"  {C.MUTED}Created .env from template{C.R}")

    _env_set("PRIVATE_KEY", raw_key)
    _env_set("HEDERA_ACCOUNT_ID", hedera_id)
    _env_set("PACMAN_SIMULATE", "false")

    print(f"  {C.OK}✅ Wallet configured:{C.R} {C.BOLD}{hedera_id}{C.R}")
    return hedera_id


def _env_set(key, value):
    """Set a key=value in .env, updating if exists or appending."""
    if not ENV_FILE.exists():
        ENV_FILE.write_text(f"{key}={value}\n")
        return
    lines = ENV_FILE.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"# {key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n")


# ─── Step 2: OpenClaw Agent ──────────────────────────────────

def setup_openclaw_agent():
    """Configure the Pacman agent in openclaw.json."""
    print(f"\n  {C.BOLD}[2/3] OPENCLAW AGENT{C.R}")

    # Link the skill
    skill_link = OPENCLAW_DIR / "skills" / "pacman-hedera" / "SKILL.md"
    skill_target = PACMAN_DIR / "SKILL.md"
    if not skill_link.exists() and skill_target.exists():
        try:
            skill_link.symlink_to(os.path.relpath(skill_target, skill_link.parent))
            print(f"  {C.OK}✓{C.R} Skill linked: SKILL.md → {C.MUTED}{skill_target}{C.R}")
        except OSError:
            # Symlink failed (Windows?), copy instead
            shutil.copy2(skill_target, skill_link)
            print(f"  {C.OK}✓{C.R} Skill copied to workspace")
    elif skill_link.exists():
        print(f"  {C.OK}✓{C.R} Skill already linked")

    # Read existing config
    config = json.loads(OPENCLAW_CONFIG.read_text())
    workspace_path = str(OPENCLAW_DIR)

    # Check if pacman skill/workspace already configured
    existing_workspace = config.get("agents", {}).get("defaults", {}).get("workspace", "")
    if "pacman" in existing_workspace.lower():
        print(f"  {C.OK}✓{C.R} Already configured as default workspace")
        return True

    # Check for multi-agent setup (agents.list exists)
    agents_list = config.get("agents", {}).get("list", [])
    pacman_exists = any(a.get("id") == "pacman" for a in agents_list)

    if pacman_exists:
        print(f"  {C.OK}✓{C.R} Pacman agent already in agents list")
        return True

    print(f"  {C.MUTED}How should Pacman be added to your OpenClaw?{C.R}")
    print(f"  {C.ACCENT}[D]{C.R} Default agent {C.MUTED}(replace current workspace — Pacman becomes your main agent){C.R}")
    print(f"  {C.ACCENT}[S]{C.R} Second agent  {C.MUTED}(keep existing agent, add Pacman alongside it){C.R}")

    choice = safe_input(f"\n  Choice {C.MUTED}(d/s){C.R}: ", default="s").lower()

    if choice == "d":
        # Simple: just swap the workspace
        old_workspace = config.get("agents", {}).get("defaults", {}).get("workspace", "")
        config.setdefault("agents", {}).setdefault("defaults", {})["workspace"] = workspace_path
        print(f"  {C.OK}✓{C.R} Workspace set to: {C.MUTED}{workspace_path}{C.R}")
        if old_workspace:
            print(f"  {C.MUTED}Previous workspace: {old_workspace}{C.R}")
    else:
        # Multi-agent: promote to agents.list structure
        defaults = config.get("agents", {}).get("defaults", {})
        old_workspace = defaults.get("workspace", str(Path.home() / ".openclaw" / "workspace"))

        if not agents_list:
            # First time multi-agent — create list from existing defaults
            agents_list = [
                {
                    "id": "default",
                    "default": True,
                    "name": "Assistant",
                    "workspace": old_workspace
                }
            ]

        agents_list.append({
            "id": "pacman",
            "name": "Pacman",
            "workspace": workspace_path
        })

        config.setdefault("agents", {})["list"] = agents_list
        print(f"  {C.OK}✓{C.R} Added Pacman as second agent")
        print(f"  {C.MUTED}Default agent workspace: {old_workspace}{C.R}")
        print(f"  {C.MUTED}Pacman agent workspace: {workspace_path}{C.R}")

    # Write config
    _backup_and_write_config(config)
    return True


# ─── Step 3: Telegram Bot ────────────────────────────────────

def setup_telegram(is_multi_agent):
    """Configure Telegram routing for the Pacman agent."""
    print(f"\n  {C.BOLD}[3/3] TELEGRAM ROUTING{C.R}")

    config = json.loads(OPENCLAW_CONFIG.read_text())
    existing_telegram = config.get("channels", {}).get("telegram", {})

    if not is_multi_agent:
        # Single agent — existing telegram config routes to Pacman automatically
        if existing_telegram.get("enabled"):
            print(f"  {C.OK}✓{C.R} Telegram already configured — routes to your default agent (now Pacman)")
            return True
        # No telegram at all yet
        want_tg = safe_input(f"  Set up a Telegram bot? {C.MUTED}(y/N){C.R} ", default="n").lower()
        if want_tg not in ["y", "yes"]:
            print(f"  {C.MUTED}Skipped. You can set this up later in openclaw.json.{C.R}")
            return True

        token = safe_input(f"  {C.ACCENT}Paste Telegram bot token from @BotFather:{C.R} ")
        if not token or ":" not in token:
            print(f"  {C.ERR}✗{C.R} Invalid token format (expected: 123456:ABC...)")
            return False

        config.setdefault("channels", {})["telegram"] = {
            "enabled": True,
            "botToken": token,
            "dmPolicy": "pairing"
        }
        _backup_and_write_config(config)
        print(f"  {C.OK}✓{C.R} Telegram configured!")
        return True

    # Multi-agent — need a SECOND bot token for Pacman
    print(f"  {C.MUTED}You have two agents. To route messages to Pacman,{C.R}")
    print(f"  {C.MUTED}you need a dedicated Telegram bot for it.{C.R}")
    print()
    print(f"  {C.BOLD}Quick guide:{C.R}")
    print(f"  {C.MUTED}  1. Open Telegram → @BotFather → /newbot{C.R}")
    print(f"  {C.MUTED}  2. Name it something like 'Pacman Wallet'{C.R}")
    print(f"  {C.MUTED}  3. Copy the bot token and paste it below{C.R}")
    print()

    want_tg = safe_input(f"  Got a bot token ready? {C.MUTED}(y/N){C.R} ", default="n").lower()
    if want_tg not in ["y", "yes"]:
        print(f"  {C.MUTED}No problem. Add it later — see openclaw/SETUP.md for instructions.{C.R}")
        return True

    token = safe_input(f"  {C.ACCENT}Paste Pacman bot token:{C.R} ")
    if not token or ":" not in token:
        print(f"  {C.ERR}✗{C.R} Invalid token format")
        return False

    # Get existing allowFrom from the default account if available
    existing_allow = []
    telegram_conf = config.get("channels", {}).get("telegram", {})
    if "accounts" in telegram_conf:
        existing_allow = telegram_conf.get("accounts", {}).get("default", {}).get("allowFrom", [])
    else:
        existing_allow = telegram_conf.get("allowFrom", [])

    if existing_allow:
        your_tg_id = existing_allow[0]
        # Validate it's numeric
        if not str(your_tg_id).lstrip("-").isdigit():
            print(f"  {C.WARN}⚠{C.R} Existing config has non-numeric ID: {C.BOLD}{your_tg_id}{C.R}")
            your_tg_id = _resolve_telegram_username(token, str(your_tg_id))
        else:
            print(f"  {C.MUTED}Found your Telegram ID from existing config: {C.BOLD}{your_tg_id}{C.R}")
    else:
        print(f"  {C.WARN}IMPORTANT:{C.R} Telegram requires a {C.BOLD}numeric{C.R} user ID (not your @username).")
        print(f"  {C.MUTED}To find yours: message @userinfobot on Telegram.{C.R}")
        your_tg_id = safe_input(f"  {C.ACCENT}Telegram ID{C.R} {C.MUTED}(numeric, or Enter to skip){C.R}: ")
        # Catch @username input
        if your_tg_id and not your_tg_id.lstrip("-").isdigit():
            your_tg_id = _resolve_telegram_username(token, your_tg_id)

    # Add multi-account telegram config
    telegram_conf = config.get("channels", {}).get("telegram", {})

    # Restructure to multi-account format if needed
    if "accounts" not in telegram_conf:
        # Existing config is flat — migrate to multi-account
        existing_token = telegram_conf.get("botToken", "")
        existing_allow = telegram_conf.get("allowFrom", [])

        new_telegram = {
            "enabled": True,
            "configWrites": telegram_conf.get("configWrites", True),
            "accounts": {
                "default": {
                    "botToken": existing_token,
                    "dmPolicy": telegram_conf.get("dmPolicy", "pairing"),
                },
                "pacman": {
                    "botToken": token,
                    "dmPolicy": "allowlist" if your_tg_id else "pairing",
                }
            }
        }
        if existing_allow:
            new_telegram["accounts"]["default"]["allowFrom"] = existing_allow
        if your_tg_id:
            new_telegram["accounts"]["pacman"]["allowFrom"] = [your_tg_id]
    else:
        # Already multi-account — just add pacman
        new_telegram = telegram_conf
        new_telegram["accounts"]["pacman"] = {
            "botToken": token,
            "dmPolicy": "allowlist" if your_tg_id else "pairing",
        }
        if your_tg_id:
            new_telegram["accounts"]["pacman"]["allowFrom"] = [your_tg_id]

    config["channels"]["telegram"] = new_telegram

    # Add bindings: each bot token → its agent
    bindings = config.get("bindings", [])
    pacman_binding = {"agentId": "pacman", "match": {"channel": "telegram", "accountId": "pacman"}}
    default_binding = {"agentId": "default", "match": {"channel": "telegram", "accountId": "default"}}
    if not any(b.get("agentId") == "pacman" for b in bindings):
        bindings.append(pacman_binding)
    if not any(b.get("agentId") == "default" and b.get("match", {}).get("accountId") == "default" for b in bindings):
        bindings.append(default_binding)
    config["bindings"] = bindings

    _backup_and_write_config(config)
    print(f"  {C.OK}✓{C.R} Telegram bot added for Pacman agent!")
    if your_tg_id:
        print(f"  {C.MUTED}Restricted to user ID: {your_tg_id}{C.R}")

    # Bot command registration deprecated — setMyCommands overwrites
    # the platform's own command list. Natural language works better.

    return True


def _resolve_telegram_username(bot_token, username):
    """Try to resolve a @username to a numeric Telegram ID.

    Unfortunately the Telegram Bot API doesn't support username→ID lookup
    directly. We guide the user to @userinfobot instead.
    Returns the username as-is if resolution fails.
    """
    clean = username.lstrip("@")
    print(f"  {C.WARN}⚠  '{clean}' looks like a username, not a numeric ID.{C.R}")
    print(f"  {C.MUTED}Telegram requires numeric IDs for allowlists.{C.R}")
    print(f"  {C.MUTED}To find yours: message @userinfobot on Telegram — it replies with your numeric ID.{C.R}")
    print(f"  {C.MUTED}Or run: openclaw doctor --fix  (auto-resolves usernames){C.R}")
    numeric = safe_input(f"  {C.ACCENT}Numeric ID{C.R} {C.MUTED}(or Enter to keep '{clean}' for now){C.R}: ")
    return numeric if numeric and numeric.isdigit() else clean


def _register_bot_commands(bot_token):
    """Register Pacman slash commands with BotFather via Telegram Bot API."""
    import urllib.request

    commands = [
        {"command": "portfolio", "description": "View your portfolio and balances"},
        {"command": "swap", "description": "Swap tokens (e.g. 5 USDC for HBAR)"},
        {"command": "send", "description": "Send tokens to an address"},
        {"command": "price", "description": "Check live token prices"},
        {"command": "orders", "description": "View and manage limit orders"},
        {"command": "robot", "description": "Power Law rebalancer status"},
        {"command": "nfts", "description": "Browse your NFT collection"},
        {"command": "gas", "description": "Check HBAR gas reserve"},
        {"command": "health", "description": "System health check"},
        {"command": "backup", "description": "Backup your wallet keys"},
    ]

    try:
        url = f"https://api.telegram.org/bot{bot_token}/setMyCommands"
        payload = json.dumps({"commands": commands}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"  {C.OK}✓{C.R} Registered {len(commands)} slash commands with BotFather")
                print(f"  {C.MUTED}  Users see: /portfolio /swap /send /price /orders /robot ...{C.R}")
            else:
                print(f"  {C.WARN}⚠{C.R} Command registration failed: {result.get('description', 'unknown')}")
    except Exception as e:
        print(f"  {C.WARN}⚠{C.R} Could not register commands: {e}")
        print(f"  {C.MUTED}  You can set them manually via @BotFather → /setcommands{C.R}")


def _backup_and_write_config(config):
    """Backup and write openclaw.json safely."""
    backup = OPENCLAW_CONFIG.with_suffix(".json.backup")
    if OPENCLAW_CONFIG.exists():
        shutil.copy2(OPENCLAW_CONFIG, backup)
    OPENCLAW_CONFIG.write_text(json.dumps(config, indent=2) + "\n")


# ─── Finish ──────────────────────────────────────────────────

def finish(hedera_id, is_multi_agent):
    """Print summary and next steps."""
    print(f"\n  {C.OK}{C.BOLD}✨ SETUP COMPLETE!{C.R}")
    print(f"  {C.MUTED}{'═' * 52}{C.R}")

    if hedera_id:
        print(f"  {C.BOLD}Hedera Account:{C.R}  {hedera_id}")
    print(f"  {C.BOLD}Agent Workspace:{C.R} {OPENCLAW_DIR}")
    print(f"  {C.BOLD}Config Updated:{C.R}  {OPENCLAW_CONFIG}")

    # Auto-restart gateway
    print(f"\n  {C.MUTED}Restarting OpenClaw gateway...{C.R}")
    import subprocess
    try:
        subprocess.run(["openclaw", "gateway", "restart"], capture_output=True, timeout=15)
        print(f"  {C.OK}✓{C.R} Gateway restarted")
    except Exception:
        print(f"  {C.WARN}⚠{C.R} Could not restart gateway — run: {C.BOLD}openclaw gateway restart{C.R}")

    # Auto-fix doctor warnings (resolves @usernames → numeric IDs)
    try:
        subprocess.run(["openclaw", "doctor", "--fix"], capture_output=True, timeout=30)
    except Exception:
        pass

    print(f"\n  {C.ACCENT}Next steps:{C.R}")
    print(f"  {C.MUTED}  1.{C.R} Start Pacman daemons: {C.BOLD}./launch.sh daemon-start{C.R}")
    print(f"  {C.MUTED}  2.{C.R} Open Telegram and message your Pacman bot!")

    if is_multi_agent:
        print(f"\n  {C.MUTED}Agent routing:{C.R}")
        print(f"  {C.MUTED}  • Your existing bot → default agent{C.R}")
        print(f"  {C.MUTED}  • Pacman bot → Pacman agent (trading, portfolio, daemons){C.R}")
        print(f"  {C.MUTED}  Verify: openclaw agents list --bindings{C.R}")

    print(f"\n  {C.MUTED}Docs: openclaw/SETUP.md for advanced config (multi-channel, Discord, WhatsApp){C.R}")
    print()


# ─── Main ─────────────────────────────────────────────────────

def main():
    banner()

    if not check_prerequisites():
        sys.exit(1)

    # Step 1: Hedera wallet
    hedera_id = setup_hedera_wallet()

    # Step 2: OpenClaw agent workspace
    is_multi_agent = False
    print_choice_made = False

    config = json.loads(OPENCLAW_CONFIG.read_text())
    agents_list = config.get("agents", {}).get("list", [])

    setup_openclaw_agent()

    # Re-read to check what was chosen
    config = json.loads(OPENCLAW_CONFIG.read_text())
    agents_list = config.get("agents", {}).get("list", [])
    is_multi_agent = len(agents_list) > 1

    # Step 3: Telegram
    setup_telegram(is_multi_agent)

    # Done
    finish(hedera_id, is_multi_agent)


if __name__ == "__main__":
    main()
