# ᗧ PACMAN

```text
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚╚╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```

[![Network: Hedera](https://img.shields.io/badge/Network-Hedera-blue.svg)](https://hedera.com)
[![DEX: SaucerSwap](https://img.shields.io/badge/DEX-SaucerSwap-purple.svg)](https://saucerswap.finance)
[![License: MIT](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](https://opensource.org/licenses/MIT)

> **Your AI agent doesn't need an exchange, a browser, or a login. It needs Pacman.**

---

## The Vision

Pacman is **self-custody middleware** — a locally-run, AI-native operating system for the Hedera Hashgraph. It collapses exchanges, portfolio trackers, and DeFi frontends into a single process your AI agent operates autonomously.

No intermediaries. No browser extensions. No counterparty risk. Just your agent, your keys, and the hashgraph.

**Three reasons this matters:**

1. **True Self-Custody**: Your private key never leaves your machine. No exchange holds your funds.
2. **AI-Native**: Every command is a deterministic function. No web DOMs, no CAPTCHAs, no session cookies.
3. **Network-Direct**: Talks directly to Hedera smart contracts via RPC. Shortest possible path from intent to on-chain execution.

---

## 🚀 One-Line Install

```bash
git clone https://github.com/chris0x88/pacman.git && cd pacman && ./launch.sh
```

That's it. The `launch.sh` script auto-installs `uv` (if needed), resolves Python + all dependencies, and launches Pacman. No pip, no venv, no manual setup.

### 30-Second Demo

```bash
./launch.sh dashboard                      # Open the web dashboard (http://127.0.0.1:8088/)
./launch.sh balance                        # Show your portfolio
./launch.sh swap 10 HBAR for USDC          # Execute a swap
./launch.sh send 5 USDC to 0.0.1234       # Transfer tokens
./launch.sh price bitcoin                   # Check prices (canonical names work)
```

### 💻 Compatibility & Support

Pacman is cross-platform and handles its own environment:

- **macOS**: Built and optimized for Apple Silicon (M1/M2/M3/M4) and Intel Macs.
- **Linux**: Works on any modern distribution (Ubuntu, Fedora, etc.).
- **Windows**: Seamless support via **WSL2** (Windows Subsystem for Linux).

The `launch.sh` script is the standard entry point. It ensures you have the correct Python version and dependencies without modifying your system.

### First-Time Setup

```bash
./launch.sh setup    # Guided wizard: paste your Hedera private key
```

> ⚠️ **SECURITY WARNING**: Store only disposable keys. Create a fresh account on [HashPack](https://www.hashpack.app/) with 5-10 HBAR. **Assume any key you give this app is compromised.** We recommend keeping `PACMAN_SIMULATE=true` in your `.env` while testing — this simulates swaps without broadcasting transactions.

---

## 🌪️ What It Does

| Command | What It Does |
|---|---|
| `balance` | Show all token holdings with USD values |
| `swap 10 HBAR for USDC` | Trade tokens (natural language) |
| `swap HBAR for 5 USDC` | Exact output: receive precisely 5 USDC |
| `send 100 USDC to 0.0.xxx` | Transfer tokens to any Hedera account |
| `price bitcoin` | Check live prices (canonical names: bitcoin, ethereum, dollar) |
| `order buy HBAR at 0.08 size 100` | Set a limit order (background daemon) |
| `stake` | Stake HBAR to a consensus node |
| `robot signal` | Show BTC heartbeat model allocation signal |
| `robot start` | Start the Power Law rebalancer daemon |

**Advanced** (pool management, liquidity, sub-accounts): Run `help` inside the shell.

---

## 🤖 AI Agent Integration

Pacman is built as an **agentic trading primitive**. Every command outputs deterministic, structured text designed for LLM parsing.

### Supported Integration Methods

| Method | Best For | Setup |
|---|---|---|
| **Subprocess (CLI)** | Any LLM, universal | `./launch.sh swap 10 HBAR for USDC` |
| **OpenClaw** | Purpose-built agent tools | Load `docs/SKILLS.md` as system prompt |
| **MCP Server** | Claude, Cursor, etc. | *(Coming soon)* |
| **Local LLM (Ollama)** | Offline, privacy-focused | Any model via subprocess |
| **Embedded Model** | Zero-dependency agent | Qwen 3.5 0.6B driver *(future)* |

### Quick Start for Agents

1. Load [`docs/SKILLS.md`](docs/SKILLS.md) as your system prompt
2. Execute commands via subprocess: `./launch.sh <command>`
3. Parse stdout for results — every execution saves detailed JSON to `execution_records/`

### Canonical Token Names

Agents can use human-friendly names that always resolve:

| Say | Gets |
|---|---|
| `bitcoin`, `btc` | WBTC_HTS (SaucerSwap native, HashPack visible) |
| `ethereum`, `eth` | WETH_HTS (SaucerSwap native, HashPack visible) |
| `dollar`, `usd` | USDC (native stablecoin) |
| `hbar`, `hedera` | HBAR (native network token) |

---

## 🔮 Roadmap

### Now
- ✅ Natural language swaps, transfers, limit orders
- ✅ Never-fail routing with canonical token defaults
- ✅ Zero-dependency install via `uv`
- ✅ AI agent skills file for OpenClaw
- ✅ Power Law Heartbeat rebalancer robot

### Next
- 🔄 MCP server for Claude/Cursor integration
- 🔄 AWS KMS key management (keys never leave the HSM)
- 🔄 HCS agent-to-agent P2P communication  
- 🔄 Hedera Schedule Service for autonomous portfolio rebalancing

### Vision
- 🚧 True P2P atomic swaps via HCS (no DEX, no fees beyond gas)
- 🚧 Self-deploying smart contracts (escrow, rebalancing)
- 🚧 x402 agent micropayments
- 🚧 Self-installing agents (OpenClaw downloads and runs Pacman autonomously)

---

## 📂 Repository Structure

```
cli/              → Interactive shell and command handlers
  commands/       → Modular sub-commands (swap, balance, orders, etc.)
src/              → Backend logic and Hedera action layer
  router.py       → Pathfinding engine with cost-aware hub routing
  executor.py     → Transaction broadcaster (swaps, approvals, transfers)
  controller.py   → SDK facade — the only thing CLI talks to
lib/              → External API clients (SaucerSwap, prices)
data/             → Local config caches (pools, tokens, orders)
docs/             → Agent guides and skills files
launch.sh         → Zero-dependency launcher
```

---

## 🛡️ Security Model

| Layer | Current | Planned |
|---|---|---|
| Key Storage | `.env` file (XOR-obfuscated in memory) | AWS KMS (key never exposed) |
| Transaction Safety | Mandatory `eth_call` simulation before broadcast | + Rate limiting, contract whitelist |
| Agent Guardrails | Safety caps in config, transfer whitelist | + IBM/EqtyLab policy engine |
| Network | Direct RPC to Hedera (no intermediary) | Same |

---

```
Release: v1.0.0-beta | Hedera Apex Hackathon 2026
License: MIT
Disclaimer: Experimental software. Do not use life savings. Use disposable keys only.
```
