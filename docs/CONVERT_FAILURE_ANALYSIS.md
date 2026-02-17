# CONVERT Command Failure Analysis

**Date:** 2026-02-17  
**Status:** ❌ UNRESOLVED  
**Last Attempt:** `e35a539295c3baae9eb6c8f09e3f7f478a0249ca972b8de8baaba5f3f8060f69`

---

## Executive Summary

The `convert` command (wrap/unwrap between WBTC_HTS ↔ WBTC_EVM) **continues to fail on-chain**. Despite multiple attempts with gas limit increases and ABI corrections, the wrapper contract transaction reverts every time.

**Core Issue:** AI agents cannot reliably execute the Hedera ERC20Wrapper contract interaction. The failure appears to be at the contract level, not the code level.

---

## What Was Attempted

### 1. Initial Implementation (2026-02-16)
- Created `bitcoin_converter.py` with `UniversalSwapper` class
- Added `WRAPPER_CONTRACT_ID = "0.0.9675688"` (SaucerSwap ERC20Wrapper)
- Implemented `wrap()` and `unwrap()` methods
- Used HIP-426 standard ABI for wrap/unwrap functions

### 2. Gas Limit Increase
- Previous attempts used 1,000,000 gas (hit 98.4% utilization → suspected OOG)
- Increased to 2,000,000 gas
- **Result:** Still fails

### 3. Latest Attempt (2026-02-17 14:02)
```bash
convert 0.0001 WBTC_LEGACY to WBTC_EVM
```

**Transaction:** `e35a539295c3baae9eb6c8f09e3f7f478a0249ca972b8de8baaba5f3f8060f69`

**Flow executed:**
1. ✅ Associate HTS token (0.0.1055483) - success
2. ✅ Check/confirm approval - allowance sufficient (499,998,924)
3. ❌ Call wrapper contract `wrap(address, uint256)` - **FAILED**

---

## Technical Analysis

### Current Code (bitcoin_converter.py)

```python
WRAPPER_CONTRACT_ID = "0.0.9675688"
# EVM Address: 0x000000000000000000000000000000000093A3A8

WRAPPER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "receiver", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "wrap",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # ... unwrap similarly
]
```

### Possible Failure Reasons

| # | Hypothesis | Evidence | Status |
|---|------------|----------|--------|
| 1 | **Wrong wrapper contract** | ERC20Wrapper (0.0.9675688) may be for HBAR only | 🔶 Likely |
| 2 | **Wrong function name** | Might need `deposit()` instead of `wrap()` | 🔶 Possible |
| 3 | **Wrong ABI** | Redirect contract may need different interface | 🔶 Possible |
| 4 | **Missing token approval** | Wrapper needs approval on the *source* token | 🔶 Possible |
| 5 | **HTS token not supported** | WBTC_HTS may not be ERC20Wrapper-compatible | 🔶 Likely |
| 6 | **Network/node issue** | Mirror node or RPC returning stale data | ❌ Unlikely |

### Key Observation

The **ERC20Wrapper contract (0.0.9675688)** on Hedera is traditionally used for:
- WHBAR (Wrapped HBAR) - the canonical wrapped token
- MAYBE other SaucerSwap pairs

It is **NOT necessarily designed for arbitrary HTS tokens** like WBTC_HTS. The WBTC variants may have their own wrapping mechanism.

---

## WBTC Token Addresses

| Token | Hedera ID | EVM Address | Type |
|-------|-----------|-------------|------|
| WBTC_HTS (Native) | 0.0.10082597 | 0x...0001f0d9 | HTS Redirect |
| WBTC_LZ (Legacy) | 0.0.1055483 | 0x...0101afb | HTS Redirect |
| WBTC_EVM (LayerZero) | N/A | 0xd7d4d91d64a6061fa00a94e2b3a2d2a5fb677849 | Pure ERC-20 |

---

## What AI Agents Cannot Solve

### The Fundamental Problem

Hedera's token system uses **Redirect Contracts** (HIP-206). When you call `wrap()` on the ERC20Wrapper, you're calling a contract that expects:

1. The wrapper to have **approval** to spend your HTS tokens
2. The HTS token to be **compatible** with the wrapper's wrapping logic
3. The wrapper contract to have a **deposit/wrap function** that accepts your specific token

**The SaucerSwap ERC20Wrapper may simply not support wrapping WBTC tokens.**

### Why This Is Hard

1. **No source code access** - We cannot see the actual Solidity on the wrapper contract
2. **No error messages** - Hedera returns `TRANSACTION_REVERTED` without details
3. **Limited debugging** - Cannot easily inspect contract state
4. **HIP-426 confusion** - The standard says `wrap()` exists, but implementation varies

---

## Alternative Approaches Tried

### ❌ Failed: Direct Wrapper Call
```python
self.wrapper_contract.functions.wrap(self.account_address, amount)
```

### ❌ Failed: HTS Precompile Association
Already associated, verified via Mirror Node

### ❌ Failed: ERC20 Approval on Wrapper
The code does check approval, but wrapper may need different approval pattern

---

## Potential Solutions (Not Yet Tested)

### Option 1: Find the Correct Wrapper
- Research which SaucerSwap wrapper handles WBTC specifically
- There may be a token-specific wrapper contract
- Or use the **SaucerSwap V2 Router** which handles routing internally

### Option 2: Use Router-Mediated Wrap
- Instead of calling wrapper directly, route through SaucerSwap V2
- The router may have internal logic to handle HTS ↔ EVM swaps
- This is how SaucerSwap UI likely does it

### Option 3: Manual Bridge via Third Party
- Use a centralized bridge or another DeFi protocol
- Outside scope of Pacman

### Option 4: Accept Limitation
- The convert command may be fundamentally blocked by Hedera's architecture
- Document as "Not Supported" and focus on swap functionality

---

## Conclusion

**AI agents cannot reliably execute Hedera ERC20Wrapper operations because:**

1. The contract interface is opaque (redirect contracts)
2. Error messages don't indicate *why* it failed
3. The specific wrapper (0.0.9675688) may not support WBTC tokens
4. There's no way to introspect the contract's actual requirements

**Recommendation:** 
- Stop trying to make the direct wrapper call work
- Investigate SaucerSwap V2 Router as an alternative path
- If that fails too, document convert/wrap as "Hedera Architecture Limitation"

---

## Appendices

### A. Related Files
- `src/bitcoin_converter.py` - Current implementation
- `docs/hts_wrap_debug_report.md` - Previous debugging effort
- `docs/hts_wrap_debug_report.md` - Gas limit analysis

### B. Transaction Hashes
| Date | Hash | Operation | Result |
|------|------|-----------|--------|
| 2026-02-16 | f40ec4e6f... | approve() | ❌ Reverted |
| 2026-02-17 | e35a539295... | wrap() | ❌ Reverted |

### C. Gas Analysis
- **Last gas used:** 2,000,000 (increased from 1,000,000)
- **Result:** Still reverts - not a gas limit issue
