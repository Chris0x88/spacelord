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

## ᗧ· · · 👾 Give your OpenClaw a Hedera toolkit that can grow with your ideas and adventures 

**Pacman** is an open-source, AI-native trading and operations primitive built on the Hedera Hashgraph for the Hedera Apex Hackathon 2026. It provides a lightweight, pure-terminal interface completely bypassing web frontends, indexers, and intermediary services so that your OpenClaw can control a wallet, conduct swaps, submit and withdraw liquidity, stake, send and receive tokens and much much more, giving you direct access to the Hashgraph. 

Our vision is to collapse the software intermediary tools into one locally run, locally controlled, AI-integrated software tool. No more multi step logins, swapping between slow crypto apps and remembering app specific tools and nomenclature, just let your OpenClaw figure it out for you. By embracing low-friction, low-cost, decentralized systems, we aim to fulfill the original dream of cryptocurrency: **self custody, the cheapest fees possible, peer to peer economic freedom without rent-seeking intermediaries whilst we still rely on and support the core infrastructure and actual productive services provided by large institutions like Google for node operations and staking, Amazon for their cloud-based Key Management Service and IBM/EqtyLab for agentic guardrails. (We have a lot more to come). What we want to see is economic value flow back into the real economy and away from rent-seeking financial services intermediaries.**

Designed from the ground up for agentic infrastructure (like OpenClaw, AutoGPT, and MCP), Pacman serves as the foundational "action layer" for AI agents to interact with the Hedera ecosystem.

> ⚠️ **WARNING**: The security implications of local agentic control are experimental and **EXTREMELY HIGH RISK**. This software is in active development. Use on Testnet and treat as an experimental window into the future of self-custody.

---

## 🔮 The Vision: A Fully Autonomous AI Economy

Pacman is evolving rapidly beyond a trading CLI. It is becoming a comprehensive toolkit for AI-to-AI and AI-to-Human interactions on-chain. As agents improve, we will convert and add features into fully modular AI systems.

### 1. Agentic Communication & P2P Swaps (HCS & TOON)
We are building towards AI network communications on the Hedera Consensus Service (HCS) using the structured TOON language. 
- **Peer-to-Peer Atomic Swaps**: Users and agents will be able to directly contact each other, post peer-to-peer trade proposals to HCS topics, and scan for direct matches. 
- Bypass DEX fees and intermediaries entirely by executing trustless atomic swaps directly between wallets, negotiated purely via HCS messaging.

### 2. Auto-Pilot Index Fund style Portfolio Rebalancing - that you control!
Implement index fund-style portfolio rebalancing on auto-pilot and customisable by you and your agent. We want to give you the tools, you choose how to use them. (Coming soon). 
- Powered initially by our locally built background robot daemon.
- Evolving into fully decentralized execution using the **Hedera Schedule Service** paired with smart contracts, allowing your agent to trustlessly manage a weighted portfolio over time without waking up.

### 3. Agentic Information Markets & x402 Payments
Leveraging the upcoming **Hedera BlockStream** update for ultra-fast chain scanning:
- Agents can create discrete topics, broadcast valuable information, and scan global market data.
- Integrate **L402/x402 agentic payments**, (coming soon), to allow AI models to literally pay each other for data, API access, or real-time analysis using HBAR micropayments or other bridged assets available to us.  

### 4. Hands-Free, Self-Installing AI Agents
Our current functional focus is improving local key management and enhancing the instruction/skill sets tailored for **OpenClaw**. Debugging and strengthening core functions and tools for edge cases. 
- We want an AI agent to be able to run this CLI locally on your computer from a simple skill file.
- The ultimate goal: the agent can **self-install the program**, set up its own environment variables, and operate totally hands-free, totally locally. Frictionless deployment & utility for the user. 

---

## 🌪️ Features Today

