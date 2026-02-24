# Pacman Technical Roadmap: Journey to Decentralized Banking

**Vision**: To evolve Pacman from a simple CLI trading tool into a self-custodial, decentralized banking suite.
**Philosophy**: "Modular Expansion". We will build *around* the core engine. New features are strictly isolated plugins to ensure stability and ease of removal.

---

## Phase 1: Core Wallet & Security 👻
*Goal: Harden the foundation and catch up to 2026 wallet standards.*

### 1.1 Headless Controller (DONE)
- Extracted logic to `src/controller.py`. Core engine is now independent of the CLI.

### 1.2 Setup & Security (NEXT)
- **`pacman setup`**: Interactive command to verify `.env`, check RPC health, and validate HTS associations.
- **`pyproject.toml`**: Standardize package management for clean AI/human imports.

### 1.3 Multi-Account Management (DONE)
- **Implemented**: `lib/transfers.py` and `controller.py` support sender/receiver resolution.
- **Profiles**: Managed via environment variables and `SecureString`.

### 1.4 Native Staking (HIP-406) (DONE)
- **Implemented**: `lib/staking.py` handles `CryptoUpdate` transactions.
- **Commands**: `stake [node_id]`, `unstake`.
- **Status**: Live in v0.9.5.

---

## Phase 1.5: The "V1 Bridge" 🌪️ (DONE)
*Goal: Access V1 liquidity without contaminating the V2 core.*

### 1.5.1 The "Sidecar" Adapter (DONE)
- **`lib/v1_saucerswap.py`**: A dedicated module for SaucerSwap V1 logic.
- **Registry**: `data/v1_pools_approved.json`. Only pools approved by the user or the "Top 20" curated list are loaded.

### 1.5.2 Pool Vetting Workflow (DONE)
- **Search**: `pacman pools search <query>` (Queries Mirror Node/API).
- **Approve**: `pacman pools approve <id>` (Adds to local JSON).
- **Cleanup**: Users can wipe the V1 registry at any time without affecting V2 routing.

---

## Phase 2: autonomous Features (The "Limbs")

### 2.1 The "Sentinel" Daemon (Limit Orders) (DONE)
- Background process polling prices every block.
- Logic: `if price < target: controller.swap(...)`
- **TUI Integration**: Live monitoring and management via PACTUI.

### 2.2 Connector Framework (Farming & Lending)
- `lib/transfers.py`: Hardened transfer logic with whitelist protection.
- `lib/saucerswap.py`: V2 swap execution.

### 2.3 Liquidity Operations (DONE)
- `lib/v2_liquidity.py`: Isolated logic for depositing and withdrawing from SaucerSwap V2 pools.
- Contract integrations: `NonfungiblePositionManager` (Mint, DecreaseLiquidity, Collect).
- **Interactive Wizard**: `pool-deposit` command for guided setup.

---

## Phase 3: Networked Features (The "Voice")

### 3.1 PACTUI (The "Giant Dashboard") (DONE)
- Consolidated market, wallet, and order management into a single high-performance TUI.
- Real-time auto-refresh and precision matching CLI standards.

### 3.2 HCS Messaging (The "Bulletin Board") (RESEARCHING)
- Using Hedera Consensus Service for P2P coordination.
- **HCS Swaps**: Propose swaps to a public topic; the daemon auto-matches and notifies.

### 3.3 QR & Payments
- ASCII QR generator for easy mobile-to-terminal transfers.

---

## Phase 4: Architectural "Solid State" (POTENTIAL)
*Goal: Move from volatile JSON files to a robust, indexed database.*

### 4.1 SQLite Migration (IDEA)
- **Why**: Prevent file corruption during crashes, enable millisecond lookups for 10k+ pools.
- **Audit Logging**: Maintain a permanent, immutable record of all console commands and transaction results.
- **Price History**: Store block-by-block price data to enable local charting and volatility analysis.
- **Persistence**: All daemon settings and limit orders become ACID-compliant.

---

## Implementation Strategy: How we build without breaking

1.  **Strict Isolation**: New protocols (V1, Bonzo, Farms) get their own `src/` or `lib/` files. No mixing of logic.
2.  **Configuration-First**: Every new feature must be toggle-able in `PacmanConfig`.
3.  **Simulation Guard**: All new transaction types MUST implement `eth_call` or Hedera Simulation before broadcasting.

---

| Feature | Complexity | Status |
| :--- | :--- | :--- |
| **Headless Refactor** | Medium | [DONE] |
| **V1 Integration** | Low (Isolated) | [DONE] |
| **Staking** | Low | [DONE] |
| **Whitelisting** | Low | [DONE] |
| **Multi-Account** | Medium | [DONE] |
| **Limit Orders** | High | [DONE] |
| **V2 Liquidity Pools** | High | [DONE] |
| **PACTUI Dashboard** | High | [DONE] |
| **HCS Swaps** | Very High | Researching |
| **AUDD Integration** | Medium | Planned |
| **SQLite Migration** | High | Idea (Phase 4) |

*This roadmap is a living document. Last updated: Feb 24, 2026.*
