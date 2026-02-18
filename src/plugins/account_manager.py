"""
Pacman Account Manager Plugin
=============================

Standalone module for native Hedera account operations using hiero-sdk-python.
Features:
- New Account Creation (funded by existing account)
- Sub-account Creation (same key, funded by parent)
"""

import os
from typing import Optional, Tuple
from hiero_sdk_python.client.client import Client
from hiero_sdk_python.account.account_create_transaction import AccountCreateTransaction
from hiero_sdk_python.account.account_id import AccountId
from hiero_sdk_python.crypto.private_key import PrivateKey
from hiero_sdk_python.hbar import Hbar

class AccountManager:
    """
    Handles native Hedera account creation and management.
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
        # Clean private key
        clean_key = private_key.replace("0x", "")
        self.client.set_operator(
            AccountId.from_string(account_id),
            PrivateKey.from_string(clean_key)
        )

    def create_account(self, 
                       initial_balance_hbar: float = 1.0, 
                       alias_key: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a new Hedera account.
        If alias_key is provided, it creates a sub-account using that key.
        Otherwise, it generates a new key pair.

        Returns: (account_id, private_key)
        """
        try:
            # 1. Prepare Key
            if alias_key:
                new_key = PrivateKey.from_string(alias_key.replace("0x", ""))
                is_sub_account = True
            else:
                new_key = PrivateKey.generate_ecdsa() # Default to ECDSA for EVM compatibility
                is_sub_account = False

            # 2. Construct Transaction
            # Note: initial_balance is sent from the operator account
            tx = AccountCreateTransaction() \
                .set_key(new_key.get_public_key()) \
                .set_initial_balance(Hbar.from_hbar(initial_balance_hbar)) \
                .set_account_memo("Pacman Created Account")

            # 3. Execute
            response = tx.execute(self.client)
            receipt = response.get_receipt(self.client)
            
            new_id = str(receipt.account_id)
            
            return new_id, (None if is_sub_account else str(new_key))

        except Exception as e:
            print(f"   ❌ Account creation failed: {e}")
            return None, None

    def create_sub_account(self, initial_balance_hbar: float = 1.0) -> Optional[str]:
        """
        Create a new Account ID using the current operator's Private Key.
        """
        # Get current operator key to use for the new account
        operator_key = self.client.operator_private_key
        if not operator_key:
            raise RuntimeError("Operator key not set. Call set_operator() first.")
        
        new_id, _ = self.create_account(
            initial_balance_hbar=initial_balance_hbar,
            alias_key=str(operator_key)
        )
        return new_id
