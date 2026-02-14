# SaucerSwap Swap Architecture on Hedera

> **CRITICAL DOCUMENTATION FOR FUTURE AI SESSIONS AND APP BUILDERS**
> This document captures hard-won knowledge about SaucerSwap swaps on Hedera.
> The SaucerSwap documentation is often WRONG or incomplete. This is the source of truth.

---

## ⚠️ GOLDEN RULE: DON'T TOUCH WORKING CODE

Each swap type has its own engine. Once something works, **LOCK IT DOWN**.

- ✅ `hts_swap_engine.py` - HTS ↔ HTS (USDC ↔ WBTC) - **WORKING, DO NOT MODIFY**
- ✅ `erc20_to_hts_wrapper.py` - ERC20 → HTS unwrapping - **WORKING, DO NOT MODIFY**
- ✅ `hbar_swap_engine_v2.py` - HBAR swaps (V2) - **WORKING, DO NOT MODIFY**
- ✅ `hbar_swap_engine_v1.py` - Legacy V1 HBAR swaps - **WORKING, DO NOT MODIFY**

---

## Overview: Different Engines for Different Swap Types

| Swap Type | Engine | Key Pattern |
|-----------|--------|-------------|
| **USDC ↔ WBTC** (HTS ↔ HTS) | `hts_swap_engine.py` | `exactInput` with path encoding |
| **USDC → Native HBAR** | `hbar_swap_engine_v2.py` | `multicall(exactInput + unwrapWHBAR)` |
| **Native HBAR → USDC** | `hbar_swap_engine_v2.py` | `exactInput` with `value` (auto-wrap) |
| **Legacy V1 swaps** | `hbar_swap_engine_v1.py` | `swapExactTokensForTokens` |
| **ERC20 → HTS unwrap** | `erc20_to_hts_wrapper.py` | `withdrawTo` on wrapper contract |

---

## Complete Swap Types Matrix

### ✅ WORKING SWAP TYPES

| # | Swap Type | Status | Engine | Method | Key Notes |
|---|-----------|--------|--------|--------|-----------|
| 1 | **USDC → WBTC** (HTS → HTS) | ✅ WORKING | `hts_swap_engine.py` | `exactInput` with path | Standard V2 swap |
| 2 | **WBTC → USDC** (HTS → HTS) | ✅ WORKING | `hts_swap_engine.py` | `exactInput` with path | Same as above |
| 3 | **USDC → Native HBAR** | ✅ WORKING | `hbar_swap_engine_v2.py` | `multicall(exactInput + unwrapWHBAR)` | Deadline in MILLISECONDS! |
| 4 | **Native HBAR → USDC** | ✅ WORKING | `hbar_swap_engine_v2.py` | `exactInput` with `value` | Auto-wraps HBAR to WHBAR |
| 5 | **ERC20 WBTC → HTS WBTC** | ✅ WORKING | `erc20_to_hts_wrapper.py` | `withdrawTo` on wrapper contract | Uses SaucerSwap ERC20Wrapper |

### Why Different Engines?

**The Hedera network treats different token types differently:**

1. **HTS ↔ HTS** (e.g., USDC ↔ WBTC)
   - Both are Hedera Token Service tokens
   - Standard `exactInput` works
   - Deadline can be in seconds
   - EVM `approve()` may work (but Hedera SDK is safer)

2. **HTS → Native HBAR** (e.g., USDC → HBAR)
   - HBAR is native, not an HTS token
   - Must swap to WHBAR first, then unwrap
   - Requires `multicall(exactInput + unwrapWHBAR)`
   - **Deadline MUST be in MILLISECONDS**
   - EVM `approve()` FAILS - use Hedera SDK

3. **Native HBAR → HTS** (e.g., HBAR → USDC)
   - Send native HBAR as transaction `value`
   - Router auto-wraps to WHBAR
   - Standard `exactInput` works
   - **Deadline MUST be in MILLISECONDS**

