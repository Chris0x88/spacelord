"""
Agent Sync — Push codebase knowledge into the OpenClaw agent workspace
======================================================================
The OpenClaw agent can only see files in openclaw/. This command reads
the current state of the Pacman codebase and writes updated workspace
files that the agent picks up on its next turn.

Usage:
    ./launch.sh agent-sync           # Sync all workspace files
    ./launch.sh agent-sync --diff    # Show what would change without writing
"""

import json
import subprocess
import re
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent / "openclaw"
ROOT = Path(__file__).parent.parent.parent


def cmd_agent_sync(app, args):
    diff_only = "--diff" in args

    if not WORKSPACE.exists():
        print("  OpenClaw workspace not found at openclaw/")
        return

    updates = {
        "TOOLS.md": _build_tools(app),
        "AGENTS.md": _build_agents(),
        "BOOTSTRAP.md": _build_bootstrap(),
    }

    changed = 0
    for filename, new_content in updates.items():
        filepath = WORKSPACE / filename
        old_content = filepath.read_text() if filepath.exists() else ""

        if old_content.strip() == new_content.strip():
            print(f"  \u2705 {filename} — up to date")
            continue

        changed += 1
        if diff_only:
            print(f"  \U0001f504 {filename} — WOULD UPDATE")
            old_lines = old_content.strip().splitlines()
            new_lines = new_content.strip().splitlines()
            for i, (o, n) in enumerate(zip(old_lines, new_lines)):
                if o != n:
                    print(f"     Line {i+1}:")
                    print(f"       - {o[:80]}")
                    print(f"       + {n[:80]}")
                    break
            if len(new_lines) != len(old_lines):
                print(f"     Lines: {len(old_lines)} -> {len(new_lines)}")
        else:
            filepath.write_text(new_content)
            print(f"  \U0001f504 {filename} — updated")

    # Files we preserve
    for f in ["SOUL.md", "IDENTITY.md", "USER.md", "HEARTBEAT.md"]:
        if (WORKSPACE / f).exists():
            print(f"  \U0001f512 {f} — preserved (developer-owned)")

    print()
    if diff_only:
        print(f"  {changed} file(s) would change. Run without --diff to apply.")
    elif changed:
        print(f"  \u2705 {changed} file(s) synced. Agent will pick up changes next turn.")
    else:
        print("  \u2705 Agent workspace is already up to date.")


# ---------------------------------------------------------------------------
# Generators — each returns a complete markdown string
# ---------------------------------------------------------------------------

def _build_tools(app):
    main_id = getattr(app, "account_id", "unknown")
    robot_id = getattr(app.config, "robot_account_id", "unknown")
    commands_block = _get_help_output()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')

    return f"""# Pacman Tools — Environment-Specific Configuration

## Entry Point
All CLI commands: `./launch.sh <command>`
Working directory: The pacman repository root (where launch.sh lives)

## Accounts
- **Main**: `{main_id}` — user trading wallet
- **Robot**: `{robot_id}` — autonomous rebalancer (nickname: "Bitcoin Rebalancer Daemon")
- Switch with: `./launch.sh account switch <id_or_nickname>`

## Daemons
- Start: `./launch.sh daemon-start`
- Stop: `./launch.sh daemon-stop`
- Status: `./launch.sh daemon-status`
- Dashboard: http://127.0.0.1:8088

## HCS Topics
- Signal topic: `0.0.10371598` — Power Law signals broadcast here
- Feedback topic: check with `./launch.sh hcs status`
- Check: `./launch.sh hcs status`

## Cross-Agent Feedback (HCS)
Submit bugs, suggestions, and successes to a shared HCS topic that all Pacman agents can read.
```
./launch.sh hcs feedback submit bug "description of the issue"
./launch.sh hcs feedback submit suggestion "improvement idea"
./launch.sh hcs feedback submit success "what worked well"
./launch.sh hcs feedback submit warning "potential concern"
./launch.sh hcs feedback read                    # read recent feedback
./launch.sh hcs feedback-setup                   # create a new feedback topic
```
**Rules**: Only submit genuine feedback. Each message costs ~$0.0008.
Never include private keys, passwords, or sensitive data — HCS messages are permanent and public.
Reference transaction IDs or hashscan URLs when reporting bugs so others can investigate.

## Network
- Network: Hedera Mainnet
- DEX: SaucerSwap V2
- RPC: https://mainnet.hashio.io/v1

## Key Commands for Quick Reference
```
./launch.sh balance --all --json  # ALL accounts in one call (main + robot + totals)
./launch.sh balance --json        # Active account only
./launch.sh status --json         # Full portfolio + account info
./launch.sh robot status --json   # Rebalancer state + Power Law signal
./launch.sh doctor                # System health check
./launch.sh daemon-status         # Check running daemons
./launch.sh history               # Recent transactions
./launch.sh price bitcoin         # Live BTC price + model
./launch.sh agent-sync            # Sync this workspace with codebase changes
```

## Full Command List
{commands_block}

---
*Auto-generated by `./launch.sh agent-sync` on {ts}*
"""