- **Natural Language Execution**: Swap and send using intuitive commands: `swap 10 HBAR for USDC`. Perfect for NLP-based AI interpretation.
- **Autonomous Limit Orders**: Set passive Buy/Sell targets that execute in the background via a persistent local daemon.
- **Proactive Association**: Pacman detects missing Hedera token associations and initializes them on-chain automatically.
- **Multi-Tier Price Discovery**: Aggregates live data from SaucerSwap V2 bypassing API congestion directly via contract `eth_calls`.
- **Sub-Account Management**: Spin up disposable agent-wallets natively tethered to your primary private key.
- **Security Guardrails**: Mandatory execution simulation before transaction broadcasts. We hardcode wallet whitelist configurations to force agents to operate within strict rails. *(Note: Risks remain that an advanced agent could extract or rewrite code to bypass limits, but this flexibility is entirely intentional to attract developer community input).*

---

## 🚀 Getting Started & Safety

### 1. Prerequisites: Get a Disposable Key
Before starting, we highly recommend creating a new account on a wallet like [HashPack](https://www.hashpack.app/), and transferring in roughly 5-10 HBAR. Export the **Private Key** for this disposable account. 
- You will need HBAR to cover token association fees and minor gas costs.
- **SECURITY WARNING**: Storing a private key in a `.env` file is inherently high-risk, especially when handing runtime control to an experimental AI agent. **Assume any key you give to this application is compromised from the moment you paste it**. Do not use your main wallet!

### 2. Installation
Clone the repository and install the package locally:
```bash
git clone https://github.com/chris0x88/pacman.git
cd pacman
pip install -e .
```
*(Installing globally auto-bootstraps the `pacman_env` virtual environment and commands.)*

### 3. Configuration (Onboarding Wizard)
Run the interactive setup wizard:
```bash
pacman setup
```
Pacman (or OpenClaw) will guide you through setting up your Hedera `Account ID` and masking your `Private Key`. It will automatically generate your local `.env` file safely without printing your secrets to the console, and will auto-associate a base set of top SaucerSwap V2 tokens (USDC, WBTC, WETH, etc.) so you're ready to trade.

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
1. **Download the Skill**: Provide your agent (like OpenClaw) with `docs/SKILLS.md` and `docs/AI_AGENT_GUIDE.md`. These files act as system prompts defining exact syntax and Hedera-specific caveats.
2. **Execute as a Subprocess**: Agents can call the CLI in "One-Shot" mode entirely from their background process without needing to enter the interactive shell:
   ```bash
   pacman swap 10 HBAR for USDC
   ```
3. **Parse and Learn**: Every execution saves a highly detailed JSON artifact to `execution_records/`. Agents can ingest these local records to maintain internal ledgers without needing to query a Mirror Node or indexer.

---

## 📂 Repository Index

For developers and agents looking to explore or contribute, here is how the codebase is structured:

- **`cli/`**: The core interactive shell.
  - `commands/`: Individual user commands (`swap`, `pools`, `wallet`, `orders`, etc.).
  - `main.py` & `display.py`: The REPL loop, prompt parser, and UI formatting.
- **`src/`**: The backend logic and Hedera action layer.
  - `executor.py`: Broadcaster for transactions (swaps, approvals, transfers).
  - `limit_orders.py`: Background daemon thread for executing passive targets.
  - `history.py`: Local JSON ledger database.
  - `plugins/account_manager.py`: Sub-account derivation and token associations.
- **`lib/`**: External API clients.
  - `saucerswap.py`: Interacts with SaucerSwap V2 contracts & APIs.
  - `prices.py`: Caches live token prices.
- **`data/`**: Local configuration caches (`pools.json`, `orders.json`, `accounts.json`).
- **`docs/`**: Critical reading for AI agents (skills, upgrade plans, agent guides).

---

```markdown
**Release Status**: `v0.9.4` (Stable Beta)
```
```markdown
**Disclaimer**: Use at your own risk. This is experimental software released for criticism, feedback, and growth. Do not put life savings into a hot wallet managed by an experimental AI.
```
