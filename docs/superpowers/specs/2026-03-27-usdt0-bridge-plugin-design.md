# USDT0 Bridge Plugin Design

**Date:** 2026-03-27
**Status:** Draft
**Goal:** Bridge USDT0 from Hedera to Arbitrum via LayerZero OFT. Ship as both a Hedera Agent Kit (HAK) TypeScript plugin and a Space Lord Python integration.

---

## 1. Overview

Two deliverables from one design:

1. **`hak-usdt0-bridge-plugin`** — TypeScript npm package conforming to the Hedera Agent Kit v3 plugin interface. Clean, unopinionated SDK. Any agent framework can use it.
2. **Space Lord integration** — Python module (`lib/bridge_usdt0.py`) that calls OFT contracts directly via `web3.py` (same pattern as SaucerSwap). Adds governance limits, CLI command, training data logging.

Both share the same contract addresses, ABI, and bridging logic — just different languages.

## 2. Chain & Contract Details

### LayerZero Endpoint IDs

| Chain | EID | Chain ID |
|-------|-----|----------|
| Hedera | 30285 | 295 |
| Arbitrum | 30110 | 42161 |

### USDT0 Contract Addresses

| Chain | Token Address | OFT Address |
|-------|--------------|-------------|
| Hedera | `0x00000000000000000000000000000000009Ce723` | `0xe3119e23fC2371d1E6b01775ba312035425A53d6` |
| Arbitrum | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | `0x14E4A1B13bf7F943c8ff7C51fb60FA964A298D92` |

### Hedera-Specific Notes

- Hedera token address `0x...009Ce723` is a long-zero HTS token address. Convert: `0x009Ce723` = decimal `642851` = Hedera token ID `0.0.642851`.
- USDT0 uses **6 decimals** on all chains.
- Hedera JSON-RPC relay normalizes gas values to 18 decimals (EVM compat), but token amounts stay at 6 decimals.
- Always use `self.eoa` (ECDSA alias) for contract calls — long-zero sender addresses cause reverts.

## 3. Bridging Flow (Technical)

### OFT `send()` Sequence

```
1. Check USDT0 balance on Hedera (ERC20 balanceOf)
2. Check existing allowance (ERC20 allowance)
3. If allowance < amount: approve OFT contract to spend USDT0
4. Build SendParam:
   {
     dstEid: 30110,                    // Arbitrum
     to: bytes32(recipientAddress),    // padded to 32 bytes
     amountLD: amountInSmallestUnit,   // 6 decimals
     minAmountLD: 0,                   // set after quoteOFT
     extraOptions: "0x",
     composeMsg: "0x",
     oftCmd: "0x"
   }
5. Call quoteOFT(sendParam) → get minAmountLD from oftReceipt
6. Update sendParam.minAmountLD with oftReceipt value
7. Call quoteSend(sendParam, false) → get MessagingFee {nativeFee, lzTokenFee}
8. Call send(sendParam, messagingFee, refundAddress) with msg.value = nativeFee
9. Return tx hash + LayerZero message GUID
```

### Key Contract Functions (OFT ABI)

```solidity
// Read-only
function quoteOFT(SendParam calldata) external view returns (OFTLimit, OFTFeeDetail[], OFTReceipt);
function quoteSend(SendParam calldata, bool payInLzToken) external view returns (MessagingFee);

// State-changing
function send(SendParam calldata, MessagingFee calldata, address refundAddress) external payable returns (MessagingReceipt, OFTReceipt);

// Structs
struct SendParam {
    uint32 dstEid;
    bytes32 to;
    uint256 amountLD;
    uint256 minAmountLD;
    bytes extraOptions;
    bytes composeMsg;
    bytes oftCmd;
}

struct MessagingFee {
    uint256 nativeFee;
    uint256 lzTokenFee;
}
```

## 4. HAK TypeScript Plugin (`hak-usdt0-bridge-plugin`)

### Plugin Interface

Follows the Hedera Agent Kit v3 plugin pattern:

```typescript
export class USDT0BridgePlugin {
  name = "usdt0-bridge";
  description = "Bridge USDT0 between Hedera and other chains via LayerZero";

  getTools(): Tool[] {
    return [
      usdt0GetSupportedChains,
      usdt0QuoteBridge,
      usdt0Bridge,
      usdt0CheckBridgeStatus,
    ];
  }
}
```

