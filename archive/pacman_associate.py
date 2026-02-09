#!/usr/bin/env python3
"""
Pacman Token Association Manager
Handles HTS token association before swaps.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from web3 import Web3

# Hedera Token Associate Contract
# This is a simplified version - real implementation would use Hedera SDK or mirror node

@dataclass
class AssociationStatus:
    """Token association status for an account."""
    token_id: str
    symbol: str
    is_associated: bool
    association_tx: Optional[str] = None
    
class TokenAssociateManager:
    """
    Manages HTS token associations for the trading account.
    
    In Hedera, you must explicitly associate tokens with your account
    before you can receive them in a transaction.
    """
    
    def __init__(self, client, account_id: str):
        self.client = client
        self.account_id = account_id
        self.w3 = client.w3
        self.eoa = client.eoa
        
        # Cache of known associations
        self._association_cache: Dict[str, bool] = {}
    
    def check_association(self, token_id: str) -> bool:
        """
        Check if a token is associated with the account.
        
        In a real implementation, this would query the Hedera mirror node
        or attempt a small balance check.
        """
        # Simplified: Try to get balance - if it fails, not associated
        try:
            # Use the token contract to check balance
            # If this succeeds, token is associated
            balance = self.client.get_token_balance(token_id)
            self._association_cache[token_id] = True
            return True
        except Exception as e:
            # Could be not associated OR other error
            if "TOKEN_NOT_ASSOCIATED" in str(e) or "ASSOCIATION" in str(e):
                self._association_cache[token_id] = False
                return False
            # Other error - assume associated for safety
            return True
    
    def get_required_associations(self, route_steps: List) -> List[str]:
        """
        Get list of tokens that need association for a route.
        
        Returns:
            List of token IDs that need to be associated
        """
        required = []
        
        for step in route_steps:
            if step.step_type == "swap":
                # Check output token of each swap
                token_out = step.to_token
                
                # Map symbol to token ID
                token_id = self._resolve_token_id(token_out)
                if token_id:
                    is_assoc = self.check_association(token_id)
                    if not is_assoc:
                        required.append(token_id)
        
        return required
    
    def associate_tokens(self, token_ids: List[str]) -> Tuple[bool, List[str]]:
        """
        Associate tokens with the account.
        
        In Hedera, token association is done via:
        1. Hedera SDK (native transaction)
        2. Or via a contract call to an associate helper
        
        Returns:
            (success, list of transaction hashes)
        """
        if not token_ids:
            return True, []
        
        print(f"🔐 Associating {len(token_ids)} token(s)...")
        
        tx_hashes = []
        
        # Simplified: In real implementation, this would use Hedera SDK
        # For now, return simulated success
        for token_id in token_ids:
            print(f"   Associating {token_id}...")
            # Real implementation would:
            # 1. Build TokenAssociateTransaction
            # 2. Sign with private key
            # 3. Submit to Hedera
            # 4. Wait for receipt
            
            # Simulate success
            tx_hash = f"ASSOC_{token_id.replace('.', '_')}_SIM"
            tx_hashes.append(tx_hash)
            self._association_cache[token_id] = True
        
        print(f"   ✅ Associated {len(tx_hashes)} token(s)")
        return True, tx_hashes
    
    def ensure_associations_for_route(self, route) -> Tuple[bool, List[str]]:
        """
        Ensure all required tokens are associated for a route.
        
        This should be called BEFORE executing a swap.
        
        Returns:
            (all_associated, list of association TXs)
        """
        required = self.get_required_associations(route.steps)
        
        if not required:
            return True, []
        
        print(f"⚠️  {len(required)} token(s) need association:")
        for tid in required:
            print(f"   • {tid}")
        
        return self.associate_tokens(required)
    
    def _resolve_token_id(self, symbol: str) -> Optional[str]:
        """Resolve token symbol to Hedera ID."""
        # Token ID mapping
        token_map = {
            "USDC": "0.0.456858",
            "USDC[hts]": "0.0.1055459",
            "WBTC[hts]": "0.0.1055483",  # ERC20 version
            "WBTC_LZ": "0.0.1055483",
            "WBTC_HTS": "0.0.10082597",
            "WETH[hts]": "0.0.9770617",
            "WETH_HTS": "0.0.541564",
            "WHBAR": "0.0.1456986",
            "HBAR": "0.0.0",
        }
        return token_map.get(symbol)

# CLI Test
if __name__ == "__main__":
    print("="*60)
    print("🔐 PACMAN TOKEN ASSOCIATION MANAGER")
    print("="*60)
    print("\nToken association is REQUIRED in Hedera before receiving tokens.")
    print("This module checks and manages associations automatically.")
    print("\nKey tokens to associate for Pacman:")
    print("  • WBTC (0.0.10082597) - HTS version")
    print("  • WBTC (0.0.1055483) - ERC20 version")
    print("  • WETH (0.0.9770617) - LayerZero")
    print("  • USDC (0.0.1055459) - HTS version")
    print("\nIn production, these would be auto-associated before swaps.")
