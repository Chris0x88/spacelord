# Space Lord — Claude Code Governance

## What This Is
Space Lord is a Python CLI for Hedera Hashgraph trading (~10K LOC), designed for AI agent operation via OpenClaw. Entry point: `./launch.sh`. Core: `src/controller.py` → `src/router.py` → `src/executor.py`.

## Hard Rules

### Safety Limits
- Single source of truth: `data/governance.json`
- config.py loads from governance.json at runtime (hard-coded values are fallbacks only)
- Current limits: $100 max swap, $100 daily, 5% max slippage, 5 HBAR min gas reserve
- To change limits: edit governance.json ONLY. Never scatter across multiple files.

### Simulation
- **We NEVER simulate. EVER.** simulate_mode defaults to False.
- Simulations hide bugs and create dysfunction in real use.
- Tests override to simulate=true explicitly — that's the only acceptable use.

### Routing
- V2 is the primary and default protocol. V1 is legacy, separate file, explicit command only.
- Pool files: `data/pools_v2.json` (primary), `data/pools_v1.json` (legacy)
- **NEVER touch the blacklist** in router.py — it exists for good reasons (HBAR<->WBTC low liquidity)
- WHBAR (0.0.1456986) is internal routing only. Never expose to users.
- If routing data is stale, fix the refresh scripts — don't weaken the router.

### Accounts
- Main: 0.0.10289160 (all user operations)
- Robot: 0.0.10379302 (rebalancer daemon, currently unfunded)
- Old Robot: 0.0.10301803 (deprecated backup — NEVER delete)
- config.py discovers robot by nickname "Bitcoin Rebalancer Daemon" in accounts.json
- If robot has $0 balance: say "needs funding" — never suggest rebalancing

### Transfers
- **Wallet whitelists are the MOST important safety feature.**
- All transfers require whitelisted destination (enforced in `lib/transfers.py`)
- Token and pool whitelists are operational, not safety-critical
- EVM addresses are blocked — only Hedera IDs (0.0.xxx) for transfers
- NEVER fabricate account IDs in examples or tests — agents have sent real money to fake accounts

## Common Mistakes (Anti-Regression)
1. "Increase HBAR" means swap from USDC, NOT MoonPay
2. MoonPay only when total portfolio < $1 (see `cli/commands/wallet.py` `cmd_fund`)
3. V1 is NEVER a fallback for V2 routing failures
4. HBAR and WHBAR are unified in the router — `_id_to_sym()` maps both to "HBAR"
5. `send 100 USDC to 0.0.xxx` README example caused real money loss — never use placeholder accounts
6. Bare `input()` crashes OpenClaw — always use `_safe_input()`
7. Variables in if/else branches may be undefined — always set defaults first
8. `import json as _json` scoped in one function can't be used in another

## File Map
| File | Purpose |
|------|---------|
| `data/governance.json` | Safety limits, account roles, routing policy (SINGLE SOURCE OF TRUTH) |
| `data/pools_v2.json` | V2 routing pool registry |
| `data/pools_v1.json` | V1 legacy pool registry |
| `data/knowledge/` | Gitignored knowledge base (incidents, patterns, anti-patterns) |
| `src/config.py` | Loads from governance.json. Hard-coded values are fallbacks. |
| `SKILL.md` | OpenClaw agent brain — THE most important file for agent behavior |
| `.agent/agents.md` | Architecture guide for AI agents working in the repo |
| `FEEDBACK/` | Exported chat transcripts and handoff notes from OpenClaw sessions (gitignored). Look here for recent context when picking up mid‑session. |

## Telegram Architecture — Two Separate Bots

There are TWO completely separate Telegram bots. Different chats, different tokens, different code.

### OpenClaw Agent Bot (TELEGRAM_BOT_TOKEN) — THE MAIN PRODUCT
- Managed by OpenClaw. Agent reads `SKILL.md` (via symlink from `openclaw/skills/`), runs `./launch.sh` CLI commands.
- Agent fast-lane bridge: `cli/commands/telegram.py` → `lib/tg_router.py`
- Shared formatters: `lib/tg_format.py`
- Agent workspace: `openclaw/` (the agent can ONLY see files in this directory)
- **This is what we're optimizing for hackathon.**

### Wallet Bot (TELEGRAM_WALLET_BOT_TOKEN) — SEPARATE PLUGIN, NOT THE AGENT
- Standalone polling bot, runs via `./launch.sh telegram-start`
- Self-contained plugin: `src/plugins/tg_wallet_bot/`
- Imports shared logic from `lib/tg_router.py` and `lib/tg_format.py`
- Still works on its own Telegram channel. Not the agent.

### File Layout
```
lib/tg_router.py            ← Shared: command routing, swap/send flows
lib/tg_format.py            ← Shared: HTML card rendering, button layouts
cli/commands/telegram.py    ← Agent bridge: ./launch.sh tg <action>
src/plugins/tg_wallet_bot/  ← Wallet bot plugin (standalone, not agent)
openclaw/                   ← Agent workspace (ONLY thing the agent sees)
```

### The OpenClaw agent CANNOT see:
- `src/`, `lib/`, `cli/`, `data/`, `CLAUDE.md`, or any repo root files
- It only sees `openclaw/*.md` files + `SKILL.md` via symlink
- It interacts with the app exclusively through `./launch.sh` subprocesses

## Training Data Pipeline
We collect structured data for fine-tuning an LLM to drive and eventually BE the app.

### Auto-collected (every command):
- `logs/agent_interactions.jsonl` — Raw operational log: command, output, errors, timing, account
- `training_data/instruction_pairs.jsonl` — SFT format (system→user→assistant) for fine-tuning
- `training_data/live_executions.jsonl` — Detailed tx telemetry (gas, rates, tx hashes)

### Manually harvested (run periodically):
```bash
python3 scripts/harvest_knowledge.py --backfill --stats
```
This converts `data/knowledge/incidents/`, `antipatterns/`, `patterns/`, and `execution_records/` into:
- `training_data/preference_pairs.jsonl` — DPO format (chosen vs rejected behavior)
- `training_data/error_fix_pairs.jsonl` — Error diagnosis training data

### When to harvest:
- After adding new incidents to `data/knowledge/incidents/`
- After a session with significant debugging or new edge cases
- Before any model fine-tuning run

### All data is gitignored:
- `training_data/`, `logs/`, `FEEDBACK/`, `data/knowledge/`, `execution_records/`

## Before Any Code Change
1. Check if it affects safety limits → edit governance.json, not config.py hard-codes
2. Check if it affects agent behavior → update SKILL.md
3. Check if it's a new bug/lesson → add to `data/knowledge/incidents/`
4. Run `python3 tests/verify_all.py` after changes
5. Never push directly to `main` — use `master` for trial
