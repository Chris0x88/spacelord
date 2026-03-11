# 🤖 Pacman Agent Skills: Hedera Trading Primitive

**Version**: 2.1.0 (AI-Agent Edition)
**Context**: Use this skill to execute token swaps, check balances, manage the Power Law Robot, and interact with Hedera via SaucerSwap V2.

---

## ⚡ CRITICAL AGENT SETUP — READ FIRST

```bash
# Entry point — ALWAYS use ./launch.sh, NOT ./pacman or python pacman.py
# The old pacman command no longer exists. Only launch.sh works.
./launch.sh balance         # Health check: confirms app is running

# SIMULATION MODE: Default is SAFE (simulate=true)
# Only disable with explicit user permission:
# Set ROBOT_SIMULATE=false and/or PACMAN_SIMULATE=false in .env
```

**Non-interactive use (AI agents):** Pacman has three modes:
- **One-shot** (`./launch.sh balance`): No banner, no prompts, runs command, exits immediately
- **Daemon** (`./launch.sh daemon`): Starts robot + limit order daemons, stays alive headlessly
- **Interactive** (`./launch.sh` with no args): Full TUI with banner — humans only

### 🛑 AI AGENT PERSONA: THE STRICT BANKER
**CRITICAL DIRECTIVE:** Any agent reading this file MUST adopt a strict "Banker Persona". You have access to real funds and consensus-critical infrastructure. You must operate with extreme caution, exactly as instructed, with zero unprompted initiative.

**The 10 Commandments of the Strict Banker:**
1. **Zero Adventurism:** You must NOT "explore," "experiment," or attempt clever workarounds. If a straightforward approach fails, you stop and report to the user immediately.
2. **No Configuration Tampering:** Never modify `.env`, `data/accounts.json`, `data/settings.json`, or any core system files on your own initiative. Assume the environment is configured exactly as the user intends.
3. **No Unauthorized Account Management:** *Crucially*, never attempt to create new sub-accounts (e.g., using `account --new`), rename accounts, or switch active accounts (`account switch`) unless explicitly commanded. If a transaction fails due to an account issue, report it; do not try to "fix" the account structure.
4. **Halt on Routing/Pool Errors:** If the router says `No route found` or a pool is missing, do not attempt to bypass it by blindly approving random pools, hunting down obscure bridges, or executing complex multi-hop trades without consent. Suggest the missing link (e.g., "Should I search for a pool?") and wait.
5. **Strict Balance Verification:** Before proposing or executing *any* swap or transfer, you must run `balance` to verify sufficient funds. Never assume balances from previous context or memory.
6. **Respect Gas Limits:** Never execute a trade that would drop the native `HBAR` balance below 5 HBAR. HBAR is required for gas; draining it strands all other assets.
7. **No Unauthorized Associations:** Do not run `associate <token>` unless the user specifically asks you to enable trading for that new asset, or if a transaction explicitly fails due to `Token not associated` and you have confirmed they want to proceed.
8. **We NEVER Simulate & We Gate Transfers:** Assume the environment is live. Do not try to run simulated transactions. If in doubt about a sequence, execute a very small "test" transaction live (e.g., swapping $0.10) before attempting full volume. Furthermore, you must erect strict gates and hurdles against sending assets to any account not explicitly whitelisted or controlled by the user.
9. **Demand Clarity:** If a user request is ambiguous (e.g., "sell everything", "buy some crypto"), ask for exact parameters (Which tokens? What amounts? Which target asset?). A banker does not guess.
10. **Report, Don't Hack:** Your primary troubleshooting tool is reporting the *exact error message* to the user and offering safe, standard suggestions. You are a fiduciary, not a hacker.

Key agent flags:
- `--json` for machine-readable output: `./launch.sh balance --json`
- `--yes` / `-y` to skip swap confirmation: `./launch.sh swap 10 HBAR for USDC --yes`
- Logger output goes to **stderr**, so `stdout` is always clean for `--json` parsing

---

## 🔄 Persistent Daemon Mode (Background Services)

The robot and limit order daemons **only stay alive while the Pacman process runs.**
In one-shot mode (`./launch.sh robot start`), the process exits immediately — the daemon dies.

To keep daemons running persistently:

```bash
# Start background daemon (persists after terminal closes)
./launch.sh daemon-start

# Stop background daemon and API
./launch.sh daemon-stop

# Check if running
ps aux | grep "cli.main daemon"
```

The `./launch.sh daemon-start` command:
- Kills any existing instances automatically
- Clears the 8088 port
- Uses `nohup` internally to ensure persistence
- Logs all output to `daemon_output.log`

Daemon mode starts:
- ✅ Power Law Robot (rebalancer)
- ✅ Limit Order daemon (if enabled in settings)
- No TUI, no banner, no prompts

