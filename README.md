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
# Clone
git clone https://github.com/Chris0x88/pacman.git
cd pacman

# Setup
python3 -m venv pacman_env
source pacman_env/bin/activate
pip install web3 networkx

# Test routing
python3 pacman_chat.py
```

## 📁 Project Structure

```
pacman/
├── pacman_chat.py              # Natural language interface
├── pacman_variant_router.py    # ERC20 vs HTS routing engine
├── pacman_executor.py          # Live transaction execution
├── saucerswap_v2_client.py     # SaucerSwap V2 integration
├── training_data/              # AI training dataset
│   ├── routing_matrix.json     # Pre-computed routes
│   └── ai_training_examples.jsonl  # 1,400+ training samples
└── pacman_architecture.md      # Full design document
```

## 🧠 AI Training Pipeline

**Phase 1 (Current)**: Core routing engine with limited validated pairs
- USDC → WBTC (HTS/LZ)
- USDC → WETH (HTS)
- USDC → WHBAR

**Phase 2**: Live execution → Record every transaction

**Phase 3**: Train 5MB specialized model on real data

**Phase 4**: Expand to all tokens using learned patterns

## 🛡️ Safety

- **$1.00 testing limit** (hardcoded)
- **Human confirmation required** for all swaps
- **Simulation mode** available
- **Read-only** analysis of btc-rebalancer2 (production app)

## 🔧 Architecture

```
Natural Language → Intent Parser → Route Optimizer → Execution Engine
                                                        ↓
                                               Transaction Recording
                                                        ↓
                                               AI Training Dataset
```

## 📊 Fee Structure

| Pool Type | Fee | Example |
|-----------|-----|---------|
| Stable pairs | 0.05% | USDC ↔ USDC[hts] |
| Standard pairs | 0.15% | USDC[hts] ↔ WBTC |
| Volatile pairs | 0.30% | SAUCE ↔ HBAR |

## 🏗️ Built On

- **SaucerSwap V2** for liquidity
- **Hedera Hashgraph** for fast finality
- **Web3.py** for contract interaction
- **NetworkX** for pathfinding

## 📝 License

MIT - See LICENSE file

## 🙏 Credits

Architecture inspired by battle-tested patterns from btc-rebalancer2.
Wrap/unwrap logic from SaucerSwap's ERC20Wrapper contract.

---

**Status**: 🚧 Alpha - Core routing validated, execution engine in testing

**Next**: Live $1 transactions → AI training → Full token expansion
