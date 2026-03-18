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

- **True Self-Custody**: Your private key never leaves your machine. No exchange holds your funds. XOR-obfuscated in memory.
- **AI-Native Design**: Every command returns structured JSON. Built for agents, not browsers. Natural language parsing ("swap 10 HBAR for USDC").
- **Agent-Safe Guardrails**: $1 max per swap, $10 daily limit, transfer whitelists, mandatory simulation. Your agent can't accidentally drain your wallet.
- **Fiat Onramp**: New users fund with credit card via MoonPay — one link, zero intermediary.
- **Power Law Rebalancer**: Autonomous BTC allocation daemon based on Bitcoin's 4-year cycle model.

---

## Quick Start

```bash
git clone https://github.com/chris0x88/pacman.git && cd pacman
cp .env.template .env                     # Add your private key
./launch.sh setup                         # Guided wallet configuration
./launch.sh balance --json                # See your portfolio
```

Zero-dependency install — `launch.sh` handles Python and all packages via [uv](https://docs.astral.sh/uv/).

### 30-Second Demo

```bash
./launch.sh status --json                 # Full account + balance snapshot
./launch.sh swap 0.5 HBAR for USDC --yes  # Execute a swap
./launch.sh nfts --json                   # View your NFTs
./launch.sh fund                          # Get MoonPay link to buy HBAR
./launch.sh robot signal                  # Check BTC allocation model
```

### Platform Support

- **macOS**: Apple Silicon (M1-M4) and Intel
- **Linux**: Any modern distribution
- **Windows**: Via WSL2

---

## Features

| Feature | Status | Command |
|---|---|---|
| Natural language swaps | Done | `swap 10 HBAR for USDC` |
| Exact output swaps | Done | `swap HBAR for 5 USDC` |
| Token transfers | Done | `send 100 USDC to 0.0.xxx` |
| NFT viewing + image download | Done | `nfts`, `nfts download` |
| Portfolio dashboard | Done | `status --json`, `balance` |
| Limit orders (background) | Done | `order buy HBAR at 0.08 size 100` |
| HBAR staking | Done | `stake` |
| Power Law rebalancer daemon | Done | `robot start` |
| Fiat onramp (MoonPay) | Done | `fund` |
| Testnet faucet | Done | `fund` (on testnet) |
| HCS P2P messaging | Done | `hcs` |
| System diagnostics | Done | `doctor` |
| SaucerSwap V1 legacy | Done | `swap-v1` |
| Liquidity pool management | Done | `pool-deposit`, `pool-withdraw` |

---

## OpenClaw Integration

Pacman is designed as a skill for [OpenClaw](https://openclaw.ai/) agents. Your agent drives Pacman via subprocess — no special SDK needed.

### Setup

1. Add Pacman as a skill in your OpenClaw workspace
2. Load [`SKILL.md`](SKILL.md) or [`docs/SKILLS_OPENCLAW_QUICKSTART.md`](docs/SKILLS_OPENCLAW_QUICKSTART.md) as the agent's system instructions
3. Agent calls `./launch.sh <command> --json --yes` via exec

### Agent Flags

```bash
--json    # Structured JSON output (no ANSI codes)
--yes     # Auto-confirm all prompts (no EOFError)
```

Non-interactive mode auto-detects when stdin is not a TTY — safe for pipes and subprocess.

### Example Agent Workflow

```
Agent: ./launch.sh status --json       → Gets account + balances
Agent: ./launch.sh swap 5 USDC for WBTC --yes --json  → Executes swap
Agent: ./launch.sh balance --json      → Verifies result
Agent: Tells user "Swapped 5 USDC for 0.00006 WBTC"
```

See [`docs/SKILLS_OPENCLAW_QUICKSTART.md`](docs/SKILLS_OPENCLAW_QUICKSTART.md) for the complete skill reference including decision trees, output schemas, and error recovery.

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
# Mainnet: generates a MoonPay buy link pre-filled with your account
# Testnet: dispenses HBAR from the Hedera testnet faucet
```

MoonPay is an official HBAR Foundation partner. No developer custody, no API key needed — just a direct link. Supports 100+ countries.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│              OpenClaw / AI Agent                  │
│         (calls ./launch.sh <cmd> --json)         │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│              CLI Dispatcher (cli/main.py)         │
│   Parses args → routes to command handlers       │
│   --json / --yes flag injection for agents       │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│           PacmanController (src/controller.py)    │
│   Facade: config + router + executor             │
└───┬──────────┬──────────┬────────────────────────┘
    │          │          │
┌───▼──┐  ┌───▼───┐  ┌───▼──────┐
│Config│  │Router │  │Executor  │
│ Keys │  │Paths  │  │Swaps,    │
│Safety│  │Graphs │  │Transfers │
└──────┘  └───────┘  └──────────┘
                         │
              ┌──────────▼──────────┐
              │  Hedera Hashgraph   │
              │  RPC: hashio.io     │
              │  Mirror Node        │
              │  SaucerSwap V2      │
              └─────────────────────┘
```

### Repository Structure

```
cli/              → Command dispatcher and handlers
  commands/       → Modular sub-commands (wallet, trading, nfts, robot, etc.)
src/              → Backend logic and Hedera action layer
  router.py       → Cost-aware hub routing with graph pathfinding
  executor.py     → Transaction broadcaster (swaps, approvals, transfers)
  controller.py   → SDK facade — the only thing CLI talks to
  config.py       → Secure configuration with XOR-obfuscated keys
  plugins/        → Extensible plugin system (Power Law bot, account manager)
lib/              → External API clients (SaucerSwap, prices, transfers)
data/             → Local config caches (pools, tokens, accounts, orders)
docs/             → Agent skills guides and architecture docs
tests/            → Unit and integration tests
launch.sh         → Zero-dependency launcher
SKILL.md          → OpenClaw skill descriptor
```

---

## Security Model

| Layer | Implementation |
|---|---|
| **Key Storage** | `.env` file, XOR-obfuscated in memory via `SecureString` class |
| **Key Isolation** | Robot account has independent ECDSA key (cannot access main wallet) |
| **Transaction Safety** | Mandatory `eth_call` simulation before every broadcast |
| **Safety Caps** | $1 max per swap, $10 daily limit, 5% max slippage (hard-coded) |
| **Transfer Gating** | Whitelist + known accounts registry. External sends blocked by default |
| **Agent Guardrails** | Fiduciary persona in SKILL.md, auto-confirm detection, JSON-only output |
| **Gas Protection** | Enforces >= 5 HBAR reserve to prevent stranding assets |

---

## Roadmap

### Done
- Natural language swaps, transfers, limit orders
- NFT viewing and image download
- Fiat onramp via MoonPay
- Power Law Heartbeat rebalancer daemon
- OpenClaw skill integration (SKILL.md)
- Zero-dependency install via uv
- Testnet faucet support

### Next
- MCP server for Claude Desktop / Cursor integration
- AWS KMS key management (keys never leave the HSM)
- Hedera Agent Kit native plugin
- HCS agent-to-agent P2P coordination
- Interactive Canvas UI for wallet management

### Vision
- P2P atomic swaps via HCS (no DEX fees beyond gas)
- Self-deploying smart contracts (escrow, rebalancing)
- x402 agent micropayments
- Sentx NFT marketplace integration

---

## Contributing

Pacman is open source under the [MIT License](LICENSE). Contributions welcome.

```bash
git clone https://github.com/chris0x88/pacman.git
cd pacman
cp .env.template .env    # Add your Hedera testnet key
./launch.sh doctor       # Verify system health
./launch.sh help         # See all commands
```

---

```
Pacman v1.0.0-beta | Hedera Apex Hackathon 2026
License: MIT | Author: Christopher David Imgraben
Disclaimer: Experimental software. Use disposable keys. Not financial advice.
```