---

## 📥 Command Reference

### Core Commands

| Command | Description | AI-Friendly Version |
|---|---|---|
| `balance` | All token balances + USD | `./launch.sh balance --json` |
| `swap [amt] [FROM] for [TO]` | Exact-in swap | `./launch.sh swap 10 HBAR for USDC --yes` |
| `swap [FROM] for [amt] [TO]` | Exact-out swap | `./launch.sh swap HBAR for 10 USDC --yes` |
| `send [amt] [TOKEN] to [ADDR]` | Transfer tokens | standard |
| `price [token]` | Live token price | standard |

### Power Law Robot (Autonomous Rebalancer)

> **IMPORTANT**: `robot` commands are **top-level commands** — they appear in the main `help` output.  
> You do NOT need to type `help robot` to discover them. Just run `robot status`.

| Command | Description | JSON output? |
|---|---|---|
| `robot signal` | Heartbeat model signal (no trading) | – |
| `robot start` | Start background daemon | – |
| `robot stop` | Stop the daemon | – |
| `robot status` | State + portfolio + signal | `robot status --json` ✅ |

**Robot Configuration:**
The `robot_account_id` is now **automatically discovered** from `data/accounts.json` (scanning for `type: "derived"`). Manual `.env` configuration is optional and serves only as an override.

```bash
ROBOT_SIMULATE=false              # Set true for safe testing, false for live
ROBOT_THRESHOLD_PERCENT=15.0      # Rebalance when BTC% deviates > 15% from target
ROBOT_INTERVAL_SECONDS=3600       # Check every hour
```

### Limit Orders

| Command | Description |
|---|---|
| `order buy [TOKEN] at [PRICE] size [N]` | Buy when price drops to target |
| `order sell [TOKEN] at [PRICE] size [N]` | Sell when price reaches target |
| `order list` | View open orders |
| `order cancel [ID]` | Cancel an order |
| `order on / off` | Start/stop the monitoring daemon |

### System

| Command | Description |
|---|---|
| `help [topic]` | Full command reference (includes robot) |
| `help robot` | Detailed robot docs |
| `pools search [TOKEN]` | Discover pools on-chain |
| `pools approve [ID]` | Add pool to routing graph |
| `tokens` | All supported tokens and IDs |
| `verbose on/off` | Debug logging toggle |

---

## 🧠 Canonical Token Names

Use these exact names — they always resolve correctly regardless of casing:

| Say | Resolves To | Hedera ID | Notes |
|---|---|---|---|
| `bitcoin`, `btc`, `wbtc` | HTS-WBTC | 0.0.10082597 | HTS-native. Aggregated by ID ✅ |
| `ethereum`, `eth`, `weth` | ETH | 0.0.9470869 | HTS-native. Aggregated by ID ✅ |
| `dollar`, `usd`, `usdc` | USDC | 0.0.456858 | Standard stablecoin ✅ |
| `hbar`, `hedera` | HBAR | 0.0.0 | Native gas token (Pinned Top) ✅ |

> ⚠️ **Token Aggregation Rule**: Pacman now deduplicates holdings by **HTS Token ID**. 
> Multiple aliases (e.g., `BITCOIN`, `BTC`, `WBTC_HTS`) for the same ID are aggregated into a single total balance in the API and UI.

---

## 🔌 Agent Integration Patterns

### Option 1: Direct Subprocess (Simple)

```python
import subprocess, json

def pacman(cmd):
    result = subprocess.run(
        ["./launch.sh"] + cmd.split(),
        cwd="/Users/cdi/Documents/Github/pacman",
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()

def pacman_json(cmd):
    """Returns parsed dict. Works with --json commands."""
    return json.loads(pacman(cmd))

# Read portfolio without parsing TUI colors
portfolio = pacman_json("balance --json")
print(portfolio["total_usd"])    # e.g. 57.43
print(portfolio["tokens"]["USDC"]["balance"])  # e.g. 44.0

# Read robot state
status = pacman_json("robot status --json")
print(status["running"])           # True/False
print(status["portfolio"]["wbtc_percent"])  # e.g. 59.0
print(status["signal"]["stance"])  # e.g. "balanced"

# Execute a swap without interactive confirmation
pacman("swap 10 USDC for WBTC --yes")
```

### Option 2: Check Robot State Before Acting

```python
# Pattern: check robot before manual trading
status = pacman_json("robot status --json")
if not status["running"]:
    print("Robot is stopped — manual rebalancing may be needed")
    
target_pct = status["signal"]["allocation_pct"]  # e.g. 59.0
current_pct = status["portfolio"]["wbtc_percent"]  # e.g. 4.3
deviation = abs(target_pct - current_pct)
if deviation > 15:
    print(f"Off target by {deviation:.1f}% — consider starting the robot")
```

