# SaucerSwap V2 Integration Rules & Lessons Learned
## (Authoritative Reference for Pacman CLI)

This document captures critical "small learnings" and Hedera-specific rules discovered during the development and stabilization of the Pacman CLI swap engine.

---

### 1. HBAR Value Scaling (The "pseudo-Wei" Rule)
> [!IMPORTANT]
> Although HBAR and HTS tokens (like SAUCE/USDC) have 8 or 6 decimals, the **Hedera JSON-RPC Relay (Hashio)** expects the `value` field in the Ethereum transaction envelope to be in **18 pseudo-decimals (Wei)**.

- **Rule**: If sending 1 HBAR, the `value` field must be `1,000,000,000,000,000,000`.
- **Implementation**: Scale the raw tinybars (8 decimals) by `10^10`.
- **Status**: ✅ Implemented in `saucerswap_v2_client.py`.

### 2. The Recipient Bug (Multicall Logic)
> [!IMPORTANT]
> When performing a **Token → HBAR** swap via `multicall`, the `exactInput` function's `recipient` MUST be the **Router Address**, not the user's EOA.

- **Reason**: The Router receives the WHBAR first. The subsequent `unwrapWHBAR` call then pulls from the Router's own balance to send native HBAR to the user. If the user is the recipient of the first step, the Router has nothing to unwrap.
- **Status**: ✅ Implemented in `saucerswap_v2_client.py`.

### 3. Millisecond Deadlines
> [!WARNING]
> SaucerSwap V2 contracts on Hedera require deadlines in **milliseconds**. Standard Unix timestamps (seconds) used in most EVM chains will cause immediate transaction reverts.

- **Rule**: `deadline = int(time.time() * 1000) + 600000` (for 10 mins).
- **Status**: ✅ Implemented in `saucerswap_v2_client.py`.

### 4. HTS Token Approvals
> [!CAUTION]
> Standard EVM `approve()` calls via Web3.py frequently revert for HTS tokens on Hedera.

- **Rule**: Use the Hedera SDK (`AccountAllowanceApproveTransaction`) for HTS tokens.
- **Status**: ✅ Handled via `approve_hts_token.js` wrapper in `saucerswap_v2_client.py`.

### 5. Multi-hop Exact Output (Backwards Pass)
> [!NOTE]
> For multi-hop "Exact Output" trades (e.g., A → B → C for 10 units of C), you cannot simply quote in one direction.

- **Rule**: You must perform a **Backwards Pass** through the pools. 
    1. Quote B → C to find how much B is needed for 10 C.
    2. Quote A → B to find how much A is needed for that amount of B.
- **Status**: ✅ Implemented in `pacman_variant_router.py`.

### 6. Gas Limits for Multicall
- **Finding**: Complex `multicall` operations (like Token → HBAR) can consume over 600k gas.
- **Rule**: Set a safety limit of at least **2,500,000** for `multicall` to avoid "Out of Gas" reverts.
- **Status**: ✅ Updated in `saucerswap_v2_client.py`.
