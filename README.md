# ᗧ PACMAN

```text
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```
### ᗧ· · · 👾 SaucerSwap V2 & PACTUI on Hedera

[![Network: Hedera](https://img.shields.io/badge/Network-Hedera-blue.svg)](https://hedera.com)
[![DEX: SaucerSwap](https://img.shields.io/badge/DEX-SaucerSwap-purple.svg)](https://saucerswap.finance)
[![License: MIT](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](https://opensource.org/licenses/MIT)

**Pacman** is a lightweight, AI-native trading CLI primitive for the Hedera network. It handles the "spectral" complexity of HTS token variants, proactive associations, and high-accuracy price discovery so that your agents—and you—can trade effortlessly.

---

## 🌪️ Features

- **Natural Language Execution**: Swap and send using intuitive commands: `swap 10 HBAR for USDC`.
- **PACTUI (Giant Dashboard)**: A stunning, high-density Terminal UI for overseeing your entire portfolio and active orders in real-time.
- **Autonomous Limit Orders**: Set passive Buy/Sell targets that execute in the background via the "Sentinel" daemon.
- **Intelligent Variant Routing**: Automatically discovers the optimal path through HTS and ERC20-wrapped variants.
- **Proactive Association**: Pacman detects missing token associations and initializes them on-chain automatically.
- **Multi-Tier Price Discovery**: Aggregates live data from SaucerSwap V2, CoinGecko, and Binance.
- **Security First**: Mandatory transaction simulations and local private key management.

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and install the package:
```bash
git clone https://github.com/chris0x88/pacman.git
cd pacman
pip install -e .
```

### 2. Launching
- **CLI**: Run `pacman` to start the interactive shell.
- **TUI**: Run `pactui` for the consolidated Giant Dashboard.

### 2. Configuration (Onboarding)
Once the CLI starts, Pacman will guide you through the setup:
1.  **Wallet Setup**: Run `setup` to securely enter your Account ID and Private Key (masked input).
2.  **API Key**: Set your SaucerSwap API key when prompted for high-accuracy pricing.
3.  **Bootstrap Liquidity**: Run `pools search USDC` and `pools approve <ID>` to whitelist your first trading pairs.

> [!IMPORTANT]
> **Modular Discovery**: Pacman does not ship with a bloated pool list. You must "Approve" the pools you want to trade in to keep your routing engine fast and curated.

---

## 👤 Interactive Console

Simply run `./pacman` to enter the interactive trading shell:

| Action | Example Command |
| :--- | :--- |
| **Swap (Exact In)** | `swap 100 HBAR for USDC` |
| **Swap (Exact Out)** | `swap HBAR for 20 USDC` |
| **Limit Order** | `order buy HBAR at 0.08 size 100` |
| **Transfer** | `send 50 USDC to 0.0.1234` |
| **Liquidity** | `pool-deposit` (Wizard) |
| **Wallet Balance** | `balance` |
| **Market Prices** | `price` |

---

## 🤖 For AI Developers

Pacman is designed to be "Consumed" by AI agents. Every command generates structured terminal output that is easy for LLMs to parse, and detailed execution logs are stored in `logs/` for strategy auditing.

- [AI Agent Interaction Guide](docs/AI_AGENT_GUIDE.md)
- [Router Evolution Documentation](deprecated/ROUTER_EVOLUTION.md)

---

## 🛡️ Security & Guardrails

- **Simulation Mode**: Set `PACMAN_SIMULATE=true` in `.env` to test routes without broadcasting live transactions.
- **Local Keys Only**: Your private keys never leave your machine.
- **Slippage Protection**: Hard-capped slippage limits prevent execution during extreme volatility.

---

```markdown
**Release Status**: `v0.9.3` (Stable Beta)
```
```markdown
**Legal**: Use at your own risk. This is experimental software released for criticism and feedback, input and growth. We suggest using testnet accounts while testing.
```
