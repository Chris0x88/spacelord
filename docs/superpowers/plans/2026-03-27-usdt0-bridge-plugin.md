# USDT0 Bridge Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridge USDT0 from Hedera to Arbitrum via LayerZero OFT contracts. Deliver as both a Space Lord Python integration and a Hedera Agent Kit TypeScript npm plugin.

**Architecture:** Two independent codebases sharing the same contract addresses and ABI. The Python side uses web3.py (matching existing SaucerSwap patterns). The TypeScript side uses ethers v6 (matching HAK ecosystem). Space Lord adds governance, whitelisting, and training data on top.

**Tech Stack:** Python 3.14 + web3.py (Space Lord), TypeScript + ethers v6 (HAK plugin), LayerZero OFT v2 contracts, Hedera JSON-RPC relay

**Spec:** `docs/superpowers/specs/2026-03-27-usdt0-bridge-plugin-design.md`

---

## File Structure

### Space Lord (Python) — New Files

| File | Responsibility |
|------|---------------|
| `data/abi/oft.json` | OFT contract ABI (quoteOFT, quoteSend, send only) |
| `lib/bridge_usdt0.py` | Core bridge logic: quote, bridge, check_status |
| `cli/commands/bridge.py` | CLI handler: parse args, governance checks, confirm, execute |
| `tests/test_bridge_usdt0.py` | Unit tests for bridge logic and governance |

### Space Lord (Python) — Modified Files

| File | Change |
|------|--------|
| `data/governance.json` | Add `bridging` section + `bridge` to `never_auto_execute` |
| `data/settings.json` | Add `bridge_whitelist` array |
| `cli/main.py:109-167` | Add `"bridge": cmd_bridge` to COMMANDS dict |
| `SKILL.md` | Add bridge command documentation |

### HAK Plugin (TypeScript) — New Directory

| File | Responsibility |
|------|---------------|
| `hak-usdt0-bridge-plugin/package.json` | npm package config |
| `hak-usdt0-bridge-plugin/tsconfig.json` | TypeScript config |
| `hak-usdt0-bridge-plugin/src/index.ts` | Re-export plugin class |
| `hak-usdt0-bridge-plugin/src/plugin.ts` | USDT0BridgePlugin class with tool registration |
| `hak-usdt0-bridge-plugin/src/types.ts` | SendParam, MessagingFee, BridgeResult types |
| `hak-usdt0-bridge-plugin/src/contracts/addresses.ts` | Chain → contract address mapping |
| `hak-usdt0-bridge-plugin/src/contracts/oft-abi.ts` | Minimal OFT ABI |
| `hak-usdt0-bridge-plugin/src/contracts/erc20-abi.ts` | Standard ERC20 ABI subset |
| `hak-usdt0-bridge-plugin/src/tools/get-supported-chains.ts` | List supported chains |
| `hak-usdt0-bridge-plugin/src/tools/quote-bridge.ts` | Quote bridge cost |
| `hak-usdt0-bridge-plugin/src/tools/bridge.ts` | Execute bridge transfer |
| `hak-usdt0-bridge-plugin/src/tools/check-bridge-status.ts` | Check LZ delivery status |
| `hak-usdt0-bridge-plugin/tests/quote.test.ts` | Quote tool unit tests |
| `hak-usdt0-bridge-plugin/tests/bridge.test.ts` | Bridge tool unit tests |
| `hak-usdt0-bridge-plugin/README.md` | Usage docs for npm |

---

## Task 1: OFT ABI and Contract Constants

**Files:**
- Create: `data/abi/oft.json`
- Verify: `data/abi/` directory exists (it does — contains erc20.json, quoter.json, etc.)

- [ ] **Step 1: Create the OFT ABI file**

Create `data/abi/oft.json` with the minimal ABI for the three functions we call. Only include `quoteOFT`, `quoteSend`, and `send` — nothing else.

```json
[
  {
    "inputs": [
      {
        "components": [
          { "name": "dstEid", "type": "uint32" },
          { "name": "to", "type": "bytes32" },
          { "name": "amountLD", "type": "uint256" },
          { "name": "minAmountLD", "type": "uint256" },
          { "name": "extraOptions", "type": "bytes" },
          { "name": "composeMsg", "type": "bytes" },
          { "name": "oftCmd", "type": "bytes" }
        ],
        "name": "_sendParam",
        "type": "tuple"
      }
    ],
    "name": "quoteOFT",
    "outputs": [
      {
        "components": [
          { "name": "minAmountLD", "type": "uint256" },
          { "name": "maxAmountLD", "type": "uint256" }
        ],
        "name": "oftLimit",
        "type": "tuple"
      },
      {
        "components": [
          { "name": "feeAmountLD", "type": "uint256" },
          { "name": "description", "type": "string" }
        ],
        "name": "oftFeeDetails",
        "type": "tuple[]"
      },
      {
        "components": [
          { "name": "amountSentLD", "type": "uint256" },
          { "name": "amountReceivedLD", "type": "uint256" }
        ],
        "name": "oftReceipt",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "components": [
          { "name": "dstEid", "type": "uint32" },
          { "name": "to", "type": "bytes32" },
          { "name": "amountLD", "type": "uint256" },
          { "name": "minAmountLD", "type": "uint256" },
          { "name": "extraOptions", "type": "bytes" },
          { "name": "composeMsg", "type": "bytes" },
          { "name": "oftCmd", "type": "bytes" }
        ],
        "name": "_sendParam",
        "type": "tuple"
      },
      { "name": "_payInLzToken", "type": "bool" }
    ],
    "name": "quoteSend",
    "outputs": [
      {
        "components": [
          { "name": "nativeFee", "type": "uint256" },
          { "name": "lzTokenFee", "type": "uint256" }
        ],
        "name": "msgFee",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "components": [
          { "name": "dstEid", "type": "uint32" },
          { "name": "to", "type": "bytes32" },
          { "name": "amountLD", "type": "uint256" },
          { "name": "minAmountLD", "type": "uint256" },
          { "name": "extraOptions", "type": "bytes" },
          { "name": "composeMsg", "type": "bytes" },
          { "name": "oftCmd", "type": "bytes" }
        ],
        "name": "_sendParam",
        "type": "tuple"
      },
      {
        "components": [
          { "name": "nativeFee", "type": "uint256" },
          { "name": "lzTokenFee", "type": "uint256" }
        ],
        "name": "_fee",
        "type": "tuple"
      },
      { "name": "_refundAddress", "type": "address" }
    ],
    "name": "send",
    "outputs": [
      {
        "components": [
          { "name": "guid", "type": "bytes32" },
          { "name": "nonce", "type": "uint64" },
          {
            "components": [
              { "name": "nativeFee", "type": "uint256" },
              { "name": "lzTokenFee", "type": "uint256" }
            ],
            "name": "fee",
            "type": "tuple"
          }
        ],
        "name": "msgReceipt",
        "type": "tuple"
      },
      {
        "components": [
          { "name": "amountSentLD", "type": "uint256" },
          { "name": "amountReceivedLD", "type": "uint256" }
        ],
        "name": "oftReceipt",
        "type": "tuple"
      }
    ],
    "stateMutability": "payable",
    "type": "function"
  }
]
```

- [ ] **Step 2: Verify ABI loads correctly**

```bash
cd /Users/cdi/Developer/pacman && python3 -c "
import json
from pathlib import Path
abi = json.loads((Path('data/abi/oft.json')).read_text())
print(f'Loaded {len(abi)} functions: {[f[\"name\"] for f in abi]}')
assert len(abi) == 3
assert {f['name'] for f in abi} == {'quoteOFT', 'quoteSend', 'send'}
print('OK')
"
```

