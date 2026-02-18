# Design Decision: V1 Connector Strategy

## Overview
We are implementing a "simple connector" for SaucerSwap V1 rather than merging it into the existing `SaucerSwapV2` client.

## Rationale

### 1. Fundamental Engine Differences
SaucerSwap V1 and V2 are based on different generations of Uniswap:
- **V1 (Uniswap V2 / Constant Product)**: Uses the formula `x * y = k`. Quoting is done via `getAmountsOut(amountIn, path)`. The router interface is straightforward.
- **V2 (Uniswap V3 / Concentrated Liquidity)**: Uses ticks and ranges. Quoting requires complex state simulations (`quoteExactInput`) and path encoding (bytes-based).

### 2. Interface Divergence
The contract ABIs are incompatible:
- **Encoding**: V1 uses `address[]` for paths; V2 uses packed `bytes` with embedded fee tiers (e.g., 500/3000/10000 bps).
- **Functions**: V1's `swapExactTokensForTokens` vs V2's `exactInput`.

## Decoupled Strategy (Updated per User Feedback)

To achieve the **simplest possible solution** and ensure V2 remains 100% independent of V1, we are adopting a strictly decoupled approach:

1.  **Standalone CLI Command**: Instead of merging V1 into the existing `swap` command, we will introduce `swap-v1`. This makes the separation explicit and prevents any logic pollution in the main swap flow.
2.  **Zero-Dependency Design**: The `SaucerSwapV1` client will live in `lib/v1_saucerswap.py`. The core `PacmanExecutor` and `PacmanController` will either use lazy imports or optional registration, ensuring that if `lib/v1_saucerswap.py` is deleted, the system continues to function perfectly for V2.
3.  **NLP Routing**: The NLP processor will be updated. If it detects a V1 pool is required (based on the approved registry), it will clearly instruct the user or route specifically to the V1-aware handler.

### Benefits
- **Indestructibility**: Deleting V1 files has zero side-effects on V2.
- **Simplicity**: No complex "universal adapter" logic; just simple, direct connectors for each protocol.

This "connector" approach provides the functionality requested with the least risk of breaking existing V2 routing.