4. **ERC20 → HTS** (e.g., ERC20 WBTC → HTS WBTC)
   - Bridged tokens come as ERC20
   - Must unwrap to HTS for HashPack/SaucerSwap UI
   - Uses SaucerSwap's ERC20Wrapper contract
   - Standard EVM `approve()` works (it's ERC20, not HTS)

---

## CRITICAL BUG FIXES (Learned the Hard Way)

### 1. Deadline Must Be MILLISECONDS (Not Seconds!)

```python
# ❌ WRONG - will cause revert
deadline = int(time.time()) + 300

# ✅ CORRECT - SaucerSwap V2 uses milliseconds
deadline = int(time.time() * 1000) + 600000  # 10 mins
```

### 2. HTS Token Approvals Require Hedera SDK (Not EVM!)

EVM `approve()` calls **REVERT** for HTS tokens on Hedera. You MUST use the Hedera JavaScript SDK:

```javascript
// approve_hts_token.js
const { AccountAllowanceApproveTransaction } = require("@hashgraph/sdk");

const transaction = new AccountAllowanceApproveTransaction()
    .approveTokenAllowance(tokenId, accountId, spenderId, amount);
await transaction.execute(client);
```

Call from Python:
```python
import subprocess
result = subprocess.run([
    "node", "approve_hts_token.js", 
    "0.0.456858",  # USDC token ID
    "0.0.3949434", # SaucerSwap V2 Router
    "1000000000000"  # Amount
], capture_output=True)
```

### 3. Native HBAR Output Requires Multicall

When swapping TO native HBAR (not WHBAR), you must use:
```python
# multicall(exactInput + unwrapWHBAR)
swap_params = (path, router_address, deadline, amount_in, min_out)  # recipient = ROUTER
swap_call = router.encode_abi("exactInput", [swap_params])
unwrap_call = router.encode_abi("unwrapWHBAR", [0, user_address])

tx = router.functions.multicall([swap_bytes, unwrap_bytes]).build_transaction({...})
```

**Key:** The `exactInput` recipient must be the **router address** (not user), so `unwrapWHBAR` can access the WHBAR.

### 4. Path Encoding Uses Hedera IDs

```python
from saucerswap_v2_client import encode_path

# Use Hedera IDs (0.0.XXXXX format), NOT EVM addresses
path = encode_path(["0.0.456858", "0.0.1456986"], [1500])
```

### 5. Gas Requirements

| Operation | Minimum Gas |
|-----------|-------------|
| HTS approval (via SDK) | N/A (native Hedera) |
| Simple swap | 1,000,000 |
| Multicall (swap + unwrap) | 2,000,000 |

---

## Contract Addresses (Mainnet)

| Contract | Hedera ID | EVM Address |
|----------|-----------|-------------|
| SaucerSwap V2 Router | 0.0.3949434 | 0x00000000000000000000000000000000003c437A |
| SaucerSwap V2 Quoter | 0.0.3949424 | 0x00000000000000000000000000000000003c4380 |
| USDC | 0.0.456858 | 0x000000000000000000000000000000000006f89a |
| WHBAR | 0.0.1456986 | 0x0000000000000000000000000000000000163b5a |
| HTS-WBTC | 0.0.10082597 | (derived) |

---

## Token Decimals

| Token | Decimals | Notes |
|-------|----------|-------|
| USDC | 6 | |
| WBTC | 8 | |
| WHBAR | 8 | Wrapped HBAR token |
| Native HBAR | 18 | In EVM context (wei) |

---

## Fee Tiers

| Fee | Percentage | Use Case |
|-----|------------|----------|
| 500 | 0.05% | Stable pairs |
| 1500 | 0.15% | **Default for USDC/WHBAR, USDC/WBTC** |
| 3000 | 0.30% | Volatile pairs |
| 10000 | 1.00% | Exotic pairs |

---

## File Reference

| File | Purpose |
|------|---------|
| `hts_swap_engine.py` | Main engine for HTS ↔ HTS swaps (USDC ↔ WBTC) |
| `hbar_swap_engine_v2.py` | V2 engine for HBAR swaps (from CL12) |
| `hbar_swap_engine_v1.py` | Legacy V1 HBAR swaps |
| `erc20_to_hts_wrapper.py` | ERC20 → HTS unwrapping |
| `saucerswap_v2_client.py` | Low-level V2 client (quoter, path encoding) |
| `approve_hts_token.js` | Node.js script for HTS approvals |
| `tokens.py` | Core token definitions (used by bot) |
| `token_whitelist.py` | **NEW** Curated whitelist of verified tokens |

---

## Bridge Infrastructure on Hedera

### How Tokens Get to Hedera

Tokens on Hedera come from different sources via different bridges:

| Bridge | Tokens | How It Works |
|--------|--------|--------------|
| **Hashport** | LINK, QNT, AVAX, MATIC, DOVU, LCX | Enterprise-grade bridge from Ethereum/EVM chains. Tokens get `[hts]` suffix. |
| **LayerZero/Stargate** | WBTC, WETH | Cross-chain messaging protocol. Tokens get `HTS-` prefix. |
| **Axelar** | Various | Squid Router integration. Less common on Hedera. |
| **Circle (Native)** | USDC | Native issuance by Circle. No bridging needed. |
| **Native** | SAUCE, HBARX, GRELF, etc. | Born on Hedera. No bridging. |

### Bridge Token Naming Conventions

```
Hashport:    LINK[hts], WMATIC[hts], WAVAX[hts], DOV[hts], LCX[hts]
LayerZero:   HTS-WBTC, HTS-WETH
Native:      USDC, SAUCE, HBARX, WHBAR
```

### Why This Matters for Swaps

1. **Token IDs differ from symbols** - Always use Hedera ID (0.0.XXXXX), not symbol
2. **Decimals vary** - USDC=6, most bridged=8, WETH=8 (not 18!)
3. **Approvals differ** - HTS tokens need Hedera SDK, ERC20 can use standard approve

---

## Token Whitelist

See `token_whitelist.py` for the curated list of verified tokens.

**Categories:**
- **Stablecoins**: USDC, USDT
- **Major Crypto**: WBTC, WETH, AVAX, MATIC
- **DeFi**: LINK, LCX
- **Hedera Native**: SAUCE, XSAUCE, HBARX
- **Hedera Ecosystem**: DOVU, GRELF, BONZO, SENTX

**Usage:**
```python
from token_whitelist import get_token, is_whitelisted, get_fee_tier

# Check if token is safe to trade
if is_whitelisted("LINK"):
    token = get_token("LINK")
    print(f"Hedera ID: {token.hedera_id}")
    print(f"Decimals: {token.decimals}")
    
# Get appropriate fee tier for a pair
fee = get_fee_tier("USDC", "WBTC")  # Returns 1500
```

---

## Troubleshooting

### "Transaction reverted" on swap
1. Check deadline is in **milliseconds**
2. Check approval exists (use Hedera SDK, not EVM)
3. Check gas is sufficient (2M for multicall)
4. Check path encoding uses Hedera IDs

### "Could not transact with contract"
1. RPC connection issue - try fallback RPC
2. Wrong contract address
3. ABI mismatch

### Approval reverts
1. **DO NOT use EVM approve() for HTS tokens**
2. Use `approve_hts_token.js` with Hedera SDK
3. Ensure HEDERA_ACCOUNT_ID is set correctly

---

## Working Example: USDC → Native HBAR

```python
from saucerswap_v2_engine import SaucerSwapV2Engine

engine = SaucerSwapV2Engine()

result = engine.swap(
    token_in_id="0.0.456858",  # USDC
    token_out_id="HBAR",       # Native HBAR
    amount=1.0,                # 1 USDC
    decimals_in=6,
    decimals_out=8,
    slippage=0.02              # 2%
)

if result.success:
    print(f"✅ Swapped! TX: {result.tx_hash}")
    print(f"   Received: {result.amount_out} HBAR")
```

---

## History

- **Jan 2026**: Fixed USDC→HBAR swap by discovering deadline must be milliseconds
- **Jan 2026**: Discovered HTS approvals require Hedera SDK, not EVM
- **CL12 repo**: Contains the working V2 engine implementation

---

*Last updated: January 9, 2026*
