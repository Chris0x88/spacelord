# 🚀 Space Lord

**Open-source Hedera DeFi toolkit built for an [OpenClaw](https://openclaw.ai) AI agent to drive — via CLI tool use, not MCP. Fully built. Ready to go.**

[![Hedera Apex Hackathon 2026](https://img.shields.io/badge/Hedera_Apex_Hackathon-2026-black.svg)](https://hedera.com)
[![Hedera Mainnet](https://img.shields.io/badge/Network-Hedera_Mainnet-blue.svg)](https://hedera.com)
[![SaucerSwap V2](https://img.shields.io/badge/DEX-SaucerSwap_V2-purple.svg)](https://saucerswap.finance)
[![OpenClaw](https://img.shields.io/badge/Agent-OpenClaw-orange.svg)](https://openclaw.ai)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![MIT License](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](LICENSE)

> **Hedera Hello Future Apex Hackathon 2026** — AI & Agents Track | OpenClaw Bounty

📄 [Whitepaper (PDF)](docs/WHITEPAPER.pdf) · 🎬 [Demo Video](https://www.youtube.com/watch?v=OElX33KViGo)

---

## 💡 What is Space Lord?

Open-source software you download and run on **your own machine**. It collapses the exchange, the wallet, and the portfolio tracker into one local tool — so you or your AI agent can interact with Hedera DeFi directly, with your own keys, through natural language.

> No browser wallet. No exchange login. No click fatigue. No multi-app juggling.
> **One local tool. 30+ commands. Direct to smart contracts.**

Built from **Project Pacman** — an experiment in "eating the middleware" between users and the Hedera blockchain. Phase 1 of a larger vision: collapsing DeFi into the Hashgraph itself, or local edge compute. Still a bit clunky, but it works — **with real money, on Hedera mainnet**.

---

## ⚡ Quick Start

### Option A: From your OpenClaw Agent

We're heading to a **multi-agent universe**. The Space Lord skill is a support tool that provides agentic control of the application (installed in Option B). Your primary [OpenClaw](https://openclaw.ai) agent can clone this repo, install the app, and spin up a **dedicated trading agent** with the Space Lord skill package.

1. Ask your agent to `git clone` this repo and install the application locally
2. Have it spin up a dedicated trading agent using the Space Lord skill
3. **Set up Telegram** — create your own bot to chat directly with your new agent (OpenClaw also supports Discord and other platforms)

### Option B: Manual Install (Mac/Linux)

> ⚠️ **Best to run locally** — don't pass crypto keys through AI LLM chat APIs (unsafe — keys could end up in model training data). New key protection features coming soon. For now, treat as live network "experimental."

```bash
git clone https://github.com/Chris0x88/pacman.git
cd pacman
./launch.sh init        # Guided wizard: key setup, token associations
./launch.sh help        # See all 30+ available commands
./launch.sh balance     # Check your portfolio
./launch.sh swap 10 USDC for HBAR --yes   # Execute a real swap
```

`./launch.sh` is a zero-dependency bash launcher — installs `uv`, validates `.env`, dispatches to the CLI engine. Keys entered locally through the wizard — they never travel through any API.

---

## 🏗️ Architecture

```mermaid
graph TD
    %% Styling %%
    classDef interface fill:#1e1e2e,stroke:#cba6f7,stroke-width:2px,color:#fff,rx:8,ry:8
    classDef ai fill:#ff2052,stroke:#fff,stroke-width:2px,color:#fff,rx:8,ry:8
    classDef engine fill:#313244,stroke:#a6e3a1,stroke-width:2px,color:#fff,rx:8,ry:8
    classDef ext fill:#11111b,stroke:#f9e2af,stroke-width:2px,color:#fff,rx:8,ry:8
    classDef hedera fill:#000000,stroke:#00a8e8,stroke-width:3px,color:#fff,rx:8,ry:8

    User((You)):::interface -->|Natural Language| Agent[OpenClaw AI Agent]:::ai
    User -->|Terminal| CLI[CLI Direct]:::interface

    Agent -->|subprocess| Engine[Space Lord Engine]:::engine
    CLI --> Engine

    Engine -->|controller| Router[SaucerSwap V2 Router]:::ext
    Engine -->|HTS| Tokens[Token Transfers]:::ext
    Engine -->|HCS| Signals[On-Chain Signals]:::ext
    Engine -->|SDK| Accounts[Account Management]:::ext

    Router -->|JSON-RPC| Hedera[Hedera Mainnet]:::hedera
    Tokens --> Hedera
    Signals --> Hedera
    Accounts --> Hedera
```

### Components

| Component | Role |
|-----------|------|
| 🔧 **CLI Engine** | 30+ deterministic commands. Controller → router → executor pipeline. |
| 🔀 **SaucerSwap V2 Router** | Custom, open-source multi-hop path finding. Direct smart contract calls via JSON-RPC. |
| 🛡️ **Governance Engine** | Per-swap max, daily max, slippage cap, gas reserve. User-configurable, agent-immutable. |
| 🤖 **OpenClaw Agent** | Reads SKILL.md, interprets natural language, executes CLI via subprocesses. Light key protection — full sandbox planned. |
| 📊 **Power Law Rebalancer** | Autonomous daemon for local portfolio rebalancing. Proof of concept while awaiting Hedera Schedule Service. |
| 📡 **HCS Publisher** | (1) Crowd-sourced bug/telemetry logging for self-healing. (2) Trading signal broadcast for potential monetization. |
| 🧠 **Training Pipeline** | Records CLI commands + responses as instruction pairs for future LLM fine-tuning. |

### Interfaces

| Interface | Speed | Best for |
|-----------|-------|----------|
| 🤖 **OpenClaw Agent** (Telegram) | ~2-5s | Drives the CLI for you — no commands to remember, no multi-step waits |
| 💻 **Terminal CLI** | Instant | Scripting, automation, direct control |
| 📊 **Dashboard** | Real-time | Visual monitoring (to be replaced by OpenClaw's "canvas" feature) |

---

## 🔗 Hedera Integration

Direct to Hedera — no middleware:

| Service | Usage |
|---------|-------|
| **SaucerSwap V2** | Direct router/quoter calls via JSON-RPC. Multi-hop path finding. |
| **HTS** | Token associations, transfers, approvals via HTS Precompile. |
| **HCS** | Signal broadcast, bug telemetry, HCS-10 agent-to-agent messaging. |
| **Mirror Node** | Real-time balances, transaction history, key lookups. |
| **Accounts** | Multi-account management, creation via Hiero SDK, ECDSA signing. |
| **Staking** | HBAR staking/unstaking to consensus nodes. |

---

## 🎯 Features at a Glance

- **🔄 Token Swaps** — Natural language ("swap 10 USDC for HBAR") → SaucerSwap V2 smart contracts
- **💰 Portfolio Management** — Real-time balances, USD values, transaction history, NFT viewer
- **📤 Self-Custody Transfers** — Whitelisted destinations only. EVM addresses blocked.
- **🤖 Autonomous Rebalancing** — Power Law daemon auto-rebalances BTC allocation on thresholds
- **📡 On-Chain Signals** — Daily HCS heartbeat. Structured JSON. Anyone can subscribe.
- **🛡️ Governance & Safety** — One config file. Per-swap limits, slippage caps, gas reserves. Agent can't modify.
- **🧠 Training Data** — Every command generates fine-tuning data for future AI models

---

## 🔒 Security Model

> **The golden rule: the AI agent never sees your keys.**

- 🔐 Keys stored locally in `.env`, encrypted in memory, decrypted only at signing, then immediately cleared
- 🧠 Agent predicts *intent*. Deterministic CLI handles the *cryptography*.
- 📋 Wallet whitelists enforce all transfers — no exceptions
- 🛡️ Governance is read-only to the agent
- ⚡ We never simulate — every transaction is real

---

## 📚 Hackathon Resources

| Resource | Link |
|----------|------|
| 🎥 Demo Video | [YouTube link in submission] |
| 📑 Pitch Deck | [`pitch_deck/`](pitch_deck/) |
| 📄 Technical Whitepaper | [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) |
| 🔌 ClawHub Skill | [clawhub.ai/Chris0x88/pacman-hedera](https://clawhub.ai/Chris0x88/pacman-hedera) |
| 📡 HCS Signal Topic | `0.0.10371598` |

---

## License

MIT

---

*Built with real money. Real transactions. Real learnings.* 🚀
