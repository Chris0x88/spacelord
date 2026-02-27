# ᗧ PACMAN

```text
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚╚╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```
```markdown
```markdown
### ᗧ· · · 👾 Hedera Wallet and Saucerswap trading CLI for OpenClaw
```
```

**Welcome Hedera Apex Hackathon Mentors and Builders!** 👋

**Pacman** is an open-source, AI-native trading CLI primitive built directly on the Hedera Hashgraph. It provides a lightweight, pure-terminal interface for swapping, managing liquidity, and placing limit orders via SaucerSwap V2 pools, completely bypassing web frontends and indexers.

Designed from the ground up for agentic infrastructure (OpenClaw, AutoGPT, MCP), Pacman serves as the foundational "action layer" for AI agents to interact with Hedera's DeFi ecosystem.

> ⚠️ **WARNING**: Security implications of agentic control are experimental and **EXTREMELY HIGH RISK**. This software is in active development. Use on Testnet and treat as an experimental window into the future of self-custody.


[![Network: Hedera](https://img.shields.io/badge/Network-Hedera-blue.svg)](https://hedera.com)
[![DEX: SaucerSwap](https://img.shields.io/badge/DEX-SaucerSwap-purple.svg)](https://saucerswap.finance)
[![License: MIT](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](https://opensource.org/licenses/MIT)

---

## 🌪️ Features

- **Natural Language Execution**: Swap and send using intuitive commands: `swap 10 HBAR for USDC`. Perfect for NLP-based AI interpretation.
- **Autonomous Limit Orders**: Set passive Buy/Sell targets that execute in the background via the "Sentinel" daemon.
- **Proactive Association**: Pacman detects missing Hedera token associations and initializes them on-chain automatically.
- **Multi-Tier Price Discovery**: Aggregates live data from SaucerSwap V2 bypassing API congestion directly via contract `eth_calls`.
- **Security First**: Mandatory execution simulation before transaction broadcast and deterministic offline private key signing.

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
Pacman will guide you through setting up your `Account ID`, masking your `Private Key`, and generating your local `.env` file safely without printing secrets to the console. 

> [!TIP]
> **Safety Guardrail**: We highly recommend keeping `PACMAN_SIMULATE=true` in your `.env` file while testing. In this mode, Pacman will perform exact route finding and `eth_call` simulations against the mainnet, but will **NOT** broadcast the final signed transaction, preventing gas waste and fund loss.

### 3. Launching & Testing
Once configured, you can launch the interactive shell:
```bash
pacman
```
To bootstrap liquidity tracking for a specific asset, try approving a pool:
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
1. **Download the Skill**: Provide your agent (like OpenClaw) with `docs/SKILLS.md` and `docs/AI_AGENT_GUIDE.md`. These files act as system prompts defining exact syntax and Hedera-specific caveats (like HBAR vs WHBAR wrapping).
2. **Execute as a Subprocess**: Agents can call the CLI in "One-Shot" mode entirely from their background process without needing to enter the interactive shell:
   ```bash
   pacman swap 10 HBAR for USDC
   ```
3. **Parse and Learn**: Every execution saves a highly detailed JSON artifact to `execution_records/`. Agents can ingest these local records to maintain internal ledgers without needing to query a Mirror Node or indexer.

---

## 🔮 The Future: Agentic & Security Vision

While Pacman works out of the box today, for enterprise and autonomous consumer adoption, we must radically shift the security model.

### 1. Phasing Out Local Private Keys (AWS KMS & Privy.io)
Currently, Pacman holds the private key in local `.env` memory to sign transactions. If the agent's environment is compromised, the "Hot Account" is compromised. The future roadmap includes integrating **Multi-Party Computation (MPC)** via **Privy.io** or Hardware Security Modules via **AWS KMS**. 

In the future, Pacman will build the transaction payloads and route them to an external secure enclave. The agent *requests* a signature; it never *owns* the key.

### 2. Seamless Agent Subroutines
We plan to introduce deeper **Model Context Protocol (MCP)** support. We will wrap the underlying `src/controller.py` functions natively into MCP tool-schemas, enabling any Claude or GPT instance to preview routes, query balances, and validate token metadata *without* needing to pipe standard output via Bash.

### 3. PACTUI
A high-density Terminal UI (TUI) Dashboard is currently in the initial concept stage (`pactui`), aiming to provide human operators a commanding overview of their AI agent's concurrent trading activities.

---

```markdown
**Release Status**: `v0.9.3` (Stable Beta)
```
```markdown
**Disclaimer**: Use at your own risk. This is experimental software released for criticism, feedback, and growth. Do not put life savings into a hot wallet managed by an experimental AI.
```