Expected: `Loaded 3 functions: ['quoteOFT', 'quoteSend', 'send']` then `OK`

- [ ] **Step 3: Commit**

```bash
git add data/abi/oft.json
git commit -m "feat: add LayerZero OFT ABI for USDT0 bridging"
```

---

## Task 2: Governance and Settings Updates

**Files:**
- Modify: `data/governance.json`
- Modify: `data/settings.json`

- [ ] **Step 1: Add bridging section to governance.json**

Add after the existing `agent_rules` section (around line 70):

```json
"bridging": {
    "max_bridge_usd": 100.00,
    "allowed_chains": ["arbitrum"],
    "min_bridge_amount_usd": 1.00,
    "counts_toward_daily_limit": true
}
```

Also add `"bridge"` to the `agent_rules.never_auto_execute` array (around line 65).

- [ ] **Step 2: Add bridge_whitelist to settings.json**

Add to `data/settings.json` at the top level (next to `transfer_whitelist`):

```json
"bridge_whitelist": []
```

- [ ] **Step 3: Verify governance.json is valid JSON**

```bash
cd /Users/cdi/Developer/pacman && python3 -c "
import json
with open('data/governance.json') as f:
    g = json.load(f)
assert 'bridging' in g, 'Missing bridging section'
assert g['bridging']['max_bridge_usd'] == 100.0
assert 'bridge' in g['agent_rules']['never_auto_execute']
print('governance.json OK')
with open('data/settings.json') as f:
    s = json.load(f)
assert 'bridge_whitelist' in s, 'Missing bridge_whitelist'
print('settings.json OK')
"
```

Expected: Both print `OK`.

- [ ] **Step 4: Commit**

```bash
git add data/governance.json data/settings.json
git commit -m "feat: add bridging governance limits and bridge_whitelist"
```

---

## Task 3: Core Bridge Library (`lib/bridge_usdt0.py`)

**Files:**
- Create: `lib/bridge_usdt0.py`
- Reference: `lib/saucerswap.py:36-42` (ABI loading), `lib/saucerswap.py:67-76` (hedera_id_to_evm), `lib/transfers.py:121-150` (whitelist pattern), `src/executor.py:153-158` (pk reveal/delete)

- [ ] **Step 1: Write the test file first**

Create `tests/test_bridge_usdt0.py`:

```python
"""Tests for USDT0 bridge module."""
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestUSDT0BridgeValidation:
    """Test governance and whitelist validation (no contract calls)."""

    def _make_bridge(self):
        """Create a USDT0Bridge with mocked executor."""
        # Defer import so module load doesn't fail if web3 not in test env
        from lib.bridge_usdt0 import USDT0Bridge

        executor = MagicMock()
        executor.w3 = MagicMock()
        executor.eoa = "0x1234567890abcdef1234567890abcdef12345678"
        executor.config = MagicMock()
        executor.config.private_key = MagicMock()
        executor.config.simulate_mode = False
        executor.chain_id = 295
        executor.network = "mainnet"

        # Mock contract construction
        executor.w3.eth.contract.return_value = MagicMock()
        executor.w3.to_checksum_address = lambda x: x

        bridge = USDT0Bridge(executor)
        return bridge

    def test_invalid_chain_rejected(self):
        bridge = self._make_bridge()
        result = bridge.bridge(50.0, "polygon", "0xabc123")
        assert not result["success"]
        assert "not in allowed list" in result["error"].lower() or "not allowed" in result["error"].lower()

    def test_hedera_id_rejected_as_destination(self):
        bridge = self._make_bridge()
        result = bridge.bridge(50.0, "arbitrum", "0.0.12345")
        assert not result["success"]
        assert "hedera id" in result["error"].lower() or "evm address" in result["error"].lower()

    def test_invalid_evm_address_rejected(self):
        bridge = self._make_bridge()
        result = bridge.bridge(50.0, "arbitrum", "not-an-address")
        assert not result["success"]
        assert "invalid" in result["error"].lower()

    def test_amount_below_minimum_rejected(self):
        bridge = self._make_bridge()
        with patch.object(bridge, '_load_governance', return_value={
            "bridging": {"min_bridge_amount_usd": 1.0, "max_bridge_usd": 100.0,
                         "allowed_chains": ["arbitrum"], "counts_toward_daily_limit": True},
            "safety_limits": {"max_daily_usd": 100.0, "min_hbar_reserve": 5.0}
        }):
            result = bridge.bridge(0.5, "arbitrum", "0x1234567890abcdef1234567890abcdef12345678")
            assert not result["success"]
            assert "minimum" in result["error"].lower() or "min" in result["error"].lower()

    def test_amount_above_max_rejected(self):
        bridge = self._make_bridge()
        with patch.object(bridge, '_load_governance', return_value={
            "bridging": {"min_bridge_amount_usd": 1.0, "max_bridge_usd": 100.0,
                         "allowed_chains": ["arbitrum"], "counts_toward_daily_limit": True},
            "safety_limits": {"max_daily_usd": 100.0, "min_hbar_reserve": 5.0}
        }):
            result = bridge.bridge(150.0, "arbitrum", "0x1234567890abcdef1234567890abcdef12345678")
            assert not result["success"]
            assert "exceeds" in result["error"].lower() or "limit" in result["error"].lower()

    def test_unwhitelisted_destination_rejected(self):
        bridge = self._make_bridge()
        with patch.object(bridge, '_load_governance', return_value={
            "bridging": {"min_bridge_amount_usd": 1.0, "max_bridge_usd": 100.0,
                         "allowed_chains": ["arbitrum"], "counts_toward_daily_limit": True},
            "safety_limits": {"max_daily_usd": 100.0, "min_hbar_reserve": 5.0}
        }), patch.object(bridge, '_load_bridge_whitelist', return_value=[]):
            result = bridge.bridge(50.0, "arbitrum", "0x1234567890abcdef1234567890abcdef12345678")
            assert not result["success"]
            assert "whitelist" in result["error"].lower()

    def test_constants(self):
        from lib.bridge_usdt0 import USDT0Bridge
        assert USDT0Bridge.HEDERA_USDT0_OFT == "0xe3119e23fC2371d1E6b01775ba312035425A53d6"
        assert USDT0Bridge.HEDERA_USDT0_TOKEN == "0x00000000000000000000000000000000009Ce723"
        assert USDT0Bridge.HEDERA_USDT0_HEDERA_ID == "0.0.642851"
        assert USDT0Bridge.USDT0_DECIMALS == 6
        assert USDT0Bridge.CHAINS["arbitrum"]["eid"] == 30110
```

