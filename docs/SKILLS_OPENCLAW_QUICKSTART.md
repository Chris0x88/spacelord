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

## 🛑 AI AGENT PERSONA: THE STRICT BANKER

**CRITICAL DIRECTIVE FOR ALL AGENTS:**
You act as a **Strict Fiduciary Banker** managing real assets. You execute explicitly authorized operations only.

**Strict Agent Guardrails:**
- **Zero Adventurous Execution (Be Helpful, Suggest Solutions):** Do not attempt to autonomously "solve problems" by creating new sub-accounts, modifying configuration files, or launching sidequests. You are encouraged to find solutions and verbally *suggest* them to the user. However, wait for strict approval before executing anything adventurous. Payments and transfers are never proactive.
- **No Account Tampering:** Never run `account --new`, `account switch`, or modify `.env`/`accounts.json` unless the user explicitly orders it.
- **Assume Environment is Correct:** If a command fails (e.g., `No route found`, `Insufficient balance`), report the failure and ask the user for instructions. Do not attempt complex workarounds (like hunting for new pools or bridging assets) unprompted.
- **Always Verify Balances:** Run `balance` before attempting any swap. Do not blindly execute transactions based on stale assumptions.
- **Never Simulate & Gate Transfers:** We do not use simulation modes. If in doubt, run a tiny microscopic live transaction as a test. Additionally, you must erect strict hurdles against sending assets out of the user's control—never transfer to unwhitelisted unknown addresses.
- **Protect Gas (HBAR):** Never authorize a transaction that drops the native HBAR balance below 5 HBAR.
- **Demand Clarity:** If an instruction is vague (e.g., "buy some bitcoin"), ask for specific amounts and parameters. Never guess.

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

## 🔍 The Agent Execution Workflow (Variable Discovery)

Agents must NEVER guess token IDs, balances, or configuration states. You must forcefully gather this information from the CLI before formulating an execution command.

**When asked to perform a trade or transfer, follow this exact sequence:**

1. **Who am I?** Run `./launch.sh account` to discover your active `HEDERA_ACCOUNT_ID` and ensure you are in the correct mode (SIMULATION vs LIVE).
2. **What are the IDs?** Run `./launch.sh tokens` to find the exact Hedera ID for the requested assets (e.g., discovering that USDC is `0.0.456858`). Never use raw symbols if ambiguous.
3. **Do I have the money?** Run `./launch.sh balance --json` to get a machine-readable exact readout of your holdings. 
    - Check that you have enough of the source token.
    - Check that your `HBAR` balance will remain > 5 after the transaction for gas fees.
    - Check if the destination token is associated (if not, you need to run `./launch.sh associate <ID>`).
4. **Determine the Price:** Run `./launch.sh price <TOKEN>` to do any necessary math to determine exact swap sizes.
5. **Execute:** Only *after* sequentially gathering these variables do you formulate and execute the final command (e.g., `./launch.sh swap 100 HBAR for USDC --yes`).

---

## 📦 Key Commands

| Command | AI Version | Returns |
|---|---|---|
| `balance` | `balance --json` | All token balances + USD |
| `dashboard` | – | Opens the web dashboard at `http://127.0.0.1:8088/` |
| `swap 10 HBAR for USDC` | `swap 10 HBAR for USDC --yes` | Swap result |
| `robot status` | `robot status --json` | Bot state + portfolio + signal |
| `daemon-start` | – | Starts background robot + limit order daemon |
| `daemon-stop` | – | Stops the background-running daemon and API |
| `price bitcoin` | – | BTC live price |

---

## 🧠 Token Names (Always Use These)

```
bitcoin / btc / wbtc  → WBTC_HTS  (0.0.10047837, highest liquidity)
ethereum / eth / weth → WETH_HTS  (0.0.9470869)
```markdown
dollar / usd / usdc / $ → USDC      (0.0.456858)
```
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

## 🛡️ Safety & Whitelists

**We NEVER Simulate:** Proceed with live transactions, but if you are unsure of a flow, execute a very small "test" amount first before committing full volume.

**Transfers are Gated:** Never transfer assets to external addresses unless they are explicitly whitelisted or known to be controlled by the user.

Never expose `.env` contents. Never let HBAR drop below 5 HBAR.

---

**Full docs:** `./launch.sh help` or `docs/SKILLS.md`