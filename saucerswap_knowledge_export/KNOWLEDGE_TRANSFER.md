# SaucerSwap Knowledge Transfer Summary

This document provides a high-level overview of the SaucerSwap implementation on Hedera, as extracted from the `btc_rebalancer2` codebase.

## 1. Swap Engine Architecture

The system uses specific engines for different swap types to handle Hedera's unique tokenomics:
- **`hts_swap_engine.py`**: Handles HTS ↔ HTS swaps (e.g., USDC ↔ WBTC). Uses standard `exactInput` with path encoding.
- **`hbar_swap_engine_v2.py`**: Handles Native HBAR swaps. 
    - **Native HBAR → Token**: Uses `exactInput` with `value` (auto-wraps to WHBAR).
    - **Token → Native HBAR**: Uses `multicall(exactInput + unwrapWHBAR)`.
- **`erc20_to_hts_wrapper.py`**: Unwraps bridged ERC20 tokens into native HTS tokens using SaucerSwap's wrapper contract.

## 2. Role of WHBAR

WHBAR (Wrapped HBAR) is the bridge between native HBAR and the SaucerSwap V2 AMM.
- **Always Wrapped**: All trades on SaucerSwap V2 actually use WHBAR.
- **Auto-Wrapping**: The router automatically wraps HBAR sent with a transaction.
- **Unwrapping**: Swapping *to* HBAR requires an explicit `unwrapWHBAR` call within a `multicall` because the router only outputs WHBAR by default.

## 3. Pricing, Data, and Routing

### Price Data Pulls (`price_service.py`)
- **SaucerSwap API**: High-frequency sync (1s) pulls prices for all whitelisted tokens from `https://api.saucerswap.finance/tokens`.
- **CoinGecko**: Low-frequency sync (60s) pulls global prices (BTC, ETH, etc.) for valuation and research.
- **Pool TVL**: Medium-frequency sync (3s) pulls pool depths from `/v2/pools` to calculate slippage and routing priority.

### Routing (`valid_swap_pairs.py` & `approved_pool_router.py`)
- **Direct Pairs**: Defined in `valid_swap_pairs.py`.
- **Multi-hop Routing**: The system prioritizes USDC/USDT as intermediaries.
- **Slippage Calculation**: Uses the constant product formula (`reserve_in * reserve_out = k`) and pool data to estimate price impact before execution.

## 4. Approved Pools (`token_registry.json`)

`token_registry.json` serves as the source of truth for:
- Verified Token IDs (0.0.XXXXX format).
- Official icons and decimals.
- Deepest liquidity pools and their fee tiers.
- Selection of "Featured" tokens for the UI.

## 5. Critical Bugs & Lessons Learned

### The Deadline Bug
- **Issue**: Standard Unix timestamps (seconds) cause reverts.
- **Fix**: SaucerSwap V2 requires **MILLISECONDS**. `deadline = int(time.time() * 1000) + offset`.

### The Approval Bug
- **Issue**: Standard EVM `approve()` calls REVERT for HTS tokens on Hedera.
- **Fix**: You MUST use the Hedera SDK (`AccountAllowanceApproveTransaction`). This is handled via `approve_hts_token.js` called from Python.

### The Recipient Bug
- **Issue**: When unwrapping WHBAR, `exactInput` must have the **Router** as the recipient, not the user, so the subsequent `unwrapWHBAR` call can grab the funds from the router's context.

## 6. Key Files in this Export

| File | Purpose |
|------|---------|
| `hts_swap_engine.py` | Main swap engine for HTS tokens. |
| `hbar_swap_engine_v2.py` | specialized engine for HBAR. |
| `approve_hts_token.js` | Critical HTS approval logic. |
| `price_service.py` | API integrations for SaucerSwap & CoinGecko. |
| `token_whitelist.py` | Curated list of safe tokens. |
| `SAUCERSWAP_ARCHITECTURE.md` | Deep dive into Hedera-specific swap logic. |

---
*Created for Christopher on Feb 8, 2026*
