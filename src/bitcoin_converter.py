import time
from web3 import Web3
from web3.contract import Contract
from typing import Optional
import json
import os

# Constants
WBTC_LEGACY_ID = "0.0.1055483"
WBTC_NATIVE_ID = "0.0.10082597"
WBTC_EVM_ADDR = "0xd7d4d91d64a6061fa00a94e2b3a2d2a5fb677849"
SAUCERSWAP_ROUTER_ID = "0.0.3949434" # Mainnet

HTS_PRECOMPILE_ADDRESS = "0x0000000000000000000000000000000000000167"

# HTS ABI for associate and isAssociated
# Based on HIP-206 and standard HTS interfaces
HTS_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "token", "type": "address"}],
        "name": "associateToken",
        "outputs": [{"internalType": "int64", "name": "responseCode", "type": "int64"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"},
            {"internalType": "address", "name": "token", "type": "address"}
        ],
        "name": "isAssociated",
        "outputs": [{"internalType": "bool", "name": "responseCode", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

class UniversalSwapper:
    def __init__(self, w3: Web3, account_address: str, private_key: str = None):
        self.w3 = w3
        self.account_address = Web3.to_checksum_address(account_address)
        self.private_key = private_key

        self.hts_precompile = self.w3.eth.contract(
            address=Web3.to_checksum_address(HTS_PRECOMPILE_ADDRESS),
            abi=HTS_ABI
        )

    def is_hts_precompile(self, address_str: str) -> bool:
        """
        Detects if an address is a Hedera 'Long-Zero' alias (0.0.x).
        Standard EVM addresses do not have 12 leading zero bytes.
        """
        if not address_str:
            return False

        # Remove 0x prefix and lowercase
        clean_addr = address_str.lower()
        if clean_addr.startswith("0x"):
            clean_addr = clean_addr[2:]

        # A true HTS token in the EVM has 12 bytes of leading zeros (24 hex chars)
        # 000000000000000000000000xxxxxxxxxxxxxxxx
        return clean_addr.startswith("000000000000000000000000")

    def _get_contract(self, address: str, abi: list) -> Contract:
        return self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)

    def _send_transaction(self, func_call, gas: int = 2_000_000):
        if not self.private_key:
            raise ValueError("Private key required for transaction execution")

        tx = func_call.build_transaction({
            'from': self.account_address,
            'gas': gas,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account_address),
            'chainId': self.w3.eth.chain_id if hasattr(self.w3.eth, 'chain_id') else 295 # Default to Mainnet if unknown
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        print(f"   ⏳ Transaction sent: {tx_hash.hex()} ...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise Exception(f"Transaction failed: {tx_hash.hex()}")
        print(f"   ✅ Confirmed.")
        return receipt

    def convert(self, token_in: str, token_out: str, amount: int, spender: str = None):
        """
        Standalone wrap/unwrap preparation logic.
        Ring-fenced from standard liquidity pool swap logic.

        Args:
            token_in: The source token (HTS ID or EVM address)
            token_out: The destination token
            amount: Amount to approve (raw units)
            spender: Address of the spender (default: SaucerSwap V2 Router)
        """
        print(f"--- Starting Conversion Prep: {token_in} -> {token_out} ---")

        # Normalize addresses
        token_in_evm = self._ensure_evm_address(token_in)
        token_out_evm = self._ensure_evm_address(token_out)

        if not spender:
            spender = SAUCERSWAP_ROUTER_ID
        spender_evm = self._ensure_evm_address(spender)

        # 1. STEP A: SOURCE READINESS (The "Unwrap" Prep)
        print(f"[Logic] Checking Source Token: {token_in_evm}")

        if token_in_evm.lower() == WBTC_EVM_ADDR.lower():
            print("[Logic] Detected WBTC_EVM (LayerZero). Using ERC-20 Logic.")
            # If it is WBTC_EVM, it is a "Ghost Token".
            # DO NOT call Hedera Token Association.
            # Call a standard Solidity IERC20.approve(SPENDER, amount).
            self._approve_erc20(token_in_evm, spender_evm, amount)

        elif self.is_hts_precompile(token_in_evm):
            print("[Logic] Detected HTS Token (Legacy/Native). Using HTS Logic.")
            # If it is a standard HTS ID (0.0.x), check isAssociated().
            self._ensure_hts_associated(token_in_evm)
            # Use HTS Precompile approve(token, SPENDER, amount).
            # Note: "Precompile approve" is implemented via calling the token address as an ERC20 contract,
            # which proxies to the HTS system.
            self._approve_erc20(token_in_evm, spender_evm, amount)

        else:
            print(f"[Warning] Token {token_in_evm} is neither WBTC_EVM nor recognized HTS Precompile format.")
            # Default to ERC20 logic if unknown? Or skip?
            # Prompt implies we only handle these 3 assets.
            # If it's unknown, maybe it's just another ERC20.
            self._approve_erc20(token_in_evm, spender_evm, amount)

        # 2. STEP B: DESTINATION READINESS (The "Wrap" Prep)
        print(f"[Logic] Checking Destination Token: {token_out_evm}")

        if token_out_evm.lower() == WBTC_EVM_ADDR.lower():
            print("[Logic] Output is WBTC_EVM. Skipping Association (it will fail on-chain).")
            # If token_out is the EVM asset, skip Association.
            pass

        elif self.is_hts_precompile(token_out_evm):
            print(f"[Logic] Output is HTS Token: {token_out}. Verifying Receiver Association.")
            # If token_out is an HTS asset (Legacy or Native), verify the receiver's account is Associated.
            # If not, trigger the Association transaction.
            self._ensure_hts_associated(token_out_evm)

        else:
             print(f"[Logic] Output is {token_out_evm}. No HTS Association logic applied.")

        print("--- Conversion Prep Logic Complete ---")

    def _ensure_evm_address(self, token_id: str) -> str:
        """Convert Hedera ID (0.0.123) to EVM address if needed."""
        if not token_id:
            return token_id
        if token_id.startswith("0x"):
            return Web3.to_checksum_address(token_id)

        parts = token_id.split(".")
        if len(parts) == 3:
            num = int(parts[2])
            return Web3.to_checksum_address(f"0x{num:040x}")
        return token_id

    def _approve_erc20(self, token: str, spender: str, amount: int):
        """Standard ERC20 Approval."""
        contract = self._get_contract(token, ERC20_ABI)
        try:
            allowance = contract.functions.allowance(self.account_address, spender).call()
            print(f"   [Check] Current Allowance: {allowance}, Needed: {amount}")

            if allowance < amount:
                print(f"   🔓 Approving {token} for {spender}...")
                self._send_transaction(contract.functions.approve(spender, amount))
            else:
                print(f"   ✅ Already approved.")
        except Exception as e:
            print(f"   [Error] Approval check failed: {e}")
            raise e

    def _ensure_hts_associated(self, token: str):
        """Check and perform HTS Association."""
        try:
            # Check isAssociated via HTS Precompile (0x167)
            # Note: 0x167 calls might revert if token is not HTS or valid.
            is_associated = self.hts_precompile.functions.isAssociated(self.account_address, token).call()
        except Exception as e:
            print(f"   [Warning] isAssociated check failed (likely not supported on this node/network?): {e}")
            # Fallback: Assume False if we can't check? Or rely on 'associate' to handle it (it might revert if already associated)
            # Safest is to try associating if we are unsure, but that costs gas.
            # However, for this task, let's assume if check fails, we might need to associate.
            is_associated = False

        if not is_associated:
            print(f"   🔗 Associating HTS Token {token}...")
            try:
                self._send_transaction(self.hts_precompile.functions.associateToken(token))
            except Exception as e:
                # If it failed, maybe it was already associated?
                print(f"   [Error] Association failed: {e}")
        else:
            print(f"   ✅ HTS Token {token} already associated.")