def _build_agents():
    plugins_dir = ROOT / "src" / "plugins"
    plugin_info = {
        "power_law": ("PowerLaw", "BTC rebalancer using Power Law model", "`robot status --json`"),
        "orders": ("LimitOrders", "Price monitoring for limit buy/sell", "`order list --json`"),
        "hcs": ("HCS", "Hedera Consensus Service signals", "`hcs status`"),
        "hcs10": ("HCS-10", "Agent-to-agent messaging protocol", "`hcs10 status`"),
        "account_manager": ("AccountManager", "Multi-account management", "`account --json`"),
        "x402": ("x402", "HTTP 402 payment protocol", "`x402 status`"),
    }

    plugin_rows = ""
    if plugins_dir.exists():
        for p in sorted(plugins_dir.iterdir()):
            if p.is_dir() and not p.name.startswith(("__", "backup", "tg_")):
                info = plugin_info.get(p.name, (p.name, "Plugin", "---"))
                plugin_rows += f"| **{info[0]}** | {info[1]} | {info[2]} |\n"

    ts = datetime.now().strftime('%Y-%m-%d %H:%M')

    return f"""# Pacman Agent Architecture Guide

You operate Pacman by running CLI commands via `./launch.sh <command>`.
You do NOT modify code or config files. You are an operator, not a developer.

## How OpenClaw Drives Pacman

OpenClaw invokes Pacman as subprocess commands:
```
./launch.sh balance --all --json  -> returns multi-account balances
./launch.sh swap 5 USDC for HBAR  -> executes trade, returns receipt
./launch.sh robot status --json   -> returns structured JSON
./launch.sh agent-sync            -> syncs this workspace with codebase updates
```

Each invocation is a fresh process. No state carries between calls.
The app auto-detects non-interactive mode (pipes/agents) and auto-confirms.
No `--yes` or `--json` flags are required — they're accepted but optional.

## Architecture Map

```
cli/main.py          -> Entry point. Command dispatch.
src/controller.py    -> Facade. The only thing CLI talks to.
src/executor.py      -> Web3 transaction engine. Broadcasts to Hedera.
src/router.py        -> Pathfinding. Builds swap routes from pool graph.
src/translator.py    -> NLP. "swap 5 USDC for HBAR" -> structured intent.

lib/saucerswap.py    -> SaucerSwap V2 DEX client.
lib/transfers.py     -> Token transfer logic (whitelist enforced here).
lib/prices.py        -> Price cache. Token USD prices.
lib/tg_router.py     -> Telegram button-flow routing (shared).
lib/tg_format.py     -> Telegram HTML card rendering (shared).

data/governance.json -> Safety limits (THE source of truth)
data/pools_v2.json   -> V2 pool registry
data/tokens.json     -> Token registry (symbol -> ID, decimals)
data/settings.json   -> User config (transfer whitelist)
```

## Plugin System (Background Daemons)

When `./launch.sh daemon-start` runs, these plugins activate:

| Plugin | Purpose | Status Check |
|--------|---------|-------------|
{plugin_rows}
Plugins run as threads inside the daemon process. Each reports:
- `running`: boolean
- `last_heartbeat`: ISO timestamp
- `errors`: count

## Critical Hedera Rules

### HBAR vs WHBAR
- **HBAR** (0.0.0) = native gas token. Users interact with this.
- **WHBAR** (0.0.1456986) = internal routing wrapper. Users NEVER see this.
- The router maps both to "HBAR" for pathfinding. Wrapping is automatic.
- **Never mention WHBAR to users. Never suggest wrapping/unwrapping.**

### Token Associations
- Hedera accounts must "associate" with tokens before receiving them
- Holding ANY balance proves association — never suggest re-associating
- The `setup` wizard auto-associates base tokens

### Transfer Safety
- All outbound transfers check `data/settings.json` whitelist
- Non-whitelisted destinations are **blocked** (not warned — blocked)
- EVM addresses (0x...) are blocked entirely — only Hedera IDs (0.0.xxx)
- Own accounts in `accounts.json` are auto-whitelisted

## Data Flow: Swap Command

```
User: "swap 5 USDC for HBAR"
  -> cli/main.py dispatches to trading handler
  -> translator.py parses intent
  -> controller.get_route("USDC", "HBAR", 5.0)
  -> router builds graph, finds cheapest path
  -> controller.swap() -> executor broadcasts tx
  -> receipt returned with amounts, gas, rate
```

## Staying Up to Date

If the developer adds new commands or changes behavior, run:
```
./launch.sh agent-sync
```
This regenerates TOOLS.md and AGENTS.md from the live codebase.
You will pick up the changes on your next turn.

---
*Auto-generated by `./launch.sh agent-sync` on {ts}*
"""


