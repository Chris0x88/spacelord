"""
Pacman Staking Plugin
=====================

Isolated module for managing Hedera Native Staking.
Allows the account to stake to a consensus node (e.g., Google Council Node).

Usage:
    manager = StakingManager(network="mainnet")
    manager.set_operator(account_id, private_key)
    receipt = manager.stake_to_node(node_id=5)
"""

from typing import Optional
from hiero_sdk_python.client.client import Client
from hiero_sdk_python.account.account_update_transaction import AccountUpdateTransaction
from hiero_sdk_python.account.account_id import AccountId
from hiero_sdk_python.crypto.private_key import PrivateKey

class StakingManager:
    """
    Manages native staking operations.
    """

    def __init__(self, network: str = "mainnet"):
        self.network = network.lower()
        self.client = self._init_client()

    def _init_client(self) -> Client:
        """Initialize Hiero SDK Client."""
        if self.network == "mainnet":
            return Client.for_mainnet()
        else:
            return Client.for_testnet()

    def set_operator(self, account_id: str, private_key: str):
        """Set the account that pays for transaction fees."""
        if not account_id or not private_key:
            raise ValueError("Account ID and Private Key are required.")

        # Aggressive ECDSA Enforcement
        # We manually decode the hex to bytes and call the explicit 
        # ECDSA constructor to avoid the ambiguous 32-byte warning.
        
        clean_key = private_key.strip().replace("0x", "")
        
        try:
            # 1. Try ECDSA First (Most likely for this user)
            try:
                # Convert hex string to raw bytes (32 bytes)
                key_bytes = bytes.fromhex(clean_key)
                # Call specific ECDSA method to silence SDK warning
                pk_obj = PrivateKey.from_bytes_ecdsa(key_bytes)
            except:
                # 2. Fallback: Re-try with string parser or standard from_bytes
                pk_obj = PrivateKey.from_string(private_key)
            
            # Verify basic key validity
            if not pk_obj:
                raise ValueError("Could not parse Private Key.")

            self.client.set_operator(
                AccountId.from_string(account_id),
                pk_obj
            )
        except Exception as e:
            raise ValueError(f"Invalid credentials: {e}")

    def get_operator_evm_address(self) -> Optional[str]:
        """Return the EVM address derived from the operator's private key."""
        try:
            if not self.client.operator_public_key:
                return None
            # Hiero SDK Public Key -> EVM Address string
            return self.client.operator_public_key.to_evm_address()
        except:
            return None

    def stake_to_node(self, node_id: int, simulate: bool = False) -> dict:
        """
        Update account to stake to a specific Node ID.
        Use node_id=-1 to UNSTAKE.
        """
        if simulate:
            return {
                "success": True,
                "status": "SIMULATED",
                "node_id": node_id,
                "tx_id": "simulated_staking_tx"
            }

        try:
            # We are updating the operator's own account
            operator_id = self.client.operator_account_id
            if not operator_id:
                raise RuntimeError("Operator not set. Call set_operator first.")

            tx = AccountUpdateTransaction().set_account_id(operator_id)
            
            if node_id == -1:
                tx.clear_staked_node_id()
                tx.set_transaction_memo("Pacman Unstake")
            else:
                tx.set_staked_node_id(node_id)
                tx.set_transaction_memo("Pacman Staking Update")

            # Execute
            response = tx.execute(self.client)
            
            # Handle potential difference in SDK return types
            # Some contexts return TransactionResponse (needs get_receipt)
            # Others might return TransactionReceipt directly
            if hasattr(response, "get_receipt"):
                receipt = response.get_receipt(self.client)
                tx_id = str(response.transaction_id)
            else:
                # Assume it's already a receipt
                receipt = response
                # Try to extract tx_id if available, else placeholder
                tx_id = str(getattr(receipt, "transaction_id", "unknown_tx_id"))
            
            is_success = (str(receipt.status) == "SUCCESS")
            return {
                "success": is_success,
                "status": str(receipt.status),
                "node_id": node_id,
                "tx_id": tx_id,
                "error": None if is_success else f"Transaction Status: {receipt.status}"
            }

        except Exception as e:
            return {
                "success": False, 
                "error": str(e)
            }
