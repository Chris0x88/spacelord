"""
Pacman Controller - Headless Trading SDK
=========================================

The PacmanController class orchestrates the business logic:
- Configuration (PacmanConfig)
- Routing (PacmanVariantRouter)
- Execution (PacmanExecutor)

It is designed to be imported by CLIs, Daemons, or Web APIs.
"""

import logging
import requests
from typing import Optional, Dict, Tuple

from src.config import PacmanConfig
from src.logger import logger
from src.errors import PacmanError, ConfigurationError
from src.executor import PacmanExecutor, ExecutionResult
from src.router import PacmanVariantRouter, VariantRoute
from lib.prices import price_manager

class PacmanController:
    """
    Main controller class for Pacman.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the application components."""
        try:
            self.config = PacmanConfig.from_env()
            self.executor = PacmanExecutor(self.config)
            self.router = PacmanVariantRouter(price_manager=price_manager)
            self.router.load_pools() # Build routing graph from cached data
            
            # Record account details for display
            self.account_id = self.config.hedera_account_id
            self.network = self.config.network
            self._account_manager = None
            
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize PacmanApp: {e}")
            raise

    def get_balances(self) -> Dict[str, float]:
        """Fetch all non-zero token balances for the account."""
        return self.executor.get_balances()

    def resolve_token_id(self, symbol: str) -> Optional[str]:
        """Resolve a token symbol to a Hedera ID."""
        return self.executor._get_token_id(symbol)

    def get_route(self, from_token: str, to_token: str, amount: float, mode: str = "exact_in") -> Optional[VariantRoute]:
        """
        Recommend the best route between variants.
        """
        # Clean inputs
        from_token = from_token.upper()
        to_token = to_token.upper()

        logger.debug(f"Routing request: {from_token} -> {to_token} (Amount: {amount}, Mode: {mode})")

        # 1. Calculate USD Value (Estimated) for Routing logic
        # For exact_in, amount is in from_token. For exact_out, amount is in to_token.
        basis_token = from_token if mode == "exact_in" else to_token
        usd_value = amount
        
        try:
            meta = self.router._get_token_meta(basis_token)
            token_id = meta["id"] if meta and "id" in meta else None
            
            if not token_id and basis_token in ["HBAR", "0.0.0", "WHBAR"]:
                token_id = "0.0.0"

            if token_id:
                if price_manager.hbar_price == 0:
                    price_manager.reload()
                
                # Get price from manager
                if token_id == "0.0.0":
                    price = price_manager.get_hbar_price()
                else:
                    price = price_manager.get_price(token_id)
                
                if price > 0:
                    usd_value = amount * price
        except Exception as e:
            logger.warning(f"Failed to calculate USD value for routing: {e}")

        # Router calculates fee impact in HBAR using this USD value
        return self.router.recommend_route(
            from_variant=from_token,
            to_variant=to_token,
            user_preference="auto",
            volume_usd=usd_value
        )

    def swap(self, from_token: str, to_token: str, amount: float, mode: str = "exact_in") -> ExecutionResult:
        """
        Execute a swap.
        """
        route = self.get_route(from_token, to_token, amount, mode=mode)
        if not route:
            raise PacmanError(f"No route found for {from_token} -> {to_token}")

        # Execution using the refactored raw_amount parameter
        return self.executor.execute_swap(
            route=route,
            raw_amount=amount,
            mode=mode
        )

    def transfer(self, token_symbol: str, amount: float, recipient: str, memo: str = None) -> dict:
        """
        Send tokens to another address.
        """
        from lib.transfers import execute_transfer
        return execute_transfer(self.executor, token_symbol, amount, recipient, memo=memo)

    def get_history(self, limit: int = 10):
        """Get execution history."""
        return self.executor.get_execution_history(limit)

    def toggle_verbose(self, enabled: bool = None):
        """Toggle debug logging."""
        from src.logger import set_verbose
        if enabled is not None:
             self.config.debug = enabled
        else:
             self.config.debug = not self.config.debug
             
        set_verbose(self.config.debug)
        return self.config.debug

    def resolve_account_id(self, eoa: str) -> Optional[str]:
        """
        Query Mirror Node to find the Hedera Account ID associated with an EVM EOA.
        Returns the '0.0.xxx' ID or None if not found.
        """
        if not eoa or not eoa.startswith("0x"):
            return None

        network = self.config.network
        base_url = "https://mainnet-public.mirrornode.hedera.com" if network == "mainnet" else "https://testnet.mirrornode.hedera.com"
        url = f"{base_url}/api/v1/accounts/{eoa}"

        try:
            logger.debug(f"Discovering Hedera ID for {eoa}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("account")
            elif response.status_code == 404:
                logger.warning(f"Account {eoa} not found on Mirror Node. might be new/uninitialized.")
                return None
            else:
                logger.error(f"Mirror Node error ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to resolve account ID: {e}")
            return None

    @property
    def account_manager(self):
        """Lazy initialization of the AccountManager plugin."""
        if self._account_manager is None:
            from src.plugins.account_manager import AccountManager
            self._account_manager = AccountManager(network=self.network)
            # If we have a key, set it as operator
            if self.config.private_key:
                pk = self.config.private_key.reveal()
                # Basic validation: must be 64-char hex string (32 bytes)
                clean_pk = pk.replace("0x", "")
                if len(clean_pk) == 64 and self.account_id and "." in str(self.account_id):
                    try:
                        self._account_manager.set_operator(self.account_id, pk)
                    except Exception as e:
                        logger.warning(f"Could not set operator with ID '{self.account_id}': {e}")
                del pk
        return self._account_manager

    def create_new_account(self, initial_balance: float = 1.0) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a completely new Hedera account with a fresh private key.
        The creation is funded by the current operator account.
        """
        return self.account_manager.create_account(initial_balance_hbar=initial_balance)

    def create_sub_account(self, initial_balance: float = 1.0) -> Optional[str]:
        """
        Create a new Account ID that uses the SAME private key as the current account.
        """
        return self.account_manager.create_sub_account(initial_balance_hbar=initial_balance)

    def get_known_accounts(self) -> list:
        """Get the list of known account IDs from the local registry."""
        return self.account_manager.get_known_accounts()


    def approve_pool(self, pool_data: dict, protocol: str = "v2"):
        """
        Add a pool to the local approved registry.
        """
        import json
        from pathlib import Path
        
        protocol = protocol.lower()
        reg_file = "data/pools.json" if protocol == "v2" else "data/v1_pools_approved.json"
        reg_path = Path(reg_file)
        
        # 1. Load existing
        registry = []
        if reg_path.exists():
            with open(reg_path) as f:
                registry = json.load(f)
                
        # 2. Check if already exists
        pool_id = pool_data.get("contractId")
        if any(p.get("contractId") == pool_id for p in registry):
            logger.info(f"Pool {pool_id} already in {protocol} registry.")
            # Still sync tokens in case they are missing from tokens.json
            self._sync_pool_tokens(pool_data)
            return False

        # 3. Convert format if needed
        # Expected: {contractId, tokenA, tokenB, fee, label}
        fee = pool_data.get("fee")
        if protocol == "v1" and fee is None:
            fee = 3000 # Default V1 fee is 0.3%

        entry = {
            "contractId": pool_id,
            "tokenA": pool_data.get("tokenA", {}).get("id") if isinstance(pool_data.get("tokenA"), dict) else pool_data.get("tokenA"),
            "tokenB": pool_data.get("tokenB", {}).get("id") if isinstance(pool_data.get("tokenB"), dict) else pool_data.get("tokenB"),
            "fee": fee,
            "label": f"{pool_data.get('tokenA', {}).get('symbol')}/{pool_data.get('tokenB', {}).get('symbol')}"
        }
        
        registry.append(entry)
        
        # 4. Save
        with open(reg_path, "w") as f:
            json.dump(registry, f, indent=4)
        
        # 5. Sync tokens to main registry
        self._sync_pool_tokens(pool_data)

        logger.info(f"Approved {protocol} pool: {entry['label']} ({pool_id})")
        self.router.load_pools() # Reload graph
        return True

    def _sync_pool_tokens(self, pool_data: dict):
        """Extract tokens from pool data and add to tokens.json if missing."""
        import json
        from pathlib import Path
        
        tokens_path = Path("data/tokens.json")
        if not tokens_path.exists():
            return
            
        try:
            with open(tokens_path) as f:
                tokens = json.load(f)
                
            updated = False
            for key in ["tokenA", "tokenB"]:
                t = pool_data.get(key)
                if not isinstance(t, dict): continue
                
                tid = t.get("id")
                symbol = t.get("symbol")
                if not tid or not symbol: continue
                
                # Check if ID already exists under any key
                exists = any(meta.get("id") == tid for meta in tokens.values())
                if not exists:
                    # Add to registry
                    tokens[symbol] = {
                        "id": tid,
                        "decimals": t.get("decimals", 8),
                        "symbol": symbol,
                        "name": t.get("name", symbol)
                    }
                    updated = True
                    logger.info(f"Sync: Added new token {symbol} ({tid}) to registry.")
                    
            if updated:
                with open(tokens_path, "w") as f:
                    json.dump(tokens, f, indent=2)
        except Exception as e:
            logger.debug(f"Token sync failed: {e}")

    def remove_pool(self, pool_id: str, protocol: str = "v2"):
        """
        Remove a pool from the local approved registry.
        """
        import json
        from pathlib import Path
        
        protocol = protocol.lower()
        reg_file = "data/pools.json" if protocol == "v2" else "data/v1_pools_approved.json"
        reg_path = Path(reg_file)
        
        if not reg_path.exists():
            return False
            
        with open(reg_path) as f:
            registry = json.load(f)
            
        new_registry = [p for p in registry if p.get("contractId") != pool_id]
        
        if len(new_registry) == len(registry):
            return False
            
        with open(reg_path, "w") as f:
            json.dump(new_registry, f, indent=4)
            
        logger.info(f"Removed {protocol} pool: {pool_id}")
        self.router.load_pools() # Reload graph
        return True

    def is_v1_only(self, symbol_in: str, symbol_out: str) -> bool:
        """
        Check if a pair only exists in the approved V1 registry.
        Returns True if the pair is in V1 AND either token is not in V2.
        """
        import json
        from pathlib import Path
        
        symbol_in = symbol_in.upper()
        symbol_out = symbol_out.upper()
        
        # 1. Load V1
        v1_reg_path = Path("data/v1_pools_approved.json")
        if not v1_reg_path.exists():
            return False
            
        try:
            with open(v1_reg_path) as f:
                v1_reg = json.load(f)
                
            in_v1 = False
            for p in v1_reg:
                label = p.get("label", "").upper()
                if symbol_in in label and symbol_out in label:
                    in_v1 = True
                    break
            
            if not in_v1:
                return False
                
            # 2. Check if either is completely missing from V2 pools
            # Note: Native HBAR and major stables are guaranteed to be in V2 
            # if the registry is healthy, but we check specifically for community tokens.
            if symbol_in in ["HBAR", "0.0.0", "WHBAR", "USDC", "USDT"] and \
               symbol_out in ["HBAR", "0.0.0", "WHBAR", "USDC", "USDT"]:
                return False # Top pairs always have V2

            v2_reg_path = Path("data/pools.json")
            if not v2_reg_path.exists():
                return True # No V2 registry means it's V1-only by default if it was in V1
                
            with open(v2_reg_path) as f2:
                v2_reg = json.load(f2)
                # Check tokens in V2 - symbols are often in the tokenA/tokenB symbol field in pools.json
                # But router.py's pool_graph is the true source.
                # However, for a simple hint, checking the pool metadata symbols is enough.
                in_v2_in = any(p.get("tokenA", {}).get("symbol") == symbol_in or p.get("tokenB", {}).get("symbol") == symbol_in for p in v2_reg)
                in_v2_out = any(p.get("tokenA", {}).get("symbol") == symbol_out or p.get("tokenB", {}).get("symbol") == symbol_out for p in v2_reg)
                
                return not (in_v2_in and in_v2_out)

        except Exception as e:
            logger.debug(f"is_v1_only check failed: {e}")
            return False

    # ---------------------------------------------------------------------------
    # Whitelist Management
    # ---------------------------------------------------------------------------

    def get_whitelist(self) -> list:
        """Get the list of whitelisted transfer recipients."""
        import json
        from pathlib import Path
        
        try:
            with open("data/settings.json") as f:
                settings = json.load(f)
                return settings.get("transfer_whitelist", [])
        except Exception:
            return []

    def add_to_whitelist(self, address: str) -> bool:
        """Add an address to the transfer whitelist."""
        import json
        from pathlib import Path
        import re
        
        # Validate format (0.0.xxx)
        if not re.match(r"^0\.0\.\d+$", address):
            logger.error(f"Invalid Hedera ID format: {address}")
            return False
            
        settings_path = Path("data/settings.json")
        if not settings_path.exists():
            return False
            
        try:
            with open(settings_path) as f:
                settings = json.load(f)
                
            whitelist = settings.get("transfer_whitelist", [])
            if address in whitelist:
                logger.info(f"Address {address} already in whitelist.")
                return True
                
            whitelist.append(address)
            settings["transfer_whitelist"] = whitelist
            
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
                
            logger.info(f"Added {address} to whitelist.")
            return True
        except Exception as e:
            logger.error(f"Failed to update whitelist: {e}")
            return False

    def remove_from_whitelist(self, address: str) -> bool:
        """Remove an address from the transfer whitelist."""
        import json
        from pathlib import Path
        
        settings_path = Path("data/settings.json")
        if not settings_path.exists():
            return False
            
        try:
            with open(settings_path) as f:
                settings = json.load(f)
                
            whitelist = settings.get("transfer_whitelist", [])
            if address not in whitelist:
                logger.info(f"Address {address} not in whitelist.")
                return False
                
            whitelist.remove(address)
            settings["transfer_whitelist"] = whitelist
            
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
                
            logger.info(f"Removed {address} from whitelist.")
            return True
        except Exception as e:
            logger.error(f"Failed to update whitelist: {e}")
            return False
