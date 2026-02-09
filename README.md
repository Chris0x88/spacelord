# 🧠 Pacman - AI Trading Assistant for Hedera

**Natural language interface for crypto swaps on Hedera with intelligent routing.**

## 🎯 What It Does

Pacman understands plain English trading commands and routes them through the optimal path on SaucerSwap V2:

```
👤 You: "swap 1 USDC for WBTC"
🤖 Pacman: Found route via USDC[hts] hub
          Total cost: 0.20% + 0.04 HBAR
          HashPack visible: ✅
          Execute? (yes/no)
```

## 🧬 Smart Routing

Pacman understands Hedera's **dual-token complexity**:

| Variant | Type | Visible in HashPack | Best For |
|---------|------|-------------------|----------|
| WBTC_LZ | ERC20 (LayerZero) | ❌ No | Cheapest swaps |
| WBTC_HTS | HTS Native | ✅ Yes | HashPack compatibility |

**Routes:**
- **Cheapest**: USDC → WBTC_LZ (0.20% fees, ERC20 output)
- **Visible**: USDC → WBTC_HTS (0.20% fees, HTS output)
- **Smart**: Auto-unwrap if cheaper (coming in v2)

## 🚀 Quick Start

```bash
# Setup
pip install web3 networkx python-dotenv

# Set Environment Variables
export PACMAN_PRIVATE_KEY="your_private_key"
export HEDERA_ACCOUNT_ID="0.0.xxxxx"

# Run Pacman
python3 pacman_cli.py
```

## 🛠️ Specialized Commands

- `swap [amount] [tokenA] for [tokenB]` (Exact Input)
- `swap [tokenA] for [amount] [tokenB]` (Exact Output)
- `balance`: View wallet assets and HTS association status
- `history`: Professional record of recent transactions
- `help`: Full command reference

## 📁 Project Structure

```
pacman/
├── pacman_cli.py              # Main Entry Point (Operational CLI)
├── pacman_executor.py          # HTS/HBAR execution engine (Safe Approvals)
├── pacman_variant_router.py    # Multi-token variant routing (HTS vs ERC20)
├── pacman_price_manager.py     # Live pool-based pricing
├── saucerswap_v2_client.py     # Protocol interaction layer
├── pacman_translator.py        # Natural language intent parsing
├── tokens.json                 # Authority on supported tokens
└── pacman_data_raw.json        # Live pool data source
```

## 🛡️ Release-Ready Features

- **HTS Safe Approvals**: Automatically scales approval amounts to prevent supply errors.
- **Proactive Association**: Detects and fixes missing token associations on-the-fly.
- **ATO-Ready Receipts**: Professional boxed receipts with fees, rates, and HashScan links.
- **Live Pricing**: Real-time USD valuation for all assets and network gas.
- **Universal Routing**: Automatically finds the best path across standard and native HBAR pools.

## 🏗️ Built On

- **SaucerSwap V2** for deep liquidity
- **Hedera Hashgraph** for sub-cent gas fees
- **Web3.py** for secure contract interaction

---

**Status**: ✅ Release Candidate - Fully operational for HBAR and HTS swaps with professional reporting.
