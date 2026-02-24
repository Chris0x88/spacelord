# HTS Token Approval Bug — Wrapper Contract Specific

**Status:** 🚨 BLOCKING (for wrap/unwrap operations)  
**Created:** 2026-02-24  
**Last Updated:** 2026-02-25  
**Severity:** Critical — Prevents all **wrap/unwrap** operations (variant conversions)

---

## Problem Summary

Wrap and unwrap transactions (converting between HTS and ERC20 variants via the wrapper contract `0.0.9675688`) fail during the approval step with:

```
Transaction: <hash>
Error: Approval failed on-chain
Gas Used: ~980k / 1M limit (98% utilization)
```

The root cause is using standard ERC20 `approve()` for HTS tokens when the spender is the **wrapper contract**. The wrapper requires Hedera's HTS precompile `grantTokenApproval()`.

---

## ⚠️ Important Clarification: Not All HTS Swaps Are Affected

**This bug does NOT affect regular swaps** (e.g., `USDC → WBTC_HTS`) via the SaucerSwap Router. Those work fine.

**Evidence:**
- Successful execution: `execution_records/exec_20260220_015932_USDC_to_WBTC_HTS.json` (USDC → WBTC_HTS)
- Failed executions: `WBTC_HTS → WBTC_LZ` (wrap/unwrap via wrapper)

The difference is the **spender**:
- Router (`0.0.3949434`) as spender → ✅ Approvals work (likely uses EVM approve for HTS tokens successfully)
- Wrapper (`0.0.9675688`) as spender → ❌ Approvals fail (requires HTS precompile)

---

## Root Cause

When the token being approved is an **HTS token** (e.g., `0.0.10082597`) and the spender is the **wrapper contract** (`0.0.9675688`), Hedera's HTS precompile requires `grantTokenApproval()` instead of the standard EVM `approve()`.

The code currently uses:
```python
self.client.approve_token(token_id, amount, spender=WRAPPER_ID)
```
which always calls EVM `approve()`, regardless of token type or spender.

The wrapper contract's expectations differ from the router's.

---

## Affected Code Paths

| File | Lines | Purpose |
|------|-------|---------|
| `src/executor.py` | 744, 805 | `_execute_unwrap_step()` and `_execute_wrap_step()` call `approve_token(..., spender=WRAPPER_ID)` |
| `lib/saucerswap.py` | ~620 | `approve_token()` implements only standard EVM `approve()` |

**Transaction evidence:**
- Tx: `83de216bbab3518a691fe6a61f26c9c278a8224f4adc0f7d206f9dc4e51aa27f`
- Token: `0.0.10082597` (WBTC_HTS)
- Spender: `0.0.9675688` (Wrapper contract)
- Error occurs during approval, before the actual wrap/unwrap call

---

## Current System Behavior

- **Variant routing is automatic**: The router (`recommend_route`) detects wrap/unwrap pairs and returns a one-step route with `step_type="wrap"` or `"unwrap"`.
- **`convert` command removed**: Users now use `swap WBTC_LZ → WBTC_HTS` and the router adds the unwrap step automatically (commit `de4ea365`).
- **These automatic wrap/unwrap steps fail** due to the approval bug. The system attempts them, but they revert.

---

## Required Fix

### 1. Add HTS Precompile Approval Function

In `lib/saucerswap.py`:

```python
def approve_token_hts(self, token_id: str, spender: str, amount: int) -> dict:
    """
    Approve token for spending via HTS precompile.
    token_id: Hedera token ID (e.g., "0.0.10082597")
    spender: Account/contract ID (e.g., "0.0.9675688")
    amount: Amount in atomic units
    """
    HTS_PRECOMPILE = "0x0000000000000000000000000000000000000167"

    # ABI encode grantTokenApproval(token, spender, amount)
    # Need proper address conversion: Hedera IDs to 32-byte EVM format
    token_addr = hedera_id_to_evm_bytes32(token_id)  # new helper
    spender_addr = hedera_id_to_evm_bytes32(spender)

    abi_encoded = self.w3.codec.encode(
        ['address', 'address', 'uint256'],
        [token_addr, spender_addr, amount]
    )

    return self.w3.eth.call({
        "to": HTS_PRECOMPILE,
        "data": abi_encoded
    })
```

### 2. Update `approve_token()` or Create Wrapper-Specific Variant

Option A (token-type detection):
```python
def approve_token(self, token_id: str, spender: str, amount: int):
    # If spender is the wrapper and token is HTS, use precompile
    if spender == WRAPPER_ID and self._is_hts_token(token_id):
        return self.approve_token_hts(token_id, spender, amount)
    else:
        # existing EVM approve logic
```

Helper to detect HTS tokens by format (`0.0.` prefix) or by metadata.

Option B (separate wrapper approval method):
- Create `approve_token_for_wrapper()` in executor that calls precompile directly
- Simpler: just make `approve_token` smart enough

### 3. Comprehensive Testing

- HTS approval to wrapper (precompile) success
- ERC20 approval to router (EVM approve) unchanged
- Token detection edge cases

---

## Impact

- **Pacman:** All wrap/unwrap operations are currently broken (variant conversions).
- **btc_rebalancer2:** Same bug if it uses identical approval logic.
- **Agents:** Cannot execute `swap WBTC_LZ → WBTC_HTS` or similar variant conversions.

---

## Workarounds

**None currently.** The code cannot execute HTS approvals to the wrapper. Users must avoid variant conversions until fixed.

---

## Related References

- `docs/PRODUCT_SPEC.md` — variant routing design
- `docs/AI_AGENT_GUIDE.md` — agent instructions (updated 2026-02-25)
- `docs/SKILLS.md` — skill spec (updated 2026-02-25)
- Commit `de4ea365` — removal of `convert` command (UI simplification)
- `src/executor.py::_execute_wrap_step()` / `_execute_unwrap_step()` — failing code paths

---

## Next Steps

1. Implement `approve_token_hts()` with correct 32-byte address encoding for Hedera IDs
2. Add token type detection or conditional routing in `approve_token`
3. Update wrap/unwrap steps to use the correct approval method
4. Write unit tests for HTS approval path
5. End-to-end test on testnet
6. Update docs to clarify the scope (only wrapper, not all HTS)

---

**🚨 DO NOT DEPLOY** to production until HTS approval to wrapper is verified on testnet.
