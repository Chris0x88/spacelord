# Resolution: SaucerSwap V2 LP Mint Reverts & Discovery Issues

This document outlines the technical challenges and final solutions implemented to resolve `CONTRACT_REVERT_EXECUTED` (MF/TB:FT) errors during V2 liquidity deposits and the subsequent discovery of those positions via the CLI.

## 1. The `MF` (Mint Failed) Revert
**Root Cause:** EVM 256-bit fixed-point math truncation discrepancies between the Python simulation and the on-chain contract.
- **Problem:** When calculating "optimal" token amounts for a one-sided deposit, the EVM might require slightly more tokens than the Python-derived value due to internal rounding. This triggered the mandatory slippage check in the Uniswap V3 `mint` function.
- **Solution:** Implemented **2% precision padding** on auto-derived token amounts in `PacmanController.add_liquidity`. This ensures the contract always has slightly more than the "perfect" math suggests, satisfying the liquidity requirement. Excess HBAR is safely returned via `refundETH`.

## 2. The Missing `mintFee`
**Root Cause:** SaucerSwap V2 Factory requires a protocol fee for every new position mint.
- **Problem:** Unlike standard Uniswap V3, SaucerSwap V2 requires ~0.5 HBAR (50,000,000 tinybar) as a `mintFee`. Transactions without this fee in the `value` field reverted immediately.
- **Solution:** Explicitly identified the `MINT_FEE` constant and integrated it into the `hbar_value_raw` calculation. It is passed as the transaction `value` during the `multicall`.

## 3. The `TB:FT` (Token Balance: Frequent Token?) Revert
**Root Cause:** Missing NFT Token association.
- **Problem:** On Hedera, an account must be associated with a token before it can receive it. Since the `NonfungiblePositionManager` (NFPM) mints a new NFT for every position, the user must be associated with the NFPM's NFT token collection (`0.0.4054027`).
- **Solution:** Added a mandatory association check in `PacmanController`. If the user is not associated with token `0.0.4054027`, the system automatically executes an `associate_tokens` transaction before the mint.

## 4. LP Position Discovery Failures
**Root Cause:** ABI Mismatch and Incorrect Function Selector.
- **Problem 1:** Direct `eth_call` to `positions(uint256)` used a generic Uniswap V3 ABI, but SaucerSwap V2's NFPM returns a different structure (10 fields, 320 bytes).
- **Problem 2:** The manual hex selector used in initial fixes (`0x99fbabfa`) was incorrect.
- **Solution:** 
    - Switched to the correct selector **`0x99fbab88`** for `positions(uint256)`.
    - Implemented a robust Mirror Node query for NFT serial numbers.
    - Used manual slicing of the 320-byte response to decode the first 6 critical fields (`token0`, `token1`, `fee`, `tickLower`, `tickUpper`, `liquidity`).

## 5. Summary of Architecture Changes
- **`src/controller.py`**: Added padding logic, mint fee handling, NFT association checks, and robust discovery logic.
- **`lib/v2_liquidity.py`**: Adjusted gas limits (1.0M) and increased deadline margins (60 mins) to handle Hedera-specific timing and complexity.
- **`abi/position_manager.json`**: Corrected the `positions` output structure to match the legacy SaucerSwap V2 contract.

---
*Created on: 2026-02-21*
