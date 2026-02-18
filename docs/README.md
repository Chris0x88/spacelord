# 👻 Pacman: AI-Powered Trading for Hedera

> [!CAUTION]
> **EXPERIMENTAL / TESTING ONLY.** User beware: this software is in active testing and some functions may not work as desired. Use at your own risk. Private keys are handled locally; ensure your environment is secure. See [SECURITY.md](SECURITY.md) for critical safety guidelines.

[![License: MIT](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](https://opensource.org/licenses/MIT)
[![Hedera](https://img.shields.io/badge/Network-Hedera-blue.svg)](https://hedera.com)
[![SaucerSwap](https://img.shields.io/badge/DEX-SaucerSwap-purple.svg)](https://saucerswap.finance)

**Pacman is a lightweight CLI primitive that gives AI agents (like OpenClaw) the power to swap on Hedera. Built for strategy malleability, it handles the "spectral" HTS variants while you tweak your logic in plain English.**

---

## 🌪️ The "Ghost" Advantage
Trading on Hedera often involves complex token variants (HTS vs ERC20 bridged) and manual association requirements. **Pacman haunts the machine** to handle it all for you:

- **Natural Language Parsing**: Just tell it what you want. "swap 10 HBAR for USDC".
- **Intelligent Variant Routing**: Automatically finds the best path through HBAR, USDC, or SAUCE hubs.
- **Proactive Association**: Pacman detects missing token associations and fixes them on-chain before you swap.
- **Hardened Approvals**: No more "Amount Exceeds Supply" errors. Pacman scales approvals perfectly for every token type.
- **Professional Receipts**: Boxed receipts with transparent fees, net rates, and live HashScan links.

---

## 🚀 Quick Start (One-Shot Mode)

```bash
# 1. Install Dependencies
pip install web3 networkx python-dotenv

# 2. Configure# Required for live trading (Standard Ethereum Format)
PRIVATE_KEY=your_private_key_here_without_0x_prefix
PACMAN_SIMULATE=true  # Start in safety mode

# 3. Just Swap
python3 pacman_cli.py "swap 10 HBAR for USDC"
```

---

## 👤 Human Commands, 🤖 Robot Execution

| Goal | Command Example |
| :--- | :--- |
| **Buy Exact** | `buy 0.001 WBTC with USDC` |
| **Sell Exact** | `sell 50 HBAR for SAUCE` |
| **Bridge/Wrap** | `convert 0.01 WBTC_LZ to WBTC_HTS` |
| **Portfolio** | `balance` |
| **Audit Trail** | `history` |

---

## 🧠 For AI Agent Developers
Pacman is built to be a **primitive for agentic infrastructure**. If you are building with OpenClaw, AutoGPT, or LangChain, check out our specialized guides:

- [AI Agent Interaction Guide](docs/AI_AGENT_GUIDE.md)
- [Infrastructure Integration Plan](docs/INTEGRATION_GUIDE.md)

---

## 🛠️ Tech Stack
- **Engine**: Python 3.10+
- **Connectivity**: Web3.py & Hedera JSON-RPC
- **Routing**: NetworkX-powered variant graph
- **Source of Truth**: SaucerSwap V2 Liquidity Pools

---

### 🛡️ Security
Pacman never stores your private key. It reads from environment variables at runtime and supports a full **Simulation Mode** (`PACMAN_SIMULATE=true`) for risk-free testing of any trade route.

**Release Status**: `V1.0-BETA` (Experimental / Testing Only)
