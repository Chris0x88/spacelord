# Pacman Quick Start for OpenClaw

**App:** Pacman v2 (SaucerSwap V2 CLI for Hedera)  
**Entry point:** `./launch.sh <command>` ← **ONLY this works. `./pacman` is deprecated.**  
**Mode:** Subprocess (one-shot) or interactive TTY  

---

## ⚡ 30-Second Setup

```bash
# 1. Clone (first time only)
git clone https://github.com/chris0x88/pacman.git ~/Documents/Github/pacman
cd ~/Documents/Github/pacman

# 2. Run (auto-installs Python via uv — no venv, no pip needed)
./launch.sh balance
# → First run may take 30s to install dependencies

# 3. If wallet not configured:
./launch.sh setup   # Follow the wizard
```

---

## 🤖 Agent-Specific Flags (NEW in v2.1)

These flags make Pacman safe to drive from a subprocess without TTY:

```bash
# --json: Machine-readable output (no ANSI color codes)
./launch.sh balance --json
./launch.sh robot status --json

# --yes / -y: Skip confirmation prompts (for swaps)
./launch.sh swap 10 USDC for WBTC --yes

# EOFError handling: stdin not a TTY → auto-confirms (same as --yes)
# Relevant for: echo "swap 10 HBAR for USDC" | ./launch.sh
```

---

## 📦 Key Commands

| Command | AI Version | Returns |
|---|---|---|
| `balance` | `balance --json` | All token balances + USD |
| `swap 10 HBAR for USDC` | `swap 10 HBAR for USDC --yes` | Swap result |
| `robot status` | `robot status --json` | Bot state + portfolio + signal |
| `robot start` | – | Starts background daemon |
| `price bitcoin` | – | BTC live price |

---

## 🧠 Token Names (Always Use These)

```
bitcoin / btc / wbtc  → WBTC_HTS  (0.0.10047837, highest liquidity)
ethereum / eth / weth → WETH_HTS  (0.0.9470869)
dollar / usd / usdc   → USDC      (0.0.456858)
hbar / hedera         → HBAR      (native)
```

> ⚠️ There are two WBTC tokens on Hedera. **Always use the symbol**  — Pacman picks the right pool automatically. Using the wrong token ID directly (`0.0.1055483`) will cause swap failures.

---

## 💻 Python Integration

```python
import subprocess, json

CWD = "/Users/cdi/Documents/Github/pacman"

def pacman(cmd):
    r = subprocess.run(["./launch.sh"] + cmd.split(), cwd=CWD,
                       capture_output=True, text=True, timeout=120)
    return r.stdout.strip()

def pacman_json(cmd):
    return json.loads(pacman(cmd))

# --- Examples ---
# Get parseable portfolio
portfolio = pacman_json("balance --json")
usdc = portfolio["tokens"]["USDC"]["balance"]  # e.g. 44.0
total = portfolio["total_usd"]                 # e.g. 69.09

# Get robot state
status = pacman_json("robot status --json")
running     = status["running"]                # True/False
wbtc_pct    = status["portfolio"]["wbtc_percent"]  # e.g. 59.1
target_pct  = status["signal"]["allocation_pct"]   # e.g. 59.0
deviation   = abs(wbtc_pct - target_pct)

# Execute swap (skips confirmation)
pacman("swap 10 USDC for WBTC --yes")
```

---

## 🚨 Error Cheat Sheet

| Error | Fix |
|---|---|
| `No route found` | Try 2-hop: `swap X for USDC --yes` then `swap USDC for Y --yes`. Or `pools search Y` → `pools approve <ID>` |
| `Token not associated` | `./launch.sh associate <TOKEN>` |
| `Insufficient balance` | Keep ≥ 5 HBAR for gas |
| `Transaction reverted` | `./launch.sh slippage 3.0` then retry |
| `CONTRACT_REVERT on approval` | HTS token approval bug — route via USDC instead |
| `command not found: pacman` | Use `./launch.sh` not `./pacman` |

---

## 🛡️ Safety

```
PACMAN_SIMULATE=true      ← Keep this unless user explicitly says "go live"
ROBOT_SIMULATE=true       ← Same — robot won't trade without false
```

Never expose `.env` contents. Never let HBAR drop below 5 HBAR.

---

**Full docs:** `./launch.sh help` or `docs/SKILLS.md`