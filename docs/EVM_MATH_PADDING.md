# EVM Math Padding Requirements for V3 Liquidity

## overview
When interacting with Uniswap V3 style Concentrated Liquidity protocols (such as SaucerSwap V2 on Hedera), clients must provide two core parameter sets for minting or adding liquidity:
1. `amount0Desired` and `amount1Desired`: The **maximum** tokens you are willing to spend.
2. `amount0Min` and `amount1Min`: The **minimum** liquidity limits (slippage protection).

## The "MF" and "TB:FT" Reverts

For optimal interactions, clients often want to calculate the exact ratio of `token1` required to pair with a specific amount of `token0` at the current tick.

However, a fundamental disconnect exists between standard **Python 64-bit floating-point math** and **Ethereum Virtual Machine (EVM) 256-bit fixed-point math**.
When the exact calculated ratio is passed into `PositionManager.mint(...)` as the `amountDesired`, the EVM recalculates the pool constraints internally. Due to truncation and rounding direction differences, the EVM frequently decides it needs a fraction of a unit *more* than the exact Python calculation provided.

This instantly triggers two fatal errors:
1. **`MF` (Mint Failed)**: The contract checks `require(amount0 <= amount0Desired)` and reverts because the EVM needs strictly more base units than provided in the parameter.
2. **`TB:FT` (Token Balance: Failed Transfer)**: If the parameters mathematically restrict the amount but the ERC20/HTS `approve()` is limited to the exact Python calculation, the EVM attempts to pull the higher internally-calculated amount via `safeTransferFrom`, exceeding the allowance and reverting.

## The Solution: EVM Padding Margin

To bridge the translation between Python client estimates and on-chain exact mathematics, clients **must apply a padding margin** to the `amountDesired` and corresponding `approve()` logic.

For example, a **+2% precision buffer**:
```python
# User inputs amount of Token A
opt_raw0 = amount0

# Python calculates exact ratio for Token B
opt_raw1 = calculate_token_b_exact(opt_raw0) 

# Pad BOTH bounds to give EVM 256-bit rounding headroom
padded_raw0 = max(1, int(opt_raw0 * 1.02))
padded_raw1 = max(1, int(opt_raw1 * 1.02))

# 1. Approve padded amounts
approve(token0, padded_raw0)
approve(token1, padded_raw1)

# 2. Pass padded amounts to Contract params
mint(..., amount0Desired=padded_raw0, amount1Desired=padded_raw1)
```

By safely widening the upper bound (`amountDesired`), the V3 contract computes the exact required constraints under the hood without reverting, securely refunds the remaining unspent buffer, and ensures LP positions can be seamlessly minted in highly volatile low-liquidity environments.

*(Users can configure this padding factor via standard application settings).*
