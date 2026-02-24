# Hedera AccountBalanceQuery Deprecation

**Status:** Informational ⚠️  
**Date:** 2025-02-23  
**Deprecation Target:** July 2026 Consensus Node release (v0.75)  
**Pacman Impact:** ✅ **NO IMPACT** - Pacman does not use `AccountBalanceQuery`

---

## Executive Summary

Hedera is deprecating the `AccountBalanceQuery` RPC method to improve network scalability. The deprecation timeline:

- **Feb–Apr 2026:** 40,000 rps (unchanged)
- **May 2026:** 20,000 rps (throttles begin)
- **Jun 2026:** 10,000 rps
- **Jul 2026:** Removed (all requests will fail)

Migration path: Use **Hedera Mirror Node REST API** for account balance lookups.

---

## Pacman Current Implementation

### ✅ Safe from Deprecation

Pacman **does not** use `CryptoGetAccountBalanceQuery` or any Hedera `AccountBalanceQuery` method. Balance lookups are performed via:

1. **HBAR (native):** `w3.eth.get_balance(eoa)` - Standard EVM RPC call
2. **HTS Tokens:** `token.functions.balanceOf(account).call()` - Direct ERC20 contract call
3. **Batch optimization:** Multicall aggregates token balance queries into single RPC calls

These methods use the standard EVM JSON-RPC interface (`eth_call`) and are completely unaffected by the Hedera consensus node changes.

### Relevant Code

- **HBAR balance:** `src/balances.py:get_balances()` → `w3.eth.get_balance()`
- **Token balances:** `lib/saucerswap.py:get_token_balance()` → ERC20 `balanceOf()`
- **Multicall batching:** `lib/multicall.py` reduces 30+ calls to 1-2 chunks

---

## Monitoring & Readiness

While Pacman is currently safe, consider adding Mirror Node API as a **future enhancement**:

- Mirror Node provides REST endpoints for account/balance queries
- Could be used for analytics, historical balances, or off-chain monitoring
- Not required for live trading operations

### Mirror Node API Example (for reference)

```bash
GET https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{accountId}/balances
```

Response includes all token balances in a single REST call.

---

## Action Items

- [x] **Verify** current balance query methods (complete: no AccountBalanceQuery used)
- [ ] **Monitor** Hedera's deprecation communications for any breaking changes to Mirror Node
- [ ] **Consider** adding Mirror Node API calls for wallet overview page (non-critical)
- [ ] **Document** any future RPC method changes in this file

---

## Technical Context

Pacman's architecture deliberately avoids Hedera-specific query methods in favor of:

- **EVM compatibility:** Works on any EVM chain (Hedera, Ethereum, etc.)
- **Standard tooling:** Uses web3.py and contract ABIs directly
- **No vendor lock-in:** Can switch to different Hedera clients without rewrites

This design decision protects us from Hedera-specific breaking changes like the AccountBalanceQuery deprecation.

---

## References

- Hedera Improvement Proposal (HIP): TBD
- Mirror Node API Docs: https://docs.hedera.com/guides/mainnet/mirror-node-api
- SaucerSwap V2 Contracts: `0.0.3949424` (quoter), `0.0.3949434` (router)
