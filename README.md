# 👻 Pacman: AI-Powered Trading for Hedera

[![License: MIT](https://img.shields.io/badge/License-MIT-ghostwhite.svg)](https://opensource.org/licenses/MIT)
[![Hedera](https://img.shields.io/badge/Network-Hedera-blue.svg)](https://hedera.com)
[![SaucerSwap](https://img.shields.io/badge/DEX-SaucerSwap-purple.svg)](https://saucerswap.finance)

**Pacman is a high-precision trading assistant that brings natural language power to the Hedera ecosystem. Trade any HTS token using plain English commands with intelligent routing and professional-grade reporting.**

---

## 🌪️ The "Ghost" Advantage
Trading on Hedera often involves complex token variants (HTS vs ERC20 bridged) and manual association requirements. **Pacman haunts the machine** to handle it all for you:

- **Natural Language Parsing**: Just tell it what you want. "swap 10 HBAR for USDC".
- **Intelligent Variant Routing**: Automatically finds the best path through HBAR, USDC, or SAUCE hubs.
- **Proactive Association**: Pacman detects missing token associations and fixes them on-chain before you swap.
- **Hardened Approvals**: No more "Amount Exceeds Supply" errors. Pacman scales approvals perfectly for every token type.
- **Professional Receipts**: Boxed, ATO-ready receipts with transparent fees, net rates, and live HashScan links.

---

## 🚀 Quick Start (One-Shot Mode)

```bash
# 1. Install Dependencies
pip install web3 networkx python-dotenv

# 2. Configure Environment (.env)
PACMAN_PRIVATE_KEY="0x..."
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
| **Bridge/Wrap** | `convert 10 HBAR to WHBAR` |
| **Portfolio** | `balance` |
| **Audit Trail** | `history` |

---

## 🧠 For AI Agent Developers
Pacman is built to be a **primitive for agentic infrastructure**. If you are building with OpenClaw, AutoGPT, or LangChain, check out our specialized guides:

- [AI Agent Interaction Guide](AI_AGENT_GUIDE.md)
- [Infrastructure Integration Plan](INTEGRATION_GUIDE.md)

---

## 🛠️ Tech Stack
- **Engine**: Python 3.10+
- **Connectivity**: Web3.py & Hedera JSON-RPC
- **Routing**: NetworkX-powered variant graph
- **Source of Truth**: SaucerSwap V2 Liquidity Pools

---

### 🛡️ Security
Pacman never stores your private key. It reads from environment variables at runtime and supports a full **Simulation Mode** (`PACMAN_SIMULATE=true`) for risk-free testing of any trade route.

**Release Status**: `V1.0-RC1` (Production Ready)
