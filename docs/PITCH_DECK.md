# SPACE LORD

### Your Tokens. Your Machine. Your Agent.

*A specialist OpenClaw agent runs your wallet, exchange, and every other engagement with Hedera — all from software YOU own and control locally. No clicks, no logins, no switching between apps. Customise your plugins. Take a backseat and let your OpenClaw drive!*

**Hedera Hello Future Apex Hackathon 2026 — AI & Agents Track**

github.com/Chris0x88/pacman | [Demo Video](https://www.youtube.com/watch?v=OElX33KViGo)

<div style="page-break-after: always;"></div>

## Team & Project Introduction

**Builder:** Chris — solo developer, full-stack engineer, crypto infrastructure enthusiast.

**Project:** Space Lord (codename: Pacman) — an open-source Hedera DeFi toolkit built for AI agents to drive via CLI tool use.

**Status:** Live on Hedera mainnet with real tokens. ~10,000 lines of Python. 30+ CLI commands. Fully functional today.

**Tagline:** *Take a backseat and let your OpenClaw drive.*

---

## What We Built

Space Lord is the **connective tissue** between OpenClaw AI agents and the Hedera hashgraph.

It consumes the software interfaces in between — starting with HashPack and SaucerSwap — and replaces them with a local CLI that an AI agent drives. You talk to the network without a middleman. No wallet app. No exchange UI. No API dependencies. Just your agent, your CLI, your machine.

> This is not a library. It is not an SDK. It is a **complete, governed, locally-owned application** that an AI agent drives end-to-end.

### The Architecture

```
You (Telegram) → OpenClaw Agent → Space Lord CLI → Hedera Network
```

| Step | What Happens |
|------|-------------|
| **You Speak** | Natural language through Telegram: "Swap 10 SAUCE for HBAR" |
| **Agent Interprets** | OpenClaw specialist agent maps intent to CLI command |
| **CLI Executes** | Deterministic code runs directly against Hedera — no middleware |
| **Hedera Settles** | Transaction confirmed in ~3 seconds, HashScan link returned |

The agent doesn't write code. It calls fixed functions. One valid execution path per operation. **Fewer tokens, consistent results, deterministic security.**

### Three Platforms, One Agent

Space Lord connects Hedera's DeFi infrastructure to your Telegram through an OpenClaw AI agent.

| Platform | Role |
|----------|------|
| **Hedera** | Settlement layer — SaucerSwap V2, HTS, HCS, Mirror Node, Accounts, Staking |
| **OpenClaw** | Agent runtime — specialist agent with SKILL.md, config, memory, Telegram bridge |
| **Telegram** | User interface — conversational UI, natural language, accessible from any phone |

<div style="page-break-after: always;"></div>

## Innovation — What Makes This Novel

### 1. CLI Tool Use, Not MCP
OpenClaw's breakthrough: give an agent a terminal, not an MCP server. No Docker, no port management, no container orchestration. Just a skill file and a CLI. This is the architecture that makes edge compute viable for individual users.

### 2. Direct to Smart Contracts — No API Dependencies
We built a native SaucerSwap V2 plugin from scratch. Direct smart contract calls via JSON-RPC. No SaucerSwap API. No redirections. No extra fees. If SaucerSwap's API goes down, Space Lord still works — only the smart contracts and Hedera need to be running.

### 3. Governed Agent Autonomy
One JSON config file (`governance.json`) — the agent can read it but **never write it**. Per-swap limits ($100), daily caps ($100), slippage ceilings (5%), gas reserves (5 HBAR). Deterministic code enforces these before the agent touches any transaction. The agent is a **user of the CLI, not an admin**.

### 4. The Agent Builds Its Own Training Data
Every command auto-generates structured fine-tuning data (SFT, DPO, error-fix pairs). The agent is building the curriculum for its own replacement — a personalised edge-local model tuned to your portfolio. Sovereign compute on your device.

### 5. Our Target Market is AI Agents
Space Lord's primary consumer is not people — it is AI agents. The CLI is designed for machine readability. The governance system is designed for autonomous operation. Humans can use it directly, but the architecture optimises for agent operation.

---

## Hedera Integration Depth

We connect directly to **six Hedera services** with no middleware:

| Service | How We Use It |
|---------|--------------|
| **SaucerSwap V2 (EVM)** | Custom open-source router — direct smart contract calls, three fee tiers, hub routing through USDC/HBAR pools. Zero interface fees. |
| **HTS** | Token creation, association, transfers, ERC20 approvals via precompile |
| **HCS** | On-chain trading signals (structured JSON), self-healing bug telemetry, HCS-10 agent-to-agent messaging |
| **Mirror Node** | Real-time balances, transaction history, pool data, token pricing, NFT metadata |
| **Accounts** | Multi-account management with independent ECDSA keys, nickname-based discovery |
| **Staking** | Native HBAR staking to consensus nodes |

### Why Hedera is the Right Chain

Hedera's sub-cent transaction fees and 3-second finality make it **uniquely suited for agent-driven DeFi**. When an AI agent manages a portfolio autonomously, cost per operation matters enormously. This is the lowest-cost chain for agent autonomy — and the value lives in owning the on-chain smart contracts and positions, not paying middleware fees.

<div style="page-break-after: always;"></div>

## Security Model

### The Golden Rule: The AI agent never sees your keys.

| Layer | How It Works |
|-------|-------------|
| **Key Isolation** | Private keys stay on your machine, XOR-obfuscated in memory, decrypted only at signing. Agent workspace has zero access. |
| **Deterministic Execution** | Every command produces the same result for the same input. No probabilistic failures. |
| **Transfer Whitelists** | All outbound transfers blocked unless destination is pre-approved. EVM addresses blocked entirely. |
| **Safety Limits** | `governance.json` enforces hard limits — the agent cannot override them. |
| **Agent Sandboxing** | The agent calls the same CLI you would. No hidden APIs. No special privileges. Same governance. Same limits. |

---

## Features — What Works Today

| Feature | Detail |
|---------|--------|
| **Token Swaps** | Native SaucerSwap V2 — direct smart contract calls, no API |
| **Limit Orders** | Local background daemon with price polling and passive execution |
| **Portfolio Management** | Real-time balances, USD values, transaction history, multi-account |
| **Self-Custody Transfers** | Whitelisted destinations only, EVM blocked |
| **Autonomous Rebalancing** | Power Law daemon with independent robot account |
| **On-Chain Signals** | Daily HCS heartbeat, structured JSON, anyone can subscribe |
| **Governance Engine** | Per-swap limits, daily caps, slippage ceilings — one config file |
| **Custom Plugins** | Extend BasePlugin, drop in `src/plugins/`, direct blockchain access |
| **Agent Workflows** | Multi-step prompts — chain multiple actions in one instruction |
| **Training Pipeline** | Auto-generates SFT, DPO, and error-fix datasets from every command |
| **HCS Bug Telemetry** | On-chain crowd-sourced bug reporting — no GitHub account needed |
| **30+ CLI Commands** | Swap, transfer, stake, signal, liquidity, NFTs, and more |

---

## Space Lord vs Hedera Agent Kit

The Hedera Agent Kit is an excellent SDK that provides Hedera building blocks. Space Lord is a different layer — a full-stack application that wraps those building blocks into a governed, agent-driven system. **They are complementary, not competing.**

|  | Hedera Agent Kit | Space Lord |
|--|-----------------|------------|
| **Type** | SDK / library for developers | Complete application agents drive |
| **Framework** | LangChain, ElizaOS, MCP | OpenClaw CLI tool use (no MCP) |
| **SaucerSwap** | Via SaucerSwap API | Direct smart contract calls, no API |
| **Governance** | None | Per-swap limits, daily caps, slippage — agent reads, can't write |
| **Key Security** | Developer-managed | XOR-obfuscated, agent sandboxed entirely |
| **Training** | No | Every command auto-generates fine-tuning data |
| **Interface** | None (bring your own) | Telegram bot via OpenClaw |
| **Runs on** | Testnet examples | Mainnet with real tokens |

<div style="page-break-after: always;"></div>

## Execution & Validation

### What We Delivered

- **~10,000 lines** of production Python code
- **30+ CLI commands** — all functional on Hedera mainnet
- **Real transactions** with real tokens — no testnet, no simulations
- **Full OpenClaw integration** — specialist agent with SKILL.md, config files, Telegram bridge
- **Native SaucerSwap V2 plugin** — built from scratch, open-sourced, no API dependency
- **Governance engine** — deterministic safety limits enforced in code
- **Training data pipeline** — auto-generating fine-tuning datasets from every interaction
- **HCS integration** — on-chain signals and crowd-sourced bug telemetry
- **Plugin architecture** — extensible system for community-built tools

### Key Learnings

1. **CLI tool use > MCP for edge compute** — simpler, faster, no container overhead. The right architecture for individual users on personal devices.
2. **Governance must be deterministic, not probabilistic** — AI agents cannot be trusted to self-govern. Hard limits in fixed code are the only reliable safety model.
3. **The middleware is the vulnerability** — every API dependency is a point of failure, a potential fee, and a loss of sovereignty. Direct smart contract interaction is harder to build but fundamentally more resilient.
4. **Agents need applications, not just SDKs** — the gap in the market is not more building blocks. It's governed, user-ready systems that agents can operate autonomously.
5. **Training data is a byproduct, not a feature** — if every agent interaction auto-generates fine-tuning data, the system improves without explicit effort.

---

## Future Roadmap

### Now — Building

| Priority | Detail |
|----------|--------|
| **CLI Confirmation Gates** | Hardcoded tool gates to prevent agents from skipping user approval |
| **HCS-10 Bug Tracking** | Live on-chain bug reporting routed to coding agents for automated fixes |
| **Latency Optimisation** | Collapsing LLM call overhead alongside Hedera Block Streams |
| **Local Edge Models** | Downloadable small expert models optimised for Mac Minis |

### Endgame — The Thesis

| Vision | Detail |
|--------|--------|
| **Autonomous Index Funds** | Locally-controlled portfolio strategies as Hedera agents |
| **Personalised Edge-Local AI** | Models trained on your usage, running on your device |
| **Agentic UI** | OpenClaw Canvas — agents generating buttons and interactive interfaces |
| **Plugin Interop** | Hedera Agent Kit alignment — interchangeable plugins across ecosystems |
| **Zero-UI Financial Infrastructure** | Absorb every DeFi app into local agent-driven plugins |

> *"Every SaaS company will become an AGaaS company — an Agent as a Service company."*
> — Jensen Huang, CEO, NVIDIA

We are one of the earliest edge-compute AGaaS business models. You own the software, you own the keys, and your agent runs locally. The middleware is being peeled away. We didn't know this business model had a name. We just built it.

<div style="page-break-after: always;"></div>

# SPACE LORD

### We're not building a better dashboard. We're consuming the dashboards.

---

**github.com/Chris0x88/pacman**

[Demo Video](https://www.youtube.com/watch?v=OElX33KViGo)

---

*Built with real money. Real transactions. Real learnings.*

**Hedera Hello Future Apex Hackathon 2026 — AI & Agents Track**
