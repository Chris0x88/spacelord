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

### 2.1 The "Sentinel" Daemon (Limit Orders) (IN PROGRESS)
- Background process polling prices every block.
- Logic: `if price < target: controller.swap(...)`

### 2.2 Connector Framework (Farming & Lending)
- `lib/transfers.py`: Hardened transfer logic with whitelist protection.
- `lib/saucerswap.py`: V2 swap execution.

---

## Phase 3: Networked Features (The "Voice")

### 3.1 HCS Messaging (The "Bulletin Board")
- Using Hedera Consensus Service for P2P coordination.
- **HCS Swaps**: Propose swaps to a public topic; the daemon auto-matches and notifies.

### 3.2 QR & Payments
- ASCII QR generator for easy mobile-to-terminal transfers.

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
| **Limit Orders** | High | In Progress |
| **HCS Swaps** | Very High | Researching |

*This roadmap is a living document. Last updated: Feb 19, 2026.*
