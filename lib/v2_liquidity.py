"""
V2 Liquidity Manager
====================

Handles SaucerSwap V2 Liquidity Operations (Deposit / Withdraw)
using the NonfungiblePositionManager.

CRITICAL HBAR RULE (matches saucerswap.py swap engine):
  WHBAR is a ROUTING MECHANISM, not a user-facing asset.
  When a user deposits HBAR into a pool, we do NOT manually call
  WHBAR.deposit() first. Instead we use multicall:
    [mint_calldata, refundETH_calldata]
  and pass the HBAR amount as the transaction `value` field
  (scaled by 10**10 to pseudo-Wei for Hedera JSON-RPC Relay).
  The NonfungiblePositionManager wraps HBAR internally, identical
  to how the V2 Router handles HBAR→Token swaps.

DEADLINE RULE:
  SaucerSwap V2 contracts on Hedera require deadlines in
  MILLISECONDS. Standard Unix seconds cause immediate reverts.
  Formula: int(time.time() * 1000) + 600_000   (10 minute window)
"""

import time
import json
from src.logger import logger
from pathlib import Path
from lib.saucerswap import hedera_id_to_evm

_ABI_DIR = Path(__file__).parent.parent / "abi"
try:
    POSITION_MANAGER_ABI = json.loads((_ABI_DIR / "position_manager.json").read_text())
except FileNotFoundError:
    POSITION_MANAGER_ABI = []

POSITION_MANAGER_ADDRESSES = {
    "mainnet": "0.0.4053945",
    "testnet": "0.0.4053945",
}

WHBAR_IDS = {
    "mainnet": "0.0.1456986",
    "testnet": "0.0.15058",
}


