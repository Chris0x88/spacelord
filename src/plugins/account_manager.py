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
        
        # Explicitly use ECDSA for this wallet to avoid SDK ambiguity (Ed25519 vs ECDSA)
        try:
             # If it's a 32-byte hex, we force ECDSA interpretation
             key_bytes = bytes.fromhex(clean_key)
             if len(key_bytes) == 32:
                 pk = PrivateKey.from_bytes_ecdsa(key_bytes)
             else:
                 pk = PrivateKey.from_string(clean_key)
        except Exception:
             pk = PrivateKey.from_string(clean_key)

        self.client.set_operator(
            AccountId.from_string(account_id),
            pk
        )
        self.operator_id = account_id
        self._operator_raw_key = clean_key # Cache raw key securely (internal only)

    def get_known_accounts(self) -> list:
        """Get the list of known account IDs from the local registry."""
        import json
        from pathlib import Path
        
        accounts_path = Path("data/accounts.json")
        if not accounts_path.exists():
            return []
            
        try:
            with open(accounts_path) as f:
                return json.load(f)
        except Exception:
            return []

    def _save_account(self, account_id: str, type: str = "imported", nickname: str = ""):
        """Save an account ID to the local registry."""
        import json
        from pathlib import Path
        import time
        from src.logger import logger

        accounts_path = Path("data/accounts.json")
        accounts = self.get_known_accounts()

        # Check if already exists — update nickname if provided
        for a in accounts:
            if a.get("id") == account_id:
                if nickname:
                    a["nickname"] = nickname
                    try:
                        with open(accounts_path, "w") as f:
                            json.dump(accounts, f, indent=4)
                    except Exception as e:
                        logger.error(f"Failed to update nickname: {e}")
                return

        accounts.append({
            "id": account_id,
            "type": type,
            "nickname": nickname,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        try:
            accounts_path.parent.mkdir(parents=True, exist_ok=True)
            with open(accounts_path, "w") as f:
                json.dump(accounts, f, indent=4)
            logger.info(f"Saved account {account_id} ('{nickname}') to registry.")
        except Exception as e:
            logger.error(f"Failed to save account to registry: {e}")

    def create_account(self, 
                       initial_balance_hbar: float = 1.0, 
                       alias_key: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a new Hedera account.
        If alias_key is provided, it creates a sub-account using that key.
        Otherwise, it generates a new key pair.

        Returns: (account_id, private_key)
        """
        is_sub_account = (alias_key is not None)
        
        try:
            # 1. Prepare Key
            if is_sub_account:
                # Force ECDSA for sub-accounts too
                clean_alias = alias_key.replace("0x", "")
                key_bytes = bytes.fromhex(clean_alias)
                if len(key_bytes) == 32:
                    new_key = PrivateKey.from_bytes_ecdsa(key_bytes)
                else:
                    new_key = PrivateKey.from_string(clean_alias)
            else:
                new_key = PrivateKey.generate_ecdsa()

            # 2. Construct Transaction
            # Note: initial_balance is sent from the operator account
            tx = AccountCreateTransaction() \
                .set_key(new_key.public_key()) \
                .set_initial_balance(Hbar.from_hbars(initial_balance_hbar)) \
                .set_max_automatic_token_associations(-1) \
                .set_account_memo("Pacman Created Account")

            # Set EVM Alias for ECDSA keys to ensure wallet compatibility (HashPack/Metamask)
            if new_key.public_key().is_ecdsa():
                evm_address = new_key.public_key().to_evm_address()
                tx.set_alias(evm_address)

            # 3. Execute
            tx.freeze_with(self.client)
            response = tx.execute(self.client)
            
            # Handle potential difference in SDK return types (Proven pattern from staking.py)
            if hasattr(response, "get_receipt"):
                receipt = response.get_receipt(self.client)
            else:
                # Assume it's already a receipt
                receipt = response
            
            new_id = str(receipt.account_id)
            return new_id, (None if is_sub_account else new_key.to_string())

        except Exception as e:
            # Strip potential key data from error messages for security
            err_msg = str(e)
            if "hex" in err_msg.lower() or "string" in err_msg.lower():
                err_msg = "Invalid key format or permission error."
            print(f"   ❌ Account creation failed: {err_msg}")
            return None, None

    def create_sub_account(self, initial_balance_hbar: float = 1.0, nickname: str = "") -> Optional[str]:
        """
        Create a new Account ID using the current operator's Private Key.
        Automatically saves to the local registry with an optional nickname.
        """
        if not hasattr(self, "_operator_raw_key") or not self._operator_raw_key:
            raise RuntimeError("Operator key not set. Call set_operator() first.")

        new_id, _ = self.create_account(
            initial_balance_hbar=initial_balance_hbar,
            alias_key=self._operator_raw_key
        )

        if new_id:
            self._save_account(new_id, type="derived", nickname=nickname)

        return new_id

    def rename_account(self, account_id: str, nickname: str) -> bool:
        """
        Update the nickname for an existing account in the local registry.
        Returns True if found and updated, False if not found.
        """
        import json
        from pathlib import Path
        from src.logger import logger

        accounts_path = Path("data/accounts.json")
        accounts = self.get_known_accounts()

        updated = False
        for a in accounts:
            if a.get("id") == account_id:
                a["nickname"] = nickname
                updated = True
                break

        if not updated:
            return False

        try:
            with open(accounts_path, "w") as f:
                json.dump(accounts, f, indent=4)
            logger.info(f"Updated nickname for {account_id} to '{nickname}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to rename account: {e}")
            return False
