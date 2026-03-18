# PACMAN

```text
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚╚╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```

[![Network: Hedera Mainnet](https://img.shields.io/badge/Network-Hedera_Mainnet-blue.svg)](https://hedera.com)
[![DEX: SaucerSwap V2](https://img.shields.io/badge/DEX-SaucerSwap_V2-purple.svg)](https://saucerswap.finance)
[![License: MIT](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)

> **AI-native self-custody middleware for Hedera Hashgraph.** Your OpenClaw agent becomes a Hedera power user — swaps, transfers, NFTs, portfolio management, and autonomous rebalancing. No exchange, no browser, no intermediary.

**Hedera Apex Hackathon 2026** | Built for OpenClaw agents | Compatible with Hedera Agent Kit

---

## Why Pacman?

- **True Self-Custody**: Private keys never leave your machine. XOR-obfuscated in memory. Auto-backed up to ~/Downloads on account creation.
- **AI-Native Design**: Every command returns structured JSON. Natural language parsing ("swap 10 HBAR for USDC"). Agents drive it like a tool, not a website.
- **Agent-Safe Guardrails**: $1 max per swap, $10 daily limit, transfer whitelists, mandatory simulation. Your agent can't accidentally drain your wallet.
- **Fiat Onramp**: New users fund with credit card via MoonPay — one link, zero intermediary, HBAR arrives direct.
- **Power Law Rebalancer**: Autonomous BTC allocation daemon based on Bitcoin's 4-year cycle model (Heartbeat V3.2).
- **Single-Instance Daemon**: One command starts everything — robot, API, dashboard. PID-locked, idempotent, no orphaned processes.

---

## Quick Start

```bash
git clone https://github.com/chris0x88/pacman.git && cd pacman
cp .env.template .env                     # Add your private key
./launch.sh setup                         # Guided wallet configuration
./launch.sh daemon-start                  # Start background services
./launch.sh dashboard                     # Open web dashboard
```

Zero-dependency install — `launch.sh` handles Python and all packages via [uv](https://docs.astral.sh/uv/).

### 30-Second Demo

```bash
./launch.sh doctor                        # System health check (6 categories)
./launch.sh status --json                 # Full account + balance snapshot
./launch.sh swap 0.5 HBAR for USDC --yes  # Execute a swap
./launch.sh nfts --json                   # View your NFTs
./launch.sh fund                          # Buy HBAR with credit card (MoonPay)
./launch.sh robot signal                  # Bitcoin Power Law model signal
./launch.sh backup-keys --file            # Auto-save keys to ~/Downloads + open email draft
```

### Platform Support

- **macOS**: Apple Silicon (M1-M4) and Intel
- **Linux**: Any modern distribution
- **Windows**: Via WSL2

---

## Features

| Feature | Status | Command |
|---|---|---|
| Natural language swaps | ✅ | `swap 10 HBAR for USDC` |
| Exact output swaps | ✅ | `swap HBAR for 5 USDC` |
| Token transfers | ✅ | `send 100 USDC to 0.0.xxx` |
| NFT viewing + image download | ✅ | `nfts`, `nfts download` |
| Portfolio snapshot | ✅ | `status --json` |
| Key backup (~/Downloads + email) | ✅ | `backup-keys --file` |
| Fiat onramp (MoonPay) | ✅ | `fund` |
| Testnet faucet | ✅ | `fund` (on testnet) |
| Power Law rebalancer daemon | ✅ | `robot start` |
| Limit orders | ✅ | `order buy HBAR at 0.08 size 100` |
| HBAR staking | ✅ | `stake` |
| HCS P2P messaging | ✅ | `hcs` |
| System diagnostics (6 checks) | ✅ | `doctor` |
| Single-instance daemon | ✅ | `daemon-start` / `daemon-stop` |
| SaucerSwap V1 + V2 | ✅ | `swap` / `swap-v1` |
| Liquidity pool management | ✅ | `pool-deposit`, `pool-withdraw` |
| AWS KMS key provider | ✅ PoC | `src/kms_provider.py` |

---

## OpenClaw Integration

Pacman is designed as a conversational skill for [OpenClaw](https://openclaw.ai/) agents. The agent acts as a **Personal Hedera Operations Assistant** — it greets users, shows formatted portfolios, suggests actions, and handles all CLI interaction behind the scenes.

### How It Works

1. Load [`SKILL.md`](SKILL.md) as the agent's system instructions in OpenClaw
2. User talks naturally: *"what's my balance?"*, *"swap 5 bucks for bitcoin"*, *"show my NFTs"*
3. Agent silently runs `./launch.sh <command> --json --yes` and presents results conversationally
4. User never sees CLI commands — they interact through natural language

### What the Agent Does on Startup

When a user says "hi" or "open wallet", the agent automatically:
1. Runs `doctor` — checks system health, daemons, gas, connectivity
2. Runs `status --json` — gets full portfolio
3. Runs `robot status --json` — checks rebalancer
4. Presents a formatted greeting with portfolio table and action menu

### Agent Flags

```bash
--json    # Structured JSON output (no ANSI codes)
--yes     # Auto-confirm all prompts (no EOFError in subprocess)
```

### Proactive Intelligence

The agent doesn't just respond — it looks for issues to flag:
- ⚠️ Low HBAR (gas reserve below 5)
- 🤖 Robot daemon stopped
- 📈 Bitcoin model signal changes (deep value / overvalued)
- 🔐 No key backup detected
- 🆕 New user with empty wallet

See [`SKILL.md`](SKILL.md) for the full conversation design and persona specification.

---

## Hedera Agent Kit Compatibility

Pacman can be used as a plugin for the [Hedera Agent Kit](https://github.com/hashgraph/hedera-agent-kit). Each Pacman command maps to a HAK tool:

| HAK Tool | Pacman Command |
|---|---|
| `pacman_balance` | `./launch.sh balance --json` |
| `pacman_swap` | `./launch.sh swap ... --yes --json` |
| `pacman_transfer` | `./launch.sh send ... --yes --json` |
| `pacman_nfts` | `./launch.sh nfts --json` |
| `pacman_robot_status` | `./launch.sh robot status --json` |

---

## Fiat Onramp

New users can purchase HBAR with a credit/debit card:

```bash
./launch.sh fund
# Mainnet: MoonPay buy link pre-filled with your account
# Testnet: Hedera testnet faucet (free HBAR)
```

MoonPay is an official HBAR Foundation partner. No custody, no API key, 100+ countries.

---

## Key Security

| Feature | How |
|---|---|
| **Storage** | `.env` file, XOR-obfuscated in memory via `SecureString` |
| **Auto-Backup** | New keys saved to `~/Downloads/` + `backups/` automatically |
| **Email Draft** | macOS: Mail.app opens with backup file attached. User hits Send. |
| **Never Lost** | `_update_env()` archives old keys before overwriting (timestamped) |
| **Agent-Safe** | Private keys NEVER appear in `--json` output or agent API traffic |
| **Key Isolation** | Robot account has independent ECDSA key (separate EVM address) |
| **KMS Ready** | AWS KMS key provider PoC — keys can stay in HSM (FIPS 140-2 L3) |
| **Inventory** | `backup-keys --json` shows all keys with accounts (redacted) |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│              OpenClaw / AI Agent                  │
│   Reads SKILL.md → drives CLI conversationally   │
└──────────────────┬───────────────────────────────┘
                   │  ./launch.sh <cmd> --json --yes
┌──────────────────▼───────────────────────────────┐
│            Single-Instance Launcher               │
│   PID lock → daemon management → one-shot cmds   │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│              CLI Dispatcher (cli/main.py)         │
│   30+ commands → --json/--yes flag injection     │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│           PacmanController (src/controller.py)    │
│   Facade: config + router + executor + plugins   │
└───┬──────────┬──────────┬──────────┬─────────────┘
    │          │          │          │
┌───▼──┐  ┌───▼───┐  ┌───▼──────┐  ┌▼──────────┐
│Config│  │Router │  │Executor  │  │Plugins    │
│ Keys │  │Paths  │  │Swaps,    │  │PowerLaw,  │
│Safety│  │Graphs │  │Transfers │  │AcctMgr,   │
│ KMS  │  │Prices │  │NFTs      │  │HCS, ...   │
└──────┘  └───────┘  └──────────┘  └───────────┘
                         │
              ┌──────────▼──────────┐
              │  Hedera Hashgraph   │
              │  JSON-RPC (Hashio)  │
              │  Mirror Node API    │
              │  SaucerSwap V2 DEX  │
              └─────────────────────┘
```

### Repository Structure

```
launch.sh         → Single-instance launcher (daemon + one-shot + interactive)
SKILL.md          → OpenClaw agent persona and conversation design
cli/
  main.py         → Command dispatcher (30+ commands)
  commands/       → Modular handlers (wallet, trading, nfts, robot, doctor)
src/
  controller.py   → SDK facade — the only thing CLI talks to
  executor.py     → Transaction broadcaster (swaps, approvals, transfers)
  router.py       → Cost-aware graph pathfinding with hub routing
  config.py       → Secure config with XOR-obfuscated SecureString
  kms_provider.py → AWS KMS signing PoC (HSM-backed keys)
  plugins/        → Extensible plugin system
    power_law/    → Bitcoin Heartbeat rebalancer (V3.2 model)
    account_manager.py → Multi-account with independent ECDSA keys
lib/              → External API clients (SaucerSwap, prices, transfers)
data/             → Local caches (pools, tokens, accounts, price history)
dashboard/        → Web dashboard (served on :8088 by daemon)
docs/             → Agent skill guides and architecture docs
```

---

## Daemon Management

```bash
./launch.sh daemon-start     # Start (idempotent — won't create duplicates)
./launch.sh daemon-stop      # Graceful shutdown
./launch.sh daemon-restart   # Stop + start
./launch.sh daemon-status    # Check PID + API health
./launch.sh dashboard        # Opens browser (starts daemon if needed)
```

The daemon runs: Power Law rebalancer, limit order engine, API server (:8088), web dashboard, HCS listener, backup service.

---

## Roadmap

### Shipped
- Natural language swaps, transfers, limit orders, staking
- NFT viewing and image download
- Fiat onramp (MoonPay) + testnet faucet
- Power Law Heartbeat V3.2 rebalancer daemon
- OpenClaw conversational skill (SKILL.md)
- Single-instance daemon with PID lock
- Auto key backup (~/Downloads + email draft)
- AWS KMS key provider architecture
- Hedera ecosystem price tracking (HBAR, SAUCE)
- System diagnostics (doctor — 6 categories)
- Zero-dependency install via uv

### Next
- React + Tailwind dashboard rebuild
- MCP server for Claude Desktop / Cursor
- Hedera Agent Kit native plugin package
- HCS agent-to-agent data trading
- Canvas interactive UI for wallet management
- Ecosystem plugins (Bonzo, Neuron, Sentx)

### Vision
- P2P atomic swaps via HCS (no DEX fees beyond gas)
- Agent micropayments via x402
- On-chain supply chain data tracking
- Self-deploying smart contracts (escrow, rebalancing)
- Multi-agent coordination and data marketplace

---

## Contributing

Open source under the [MIT License](LICENSE). Contributions welcome.

```bash
git clone https://github.com/chris0x88/pacman.git
cd pacman
cp .env.template .env    # Add your Hedera testnet key
./launch.sh doctor       # Verify system health
./launch.sh help         # See all commands
```

---

```
Pacman v2.3 | Hedera Apex Hackathon 2026
License: MIT | Author: Christopher David Imgraben
Disclaimer: Experimental software. Use disposable keys. Not a regulated service.
```
