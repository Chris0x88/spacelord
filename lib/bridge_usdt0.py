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
        if dest_chain not in self.CHAINS:
            allowed = list(self.CHAINS.keys())
            return f"Chain '{dest_chain}' not in allowed list: {allowed}"

        if recipient.startswith("0.0."):
            return "Bridge destination must be an EVM address (0x...), not a Hedera ID"

        if not re.match(r"^0x[0-9a-fA-F]{40}$", recipient):
            return f"Invalid EVM address: {recipient}"

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

        if bridging.get("counts_toward_daily_limit", True):
            max_daily = limits.get("max_daily_usd", 100.0)
            daily_used = self._get_daily_volume_usd()
            if daily_used + amount > max_daily:
                return (
                    f"Bridge would exceed daily limit. "
                    f"Used today: ${daily_used:.2f}, Bridge: ${amount:.2f}, "
                    f"Limit: ${max_daily:.2f}"
                )

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

        to_bytes32 = self.eoa.lower().replace("0x", "").zfill(64)
        to_bytes32 = bytes.fromhex(to_bytes32)

        send_param = (
            chain["eid"], to_bytes32, amount_raw, 0, b"", b"", b""
        )

        try:
            oft_limit, fee_details, oft_receipt = self.oft_contract.functions.quoteOFT(
                send_param
            ).call()

            min_amount = oft_receipt[1]

            send_param_with_min = (
                chain["eid"], to_bytes32, amount_raw, min_amount, b"", b"", b""
            )

            msg_fee = self.oft_contract.functions.quoteSend(
                send_param_with_min, False
            ).call()

            native_fee_wei = msg_fee[0]
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
        err = self._validate(amount, dest_chain, recipient)
        if err:
            return {"success": False, "error": err}

        chain = self.CHAINS[dest_chain]
        amount_raw = int(amount * 10**self.USDT0_DECIMALS)

        recipient_clean = recipient.lower().replace("0x", "").zfill(64)
        to_bytes32 = bytes.fromhex(recipient_clean)

        try:
            balance = self.token_contract.functions.balanceOf(self.eoa).call()
            if balance < amount_raw:
                have = balance / 10**self.USDT0_DECIMALS
                return {
                    "success": False,
                    "error": f"Insufficient USDT0 balance. Have: {have:.2f}, Need: {amount:.2f}",
                }

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

            send_param = (
                chain["eid"], to_bytes32, amount_raw, 0, b"", b"", b""
            )

            _, _, oft_receipt = self.oft_contract.functions.quoteOFT(
                send_param
            ).call()
            min_received = oft_receipt[1]

            send_param_final = (
                chain["eid"], to_bytes32, amount_raw, min_received, b"", b"", b""
            )

            msg_fee = self.oft_contract.functions.quoteSend(
                send_param_final, False
            ).call()
            native_fee = msg_fee[0]

            gov = self._load_governance()
            min_reserve = gov.get("safety_limits", {}).get("min_hbar_reserve", 5.0)
            gas_estimate_hbar = 0.5
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

            send_tx = self.oft_contract.functions.send(
                send_param_final,
                (native_fee, 0),
                self.eoa,
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

            lz_guid = tx_hash  # Use tx_hash as lookup key for LZ scan

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