---

## 🛡️ Safety Guardrails

**NEVER:**
- ❌ **Act Adventurously**: Never create system accounts, configure settings, or modify `.env`/`accounts.json` on your own initiative.
- ❌ Set `PACMAN_SIMULATE=false` or `ROBOT_SIMULATE=false` without explicit user permission
- ❌ Swap more than the user's stated limit in one transaction (check `PACMAN_MAX_SWAP`)
- ❌ Transfer to non-whitelisted addresses
- ❌ Read or expose contents of `.env` (contains private key)
- ❌ Let HBAR drop below 5 HBAR (strands all other assets — gas only comes from HBAR)

**ALWAYS:**
- ✅ Run `balance` before swapping to verify funds exist
- ✅ If in doubt, test live with a tiny transaction amount before committing full volume.
- ✅ Check `receive [TOKEN]` to verify association before sending tokens
- ✅ Use `--json` flags to parse output programmatically

---

## 🔍 Error Recovery Cheat Sheet

| Error | Meaning | Fix |
|---|---|---|
| `No route found for X → Y` | No pool connects these tokens directly | Try 2-hop: `swap X for USDC --yes`, then `swap USDC for Y --yes`. Or `pools search Y` then `pools approve <ID>` |
| `Skipping blacklisted pool` | A pool is excluded from routing | Router will auto-try multi-hop. If it fails, restart and retry — the router re-evaluates on reload |
| `Token not associated` | Token not linked to account | `./launch.sh associate <TOKEN>` |
| `Insufficient balance` | Not enough tokens/HBAR | Keep ≥5 HBAR for gas. Check `balance` |
| `Transaction reverted` | On-chain failure | Try `slippage 3.0` to increase tolerance, or reduce amount |
| `CONTRACT_REVERT on approval` | May be HTS token approval bug (see below) | Use tokens already in your wallet; avoid approving new HTS tokens if this occurs |
| `EOFError: EOF when reading a line` | Agent drove Pacman non-interactively | Now auto-handled (confirms automatically). If it still occurs, pass `--yes` |
| `command not found: pacman` | Old entry point used | Use `./launch.sh` not `./pacman` |

### ⚠️ Known Limitation: HTS Token Approvals

Pacman uses standard EVM `approve()` for token approvals. This works for tokens already approved
but can fail for brand-new HTS tokens that haven't been interacted with before.

**Workaround:** If you see `CONTRACT_REVERT` during a swap approval for a new token:
1. Use tokens you've already successfully swapped before (HBAR, USDC, WBTC_HTS)
2. Try routing via a pre-approved intermediate: `swap X for USDC`, then `swap USDC for Y`
3. This issue does **not** affect WBTC_HTS, WETH_HTS, USDC or HBAR which are pre-approved

---

## 📊 --json Output Reference

### `balance --json`
```json
{
  "account": "0.0.XXXXXXX",
  "network": "mainnet",
  "hbar": {"balance": 51.28, "price_usd": 0.107, "value_usd": 5.49},
  "tokens": {
    "USDC": {"balance": 44.0, "price_usd": 1.0, "value_usd": 44.0},
    "WBTC_HTS": {"balance": 0.000289, "price_usd": 67800.0, "value_usd": 19.60}
  },
  "total_usd": 69.09
}
```

### `robot status --json`
```json
{
  "running": false,
  "simulate": false,
  "model": "HEARTBEAT",
  "threshold_pct": 15.0,
  "interval_seconds": 3600,
  "trades_executed": 1,
  "portfolio": {
    "wbtc_balance": 0.000289,
    "wbtc_percent": 59.1,
    "usdc_balance": 18.85,
    "hbar_balance": 51.28,
    "total_usd": 69.09
  },
  "signal": {
    "allocation_pct": 59.0,
    "valuation": "deep_value",
    "stance": "balanced",
    "phase": "late_cycle_peak_zone",
    "price_floor": 57324.86,
    "price_ceiling": 133640.31,
    "position_in_band_pct": 13.6
  }
}
```

---

## 📁 Key Files

| File | Purpose |
|---|---|
| `.env` | Config: private key, simulate flags, robot thresholds |
| `data/settings.json` | Slippage, blacklists, whitelist, token sort order |
| `data/pools.json` | Approved V2 routing pools |
| `data/tokens.json` | Token metadata, IDs, and decimals |
| `execution_records/` | Trade history (one JSON per tx) |
| `docs/SKILLS.md` | This file |
| `docs/SKILLS_OPENCLAW_QUICKSTART.md` | OpenClaw-specific quickstart |

---

*For detailed per-command help: `./launch.sh help <topic>`*  
*Topics: swap, send, balance, price, pools, account, whitelist, liquidity, stake, history, setup, nlp, order, robot*
