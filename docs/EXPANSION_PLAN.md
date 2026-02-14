# 👻 Pacman Expansion Roadmap: Analysis & Archive

This document captures the full planning session from Feb 14, 2026, regarding the future direction of the Pacman CLI primitive for Hedera trading.

---

## 💡 Initial User Proposal
The user proposed 13 specific ideas to expand Pacman's capabilities while maintaining its "super easy code" remit for both humans and AI agents.

### The "13 Ideas":
1.  **Staking**: Include critical transaction types like HBAR Native Staking.
2.  **Wallet Management**: Guided setup to upload keys to `.env`.
3.  **Multi-Account**: Support for switching between different wallets/agents.
4.  **Liquidity Pools**: Deposit and withdraw from SaucerSwap V2 pools.
5.  **Monitoring**: Super basic live dashboard for top pairs/liquidity.
6.  **Smart Routing**: AI-driven or price-based routing (handling rate limits).
7.  **Payment QR**: Generator for receiving funds.
8.  **Payment Requests**: Send requests for funds.
9.  **HCS Broadcasting**: Offer small rebalancing trades via HCS.
10. **HCS Scanning**: Passive scanning for atomic swap matches (HCS bids/offers).
11. **Network Status**: AI interpretation of Hedera roadmap and HIIP status.
12. **AUDD Integration**: Native AUDD support for cheap DEFI.
13. **SSV2 Snapshots**: Snapshot data for top volume pools.

---

## 🏁 Assistant Gap Analysis
Comparing Pacman to industry standards:
*   **HashPack Gap**: Missing Native Staking and Account Management.
*   **Hedera Agent SDK Gap**: Missing HCS primitives for true "Agent-to-Agent" interactions.
*   **Technical Feasibility**: SSV2 LP operations are high-complexity due to NFT position management. HCS swaps are highly valuable for bypassing DEX fees.

---

## 🗺️ The Roadmap (Proposed)

### Phase 1: Core Wallet & Security 👻
*   **Setup Cmd**: Secure `.env` configuration.
*   **Multi-Account**: Agent profile switching.
*   **Staking**: Command-line HBAR staking support.

### Phase 2: Live Data & Monitoring 📊
*   **Live Dashboard**: Real-time TUI for market monitoring.
*   **Pool Stats**: Granular SSV2 liquidity data.

### Phase 3: Agentic Intelligence 🤖
*   **HCS Atomic Swaps**: Broadcasting and scanning for P2P rebalancing trades.

### Phase 4: Advanced DeFi 🌪️
*   **LP Ops**: Full deposit/withdraw logic for SSV2.

---

## 📝 Transcript Excerpt
**User**: "Where are there gaps compared to hashpack and Hedera Agent SDK that still strictly stick to the remit of this app which is to be super easy code and rules for ai agents and humans to trade their HBAR easily..."

**Assistant**: "compared to HashPack, the biggest functional gap is HBAR Staking. Compared to the Hedera Agent SDK, the next frontier is HCS integration for agent-to-agent interactions."

*Status: Plan archived to project docs for future implementation decisions.*