### Tools

#### `usdt0_get_supported_chains`
- **Input:** none
- **Output:** `{ chains: [{ name, eid, chainId, tokenAddress, oftAddress }] }`
- **Description:** Returns all supported chains with their contract addresses.

#### `usdt0_quote_bridge`
- **Input:** `{ amount: number, sourceChain: string, destChain: string }`
- **Output:** `{ estimatedReceived: string, nativeFee: string, nativeFeeUsd: string, minReceived: string }`
- **Description:** Quotes the bridge cost without executing. Calls `quoteOFT()` + `quoteSend()`.

#### `usdt0_bridge`
- **Input:** `{ amount: number, sourceChain: string, destChain: string, recipientAddress: string }`
- **Output:** `{ success: boolean, txHash: string, lzMessageGuid: string, amountSent: string, estimatedArrival: string }`
- **Description:** Executes the full bridge: approve → quoteOFT → quoteSend → send.

#### `usdt0_check_bridge_status`
- **Input:** `{ txHash: string }` or `{ lzMessageGuid: string }`
- **Output:** `{ status: "pending" | "inflight" | "delivered" | "failed", srcTxHash, dstTxHash }`
- **Description:** Checks LayerZero message delivery via the LayerZero Scan API (`https://scan.layerzero.network/api`).

### Directory Structure

```
hak-usdt0-bridge-plugin/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts                # Re-exports plugin class
│   ├── plugin.ts               # USDT0BridgePlugin class
│   ├── tools/
│   │   ├── get-supported-chains.ts
│   │   ├── quote-bridge.ts
│   │   ├── bridge.ts
│   │   └── check-bridge-status.ts
│   ├── contracts/
│   │   ├── oft-abi.ts          # OFT contract ABI (minimal — only functions we call)
│   │   ├── erc20-abi.ts        # Standard ERC20 ABI (balanceOf, approve, allowance)
│   │   └── addresses.ts        # Chain → {eid, chainId, token, oft} mapping
│   └── types.ts                # SendParam, MessagingFee, BridgeResult, etc.
├── tests/
│   ├── quote.test.ts           # Mock contract calls, verify param encoding
│   ├── bridge.test.ts          # Mock full flow, verify tx construction
│   └── integration.test.ts     # Testnet bridge (manual, not CI)
└── README.md
```

### Dependencies

- `ethers` v6 (standard in HAK ecosystem)
- `@hashgraph/sdk` (for Hedera-specific address resolution if needed)
- No other dependencies — keep it minimal.

## 5. Space Lord Python Integration

### New Files

| File | Purpose |
|------|---------|
| `lib/bridge_usdt0.py` | Core bridge logic using web3.py |
| `cli/commands/bridge.py` | CLI command handler |
| `data/abi/oft_abi.json` | OFT contract ABI (subset) |

### `lib/bridge_usdt0.py`

Uses the same `web3.py` + contract interaction pattern as `lib/saucerswap.py`:

```python
class USDT0Bridge:
    """Bridge USDT0 from Hedera to other chains via LayerZero OFT."""

    CHAINS = {
        "arbitrum": {
            "eid": 30110,
            "chain_id": 42161,
            "token": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "oft": "0x14E4A1B13bf7F943c8ff7C51fb60FA964A298D92",
        },
    }

    HEDERA_USDT0_TOKEN = "0x00000000000000000000000000000000009Ce723"
    HEDERA_USDT0_OFT = "0xe3119e23fC2371d1E6b01775ba312035425A53d6"
    HEDERA_USDT0_HEDERA_ID = "0.0.642851"
    USDT0_DECIMALS = 6

    # Required executor attributes: w3, eoa, config.private_key, chain_id, network
    def __init__(self, executor):
        self.executor = executor
        self.w3 = executor.w3
        self.oft_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.HEDERA_USDT0_OFT),
            abi=self._load_abi()
        )
        self.token_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.HEDERA_USDT0_TOKEN),
            abi=ERC20_ABI
        )

    def quote(self, amount: float, dest_chain: str) -> dict:
        """Quote bridge cost without executing."""
        # ... quoteOFT + quoteSend calls

    def bridge(self, amount: float, dest_chain: str, recipient: str) -> dict:
        """Execute bridge: approve → quote → send."""
        # ... full flow with private key reveal/delete pattern

    def check_status(self, tx_hash: str) -> dict:
        """Check LayerZero message delivery status."""
        # ... call LZ scan API
```

