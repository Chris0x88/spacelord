# SaucerSwap V2 Swap Types Reference
## Documentation for Future Implementation

This document describes the different swap types available on SaucerSwap V2 and their implementation status.

---

## ✅ WORKING: Token ↔ Token (HTS to HTS)

**Status:** Production-ready, battle-tested

**Current Implementation:**
- `swap_engine.py` - Uses `exactInput` with encoded path
- `tokens.py` - Token and SwapPair definitions

**Supported Pairs:**
| Pair | Direction | Status |
|------|-----------|--------|
| USDC → WBTC | Buy BTC | ✅ Working |
| WBTC → USDC | Sell BTC | ✅ Working |

**Method:** `exactInput(path, recipient, deadline, amountIn, amountOutMinimum)`

---

## 🔮 FUTURE: Native HBAR → HTS Token

**Status:** Documented, not yet implemented

**SaucerSwap Official Pattern:**
```javascript
// From SaucerSwap V2 Docs: "Swap Exact HBAR for Tokens"

// 1. Build exactInput params with WHBAR in path
const params = {
  path: routeDataWithFee,        // e.g., WHBAR → USDC
  recipient: userAddress,
  deadline: deadline,
  amountIn: inputTinybar,
  amountOutMinimum: outputAmountMin
};

// 2. Encode swap + refundETH into multicall
const swapEncoded = abiInterfaces.encodeFunctionData('exactInput', [params]);
const refundHBAREncoded = abiInterfaces.encodeFunctionData('refundETH');
const multiCallParam = [swapEncoded, refundHBAREncoded];
const encodedData = abiInterfaces.encodeFunctionData('multicall', [multiCallParam]);

// 3. Execute with payable amount
const response = await new ContractExecuteTransaction()
  .setPayableAmount(Hbar.from(inputTinybar, HbarUnit.Tinybar))
  .setContractId(swapRouterContractId)
  .setGas(gasLim)
  .setFunctionParameters(encodedDataAsUint8Array)
  .execute(client);
```

**Key Points:**
- Path starts with WHBAR address
- Use `multicall` to bundle swap + `refundETH`
- Send native HBAR as payable amount
- `refundETH` returns unused HBAR if input exceeds actual swap

---

## 🔮 FUTURE: HTS Token → Native HBAR

**Status:** Documented, not yet implemented

**SaucerSwap Official Pattern:**
```javascript
// From SaucerSwap V2 Docs: "Swap Exact Tokens for HBAR"

// 1. Build exactInput params - IMPORTANT: recipient is ROUTER, not user!
const params = {
  path: routeDataWithFee,        // e.g., USDC → WHBAR
  recipient: swapRouterAddress,   // Router receives WHBAR first!
  deadline: deadline,
  amountIn: inputAmount,
  amountOutMinimum: outputTinybarMin
};

// 2. Encode swap + unwrapWHBAR into multicall
const swapEncoded = abiInterfaces.encodeFunctionData('exactInput', [params]);
const unwrapEncoded = abiInterfaces.encodeFunctionData('unwrapWHBAR', [0, userAddress]);
const multiCallParam = [swapEncoded, unwrapEncoded];
const encodedData = abiInterfaces.encodeFunctionData('multicall', [multiCallParam]);

// 3. Execute (no payable amount needed)
const response = await new ContractExecuteTransaction()
  .setContractId(swapRouterContractId)
  .setGas(gasLim)
  .setFunctionParameters(encodedDataAsUint8Array)
  .execute(client);
```

**Key Points:**
- Path ends with WHBAR address
- **recipient = router address** (NOT user) for swap step
- Use `multicall` to bundle swap + `unwrapWHBAR`
- `unwrapWHBAR(0, userAddress)` converts WHBAR to native HBAR and sends to user

---

## 🔮 FUTURE: Memejob Trading

**Status:** To be integrated from HederaAgentKit

**Source Files Needed:**
- From `CL10-HederaAgentKit_with_memejob_connector/hedera-agent-kit-js`
- Memejob connector module
- Token association utilities

**Implementation Notes:**
- Requires token association before receiving HTS tokens
- May have different patterns for memecoin pools
- Follow SaucerSwap docs precisely for each swap type

---

## Contract Addresses (Mainnet)

| Contract | Hedera ID | EVM Address |
|----------|-----------|-------------|
| Quoter V2 | 0.0.3949424 | 0x00...003c4380 |
| Router V2 | 0.0.3949434 | 0x00...003c437A |
| WHBAR | 0.0.1456986 | 0x00...00163b8a |

---

## Implementation Checklist for Future Swaps

### HBAR → Token
- [ ] Implement WHBAR path encoding
- [ ] Implement multicall with exactInput + refundETH
- [ ] Handle payable transaction
- [ ] Test with small amounts

### Token → HBAR  
- [ ] Implement WHBAR path encoding
- [ ] Implement multicall with exactInput + unwrapWHBAR
- [ ] Handle router as intermediate recipient
- [ ] Test with small amounts

---

## ⚠️ Important Notes

1. **DO NOT modify `swap_engine.py`** - it's working for USDC↔WBTC
2. **Each swap type is specific** - follow SaucerSwap docs exactly
3. **Test with minimal amounts** before production use
4. **Token association required** for receiving new HTS tokens
