#!/usr/bin/env python3
"""
Pacman App - The Controller
===========================

The central brain that orchestrates:
1. Configuration (Env/User)
2. Routing (Finding paths)
3. Execution (Swapping/Bridging)
4. State Management (Balances/History)

This class is the "Public API" of the Pacman library.
"""

from typing import Optional, Dict, List, Any
from pacman_logger import logger, set_verbose
from pacman_config import PacmanConfig
from pacman_errors import PacmanError, ConfigurationError
from pacman_variant_router import PacmanVariantRouter, VariantRoute
from pacman_executor import PacmanExecutor, ExecutionResult
from pacman_price_manager import price_manager

class PacmanApp:
    """
    High-level controller for Hedera DeFi operations.
    """

    def __init__(self, config: Optional[PacmanConfig] = None):
        """
        Initialize the Pacman Application.

        Args:
            config: Optional pre-loaded config. If None, loads from env.
        """
        # 1. Load Configuration
        self.config = config or PacmanConfig.from_env()

        # 2. Set Logging Level
        if self.config.verbose_mode:
            set_verbose(True)
            logger.debug("Verbose Mode Enabled")

        # 3. Initialize Components
        self.router = PacmanVariantRouter()

        # Executor is lazy-loaded to allow lightweight usage (e.g. quote only)
        self._executor: Optional[PacmanExecutor] = None

    def toggle_verbose(self, enabled: Optional[bool] = None) -> bool:
        """
        Toggle or set verbose logging mode.
        
        Args:
            enabled: Specific state to set, or None to toggle.
        """
        if enabled is None:
            enabled = not self.config.verbose_mode
        
        self.config.verbose_mode = enabled
        set_verbose(enabled)
        return enabled

        # Load static data
        try:
            self.router.load_pools(pools_file="data/pacman_data_raw.json")
        except Exception:
            # Non-fatal if just starting up, but routing won't work
            pass

    @property
    def executor(self) -> PacmanExecutor:
        """Lazy-load the executor."""
        if not self._executor:
            # Validate config before initializing executor
            if not self.config.private_key and not self.config.simulate_mode:
                raise ConfigurationError("Private key required for live execution.")

            self._executor = PacmanExecutor(self.config)
        return self._executor

    def get_balance(self, token_symbol: Optional[str] = None) -> Dict[str, float]:
        """
        Get wallet balance(s).

        Args:
            token_symbol: Specific token (e.g. "USDC") or None for all.
        """
        balances = self.executor.get_balances()
        if token_symbol:
            # Fuzzy match or exact match
            normalized = token_symbol.upper()
            if normalized in balances:
                return {normalized: balances[normalized]}
            return {}
        return balances

    def get_route(self, from_token: str, to_token: str, amount: float) -> Optional[VariantRoute]:
        """
        Find the best route for a swap.
        """
        # Clean inputs
        from_token = from_token.upper()
        to_token = to_token.upper()

        # Resolve Variants (e.g. USDC -> USDC[hts] if preferred)
        # For now, simplistic routing logic from the variant router
        return self.router.recommend_route(
            from_variant=from_token,
            to_variant=to_token,
            user_preference="auto",
            amount_usd=amount # Approximation
        )

    def swap(self, from_token: str, to_token: str, amount: float, mode: str = "exact_in") -> ExecutionResult:
        """
        Execute a swap.

        Args:
            from_token: Input token symbol.
            to_token: Output token symbol.
            amount: Amount of input (or output if exact_out).
            mode: "exact_in" or "exact_out".
        """
        route = self.get_route(from_token, to_token, amount)
        if not route:
            raise PacmanError(f"No route found for {from_token} -> {to_token}")

        # Security: Check limits (Hardcoded in config, but good to enforce here)
        # Ideally we check USD value here.

        return self.executor.execute_swap(
            route=route,
            amount_usd=amount, # Passing raw amount as 'usd' param in legacy executor signature
            mode=mode
        )

    def transfer(self, token_symbol: str, amount: float, recipient: str) -> dict:
        """
        Send tokens to another address.
        """
        # This requires porting execute_transfer logic to be a method of Executor or App
        # For now, we delegate to the existing transfer module but wrap it
        from pacman_transfers import execute_transfer
        return execute_transfer(self.executor, token_symbol, amount, recipient)

    def resolve_token_id(self, symbol: str) -> Optional[str]:
        """Resolve symbol to Hedera ID."""
        return self.executor._get_token_id(symbol)

    def get_history(self, limit: int = 10) -> List[dict]:
        """Get transaction history."""
        return self.executor.get_execution_history(limit)
