# SaucerSwap V2 Integration Rules & Lessons Learned
## (Authoritative Reference for Pacman CLI)

This document captures critical "small learnings" and Hedera-specific rules discovered during the development and stabilization of the Pacman CLI swap engine.

---

### 1. HBAR Value Scaling (The "pseudo-Wei" Rule)
> [!IMPORTANT]
> Although HBAR and HTS tokens (like SAUCE/USDC) have 8 or 6 decimals, the **Hedera JSON-RPC Relay (Hashio)** expects the `value` field in the Ethereum transaction envelope to be in **18 pseudo-decimals (Wei)**.

- **Rule**: If sending 1 HBAR, the `value` field must be `1,000,000,000,000,000,000`.
- **Implementation**: Scale the raw tinybars (8 decimals) by `10^10`.
- **Status**: ✅ Implemented in `lib/saucerswap.py`.

### 2. The Recipient Bug (Multicall Logic)
> [!IMPORTANT]
> When performing a **Token → HBAR** swap via `multicall`, the `exactInput` function's `recipient` MUST be the **Router Address**, not the user's EOA.

- **Reason**: The Router receives the WHBAR first. The subsequent `unwrapWHBAR` call then pulls from the Router's own balance to send native HBAR to the user. If the user is the recipient of the first step, the Router has nothing to unwrap.
- **Status**: ✅ Implemented in `lib/saucerswap.py`.

### 3. Millisecond Deadlines
> [!WARNING]
> SaucerSwap V2 contracts on Hedera require deadlines in **milliseconds**. Standard Unix timestamps (seconds) used in most EVM chains will cause immediate transaction reverts.

- **Rule**: `deadline = int(time.time() * 1000) + 600000` (for 10 mins).
- **Status**: ✅ Implemented in `lib/saucerswap.py`.

### 4. HTS Token Approvals
> [!CAUTION]
> Standard EVM `approve()` calls via Web3.py frequently revert for HTS tokens on Hedera.

- **Rule**: Use the Hedera SDK (`AccountAllowanceApproveTransaction`) for HTS tokens.
- **Status**: ✅ Handled via `lib/saucerswap.py`.

### 5. Multi-hop Exact Output (Backwards Pass)
> [!NOTE]
> For multi-hop "Exact Output" trades (e.g., A → B → C for 10 units of C), you cannot simply quote in one direction.

- **Rule**: You must perform a **Backwards Pass** through the pools. 
    1. Quote B → C to find how much B is needed for 10 C.
    2. Quote A → B to find how much A is needed for that amount of B.
- **Status**: ✅ Implemented in `src/router.py`.

### 6. Gas Limits for Multicall
- **Finding**: Complex `multicall` operations (like Token → HBAR) can consume over 600k gas.
- **Rule**: Set a safety limit of at least **2,500,000** for `multicall` to avoid "Out of Gas" reverts.
- **Status**: ✅ Updated in `lib/saucerswap.py`.

### 7. HBAR in LP Deposits — Multicall, NOT Pre-Wrap (CRITICAL)
> [!CAUTION]
> A common mistake is to manually call `WHBAR.deposit()` before minting an LP position when HBAR is one of the pool tokens. **This is WRONG and will waste gas on a revert.**

- **Correct Pattern**: The `NonfungiblePositionManager` handles HBAR wrapping internally, exactly like the V2 Router does for swaps.
  1. Build `mint(params)` calldata normally, using the WHBAR address for the HBAR token slot.
  2. Build `refundETH()` calldata to return unused HBAR to the sender.
  3. Send both via `multicall([mint_calldata, refundETH_calldata])` with the HBAR amount passed as the transaction `value` field (scaled by `10**10` per Rule 1).
  4. **Never** send an ERC20 `approve` call for the HBAR side—HBAR is not an ERC20.
- **Status**: ✅ Implemented in `lib/v2_liquidity.py` → `add_liquidity(hbar_value_raw=...)` + multicall path.

### 8. LP Deposit Deadline — Milliseconds (Same as Swaps)
> [!WARNING]
> LP mint/decrease operations also check `deadline`. Using Unix seconds (the Uniswap V3 Ethereum default) causes immediate reverts on Hedera.

- **Rule**: `deadline = int(time.time() * 1000) + 600_000` (10 minutes in ms).
- **Status**: ✅ Implemented in `lib/v2_liquidity.py`.

### 9. LP Deposit `amountDesired` Padding — EVM Math Tolerance
> [!WARNING]
> Passing EXACTLY the mathematical minimum target tokens for V3 LP Deposits via Python into `amountDesired` causes unexpected Edge-case reverts (`MF` or `TB:FT`) due to difference in Python 64-bit float math versus EVM 256-bit fixed point truncation up/down. 

- **Details**: `PositionManager.mint(...)` checks `require(amountOwed <= amountDesired, 'MF')`. When python exactly matches `amountDesired`, EVM internal recalculation often demands slightly more `amountOwed` than allowed, instantly reverting. Similarly, if `amountOwed` > `approve()` allowance, the transaction breaks on `safeTransfer` yielding `TB:FT`.
- **Rule**: You MUST apply a tiny tolerance buffer (+1%) to ALL calculated Python outputs before feeding them to the EVM as parameters!
- **Status**: ✅ Implemented `opt_raw = max(1, int(raw * 1.01))` in `src/controller.py`.
