#!/usr/bin/env python3
"""
Pacman App - Main Application Controller
=========================================

The PacmanApp class coordinates the various components of the Pacman CLI:
- Configuration (PacmanConfig)
- Routing (PacmanVariantRouter)
- Execution (PacmanExecutor)
- Price Management (PacmanPriceManager)

It provides a high-level API for the CLI to interact with.
"""

import logging
from typing import Optional, Dict

from pacman_config import PacmanConfig
from pacman_logger import logger
from pacman_errors import PacmanError, ConfigurationError
from pacman_executor import PacmanExecutor, ExecutionResult
from pacman_variant_router import PacmanVariantRouter, VariantRoute
from pacman_price_manager import price_manager

class PacmanApp:
    """
    Main application class for Pacman.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the application components."""
        try:
            self.config = PacmanConfig.from_env()
            self.executor = PacmanExecutor(self.config)
            self.router = PacmanVariantRouter(price_manager=price_manager)
            
            # Record account details for display
            self.account_id = self.config.hedera_account_id
            self.network = self.config.network
            
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize PacmanApp: {e}")
            raise

    def get_balances(self) -> Dict[str, float]:
        """Fetch all non-zero token balances for the account."""
        return self.executor.get_all_balances()

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
            amount_usd=usd_value
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

    def transfer(self, token_symbol: str, amount: float, recipient: str) -> dict:
        """
        Send tokens to another address.
        """
        from pacman_transfers import execute_transfer
        return execute_transfer(self.executor, token_symbol, amount, recipient)

    def get_history(self, limit: int = 10):
        """Get execution history."""
        return self.executor.get_execution_history(limit)
