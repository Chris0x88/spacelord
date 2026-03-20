# Pacman Agent Architecture Guide

You operate Pacman by running CLI commands via `./launch.sh <command>`.
You do NOT modify code or config files. You are an operator, not a developer.

## How OpenClaw Drives Pacman

OpenClaw invokes Pacman as subprocess commands:
```
./launch.sh balance          → one-shot, returns output, exits
./launch.sh swap 5 USDC for HBAR  → executes trade, returns receipt
./launch.sh robot status --json   → returns structured JSON
```

Each invocation is a fresh process. No state carries between calls.
The app auto-detects non-interactive mode (pipes/agents) and auto-confirms.
No `--yes` or `--json` flags are required — they're accepted but optional.

## Architecture Map

```
cli/main.py          → Entry point. Command dispatch.
src/controller.py    → Facade. The only thing CLI talks to.
src/executor.py      → Web3 transaction engine. Broadcasts to Hedera.
src/router.py        → Pathfinding. Builds swap routes from pool graph.
src/translator.py    → NLP. "swap 5 USDC for HBAR" → structured intent.

lib/saucerswap.py    → SaucerSwap V2 DEX client.
lib/transfers.py     → Token transfer logic (whitelist enforced here).
lib/prices.py        → Price cache. Token USD prices.

data/governance.json → Safety limits (THE source of truth)
data/pools_v2.json   → V2 pool registry
data/tokens.json     → Token registry (symbol → ID, decimals)
data/settings.json   → User config (transfer whitelist)
```

## Plugin System (Background Daemons)

When `./launch.sh daemon-start` runs, these plugins activate:

| Plugin | Purpose | Status Check |
|--------|---------|-------------|
| **PowerLaw** | BTC rebalancer using Power Law model | `robot status --json` |
| **LimitOrders** | Price monitoring for limit buy/sell | `order list --json` |
| **HCS** | Hedera Consensus Service messaging | `hcs status` |

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
  → cli/main.py dispatches to trading handler
  → translator.py parses intent
  → controller.get_route("USDC", "HBAR", 5.0)
  → router builds graph, finds cheapest path
  → controller.swap() → executor broadcasts tx
  → receipt returned with amounts, gas, rate
```
