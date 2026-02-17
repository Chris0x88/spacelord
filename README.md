# ᗧ PACMAN

```text
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```
### ᗧ· · · 👾 SaucerSwap V2 on Hedera Hashgraph

[![Network: Hedera](https://img.shields.io/badge/Network-Hedera-blue.svg)](https://hedera.com)
[![DEX: SaucerSwap](https://img.shields.io/badge/DEX-SaucerSwap-purple.svg)](https://saucerswap.finance)
[![License: MIT](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](https://opensource.org/licenses/MIT)

**Pacman** is a lightweight, AI-native trading CLI primitive for the Hedera network. It handles the "spectral" complexity of HTS token variants, proactive associations, and high-accuracy price discovery so that your agents—and you—can trade effortlessly.

---

## 🌪️ Features

- **Natural Language Execution**: Swap, convert, and send using intuitive commands: `swap 10 HBAR for USDC`.
- **Intelligent Variant Routing**: Automatically discovers the optimal path through HTS and ERC20-wrapped variants.
- **Proactive Association**: Pacman detects missing token associations and initializes them on-chain automatically.
- **Multi-Tier Price Discovery**: Aggregates live data from SaucerSwap V2, CoinGecko, and Binance.
- **AI-Agent Ready**: Built as a primitive for agentic infrastructures (OpenClaw, AutoGPT, etc.) with detailed logging and low-latency startup.
- **Security First**: Mandatory transaction simulations and local private key management.

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and run the auto-installer:
```bash
git clone https://github.com/chris0x88/pacman.git
cd pacman
./pacman  # This will auto-initialize the venv and dependencies
```

### 2. Configuration
Copy the template and add your credentials:
```bash
cp .env.template .env
# Edit .env and add your PACMAN_PRIVATE_KEY and HEDERA_ACCOUNT_ID
```
> [!TIP]
> **SaucerSwap API**: On first run, Pacman will prompt you to set your SaucerSwap API key. You can choose to use the public fallback, but a personal key is recommended for high-accuracy liquidity depth mapping.

---

## 👤 Interactive Console

Simply run `./pacman` to enter the interactive trading shell:

| Action | Example Command |
| :--- | :--- |
| **Swap (Exact In)** | `swap 100 HBAR for USDC` |
| **Swap (Exact Out)** | `swap HBAR for 20 USDC` |
| **Wrap/Unwrap** | `convert 10 HBAR for WHBAR` |
| **Transfer** | `send 50 USDC to 0.0.1234` |
| **Wallet Balance** | `balance` |
| **Market Prices** | `price` |

---

## 🤖 For AI Developers

Pacman is designed to be "Consumed" by AI agents. Every command generates structured terminal output that is easy for LLMs to parse, and detailed execution logs are stored in `logs/` for strategy auditing.

- [AI Integration Guide](docs/SAUCERSWAP_API_GUIDE.md)
- [Router Evolution Documentation](docs/ROUTER_EVOLUTION.md)

---

## 🛡️ Security & Guardrails

- **Simulation Mode**: Set `PACMAN_SIMULATE=true` in `.env` to test routes without broadcasting live transactions.
- **Local Keys Only**: Your private keys never leave your machine.
- **Slippage Protection**: Hard-capped slippage limits prevent execution during extreme volatility.

---

```markdown
**Release Status**: `v0.2` (Experimental / Testing Only)
```
```markdown
**Legal**: Use at your own risk. This is experimental software released for criticism and feedback, input and growth. We suggest using testnet accounts while testing.
```
