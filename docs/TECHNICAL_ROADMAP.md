# Pacman Technical Roadmap: Journey to Decentralized Banking

**Vision**: To evolve Pacman from a simple CLI trading tool into a self-custodial, decentralized banking suite.
**Philosophy**: "Modular Expansion". We will build *around* the core router, not *inside* it. New features will be plugins or separate daemons.

---

## Phase 1: The "Spinal Cord" (Core Architecture)
Before adding limit orders or messaging, we must harden the core to support external control.

### 1.1 Separation of Concerns (Library vs CLI)
Currently, `main.py` holds too much logic.
- **Refactor**: Extract `PacmanRouter` and `PacmanExecutor` into a standalone `pacman-core` package.
- **Goal**: Allow other scripts (daemons, bots) to import `from pacman.core import Executor` without triggering the CLI UI.

### 1.2 Multi-Wallet Manager (`data/wallets.json`)
Support for Sub-Account Strategies.
- **Current**: Single `PACMAN_PRIVATE_KEY` env var.
- **Future**: A wallet manager that loads keys/profiles from an encrypted local vault.
- **Usage**: `pacman --profile "HighRisk_Bot" swap ...`

---

## Phase 1.5: The "Modern Standard" (Compliance & Basics)
To be a compliant 2026 Hedera Wallet, we need more than just swaps.

### 1.5.1 Native Staking (HIP-406)
- **Problem**: Holding HBAR in Pacman earns 0% APY.
- **Solution**: Implement `pacman stake <node_id>` (e.g., `pacman stake 0.0.800`).
- **Mechanism**: Send a `CryptoUpdate` transaction setting the `staked_node_id`.

### 1.5.2 Scheduled Transactions (The "Clock")
- **Problem**: Users want to execute trades at a specific future time, or require multisig approvals.
- **Solution**: `pacman schedule "swap 100 HBAR to USDC"`
- **Mechanism**: Creates a `ScheduleCreate` transaction on Hedera. The network executes it when signatures are gathered or time is reached.

### 1.5.3 Token Metadata (HIP-412)
- **Problem**: We rely on a manual `tokens.json`.
- **Solution**: Auto-fetch standard metadata from Mirror Nodes. Display NFT attributes and innovative token features.

### 1.5.4 Smart Contract Hooks (EVM Equivalence)
- **Problem**: Users want triggers based on on-chain events.
- **Solution**: "Hooks" that listen for `Transfer` events or `ContractLog`s to trigger local actions (e.g., "If verify_passed, send 100 USDC").

---

## Phase 2: autonomous Features (The "Limbs")

### 2.1 The "Sentinel" Daemon (Limit Orders)
A separate process that runs in the background (`pacman-d`).
- **Function**: Polls prices every block. Checks against a local `orders.db` (SQLite).
- **Execution**: When price matches, it spawns an `Executor` instance to fill the order.
- **User Interface**: `pacman order limit buy 100 HBAR at 0.05 USDC`

### 2.2 Connector Framework (Farming & Lending)
A plugin system for external protocol interactions.
- **Interface**: `class Connector(Protocol): def deposit(self, amount): ...`
- **Modules**:
    - `connectors/bonzo.py`: Lending/Borrowing logic.
    - `connectors/saucerswap_farm.py`: LP token staking.
- **Benefit**: Each connector is isolated. If Bonzo changes their ABI, only that file breaks.

---

## Phase 3: Networked Features (The "Voice")

### 3.1 QR Code Integration
- **Receive**: Generate ASCII QR codes in terminal (`pip install qrcode`).
- **Send**: Parse QR codes from image files or webcam input (opencv).
- **Standard**: Follow `hedera:0.0.123?amount=10&token=...` URI standards.

### 3.2 HCS Messaging (The "Bulletin Board")
Using Hedera Consensus Service (HCS) for decentralized coordination.
- **Topic**: `0.0.PACMAN_MARKET`
- **Message**: "I am selling 10k HBAR at $0.15 limit."
- **Atomic Swaps**: Two users agree on a price via HCS, then construct a multisig "Atomic Swap" transaction that settles instantly on-chain.
- **Privacy**: End-to-end encryption of messages using the user's private key.

---

## Phase 4: The Interface Evolution (The "Face")

### 4.1 "Headless" Mode & API
- Expose a simple local HTTP API (`FastAPI`) wrapping the Core.
- `GET /price/HBAR`, `POST /swap`.
- **Why?**: This allows the "Head" (UI) to be anything.

### 4.2 Web & Mobile
- **Local Web App**: A React app served locally that talks to the Headless API.
- **Remote Control**: An iOS app that connects to your home server (via Tunnel/VPN) to approve trades or view status.

---

## Implementation Strategy: How we build without breaking

1.  **The "Add-On" Rule**: New features start as standalone scripts in `scripts/` or modules in `extensions/`. They do not touch `src/executor.py` until they are stable.
2.  **State Isolation**: Each daemon (Limit Order Monitor, Copy-Trader) keeps its own state (SQLite/JSON). They do not share a global state.
3.  **Event Bus**: Core emits events (`SwapSuccess`, `PriceUpdate`). Extensions listen.

## Feature Breakdown & Complexity

| Feature | Complexity | Dependency |
|ed| :--- | :--- | :--- |
| **Native Staking** | Low (Tx Type) | Core Executor Update |
| **Limit Orders** | High (Stateful) | Daemon Infrastructure |
| **Scheduled Tx** | Medium (Logic) | Core Executor Update |
| **V1 Pools** | Low (Data) | Router Config |
| **Sub-Wallets** | Medium (Security) | Config Refactor |
| **Connectors** | Medium (ABI work) | Executor Extension |
| **QR Codes** | Low (UI) | CLI Extension |
| **HCS Messaging** | Very High (P2P Logic) | New Network Layer |

---

*This roadmap is a vision statement. Each phase represents a significant milestone in Pacman's evolution from a tool to a platform.*
