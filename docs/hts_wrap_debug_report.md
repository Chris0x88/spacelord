# SaucerSwap HTS Wrap/Unwrap Debug Report

## Current Status
Multiple on-chain attempts to use the SaucerSwap `ERC20Wrapper` contract have failed (reverted).

- **Last Attempt**: `HTS-WBTC` -> `WBTC_LZ` (Wrap)
- **Result**: `TRANSACTION_REVERTED` during the `approve()` call.
- **Transaction Hash**: `f40ec4e6f416b109d277c933eb059a9528c518c48e2cd5dcb7e7898defd8c062`

## Findings from Code-Based Discovery

### 1. Association & Balance (Verified)
Direct Mirror Node queries confirm:
- **Account 0.0.8213379** is properly associated with both tokens.
- **Balance**: 63,819 units of `HTS-WBTC` and 2,609 units of `WBTC_LZ`.
- The "No Balance" or "Not Associated" theories are officially debunked.

### 2. The Gas Cliff
The failed approval transaction (`f40ec4e6...`) used **984,803 gas** out of a **1,000,000 gas limit**.
- This is a 98.4% utilization rate.
- In many EVM environments, hitting >95% utilization without success is a strong indicator of an "Out of Gas" revert, even if the error message is just `0x`.
- Hedera precompiles (like `approve` on a redirect) can have variable gas costs depending on the state of the account and token.

### 3. Identity Resolution
The Mirror Node reports the `from` address as the **Long-Zero** (`0x00...7d5383`), even when signing from the Alias key. This confirms Hedera's identity mapping is working as intended.

## Revised Plan
1. **Increase Gas Limits**: Set approval and wrapper contract gas to `2,000,000` (up from 1,000,000) to ensure we aren't hitting a gas cliff.
2. **Execute Live Test**: Retry the wrap conversion with the increased gas limit.