def _build_bootstrap():
    gov_path = ROOT / "data" / "governance.json"
    limits = {}
    try:
        with open(gov_path) as f:
            gov = json.load(f)
        limits = gov.get("safety_limits", {})
    except Exception:
        pass

    max_swap = limits.get("max_swap_usd", 100)
    max_daily = limits.get("max_daily_usd", 100)
    max_slippage = limits.get("max_slippage_pct", 5)
    min_gas = limits.get("min_hbar_reserve", 5)

    # Preserve developer-written sections below the limits
    bootstrap_path = WORKSPACE / "BOOTSTRAP.md"
    extra = ""
    if bootstrap_path.exists():
        content = bootstrap_path.read_text()
        marker = "## Channel Format"
        if marker in content:
            extra = "\n" + content[content.index(marker):]

    result = f"""# Pacman Bootstrap — Safety Limits & Startup

## Safety Limits (from governance.json)

| Limit | Value | Purpose |
|-------|-------|---------|
| Max single swap | ${max_swap} | Prevent fat-finger trades |
| Max daily volume | ${max_daily} | Rate-limit total exposure |
| Max slippage | {max_slippage}% | Reject trades with excessive price impact |
| Min HBAR reserve | {min_gas} HBAR | Always keep gas for future transactions |

These are enforced by the CLI. You cannot override them. If a user asks to exceed a limit, explain why the limit exists and suggest they talk to the developer.
"""

    if extra:
        result += extra
    else:
        result += """
## Channel Format

When responding in Telegram, output clean text. No markdown code fences.
Use short paragraphs. Emoji sparingly. Numbers with proper formatting.

---
*Auto-generated by `./launch.sh agent-sync`*
"""
    return result


def _get_help_output():
    """Capture CLI help output as plain text (ANSI stripped)."""
    try:
        result = subprocess.run(
            ["./launch.sh", "help", "all"],
            capture_output=True, text=True, timeout=10,
            cwd=str(ROOT),
        )
        output = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
        lines = output.strip().splitlines()
        clean = [l for l in lines if not l.startswith("User Input:")]
        # Filter out Telegram fast-lane commands (deprecated for agent use)
        filtered = []
        skip_section = False
        for l in clean:
            if "TELEGRAM" in l and ("fast-lane" in l.lower() or "agent" in l.lower()):
                skip_section = True
                continue
            if skip_section:
                # Stop skipping when we hit the next section header or blank line after commands
                if l.strip() and not l.startswith("  "):
                    skip_section = False
                    filtered.append(l)
                elif l.strip().startswith("tg "):
                    continue  # skip tg commands
                else:
                    if not l.strip():
                        skip_section = False
                    continue
            else:
                filtered.append(l)
        return "\n".join(filtered).strip()
    except Exception as e:
        return f"(Could not capture help output: {e})"