### `cli/commands/bridge.py`

```python
def cmd_bridge(app, args):
    """
    Bridge USDT0 to another chain via LayerZero.

    Usage: bridge <amount> USDT0 <chain> [--to <address>]
    Example: bridge 50 USDT0 arbitrum --to 0xYourArbAddress
    """
    # 1. Parse args
    # 2. Governance checks (max_bridge_usd, allowed_chains, min amount)
    # 3. Validate destination address
    # 4. Quote and display fee
    # 5. Confirm with _safe_input()
    # 6. Execute bridge
    # 7. Log to training_data
    # 8. Print result
```

### Governance Additions (`data/governance.json`)

```json
"bridging": {
    "max_bridge_usd": 100.00,
    "allowed_chains": ["arbitrum"],
    "min_bridge_amount_usd": 1.00,
    "counts_toward_daily_limit": true
}
```

Bridge amounts count toward the existing `max_daily_usd` limit. If a user swaps $90 and bridges $50 in the same day, the bridge is blocked (total $140 > $100 daily limit).

### Bridge Destination Whitelist (`data/settings.json`)

Cross-chain bridges require a whitelisted destination, extending the existing whitelist pattern:

```json
"bridge_whitelist": [
    {
        "chain": "arbitrum",
        "address": "0xYourArbAddress",
        "label": "My Arbitrum Wallet"
    }
]
```

This is enforced in `lib/bridge_usdt0.py` before any contract call. The `--to` address must match a `bridge_whitelist` entry for the target chain. This parallels `transfer_whitelist` for on-chain transfers — wallet whitelists remain the most important safety feature.

**Note:** Bridge destinations are EVM addresses (0x..., 42 chars), not Hedera IDs. This is the one place where EVM addresses are required, since the destination is on an EVM chain. Hedera IDs (0.0.xxx) are rejected as bridge destinations.

### CLI Registration (`cli/main.py`)

Add to COMMANDS dict:
```python
"bridge": cmd_bridge,
```

### Training Data Logging

Every bridge operation logs to `training_data/live_executions.jsonl`:
```json
{
    "type": "bridge",
    "protocol": "layerzero_usdt0",
    "amount": 50.0,
    "source_chain": "hedera",
    "dest_chain": "arbitrum",
    "recipient": "0x...",
    "tx_hash": "0x...",
    "lz_message_guid": "0x...",
    "native_fee_hbar": 0.15,
    "timestamp": "2026-03-27T...",
    "account": "0.0.10289160"
}
```

## 6. Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Insufficient USDT0 balance | `balanceOf()` < amount | "Insufficient USDT0 balance. Have: X, Need: Y" |
| Insufficient HBAR for LZ fee + gas reserve | `hbar_balance < nativeFee + gas_estimate + min_hbar_reserve` | "Need X HBAR (Y fee + Z gas + 5 reserve), have W" |
| Amount exceeds per-tx limit | `amount > governance.bridging.max_bridge_usd` | "Bridge amount $X exceeds limit of $Y" |
| Amount exceeds daily limit | `daily_total + amount > governance.safety_limits.max_daily_usd` | "Bridge would exceed daily limit. Used: $X, Limit: $Y" |
| Destination not whitelisted | `recipient not in bridge_whitelist[chain]` | "Address not in bridge whitelist. Add it first." |
| Destination is Hedera ID | `recipient.startswith("0.0.")` | "Bridge destination must be an EVM address (0x...), not a Hedera ID" |
| Chain not in allowed list | `dest_chain not in governance.bridging.allowed_chains` | "Chain 'X' not in allowed list: [Y]" |
| Invalid EVM address | Not 0x + 40 hex chars | "Invalid EVM address: X" |
| OFT send() reverts | Transaction receipt status 0 | "Bridge transaction failed: [revert reason]" |
| LayerZero delivery timeout | Status "pending" after 15 minutes | "LayerZero delivery slow. Check: scan.layerzero.network" |
| LayerZero delivery fails | Status check returns "failed" | "LayerZero delivery failed. Funds safe — check LZ scan" |
| USDT0 token not associated | Contract call reverts | "USDT0 token not associated with account. Run: associate 0.0.642851" |

