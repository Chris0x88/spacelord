# 👻 Pacman Expansion Plan: Human & Agentic Trading

This document archives the research, user ideas, and proposed implementation plan for expanding the Pacman CLI.

---

## 💡 User Ideas (The "Remit")
The user provided 13 core ideas for expansion, strictly adhering to the "super easy code" remit for both humans and AI agents.

1.  **Staking**: Missing transaction types (absolute critical ones, e.g., Native Staking).
2.  **Wallet Management**: Guided setup to upload keys to `.env`.
3.  **Multi-Account**: Ability to switch between different wallets/agents.
4.  **Liquidity Pools**: Deposit and withdraw from SSV2 pools (requires SSV2 NFT management).
5.  **Monitoring**: Super basic live dashboard for top pairs/liquidity.
6.  **Smart Routing**: AI-driven or price-based routing (handling rate limits).
7.  **Payment QR**: Generator for receiving funds.
8.  **Payment Requests**: Send requests for funds.
9.  **HCS Broadcasting**: Offer small rebalancing trades via HCS.
10. **HCS Scanning**: Passive scanning for atomic swap matches (HCS listed bids/offers).
11. **Network Status**: AI interpretation of Hedera roadmap and HIIP status.
12. **AUDD Integration**: Native AUDD support for cheap DEFI.
13. **SSV2 Snapshots**: Snapshot data for top volume pools.

---

## 🏁 Analysis & Gaps
*   **Gap vs HashPack**: Lack of Native Staking and Multi-Account management in the CLI.
*   **Gap vs Agent SDK**: Lack of HCS primitives for true "Agent-to-Agent" atomic swaps.
*   **Technical Risk**: Liquidity Pool management (Idea 4) is complex due to SSV2 using NFTs to represent positions; this might conflict with the "simple primitive" goal if not handled carefully.

---

## 🗺️ Proposed Roadmap (Phased Approach)

### Phase 1: Core Wallet & Security 👻
*   **`pacman setup`**: Guided `.env` configuration.
*   **Multi-Account Profiles**: Switch between agents via command.
*   **HBAR Staking**: Support for `stake` command.

### Phase 2: Live Data & Monitoring 📊
*   **Live Dashboard**: TUI using `rich.live` for real-time market data.
*   **Liquidity Snapshots**: SSV2 pool stats.

### Phase 3: Agentic Intelligence 🤖
*   **HCS Atomic Swaps**: Broadcasting and scanning for P2P swaps to avoid DEX fees.

### Phase 4: Advanced DeFi 🌪️
*   **LP Ops**: Deposit/Withdraw logic for Concentrated Liquidity.

---

## 📝 Recent Context Summary
The assistant analyzed the codebase and external SDKs, identifying that while Pacman is strong on routing and execution, it lacks the broader account and network primitives found in more mature wallets. The user approved the "super easy code" focus and requested this plan be archived for future reference.