- [ ] **Step 2: Run tests — verify they fail (module doesn't exist yet)**

```bash
cd /Users/cdi/Developer/pacman && python3 -m pytest tests/test_bridge_usdt0.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'lib.bridge_usdt0'` or `ImportError`

- [ ] **Step 3: Implement `lib/bridge_usdt0.py`**

```python
"""
USDT0 cross-chain bridge via LayerZero OFT.

Bridges USDT0 from Hedera to other chains (initially Arbitrum).
Uses the same web3.py + contract pattern as lib/saucerswap.py.
"""
import json
import logging
import re
import time
from pathlib import Path

from web3 import Web3

logger = logging.getLogger("spacelord.bridge")

_ABI_DIR = Path(__file__).parent.parent / "data" / "abi"
_OFT_ABI = json.loads((_ABI_DIR / "oft.json").read_text())
_ERC20_ABI = json.loads((_ABI_DIR / "erc20.json").read_text())


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
        self.eoa = executor.eoa
        self.oft_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.HEDERA_USDT0_OFT),
            abi=_OFT_ABI,
        )
        self.token_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.HEDERA_USDT0_TOKEN),
            abi=_ERC20_ABI,
        )

    # ── Governance ──────────────────────────────────────────────

    def _load_governance(self) -> dict:
        with open(Path(__file__).parent.parent / "data" / "governance.json") as f:
            return json.load(f)

    def _load_bridge_whitelist(self) -> list:
        path = Path(__file__).parent.parent / "data" / "settings.json"
        with open(path) as f:
            settings = json.load(f)
        return settings.get("bridge_whitelist", [])

    def _validate(self, amount: float, dest_chain: str, recipient: str) -> str | None:
        """Return error string if validation fails, else None."""
        # Chain check
        if dest_chain not in self.CHAINS:
            allowed = list(self.CHAINS.keys())
            return f"Chain '{dest_chain}' not in allowed list: {allowed}"

        # Destination must be EVM address, not Hedera ID
        if recipient.startswith("0.0."):
            return "Bridge destination must be an EVM address (0x...), not a Hedera ID"

        # Valid EVM address: 0x + 40 hex chars
        if not re.match(r"^0x[0-9a-fA-F]{40}$", recipient):
            return f"Invalid EVM address: {recipient}"

        # Governance limits
        gov = self._load_governance()
        bridging = gov.get("bridging", {})
        limits = gov.get("safety_limits", {})

        allowed_chains = bridging.get("allowed_chains", [])
        if dest_chain not in allowed_chains:
            return f"Chain '{dest_chain}' not in governance allowed_chains: {allowed_chains}"

        min_amount = bridging.get("min_bridge_amount_usd", 1.0)
        if amount < min_amount:
            return f"Amount ${amount:.2f} below minimum ${min_amount:.2f}"

        max_amount = bridging.get("max_bridge_usd", 100.0)
        if amount > max_amount:
            return f"Amount ${amount:.2f} exceeds bridge limit of ${max_amount:.2f}"

        # Daily limit check (bridge counts toward max_daily_usd)
        if bridging.get("counts_toward_daily_limit", True):
            max_daily = limits.get("max_daily_usd", 100.0)
            daily_used = self._get_daily_volume_usd()
            if daily_used + amount > max_daily:
                return (
                    f"Bridge would exceed daily limit. "
                    f"Used today: ${daily_used:.2f}, Bridge: ${amount:.2f}, "
                    f"Limit: ${max_daily:.2f}"
                )

        # Whitelist check
        whitelist = self._load_bridge_whitelist()
        whitelisted = [
            e for e in whitelist
            if e.get("chain") == dest_chain
            and e.get("address", "").lower() == recipient.lower()
        ]
        if not whitelisted:
            return f"Address {recipient} not in bridge_whitelist for chain '{dest_chain}'"

        return None

    def _get_daily_volume_usd(self) -> float:
        """Read today's total volume from training data logs."""
        import datetime
        log_path = Path(__file__).parent.parent / "training_data" / "live_executions.jsonl"
        if not log_path.exists():
            return 0.0
        today = datetime.date.today().isoformat()
        total = 0.0
        for line in log_path.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("timestamp", "").startswith(today) and entry.get("success"):
                    total += float(entry.get("amount", 0))
            except (json.JSONDecodeError, ValueError):
                continue
        return total

    # ── Quote ───────────────────────────────────────────────────

    def quote(self, amount: float, dest_chain: str) -> dict:
        """Quote bridge cost without executing. Returns fee estimate."""
        if dest_chain not in self.CHAINS:
            return {"success": False, "error": f"Unsupported chain: {dest_chain}"}

        chain = self.CHAINS[dest_chain]
        amount_raw = int(amount * 10**self.USDT0_DECIMALS)

        # Pad recipient to bytes32 (use self.eoa as placeholder for quote)
        to_bytes32 = self.eoa.lower().replace("0x", "").zfill(64)
        to_bytes32 = bytes.fromhex(to_bytes32)

        send_param = (
            chain["eid"],       # dstEid
            to_bytes32,         # to
            amount_raw,         # amountLD
            0,                  # minAmountLD (get from quoteOFT)
            b"",                # extraOptions
            b"",                # composeMsg
            b"",                # oftCmd
        )

        try:
            # quoteOFT returns (OFTLimit, OFTFeeDetail[], OFTReceipt)
            oft_limit, fee_details, oft_receipt = self.oft_contract.functions.quoteOFT(
                send_param
            ).call()

            min_amount = oft_receipt[1]  # amountReceivedLD

            # Update sendParam with min amount for quoteSend
            send_param_with_min = (
                chain["eid"], to_bytes32, amount_raw, min_amount, b"", b"", b""
            )

            # quoteSend returns MessagingFee(nativeFee, lzTokenFee)
            msg_fee = self.oft_contract.functions.quoteSend(
                send_param_with_min, False
            ).call()

            native_fee_wei = msg_fee[0]
            # Hedera relay: gas in 18-decimal wei, convert to HBAR (8 decimals)
            native_fee_hbar = native_fee_wei / 10**18

            return {
                "success": True,
                "amount_in": amount,
                "estimated_received": min_amount / 10**self.USDT0_DECIMALS,
                "native_fee_hbar": round(native_fee_hbar, 6),
                "min_received_raw": min_amount,
            }
        except Exception as e:
            logger.error(f"Bridge quote failed: {e}")
            return {"success": False, "error": f"Quote failed: {e}"}

    # ── Bridge ──────────────────────────────────────────────────

    def bridge(self, amount: float, dest_chain: str, recipient: str) -> dict:
        """Execute USDT0 bridge: validate → approve → quote → send."""
        # 1. Validate
        err = self._validate(amount, dest_chain, recipient)
        if err:
            return {"success": False, "error": err}

        chain = self.CHAINS[dest_chain]
        amount_raw = int(amount * 10**self.USDT0_DECIMALS)

        # Pad recipient to bytes32
        recipient_clean = recipient.lower().replace("0x", "").zfill(64)
        to_bytes32 = bytes.fromhex(recipient_clean)

        try:
            # 2. Check balance
            balance = self.token_contract.functions.balanceOf(self.eoa).call()
            if balance < amount_raw:
                have = balance / 10**self.USDT0_DECIMALS
                return {
                    "success": False,
                    "error": f"Insufficient USDT0 balance. Have: {have:.2f}, Need: {amount:.2f}",
                }

            # 3. Approve OFT contract (exact amount per tx)
            allowance = self.token_contract.functions.allowance(
                self.eoa, Web3.to_checksum_address(self.HEDERA_USDT0_OFT)
            ).call()

            if allowance < amount_raw:
                approve_tx = self.token_contract.functions.approve(
                    Web3.to_checksum_address(self.HEDERA_USDT0_OFT), amount_raw
                ).build_transaction({
                    "from": self.eoa,
                    "gas": 100_000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.eoa),
                    "chainId": self.executor.chain_id,
                })

                pk = self.executor.config.private_key.reveal()
                try:
                    signed = self.w3.eth.account.sign_transaction(approve_tx, pk)
                    approve_hash = self.w3.eth.send_raw_transaction(
                        signed.raw_transaction
                    ).hex()
                finally:
                    del pk

                self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
                logger.info(f"USDT0 approval tx: {approve_hash}")

            # 4. Quote: quoteOFT → quoteSend
            send_param = (
                chain["eid"], to_bytes32, amount_raw, 0, b"", b"", b""
            )

            _, _, oft_receipt = self.oft_contract.functions.quoteOFT(
                send_param
            ).call()
            min_received = oft_receipt[1]  # amountReceivedLD

            send_param_final = (
                chain["eid"], to_bytes32, amount_raw, min_received, b"", b"", b""
            )

            msg_fee = self.oft_contract.functions.quoteSend(
                send_param_final, False
            ).call()
            native_fee = msg_fee[0]

            # 5. Check HBAR balance covers fee + gas + reserve
            gov = self._load_governance()
            min_reserve = gov.get("safety_limits", {}).get("min_hbar_reserve", 5.0)
            gas_estimate_hbar = 0.5  # conservative estimate for send() gas
            required_hbar = (native_fee / 10**18) + gas_estimate_hbar + min_reserve
            hbar_balance = self.w3.eth.get_balance(self.eoa) / 10**18
            if hbar_balance < required_hbar:
                return {
                    "success": False,
                    "error": (
                        f"Need {required_hbar:.2f} HBAR "
                        f"({native_fee / 10**18:.4f} LZ fee + {gas_estimate_hbar} gas + "
                        f"{min_reserve} reserve), have {hbar_balance:.2f}"
                    ),
                }

            # 6. Send
            send_tx = self.oft_contract.functions.send(
                send_param_final,
                (native_fee, 0),  # MessagingFee(nativeFee, lzTokenFee=0)
                self.eoa,         # refundAddress
            ).build_transaction({
                "from": self.eoa,
                "value": native_fee,
                "gas": 300_000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.executor.chain_id,
            })

            pk = self.executor.config.private_key.reveal()
            try:
                signed = self.w3.eth.account.sign_transaction(send_tx, pk)
                tx_hash = self.w3.eth.send_raw_transaction(
                    signed.raw_transaction
                ).hex()
            finally:
                del pk

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.status != 1:
                return {
                    "success": False,
                    "error": f"Bridge transaction reverted. TX: {tx_hash}",
                    "tx_hash": tx_hash,
                }

            # Extract LayerZero message GUID from send() return data
            # The send() returns (MessagingReceipt{guid, nonce, fee}, OFTReceipt)
            lz_guid = ""
            try:
                send_logs = self.oft_contract.events  # Parse from receipt logs if available
                # Fallback: GUID derivable from tx hash via LZ scan
                lz_guid = tx_hash  # Use tx_hash as lookup key for LZ scan
            except Exception:
                pass

            logger.info(f"Bridge TX: {tx_hash} | {amount} USDT0 → {dest_chain}")

            return {
                "success": True,
                "tx_hash": tx_hash,
                "lz_message_guid": lz_guid,
                "amount_sent": amount,
                "dest_chain": dest_chain,
                "recipient": recipient,
                "native_fee_hbar": round(native_fee / 10**18, 6),
                "estimated_arrival": "30s–3min",
            }

        except Exception as e:
            err_str = str(e)
            # Detect token association failure (Hedera-specific revert)
            if "TOKEN_NOT_ASSOCIATED" in err_str or "INVALID_TOKEN_ID" in err_str:
                return {
                    "success": False,
                    "error": f"USDT0 token not associated with account. Run: associate {self.HEDERA_USDT0_HEDERA_ID}",
                }
            logger.error(f"Bridge failed: {e}")
            return {"success": False, "error": f"Bridge failed: {e}"}

    # ── Status Check ────────────────────────────────────────────

    def check_status(self, tx_hash: str) -> dict:
        """Check LayerZero message delivery status via LZ Scan API."""
        import requests

        try:
            url = "https://scan.layerzero-api.com/v1/messages/tx/" + tx_hash
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return {"status": "unknown", "error": f"LZ Scan returned {resp.status_code}"}

            data = resp.json()
            messages = data.get("messages", data.get("data", []))
            if not messages:
                return {"status": "pending", "message": "No LayerZero message found yet"}

            msg = messages[0] if isinstance(messages, list) else messages
            status = msg.get("status", "unknown")
            return {
                "status": status,
                "src_tx_hash": msg.get("srcTxHash", tx_hash),
                "dst_tx_hash": msg.get("dstTxHash", ""),
                "src_chain": msg.get("srcChainKey", ""),
                "dst_chain": msg.get("dstChainKey", ""),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/cdi/Developer/pacman && python3 -m pytest tests/test_bridge_usdt0.py -v
```

Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/bridge_usdt0.py tests/test_bridge_usdt0.py
git commit -m "feat: add USDT0 bridge library with LayerZero OFT integration"
```

---

## Task 4: CLI Command Handler (`cli/commands/bridge.py`)

**Files:**
- Create: `cli/commands/bridge.py`
- Modify: `cli/main.py:109-167` (add `"bridge"` to COMMANDS dict)
- Reference: `cli/commands/wallet.py:26-54` (_safe_input, _clean_args, _print_account_context)

- [ ] **Step 1: Create `cli/commands/bridge.py`**

```python
"""
Bridge USDT0 to another chain via LayerZero.

Usage:
    bridge <amount> USDT0 <chain> --to <address>
    bridge status <tx_hash>
    bridge whitelist add <chain> <address> <label>
    bridge whitelist list
"""
import json
import logging
from pathlib import Path

from cli.commands.wallet import _safe_input, _clean_args, _print_account_context
from cli.display import C

logger = logging.getLogger("spacelord.cli.bridge")


def cmd_bridge(app, args):
    """Handle bridge commands."""
    clean = _clean_args(args)
    json_mode = "--json" in args

    if not clean:
        _print_help()
        return

    subcmd = clean[0].lower()

    if subcmd == "status":
        _handle_status(app, clean[1:], json_mode)
    elif subcmd == "whitelist":
        _handle_whitelist(clean[1:], json_mode)
    else:
        _handle_bridge(app, clean, args, json_mode)


def _handle_bridge(app, clean, raw_args, json_mode):
    """Bridge USDT0: bridge <amount> USDT0 <chain> --to <address>"""
    from lib.bridge_usdt0 import USDT0Bridge

    _print_account_context(app)

    # Parse: bridge 50 USDT0 arbitrum --to 0x...
    if len(clean) < 3:
        print(f"  {C.ERR}Usage: bridge <amount> USDT0 <chain> --to <address>{C.R}")
        return

    try:
        amount = float(clean[0])
    except ValueError:
        print(f"  {C.ERR}Invalid amount: {clean[0]}{C.R}")
        return

    # Token name (should be USDT0)
    token = clean[1].upper()
    if token != "USDT0":
        print(f"  {C.ERR}Only USDT0 bridging is supported. Got: {token}{C.R}")
        return

    dest_chain = clean[2].lower()

    # Parse --to flag
    recipient = None
    for i, a in enumerate(raw_args):
        if a == "--to" and i + 1 < len(raw_args):
            recipient = raw_args[i + 1]
            break

    if not recipient:
        print(f"  {C.ERR}Missing --to <address>. Destination address required.{C.R}")
        return

    bridge = USDT0Bridge(app.executor)

    # Quote first
    quote = bridge.quote(amount, dest_chain)
    if not quote["success"]:
        print(f"  {C.ERR}Quote failed: {quote['error']}{C.R}")
        return

    print(f"\n  Bridge {amount:.2f} USDT0 → {dest_chain.title()}")
    print(f"  Estimated received: {quote['estimated_received']:.2f} USDT0")
    print(f"  LayerZero fee: ~{quote['native_fee_hbar']:.4f} HBAR")
    print(f"  Destination: {recipient}")
    print(f"  Estimated arrival: 30s–3min\n")

    confirm = _safe_input("  Confirm bridge? (y/n): ", raw_args, default="y")
    if confirm.lower() not in ("y", "yes"):
        print(f"  {C.WARN}Cancelled.{C.R}")
        return

    # Execute
    result = bridge.bridge(amount, dest_chain, recipient)

    if json_mode:
        print(json.dumps(result, indent=2))
        return

    if result["success"]:
        print(f"\n  {C.OK}✓ Bridged {result['amount_sent']:.2f} USDT0 → {result['dest_chain']}{C.R}")
        print(f"  TX: {result['tx_hash']}")
        print(f"  Fee: {result['native_fee_hbar']:.4f} HBAR")
        print(f"  Check status: bridge status {result['tx_hash']}")
    else:
        print(f"\n  {C.ERR}✗ Bridge failed: {result['error']}{C.R}")

    # Log to training data
    _log_bridge(result, amount, dest_chain, recipient, app)


def _handle_status(app, args, json_mode):
    """Check bridge delivery status."""
    from lib.bridge_usdt0 import USDT0Bridge

    if not args:
        print(f"  {C.ERR}Usage: bridge status <tx_hash>{C.R}")
        return

    tx_hash = args[0]
    bridge = USDT0Bridge(app.executor)
    status = bridge.check_status(tx_hash)

    if json_mode:
        print(json.dumps(status, indent=2))
        return

    s = status.get("status", "unknown")
    color = C.OK if s == "delivered" else C.WARN if s in ("pending", "inflight") else C.ERR
    print(f"\n  LayerZero Status: {color}{s}{C.R}")
    if status.get("dst_tx_hash"):
        print(f"  Destination TX: {status['dst_tx_hash']}")
    if s == "pending":
        print(f"  Estimated: 30s–3min. Check: https://scan.layerzero.network/tx/{tx_hash}")


def _handle_whitelist(args, json_mode):
    """Manage bridge whitelist."""
    settings_path = Path(__file__).parent.parent.parent / "data" / "settings.json"

    if not args:
        args = ["list"]

    subcmd = args[0].lower()

    if subcmd == "list":
        with open(settings_path) as f:
            settings = json.load(f)
        whitelist = settings.get("bridge_whitelist", [])
        if not whitelist:
            print(f"  {C.WARN}No bridge whitelist entries.{C.R}")
            print(f"  Add one: bridge whitelist add <chain> <address> <label>")
            return
        for entry in whitelist:
            print(f"  {entry['chain']}: {entry['address']} ({entry.get('label', '')})")

    elif subcmd == "add" and len(args) >= 4:
        chain = args[1].lower()
        address = args[2]
        label = " ".join(args[3:])

        # Validate EVM address
        import re
        if address.startswith("0.0."):
            print(f"  {C.ERR}Bridge destinations must be EVM addresses (0x...), not Hedera IDs{C.R}")
            return
        if not re.match(r"^0x[0-9a-fA-F]{40}$", address):
            print(f"  {C.ERR}Invalid EVM address: {address}{C.R}")
            return

        with open(settings_path) as f:
            settings = json.load(f)

        whitelist = settings.setdefault("bridge_whitelist", [])
        # Check for duplicate
        existing = [e for e in whitelist if e.get("address", "").lower() == address.lower() and e.get("chain") == chain]
        if existing:
            print(f"  {C.WARN}Already whitelisted.{C.R}")
            return

        whitelist.append({"chain": chain, "address": address, "label": label})
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        print(f"  {C.OK}✓ Added {address} ({label}) for {chain}{C.R}")

    else:
        print(f"  {C.ERR}Usage: bridge whitelist add <chain> <address> <label>{C.R}")


def _log_bridge(result, amount, dest_chain, recipient, app):
    """Log bridge operation to training data."""
    log_path = Path(__file__).parent.parent.parent / "training_data" / "live_executions.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    import datetime
    entry = {
        "type": "bridge",
        "protocol": "layerzero_usdt0",
        "amount": amount,
        "source_chain": "hedera",
        "dest_chain": dest_chain,
        "recipient": recipient,
        "tx_hash": result.get("tx_hash", ""),
        "lz_message_guid": result.get("lz_message_guid", ""),
        "native_fee_hbar": result.get("native_fee_hbar", 0),
        "success": result.get("success", False),
        "error": result.get("error", ""),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "account": getattr(app.executor, "hedera_account_id", ""),
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _print_help():
    print("""
  Bridge USDT0 across chains via LayerZero

  Usage:
    bridge <amount> USDT0 <chain> --to <address>
    bridge status <tx_hash>
    bridge whitelist list
    bridge whitelist add <chain> <address> <label>

  Supported chains: arbitrum
  Destinations must be whitelisted first.

  Example:
    bridge whitelist add arbitrum 0xYour...Addr My Arb Wallet
    bridge 50 USDT0 arbitrum --to 0xYour...Addr
    bridge status 0xabc123...
""")
```

- [ ] **Step 2: Register command in `cli/main.py`**

Add to the COMMANDS dict (around line 109-167). Find the dict and add:

```python
"bridge": cmd_bridge,
```

Also add the import at the top of the file with the other command imports:

```python
from cli.commands.bridge import cmd_bridge
```

- [ ] **Step 3: Verify import works**

```bash
cd /Users/cdi/Developer/pacman && python3 -c "from cli.commands.bridge import cmd_bridge; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add cli/commands/bridge.py cli/main.py
git commit -m "feat: add bridge CLI command with whitelist management"
```

---

## Task 5: SKILL.md Update

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Add bridge command documentation to SKILL.md**

Find the commands section in SKILL.md and add:

```markdown
## Bridge (Cross-Chain)
- `bridge <amount> USDT0 <chain> --to <address>` — Bridge USDT0 to another chain via LayerZero
- `bridge status <tx_hash>` — Check bridge delivery status
- `bridge whitelist list` — Show whitelisted bridge destinations
- `bridge whitelist add <chain> <address> <label>` — Add a bridge destination
- Supported chains: arbitrum
- Destination must be whitelisted first (bridge whitelist add ...)
- Counts toward daily transaction limit
- Estimated arrival: 30 seconds to 3 minutes
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "docs: add bridge command to SKILL.md for OpenClaw agent"
```

---

## Task 6: HAK TypeScript Plugin — Project Setup

**Files:**
- Create: `hak-usdt0-bridge-plugin/package.json`
- Create: `hak-usdt0-bridge-plugin/tsconfig.json`
- Create: `hak-usdt0-bridge-plugin/src/types.ts`
- Create: `hak-usdt0-bridge-plugin/src/contracts/addresses.ts`
- Create: `hak-usdt0-bridge-plugin/src/contracts/oft-abi.ts`
- Create: `hak-usdt0-bridge-plugin/src/contracts/erc20-abi.ts`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "hak-usdt0-bridge-plugin",
  "version": "0.1.0",
  "description": "USDT0 cross-chain bridge plugin for Hedera Agent Kit via LayerZero OFT",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": ["dist"],
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "keywords": ["hedera", "agent-kit", "usdt0", "layerzero", "bridge", "oft"],
  "license": "MIT",
  "dependencies": {
    "ethers": "^6.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "@types/node": "^20.0.0"
  },
  "peerDependencies": {
    "hedera-agent-kit": "^3.0.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "declaration": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

- [ ] **Step 3: Create `src/types.ts`**

```typescript
export interface ChainConfig {
  name: string;
  eid: number;
  chainId: number;
  tokenAddress: string;
  oftAddress: string;
}

export interface SendParam {
  dstEid: number;
  to: string; // bytes32 hex
  amountLD: bigint;
  minAmountLD: bigint;
  extraOptions: string; // bytes hex
  composeMsg: string; // bytes hex
  oftCmd: string; // bytes hex
}

export interface MessagingFee {
  nativeFee: bigint;
  lzTokenFee: bigint;
}

export interface QuoteResult {
  success: boolean;
  estimatedReceived?: string;
  nativeFee?: string;
  minReceived?: string;
  error?: string;
}

export interface BridgeResult {
  success: boolean;
  txHash?: string;
  lzMessageGuid?: string;
  amountSent?: string;
  estimatedArrival?: string;
  error?: string;
}

export interface BridgeStatusResult {
  status: "pending" | "inflight" | "delivered" | "failed" | "unknown";
  srcTxHash?: string;
  dstTxHash?: string;
  error?: string;
}
```

- [ ] **Step 4: Create `src/contracts/addresses.ts`**

```typescript
import { ChainConfig } from "../types";

export const HEDERA_CONFIG = {
  eid: 30285,
  chainId: 295,
  tokenAddress: "0x00000000000000000000000000000000009Ce723",
  oftAddress: "0xe3119e23fC2371d1E6b01775ba312035425A53d6",
  hederaTokenId: "0.0.642851",
};

export const SUPPORTED_CHAINS: Record<string, ChainConfig> = {
  arbitrum: {
    name: "Arbitrum One",
    eid: 30110,
    chainId: 42161,
    tokenAddress: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    oftAddress: "0x14E4A1B13bf7F943c8ff7C51fb60FA964A298D92",
  },
};

export const USDT0_DECIMALS = 6;
```

- [ ] **Step 5: Create `src/contracts/oft-abi.ts`**

```typescript
export const OFT_ABI = [
  {
    inputs: [{ components: [
      { name: "dstEid", type: "uint32" },
      { name: "to", type: "bytes32" },
      { name: "amountLD", type: "uint256" },
      { name: "minAmountLD", type: "uint256" },
      { name: "extraOptions", type: "bytes" },
      { name: "composeMsg", type: "bytes" },
      { name: "oftCmd", type: "bytes" },
    ], name: "_sendParam", type: "tuple" }],
    name: "quoteOFT",
    outputs: [
      { components: [
        { name: "minAmountLD", type: "uint256" },
        { name: "maxAmountLD", type: "uint256" },
      ], name: "oftLimit", type: "tuple" },
      { components: [
        { name: "feeAmountLD", type: "uint256" },
        { name: "description", type: "string" },
      ], name: "oftFeeDetails", type: "tuple[]" },
      { components: [
        { name: "amountSentLD", type: "uint256" },
        { name: "amountReceivedLD", type: "uint256" },
      ], name: "oftReceipt", type: "tuple" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [
      { components: [
        { name: "dstEid", type: "uint32" },
        { name: "to", type: "bytes32" },
        { name: "amountLD", type: "uint256" },
        { name: "minAmountLD", type: "uint256" },
        { name: "extraOptions", type: "bytes" },
        { name: "composeMsg", type: "bytes" },
        { name: "oftCmd", type: "bytes" },
      ], name: "_sendParam", type: "tuple" },
      { name: "_payInLzToken", type: "bool" },
    ],
    name: "quoteSend",
    outputs: [{ components: [
      { name: "nativeFee", type: "uint256" },
      { name: "lzTokenFee", type: "uint256" },
    ], name: "msgFee", type: "tuple" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [
      { components: [
        { name: "dstEid", type: "uint32" },
        { name: "to", type: "bytes32" },
        { name: "amountLD", type: "uint256" },
        { name: "minAmountLD", type: "uint256" },
        { name: "extraOptions", type: "bytes" },
        { name: "composeMsg", type: "bytes" },
        { name: "oftCmd", type: "bytes" },
      ], name: "_sendParam", type: "tuple" },
      { components: [
        { name: "nativeFee", type: "uint256" },
        { name: "lzTokenFee", type: "uint256" },
      ], name: "_fee", type: "tuple" },
      { name: "_refundAddress", type: "address" },
    ],
    name: "send",
    outputs: [
      { components: [
        { name: "guid", type: "bytes32" },
        { name: "nonce", type: "uint64" },
        { components: [
          { name: "nativeFee", type: "uint256" },
          { name: "lzTokenFee", type: "uint256" },
        ], name: "fee", type: "tuple" },
      ], name: "msgReceipt", type: "tuple" },
      { components: [
        { name: "amountSentLD", type: "uint256" },
        { name: "amountReceivedLD", type: "uint256" },
      ], name: "oftReceipt", type: "tuple" },
    ],
    stateMutability: "payable",
    type: "function",
  },
] as const;
```

- [ ] **Step 6: Create `src/contracts/erc20-abi.ts`**

```typescript
export const ERC20_ABI = [
  {
    inputs: [{ name: "account", type: "address" }],
    name: "balanceOf",
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [
      { name: "owner", type: "address" },
      { name: "spender", type: "address" },
    ],
    name: "allowance",
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    name: "approve",
    outputs: [{ name: "", type: "bool" }],
    stateMutability: "nonpayable",
    type: "function",
  },
] as const;
```

- [ ] **Step 7: Commit**

```bash
git add hak-usdt0-bridge-plugin/
git commit -m "feat: scaffold HAK USDT0 bridge plugin with types and ABIs"
```

---

## Task 7: HAK Plugin — Tests First (TDD)

**Files:**
- Create: `hak-usdt0-bridge-plugin/tests/quote.test.ts`
- Create: `hak-usdt0-bridge-plugin/tests/bridge.test.ts`

- [ ] **Step 1: Create `tests/quote.test.ts`**

```typescript
import { describe, it, expect } from "vitest";
import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../src/contracts/addresses";

describe("USDT0 Bridge Constants", () => {
  it("has correct Hedera OFT address", () => {
    expect(HEDERA_CONFIG.oftAddress).toBe("0xe3119e23fC2371d1E6b01775ba312035425A53d6");
  });

  it("has correct Hedera token address", () => {
    expect(HEDERA_CONFIG.tokenAddress).toBe("0x00000000000000000000000000000000009Ce723");
  });

  it("has correct Hedera EID", () => {
    expect(HEDERA_CONFIG.eid).toBe(30285);
  });

  it("has Arbitrum chain config", () => {
    const arb = SUPPORTED_CHAINS["arbitrum"];
    expect(arb).toBeDefined();
    expect(arb.eid).toBe(30110);
    expect(arb.chainId).toBe(42161);
  });

  it("uses 6 decimals", () => {
    expect(USDT0_DECIMALS).toBe(6);
  });
});
```

- [ ] **Step 2: Create `tests/bridge.test.ts`**

```typescript
import { describe, it, expect } from "vitest";

describe("usdt0_bridge validation", () => {
  it("rejects unsupported chain", async () => {
    const { usdt0Bridge } = await import("../src/tools/bridge");
    const mockProvider = {} as any;
    const mockSigner = { getAddress: async () => "0x1234567890abcdef1234567890abcdef12345678" } as any;

    const result = await usdt0Bridge.handler(
      { amount: 50, destChain: "polygon", recipientAddress: "0x1234567890abcdef1234567890abcdef12345678" },
      mockProvider,
      mockSigner,
    );
    expect(result.success).toBe(false);
    expect(result.error).toContain("Unsupported chain");
  });

  it("rejects invalid EVM address", async () => {
    const { usdt0Bridge } = await import("../src/tools/bridge");
    const mockProvider = {} as any;
    const mockSigner = { getAddress: async () => "0x1234567890abcdef1234567890abcdef12345678" } as any;

    const result = await usdt0Bridge.handler(
      { amount: 50, destChain: "arbitrum", recipientAddress: "not-an-address" },
      mockProvider,
      mockSigner,
    );
    expect(result.success).toBe(false);
    expect(result.error).toContain("Invalid EVM address");
  });
});

describe("USDT0 Bridge Plugin", () => {
  it("exports plugin class with 4 tools", async () => {
    const { USDT0BridgePlugin } = await import("../src/plugin");
    const plugin = new USDT0BridgePlugin();
    expect(plugin.name).toBe("usdt0-bridge");
    expect(plugin.getTools()).toHaveLength(4);
  });

  it("get_supported_chains returns data", async () => {
    const { usdt0GetSupportedChains } = await import("../src/tools/get-supported-chains");
    const result = await usdt0GetSupportedChains.handler();
    expect(result.source.eid).toBe(30285);
    expect(result.destinations.length).toBeGreaterThan(0);
    expect(result.decimals).toBe(6);
  });
});
```

- [ ] **Step 3: Run tests — verify they fail (tools not implemented yet)**

```bash
cd /Users/cdi/Developer/pacman/hak-usdt0-bridge-plugin && npx vitest run 2>&1 | head -20
```

Expected: Import failures for missing tool files.

- [ ] **Step 4: Commit tests**

```bash
git add hak-usdt0-bridge-plugin/tests/
git commit -m "test: add HAK USDT0 bridge plugin tests (TDD — red phase)"
```

---

## Task 8: HAK Plugin — Tool Implementations

**Files:**
- Create: `hak-usdt0-bridge-plugin/src/tools/get-supported-chains.ts`
- Create: `hak-usdt0-bridge-plugin/src/tools/quote-bridge.ts`
- Create: `hak-usdt0-bridge-plugin/src/tools/bridge.ts`
- Create: `hak-usdt0-bridge-plugin/src/tools/check-bridge-status.ts`
- Create: `hak-usdt0-bridge-plugin/src/plugin.ts`
- Create: `hak-usdt0-bridge-plugin/src/index.ts`

- [ ] **Step 1: Create `src/tools/get-supported-chains.ts`**

```typescript
import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../contracts/addresses";

export const usdt0GetSupportedChains = {
  name: "usdt0_get_supported_chains",
  description: "List all chains supported for USDT0 bridging via LayerZero, with endpoint IDs and contract addresses.",
  parameters: {},
  handler: async () => {
    const chains = Object.entries(SUPPORTED_CHAINS).map(([key, config]) => ({
      key,
      ...config,
    }));
    return {
      source: { name: "Hedera", ...HEDERA_CONFIG },
      destinations: chains,
      decimals: USDT0_DECIMALS,
    };
  },
};
```

- [ ] **Step 2: Create `src/tools/quote-bridge.ts`**

```typescript
import { ethers } from "ethers";
import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../contracts/addresses";
import { OFT_ABI } from "../contracts/oft-abi";
import type { QuoteResult } from "../types";

export const usdt0QuoteBridge = {
  name: "usdt0_quote_bridge",
  description: "Get a fee estimate for bridging USDT0 from Hedera to a destination chain. Does not execute.",
  parameters: {
    type: "object",
    properties: {
      amount: { type: "number", description: "Amount of USDT0 to bridge" },
      destChain: { type: "string", description: "Destination chain key (e.g. 'arbitrum')" },
    },
    required: ["amount", "destChain"],
  },
  handler: async (
    params: { amount: number; destChain: string },
    provider: ethers.Provider,
    signer: ethers.Signer,
  ): Promise<QuoteResult> => {
    const chain = SUPPORTED_CHAINS[params.destChain];
    if (!chain) {
      return { success: false, error: `Unsupported chain: ${params.destChain}` };
    }

    const amountRaw = BigInt(Math.floor(params.amount * 10 ** USDT0_DECIMALS));
    const signerAddress = await signer.getAddress();
    const toBytes32 = ethers.zeroPadValue(signerAddress, 32);

    const oft = new ethers.Contract(HEDERA_CONFIG.oftAddress, OFT_ABI, provider);

    const sendParam = [chain.eid, toBytes32, amountRaw, 0n, "0x", "0x", "0x"];

    try {
      const [, , oftReceipt] = await oft.quoteOFT(sendParam);
      const minReceived = oftReceipt.amountReceivedLD;

      const sendParamWithMin = [chain.eid, toBytes32, amountRaw, minReceived, "0x", "0x", "0x"];
      const msgFee = await oft.quoteSend(sendParamWithMin, false);

      return {
        success: true,
        estimatedReceived: ethers.formatUnits(minReceived, USDT0_DECIMALS),
        nativeFee: ethers.formatEther(msgFee.nativeFee),
        minReceived: ethers.formatUnits(minReceived, USDT0_DECIMALS),
      };
    } catch (e: any) {
      return { success: false, error: `Quote failed: ${e.message}` };
    }
  },
};
```

- [ ] **Step 3: Create `src/tools/bridge.ts`**

```typescript
import { ethers } from "ethers";
import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../contracts/addresses";
import { OFT_ABI } from "../contracts/oft-abi";
import { ERC20_ABI } from "../contracts/erc20-abi";
import type { BridgeResult } from "../types";

export const usdt0Bridge = {
  name: "usdt0_bridge",
  description: "Bridge USDT0 from Hedera to a destination chain via LayerZero OFT. Handles approval, quoting, and sending.",
  parameters: {
    type: "object",
    properties: {
      amount: { type: "number", description: "Amount of USDT0 to bridge" },
      destChain: { type: "string", description: "Destination chain key (e.g. 'arbitrum')" },
      recipientAddress: { type: "string", description: "Destination EVM address (0x...)" },
    },
    required: ["amount", "destChain", "recipientAddress"],
  },
  handler: async (
    params: { amount: number; destChain: string; recipientAddress: string },
    provider: ethers.Provider,
    signer: ethers.Signer,
  ): Promise<BridgeResult> => {
    const chain = SUPPORTED_CHAINS[params.destChain];
    if (!chain) {
      return { success: false, error: `Unsupported chain: ${params.destChain}` };
    }

    if (!/^0x[0-9a-fA-F]{40}$/.test(params.recipientAddress)) {
      return { success: false, error: `Invalid EVM address: ${params.recipientAddress}` };
    }

    const amountRaw = BigInt(Math.floor(params.amount * 10 ** USDT0_DECIMALS));
    const signerAddress = await signer.getAddress();
    const toBytes32 = ethers.zeroPadValue(params.recipientAddress, 32);

    const oft = new ethers.Contract(HEDERA_CONFIG.oftAddress, OFT_ABI, signer);
    const token = new ethers.Contract(HEDERA_CONFIG.tokenAddress, ERC20_ABI, signer);

    try {
      // 1. Check balance
      const balance = await token.balanceOf(signerAddress);
      if (balance < amountRaw) {
        return {
          success: false,
          error: `Insufficient USDT0. Have: ${ethers.formatUnits(balance, USDT0_DECIMALS)}, Need: ${params.amount}`,
        };
      }

      // 2. Approve if needed (exact amount)
      const allowance = await token.allowance(signerAddress, HEDERA_CONFIG.oftAddress);
      if (allowance < amountRaw) {
        const approveTx = await token.approve(HEDERA_CONFIG.oftAddress, amountRaw);
        await approveTx.wait();
      }

      // 3. Quote
      const sendParam = [chain.eid, toBytes32, amountRaw, 0n, "0x", "0x", "0x"];
      const [, , oftReceipt] = await oft.quoteOFT(sendParam);
      const minReceived = oftReceipt.amountReceivedLD;

      const sendParamFinal = [chain.eid, toBytes32, amountRaw, minReceived, "0x", "0x", "0x"];
      const msgFee = await oft.quoteSend(sendParamFinal, false);

      // 4. Send
      const tx = await oft.send(sendParamFinal, [msgFee.nativeFee, 0n], signerAddress, {
        value: msgFee.nativeFee,
      });
      const receipt = await tx.wait();

      // Extract LZ message GUID from logs if possible, fallback to tx hash for LZ scan lookup
      const lzGuid = receipt.hash; // Use tx hash as LZ scan lookup key

      return {
        success: true,
        txHash: receipt.hash,
        lzMessageGuid: lzGuid,
        amountSent: params.amount.toString(),
        estimatedArrival: "30s-3min",
      };
    } catch (e: any) {
      return { success: false, error: `Bridge failed: ${e.message}` };
    }
  },
};
```

- [ ] **Step 4: Create `src/tools/check-bridge-status.ts`**

```typescript
import type { BridgeStatusResult } from "../types";

export const usdt0CheckBridgeStatus = {
  name: "usdt0_check_bridge_status",
  description: "Check the delivery status of a USDT0 bridge transaction via the LayerZero Scan API.",
  parameters: {
    type: "object",
    properties: {
      txHash: { type: "string", description: "Source transaction hash from the bridge call" },
      lzMessageGuid: { type: "string", description: "LayerZero message GUID (alternative to txHash)" },
    },
    required: [],
  },
  handler: async (params: { txHash?: string; lzMessageGuid?: string }): Promise<BridgeStatusResult> => {
    const lookupId = params.txHash || params.lzMessageGuid;
    if (!lookupId) {
      return { status: "unknown", error: "Provide either txHash or lzMessageGuid" };
    }
    try {
      const url = `https://scan.layerzero-api.com/v1/messages/tx/${lookupId}`;
      const resp = await fetch(url);

      if (!resp.ok) {
        return { status: "unknown", error: `LZ Scan returned ${resp.status}` };
      }

      const data = await resp.json();
      const messages = data.messages || data.data || [];

      if (!messages.length) {
        return { status: "pending" };
      }

      const msg = Array.isArray(messages) ? messages[0] : messages;
      return {
        status: msg.status || "unknown",
        srcTxHash: msg.srcTxHash || params.txHash,
        dstTxHash: msg.dstTxHash || "",
      };
    } catch (e: any) {
      return { status: "unknown", error: e.message };
    }
  },
};
```

- [ ] **Step 5: Create `src/plugin.ts`**

```typescript
import { usdt0GetSupportedChains } from "./tools/get-supported-chains";
import { usdt0QuoteBridge } from "./tools/quote-bridge";
import { usdt0Bridge } from "./tools/bridge";
import { usdt0CheckBridgeStatus } from "./tools/check-bridge-status";

export class USDT0BridgePlugin {
  name = "usdt0-bridge";
  description = "Bridge USDT0 between Hedera and other chains via LayerZero OFT";

  getTools() {
    return [
      usdt0GetSupportedChains,
      usdt0QuoteBridge,
      usdt0Bridge,
      usdt0CheckBridgeStatus,
    ];
  }
}
```

- [ ] **Step 6: Create `src/index.ts`**

```typescript
export { USDT0BridgePlugin } from "./plugin";
export type {
  ChainConfig,
  SendParam,
  MessagingFee,
  QuoteResult,
  BridgeResult,
  BridgeStatusResult,
} from "./types";
export { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "./contracts/addresses";
```

- [ ] **Step 7: Commit**

```bash
git add hak-usdt0-bridge-plugin/src/
git commit -m "feat: implement HAK USDT0 bridge plugin tools and plugin class"
```

---

## Task 9: HAK Plugin — README and Final Tests

**Files:**
- Create: `hak-usdt0-bridge-plugin/README.md`

- [ ] **Step 1: Create README.md**

```markdown
# hak-usdt0-bridge-plugin

USDT0 cross-chain bridge plugin for the [Hedera Agent Kit](https://github.com/hashgraph/hedera-agent-kit-js) via LayerZero OFT.

## Installation

```bash
npm install hak-usdt0-bridge-plugin
```

## Usage

```typescript
import { USDT0BridgePlugin } from "hak-usdt0-bridge-plugin";

// Register with your Hedera Agent Kit instance
const plugin = new USDT0BridgePlugin();
agentKit.registerPlugin(plugin);
```

## Tools

| Tool | Description |
|------|-------------|
| `usdt0_get_supported_chains` | List supported destination chains |
| `usdt0_quote_bridge` | Get fee estimate without executing |
| `usdt0_bridge` | Execute USDT0 bridge transfer |
| `usdt0_check_bridge_status` | Check LayerZero delivery status |

## Supported Chains

| Chain | EID | Status |
|-------|-----|--------|
| Hedera (source) | 30285 | Live |
| Arbitrum | 30110 | Live |

## Contract Addresses

| Chain | USDT0 Token | OFT Contract |
|-------|------------|--------------|
| Hedera | `0x...009Ce723` | `0xe3119e23fC2371d1E6b01775ba312035425A53d6` |
| Arbitrum | `0xFd086bC7...FCbb9` | `0x14E4A1B1...298D92` |

## License

MIT
```

- [ ] **Step 2: Install deps and run all tests (TDD green phase)**

```bash
cd /Users/cdi/Developer/pacman/hak-usdt0-bridge-plugin && npm install && npm test
```

Expected: All tests pass (constants, plugin class, validation, supported chains).

- [ ] **Step 3: Commit**

```bash
git add hak-usdt0-bridge-plugin/README.md
git commit -m "docs: add HAK USDT0 bridge plugin README"
```

---

## Task 10: Run Full Verification

**Files:**
- Reference: `tests/verify_all.py`

- [ ] **Step 1: Run existing test suite to ensure no regressions**

```bash
cd /Users/cdi/Developer/pacman && python3 tests/verify_all.py
```

Expected: All existing tests pass. No regressions.

- [ ] **Step 2: Run bridge-specific tests**

```bash
cd /Users/cdi/Developer/pacman && python3 -m pytest tests/test_bridge_usdt0.py -v
```

Expected: All bridge tests pass.

- [ ] **Step 3: Verify CLI help output**

```bash
cd /Users/cdi/Developer/pacman && python3 -c "
from cli.commands.bridge import cmd_bridge
# Just test it doesn't crash when printing help
import types
app = types.SimpleNamespace()
cmd_bridge(app, [])
"
```

Expected: Prints help text without errors.

- [ ] **Step 4: Verify governance.json is valid**

```bash
cd /Users/cdi/Developer/pacman && python3 -c "
import json
g = json.load(open('data/governance.json'))
assert 'bridging' in g
assert 'bridge' in g['agent_rules']['never_auto_execute']
print('All governance checks pass')
"
```

Expected: `All governance checks pass`

- [ ] **Step 5: Final commit if any fixes needed**

Only commit if previous steps required fixes. Stage specific files only:
```bash
git status
# Then add only the specific files that changed:
# git add <specific-files>
# git commit -m "fix: address issues found during verification"
```