## 7. Security Considerations

- **Private key handling:** Same reveal/delete pattern as executor — `pk = reveal(); try: ...; finally: del pk`
- **No destination address fabrication:** Recipient must be explicitly provided, never defaulted
- **Governance enforcement:** All limits checked before any contract call
- **Allowance management:** Approve exact amount per transaction, not MAX_UINT256 (minimize exposure). Each bridge call issues its own approval if allowance is insufficient. Extra gas cost is acceptable for safety.
- **Refund address:** Set to `self.eoa` so excess LZ fees return to sender
- **Amount precision:** User-facing amounts are `float` but converted to raw units via `int(amount * 10**6)` with truncation (matching `lib/saucerswap.py` pattern). All contract calls use integer raw amounts.
- **Bridge in `agent_rules.never_auto_execute`:** Add `"bridge"` to governance.json `agent_rules.never_auto_execute` — bridging is irreversible cross-chain and must require explicit user command.

## 8. Testing Strategy

### HAK Plugin (TypeScript)
- Unit tests: Mock ethers contract calls, verify SendParam encoding, verify fee calculation
- Integration test (manual): Testnet bridge with small amount

### Space Lord (Python)
- Unit tests: Governance checks, argument parsing, whitelist enforcement, error cases
- Integration test: Real execution against Hedera testnet contracts (NOT `simulate_mode` — we never simulate, per CLAUDE.md). Testnet uses real transactions against testnet OFT contracts.
- Verify: Token association, approval, quote accuracy, send execution

### Manual Verification Checklist
- [ ] USDT0 token associated on Hedera account
- [ ] Quote returns reasonable fee (< 1 HBAR expected)
- [ ] Approval transaction succeeds
- [ ] Bridge transaction succeeds
- [ ] LayerZero scan shows message delivered
- [ ] USDT0 appears on Arbitrum recipient address

## 9. SKILL.md Update

Add bridge command documentation to SKILL.md so the OpenClaw agent knows the command exists:

```
## Bridge (Cross-Chain)
- `bridge <amount> USDT0 <chain>` — Bridge USDT0 to another chain via LayerZero
- `bridge status <tx_hash>` — Check bridge delivery status
- Supported chains: arbitrum
- Destination must be whitelisted in bridge_whitelist (data/settings.json)
- Counts toward daily transaction limit
```

## 10. LayerZero Status Checking

The `check_status` tool polls the LayerZero Scan API:
- **API:** `GET https://scan.layerzero.network/api/trpc/messages.list?input={"filters":{"srcTxHash":"0x..."}}`
- **Polling:** Not automatic. User calls `bridge status <tx_hash>` manually.
- **Expected delivery:** 30 seconds to 3 minutes for Hedera → Arbitrum.
- **Timeout guidance:** If status is still "pending" after 15 minutes, display warning with link to LayerZero scan UI.
- **No retry logic:** If delivery fails, funds are held by LayerZero protocol and can be recovered. Direct user to LayerZero scan.

## 11. Future Extensions (Not in v1)

- Arbitrum → Hedera (reverse bridge)
- Additional chains (Optimism, Polygon, HyperCore direct)
- Hyperliquid Bridge2 integration (Arbitrum USDC → Hyperliquid)
- XAUt0 / CNHt0 bridging (same OFT pattern, different tokens)
- Automatic USDT0 → USDC swap on Arbitrum after bridge

## 12. Downstream Context: Hyperliquid

After bridging USDT0 to Arbitrum, the user's next step is typically depositing into Hyperliquid:
- Hyperliquid accepts native USDC on Arbitrum via Bridge2 (min $5 deposit)
- USDT0 on Arbitrum would need to be swapped to native USDC first (e.g., via Uniswap)
- Alternatively, USDT0 can be bridged directly to HyperCore via the LayerZero Composer (future v2 feature)
- The Bridge2 contract on Arbitrum: `0x2df1c51e09aecf9cacb7bc98cb1742757f163df7`