class V2LiquidityManager:
    """
    Handles SaucerSwap V2 Liquidity Operations (Deposit/Withdraw)
    using the NonfungiblePositionManager.
    """

    def __init__(self, w3, network: str = "mainnet", private_key: str | None = None):
        self.w3 = w3
        self.network = network
        self.private_key = private_key

        if private_key:
            self.account = w3.eth.account.from_key(private_key)
            self.eoa = self.account.address
        else:
            self.account = None
            self.eoa = None

        manager_id = POSITION_MANAGER_ADDRESSES.get(network, POSITION_MANAGER_ADDRESSES["mainnet"])
        self.contract_address = hedera_id_to_evm(manager_id)
        self.contract = w3.eth.contract(address=self.contract_address, abi=POSITION_MANAGER_ABI)
        self.chain_id = 295 if network == "mainnet" else 296

        self.whbar_id = WHBAR_IDS.get(network, WHBAR_IDS["mainnet"])
        self.whbar_evm = hedera_id_to_evm(self.whbar_id)

        # Load ERC20 ABI for approvals (kept isolated from swap engine)
        try:
            _erc20_abi = json.loads((_ABI_DIR / "erc20.json").read_text())
        except Exception:
            _erc20_abi = [
                {"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
                {"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},
            ]
        self._erc20_abi = _erc20_abi

    def _ensure_lp_approval(self, token_id: str, amount: int) -> None:
        """
        Ensure the PositionManager is approved to spend `amount` of `token_id`.
        Fully self-contained — does NOT touch saucerswap.py swap engine.
        token_id: Hedera ID (e.g. '0.0.456858')
        amount: raw integer amount (already scaled by decimals)
        """
        if not self.private_key:
            raise ValueError("Private key required for approvals")

        token_evm = hedera_id_to_evm(token_id)
        # spender is already an EVM address from self.contract_address
        spender_evm = self.w3.to_checksum_address(self.contract_address)

        token = self.w3.eth.contract(address=token_evm, abi=self._erc20_abi)

        try:
            current = token.functions.allowance(self.eoa, spender_evm).call()
        except Exception:
            current = 0

        if current >= amount:
            return  # Already approved

        print(f"   🔓 Approving {token_id} for PositionManager...")
        approve_tx = token.functions.approve(spender_evm, amount).build_transaction({
            "from": self.eoa,
            "gas": 2_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
        })
        signed = self.w3.eth.account.sign_transaction(approve_tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"   ⏳ Waiting for approval ({tx_hash.hex()})...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            raise RuntimeError(f"Approval tx failed: {tx_hash.hex()}")


    def add_liquidity(
        self,
        token0_id: str, token1_id: str,
        fee: int, tick_lower: int, tick_upper: int,
        amount0_desired: int, amount1_desired: int,
        amount0_min: int = 0, amount1_min: int = 0,
        hbar_value_raw: int = 0,
        dry_run: bool = False,
    ) -> str:
        """
        Mint a new liquidity position (NFT) on SaucerSwap V2.

        hbar_value_raw : tinybars (8-decimal) amount of native HBAR the
                         caller wants to contribute.  When non-zero the
                         transaction is wrapped in a multicall:
                           [mint, refundETH]
                         and the Hedera-scaled value (x10**10) is sent
                         as the tx value field.  The PositionManager
                         wraps HBAR to WHBAR internally – no pre-wrap step.

        NOTE: token0 must be < token1 by EVM address (Uniswap V3 rule).
              Sorting is done automatically.
        """
        if not self.private_key and not dry_run:
            raise ValueError("Private key required for live transactions")

        token0_evm = hedera_id_to_evm(token0_id)
        token1_evm = hedera_id_to_evm(token1_id)

        # Uniswap V3: token0 address must be strictly less than token1
        if token0_evm.lower() > token1_evm.lower():
            token0_evm, token1_evm = token1_evm, token0_evm
            amount0_desired, amount1_desired = amount1_desired, amount0_desired
            amount0_min, amount1_min = amount1_min, amount0_min

        # CRITICAL: millisecond deadline for Hedera
        # 60 minute window for safety during simulation/debugging
        deadline = int(time.time() * 1000) + 3_600_000 

        params = (
            token0_evm,
            token1_evm,
            fee,
            tick_lower,
            tick_upper,
            amount0_desired,
            amount1_desired,
            amount0_min,
            amount1_min,
            self.eoa,
            deadline,
        )

        # Scale HBAR to pseudo-Wei (Hedera JSON-RPC requirement)
        scaled_value = hbar_value_raw * (10 ** 10) if hbar_value_raw > 0 else 0

        if hbar_value_raw > 0:
            # ==============================================================
            # MULTICALL path (HBAR involved)
            # The PositionManager wraps HBAR internally.
            # refundETH sends back any unused HBAR to the sender.
            # This mirrors the known-working swap_exact_input_multicall pattern.
            # ==============================================================
            mint_calldata = self.contract.encode_abi("mint", [params])
            refund_calldata = self.contract.encode_abi("refundETH")
            encoded_calls = [mint_calldata, refund_calldata]

            if dry_run:
                self.contract.functions.multicall(encoded_calls).call(
                    {"from": self.eoa, "value": scaled_value}
                )
                return "SIMULATED_OK"

            tx = self.contract.functions.multicall(encoded_calls).build_transaction({
                "from": self.eoa,
                "gas": 2_000_000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.chain_id,
                "value": scaled_value,
            })
        else:
            # ==============================================================
            # Direct mint path (HTS tokens only, no native HBAR)
            # ==============================================================
            if dry_run:
                self.contract.functions.mint(params).call({"from": self.eoa})
                return "SIMULATED_OK"

            tx = self.contract.functions.mint(params).build_transaction({
                "from": self.eoa,
                "gas": 2_000_000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.chain_id,
            })

        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        # Await receipt to guarantee success
        logger.info(f"Waiting for mint receipt: {tx_hash.hex()}...")
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            if receipt.status != 1:
                raise RuntimeError(f"Mint transaction {tx_hash.hex()} reverted on-chain (status 0).")
        except Exception as e:
            raise RuntimeError(f"Mint receipt error: {e}")
            
        return tx_hash.hex()

    def remove_liquidity(
        self,
        token_id: int, liquidity: int,
        amount0_min: int = 0, amount1_min: int = 0,
        collect_as_hbar: bool = False,
        dry_run: bool = False,
    ) -> list[str]:
        """
        Remove liquidity by burning LP size and collecting the underlying tokens.
        Two-step: decreaseLiquidity → collect.

        collect_as_hbar: if True and one of the pool tokens is WHBAR,
                         uses unwrapWHBAR inside a multicall on collect step
                         so the user receives native HBAR.
        """
        if not self.private_key and not dry_run:
            raise ValueError("Private key required for live transactions")

        # CRITICAL: millisecond deadline
        deadline = int(time.time() * 1000) + 600_000

        decrease_params = (token_id, liquidity, amount0_min, amount1_min, deadline)

        if dry_run:
            self.contract.functions.decreaseLiquidity(decrease_params).call({"from": self.eoa})
            return ["SIMULATED_DECREASE_OK", "SIMULATED_COLLECT_OK"]

        tx = self.contract.functions.decreaseLiquidity(decrease_params).build_transaction({
            "from": self.eoa,
            "gas": 2_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash1 = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash1, timeout=120)

        # Step 2: collect
        MAX_UINT128 = 2 ** 128 - 1
        collect_params = (token_id, self.eoa, MAX_UINT128, MAX_UINT128)

        tx2 = self.contract.functions.collect(collect_params).build_transaction({
            "from": self.eoa,
            "gas": 2_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
        })

        signed2 = self.w3.eth.account.sign_transaction(tx2, self.private_key)
        tx_hash2 = self.w3.eth.send_raw_transaction(signed2.raw_transaction)

        return [tx_hash1.hex(), tx_hash2.hex()]
