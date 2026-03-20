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

> **The first fully autonomous AI wallet agent for Hedera.** Natural language wallet control, real mainnet trading on SaucerSwap V2, HCS signal marketplace, and plugin architecture for custom strategies. Conversational interface powered by OpenClaw or Telegram.

## Hackathon Submission

**Event**: Hedera Hackathon 2026
**Deadline**: March 24, 2026 11:59 PM ET

| Track | Prize | Submitted |
|-------|-------|-----------|
| AI & Agents | $18,500 | ✅ |
| OpenClaw Bounty | $4,000 | ✅ |

**Links**:
- **Demo Video**: [YouTube - TBD]
- **GitHub Repo**: [this repo](https://github.com/chris0x88/pacman)
- **Pitch Deck**: [`Pacman_Pitch_Deck.pdf`](Pacman_Pitch_Deck.pdf)
- **HCS Signal Topic**: `0.0.10371598`
- **AI Agent (Telegram)**: [@Chris0x88hederabot](https://t.me/Chris0x88hederabot)

---

## New in This Version

- **NFT photo display** via `nfts photo <token_id> <serial>` — SVG→PNG conversion with full metadata
- **Daily HCS heartbeat** — Power Law signal broadcast every day (trade or no trade)
- **OpenClaw agent improvements** — Enhanced SKILL.md with full NFT photo workflow
- **Wallet bot fast-lane** — `/nfts` command with inline photo buttons for quick trading decisions

---

## What Makes This Different

- **Built SaucerSwap V2 CLI from scratch** — The existing documentation was incomplete and EVM contract interactions were undocumented. Pacman is the first working multi-hop swap implementation available to the Hedera community.
- **First V2 multi-hop swap implementation** — Enables complex routing through liquidity pools with cost-aware pathfinding via Mirror Node.
- **Plugin architecture** — Anyone can add their own trading strategy, rebalancer, or market-making bot without modifying core code.
- **HCS signal marketplace** — First micropayment subscription service for trading signals on Hedera. Daily Power Law signals broadcast to HCS with community subscription model (~$10/year = 0.14 HBAR/day).

---

## Onboarding

Get started in 3 steps:

**Step 1: Clone & Initialize**
```bash
git clone https://github.com/chris0x88/pacman.git && cd pacman
./launch.sh setup                    # Guided wizard (testnet/mainnet selection)
```

**Step 2: Fund Your Wallet**
```bash
./launch.sh fund
# Testnet: Automatic faucet request
# Mainnet: MoonPay pre-filled link (100+ countries)
```

**Step 3: Connect Agent or Use Directly**
```bash
# Option A: OpenClaw plugin
Load SKILL.md as system instructions in OpenClaw agent

# Option B: Telegram bot
Chat with @Chris0x88hederabot

# Option C: Direct CLI
./launch.sh swap 10 HBAR for USDC
./launch.sh balance --json
./launch.sh nfts
```

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

## Hedera Integration Depth

| Service | Usage |
|---------|-------|
| **HTS (Token Service)** | Token associations, transfers, ERC20 approvals via HTS precompile |
| **HCS (Consensus Service)** | Daily Power Law signal broadcast, HCS-10 agent messaging |
| **EVM (Smart Contracts)** | SaucerSwap V2 router, multicall swaps, exact_in/exact_out |
| **Mirror Node** | Real-time balances, tx history, HCS message retrieval |
| **Accounts** | Multi-account (main + robot), ECDSA signing, nickname discovery |

## Why Pacman?

- **Fully Autonomous**: The AI agent has complete wallet control — swaps, sends, rebalancing. Safety comes from whitelists and confirmation, not restrictions.
- **Self-Custody**: Private keys stay on your machine. Ghost Tunnel encrypted key input. Never exposed in chat.
- **Real Trading**: Every swap executes on Hedera mainnet via SaucerSwap V2. No simulations. Real money, real transactions.
- **HCS Signal Marketplace**: Robot publishes daily Power Law signals to HCS. Anyone can subscribe. Creates a real micropayment economy ($10/year = ~0.14 HBAR/day).
- **Battle-Tested**: 11 documented anti-patterns from real agent sessions. Each bug became training data.
- **Power Law Rebalancer**: Autonomous BTC allocation daemon based on Bitcoin's 4-year cycle model (Heartbeat V3.2).

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
./launch.sh balance --json                # Token balances with USD values
./launch.sh swap 5 USDC for HBAR --yes    # Execute a swap (live, no simulation)
./launch.sh robot signal                  # Bitcoin Power Law model signal
./launch.sh nfts --json                   # View your NFTs
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
| Transfer whitelists | ✅ | `whitelist add 0.0.xxx` |
| Token transfers (whitelisted only) | ✅ | `send 10 HBAR to <whitelisted>` |
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
| SaucerSwap V2 (primary) | ✅ | `swap` |
| SaucerSwap V1 (legacy) | ⚠️ | `swap-v1` (explicit only) |
| Liquidity pool management | ✅ | `pool-deposit`, `pool-withdraw` |
| AWS KMS key provider | 🔧 PoC | `src/kms_provider.py` |

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
| **KMS Planned** | AWS KMS key provider PoC — keys can stay in HSM (FIPS 140-2 L3) |
| **Inventory** | `backup-keys --json` shows all keys with accounts (redacted) |

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
