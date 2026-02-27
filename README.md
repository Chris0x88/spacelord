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

## The Ultimate Edge Computing Device

**Pacman** is an open-source, AI-native trading and operations primitive built directly on the Hedera Hashgraph. It provides a lightweight, pure-terminal interface completely bypassing web frontends, indexers, and financial intermediaries.

Our vision is to collapse the tools of dozens of businesses into one locally run, locally controlled, AI-integrated software model. This is the ultimate edge computing device. By embracing ultra-productive, low-cost, decentralized systems, we aim to fulfill the original dream of cryptocurrency: **removing rent-seeking intermediaries so that economic value can flow back into the real economy.**

Designed from the ground up for agentic infrastructure (like OpenClaw, AutoGPT, and MCP), Pacman serves as the foundational "action layer" for AI agents to interact with the Hedera ecosystem.

> ⚠️ **WARNING**: The security implications of local agentic control are experimental and **EXTREMELY HIGH RISK**. This software is in active development. Use on Testnet and treat as an experimental window into the future of self-custody.

---

## 🔮 The Vision: A Fully Autonomous AI Economy

Pacman is evolving rapidly beyond a trading CLI. It is becoming a comprehensive toolkit for AI-to-AI and AI-to-Human interactions on-chain. As agents improve, we will convert and add features into fully modular AI systems.

### 1. Agentic Communication & P2P Swaps (HCS & TOON)
We are building towards AI network communications on the Hedera Consensus Service (HCS) using the structured TOON language. 
- **Peer-to-Peer Atomic Swaps**: Users and agents will be able to directly contact each other, post peer-to-peer trade proposals to HCS topics, and scan for direct matches. 
- Bypass DEX fees and intermediaries entirely by executing trustless atomic swaps directly between wallets, negotiated purely via HCS messaging.

### 2. Auto-Pilot Index Funds & Portfolio Rebalancing
Implement index fund-style portfolio rebalancing on auto-pilot.
- Powered initially by our locally built background robot daemon.
- Evolving into fully decentralized execution using the **Hedera Schedule Service** paired with smart contracts, allowing your agent to trustlessly manage a weighted portfolio over time without waking up.

### 3. Agentic Information Markets & x402 Payments
Leveraging the upcoming **Hedera BlockStream** update for ultra-fast chain scanning:
- Agents can create discrete topics, broadcast valuable information, and scan global market data.
- Integrate **L402/x402 agentic payments**, allowing AI models to literally pay each other for data, API access, or real-time analysis using HBAR micropayments.

### 4. Hands-Free, Self-Installing AI Agents
Our current functional focus is improving local key management and enhancing the instruction/skill sets tailored for **OpenClaw**.
- We want an AI agent to be able to run this CLI locally on your computer from a simple skill file.
- The ultimate goal: the agent can **self-install the program**, set up its own environment variables, and operate totally hands-free, totally locally.

---

## 🌪️ Features Today

- **Natural Language Execution**: Swap and send using intuitive commands: `swap 10 HBAR for USDC`. Perfect for NLP-based AI interpretation.
- **Autonomous Limit Orders**: Set passive Buy/Sell targets that execute in the background via a persistent local daemon.
- **Proactive Association**: Pacman detects missing Hedera token associations and initializes them on-chain automatically.
- **Multi-Tier Price Discovery**: Aggregates live data from SaucerSwap V2 bypassing API congestion directly via contract `eth_calls`.
- **Sub-Account Management**: Spin up disposable agent-wallets natively tethered to your primary private key.
- **Security Guardrails**: Mandatory execution simulation before transaction broadcasts. We hardcode wallet whitelist configurations to force agents to operate within strict rails. *(Note: Risks remain that an advanced agent could extract or rewrite code to bypass limits, but this flexibility is entirely intentional to attract developer community input).*

---

## 🚀 Quick Start (Safe Setup)

### 1. Installation
Clone the repository and install the package globally. This allows you to run `pacman` from any directory on your machine.
```bash
git clone https://github.com/chris0x88/pacman.git
cd pacman
pip install -e .
```
*(Installing globally auto-bootstraps the `pacman_env` virtual environment and commands.)*

### 2. Configuration (Onboarding Wizard)
Before you can trade, you need to configure your environment. Run the interactive setup wizard:
```bash
pacman setup
```
Pacman will guide you through setting up your `Account ID`, masking your `Private Key`, generating sub-accounts, and writing your local `.env` file safely without printing secrets to the console. 

> [!TIP]
> **Safety Guardrail**: We highly recommend keeping `PACMAN_SIMULATE=true` in your `.env` file while testing. In this mode, Pacman will perform exact route finding and `eth_call` simulations against the mainnet, but will **NOT** broadcast the final signed transaction, preventing gas waste and fund loss.

### 3. Launching & Testing
Once configured, launch the interactive shell:
```bash
pacman
```
To bootstrap liquidity tracking for a specific asset, approve a pool:
```bash
pools search USDC
pools approve 0.0.1234xx
```

> [!IMPORTANT]
> **Modular Discovery**: Pacman does not ship with a bloated pool list. You must "Approve" the pools you want to trade in. This keeps the local pathfinding graph highly optimized and lightning fast.

---

## 🤖 OpenClaw & AI Agent Integration

Pacman is built to be an **agentic trading primitive**. Every command outputs deterministic, highly structured text designed for LLM parsing, removing the need for agents to blindly navigate varying web DOMs.

### How to Hook Your Agent Up:
1. **Download the Skill**: Provide your agent (like OpenClaw) with `docs/SKILLS.md` and `docs/AGENT_INTEGRATION_PLAN.md`. These files act as system prompts defining exact syntax and Hedera-specific caveats.
2. **Execute as a Subprocess**: Agents can call the CLI in "One-Shot" mode entirely from their background process without needing to enter the interactive shell:
   ```bash
   pacman swap 10 HBAR for USDC
   ```
3. **Parse and Learn**: Every execution saves a highly detailed JSON artifact to `execution_records/`. Agents can ingest these local records to maintain internal ledgers without needing to query a Mirror Node or indexer.

---

```markdown
**Release Status**: `v0.9.4` (Stable Beta)
```
```markdown
**Disclaimer**: Use at your own risk. This is experimental software released for criticism, feedback, and growth. Do not put life savings into a hot wallet managed by an experimental AI.
```
