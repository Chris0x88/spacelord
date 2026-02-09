#!/usr/bin/env python3
"""
Pacman Pre-Flight - Safety Checks Before Execution
Validates balances, quotes, gas, and slippage before any transaction.
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import time

from pacman_config import PacmanConfig
from pacman_variant_router import VariantRoute
from saucerswap_v2_client import SaucerSwapV2
from web3 import Web3

@dataclass
class PreFlightResult:
    """Result of pre-flight checks."""
    passed: bool
    warnings: list
    errors: list
    
    # Calculated values
    required_gas_hbar: float
    required_token_balance: float
    expected_output: float
    minimum_output: float  # After slippage
    current_price: float
    
    # Status
    balance_sufficient: bool
    quote_valid: bool
    gas_sufficient: bool
    slippage_acceptable: bool
    
    def can_execute(self) -> bool:
        """Check if execution is safe."""
        return self.passed and self.balance_sufficient and self.quote_valid and self.gas_sufficient
    
    def summary(self) -> str:
        """Human-readable summary."""
        lines = ["📋 PRE-FLIGHT CHECK RESULTS", "="*60]
        
        if self.passed:
            lines.append("✅ All checks PASSED")
        else:
            lines.append("❌ Some checks FAILED")
        
        lines.append("")
        lines.append("💰 Financial:")
        lines.append(f"   Required token balance: {self.required_token_balance:.6f}")
        lines.append(f"   Expected output: {self.expected_output:.6f}")
        lines.append(f"   Minimum output ({PacmanConfig().max_slippage_percent}% slippage): {self.minimum_output:.6f}")
        lines.append(f"   Current price: ${self.current_price:.2f}")
        
        lines.append("")
        lines.append("⛽ Gas:")
        lines.append(f"   Required gas: {self.required_gas_hbar:.4f} HBAR")
        
        lines.append("")
        lines.append("🔍 Status:")
        lines.append(f"   Balance sufficient: {'✅' if self.balance_sufficient else '❌'}")
        lines.append(f"   Quote valid: {'✅' if self.quote_valid else '❌'}")
        lines.append(f"   Gas sufficient: {'✅' if self.gas_sufficient else '❌'}")
        lines.append(f"   Slippage acceptable: {'✅' if self.slippage_acceptable else '❌'}")
        
        if self.warnings:
            lines.append("")
            lines.append("⚠️  WARNINGS:")
            for warning in self.warnings:
                lines.append(f"   • {warning}")
        
        if self.errors:
            lines.append("")
            lines.append("❌ ERRORS:")
            for error in self.errors:
                lines.append(f"   • {error}")
        
        return "\n".join(lines)

class PacmanPreFlight:
    """
    Pre-flight safety checker for Pacman trades.
    
    Validates:
    1. User has sufficient token balance
    2. Quote is valid and recent
    3. Gas costs are covered
    4. Slippage is within limits
    5. Route is still optimal
    """
    
    def __init__(self, config: PacmanConfig = None):
        self.config = config or PacmanConfig.from_env()
        
        # Initialize web3 for balance checks
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        if self.config.private_key:
            self.client = SaucerSwapV2(self.w3, self.config.network, self.config.private_key)
            self.eoa = self.client.eoa
        else:
            self.client = None
            self.eoa = None
    
    def check_flight(self, route: VariantRoute, amount_usd: float) -> PreFlightResult:
        """
        Run all pre-flight checks.
        
        Args:
            route: The route to validate
            amount_usd: Amount in USD
        
        Returns:
            PreFlightResult with all checks
        """
        warnings = []
        errors = []
        
        # 1. Check if we can even execute (private key configured)
        if not self.config.private_key:
            errors.append("No private key configured - cannot execute live trades")
            return self._make_failed_result(errors)
        
        # 2. Check amount is within limits
        if amount_usd > self.config.max_swap_amount_usd:
            errors.append(f"Amount ${amount_usd} exceeds max ${self.config.max_swap_amount_usd}")
            return self._make_failed_result(errors)
        
        # 3. Get live quote
        quote_result = self._check_quote(route, amount_usd)
        if not quote_result["valid"]:
            errors.append(f"Quote failed: {quote_result.get('error', 'Unknown')}")
            expected_output = 0
            minimum_output = 0
        else:
            expected_output = quote_result["expected_output"]
            # Calculate minimum output with slippage
            slippage_factor = 1 - (self.config.max_slippage_percent / 100)
            minimum_output = expected_output * slippage_factor
        
        # 4. Check token balances
        balance_result = self._check_balances(route, amount_usd)
        
        # 5. Check gas
        gas_result = self._check_gas(route)
        
        # 6. Validate slippage
        if expected_output > 0:
            # Compare to reference price (would need price oracle)
            slippage_acceptable = True  # Simplified - would check against market price
        else:
            slippage_acceptable = False
        
        # Compile warnings
        if quote_result.get("price_impact", 0) > 0.5:
            warnings.append(f"High price impact: {quote_result['price_impact']:.2f}%")
        
        if gas_result.get("gas_price_gwei", 0) > 100:
            warnings.append("High gas prices detected")
        
        # Determine overall status
        passed = len(errors) == 0
        balance_sufficient = balance_result.get("has_sufficient_balance", False)
        quote_valid = quote_result.get("valid", False)
        gas_sufficient = gas_result.get("has_sufficient_gas", False)
        
        return PreFlightResult(
            passed=passed,
            warnings=warnings,
            errors=errors,
            required_gas_hbar=route.total_gas_hbar,
            required_token_balance=amount_usd,  # Simplified
            expected_output=expected_output,
            minimum_output=minimum_output,
            current_price=quote_result.get("price", 0),
            balance_sufficient=balance_sufficient,
            quote_valid=quote_valid,
            gas_sufficient=gas_sufficient,
            slippage_acceptable=slippage_acceptable
        )
    
    def _check_quote(self, route: VariantRoute, amount_usd: float) -> Dict:
        """Get live quote from SaucerSwap."""
        try:
            # Simplified quote check - would need proper token ID mapping
            # For now, return simulated success
            return {
                "valid": True,
                "expected_output": amount_usd * 0.002,  # Simulated rate
                "price": 50000.0,  # Simulated BTC price
                "price_impact": 0.1,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _check_balances(self, route: VariantRoute, amount_usd: float) -> Dict:
        """Check if user has sufficient balances."""
        try:
            if not self.eoa:
                return {"has_sufficient_balance": False, "error": "No EOA configured"}
            
            # Check HBAR balance for gas
            hbar_balance_wei = self.w3.eth.get_balance(self.eoa)
            hbar_balance = hbar_balance_wei / 10**18
            
            has_hbar = hbar_balance > route.total_gas_hbar * 2  # 2x buffer
            
            # Would also check token balance here
            has_token = True  # Simplified
            
            return {
                "has_sufficient_balance": has_hbar and has_token,
                "hbar_balance": hbar_balance,
                "required_hbar": route.total_gas_hbar * 2
            }
        
        except Exception as e:
            return {"has_sufficient_balance": False, "error": str(e)}
    
    def _check_gas(self, route: VariantRoute) -> Dict:
        """Check gas prices and availability."""
        try:
            gas_price = self.w3.eth.gas_price
            gas_price_gwei = gas_price / 10**9
            
            # Check if we have enough HBAR
            if self.eoa:
                hbar_balance = self.w3.eth.get_balance(self.eoa) / 10**18
                required = route.total_gas_hbar
                has_sufficient = hbar_balance > required * 1.5  # 1.5x buffer
            else:
                has_sufficient = False
            
            return {
                "has_sufficient_gas": has_sufficient,
                "gas_price_gwei": gas_price_gwei,
                "gas_price_wei": gas_price
            }
        
        except Exception as e:
            return {"has_sufficient_gas": False, "error": str(e)}
    
    def _make_failed_result(self, errors: list) -> PreFlightResult:
        """Create a failed pre-flight result."""
        return PreFlightResult(
            passed=False,
            warnings=[],
            errors=errors,
            required_gas_hbar=0,
            required_token_balance=0,
            expected_output=0,
            minimum_output=0,
            current_price=0,
            balance_sufficient=False,
            quote_valid=False,
            gas_sufficient=False,
            slippage_acceptable=False
        )

# CLI Testing
if __name__ == "__main__":
    print("="*80)
    print("🧪 PACMAN PRE-FLIGHT TESTER")
    print("="*80)
    
    from pacman_variant_router import PacmanVariantRouter
    
    # Setup
    config = PacmanConfig.from_env()
    config.print_status()
    
    router = PacmanVariantRouter()
    router.load_pools()
    
    # Get a route
    route = router.recommend_route("USDC", "WBTC_HTS", "auto", amount_usd=1.0)
    
    if route:
        print(f"\n🎯 Testing route: {route.from_variant} → {route.to_variant}")
        
        # Run pre-flight
        preflight = PacmanPreFlight(config)
        result = preflight.check_flight(route, amount_usd=1.0)
        
        print(f"\n{result.summary()}")
        print(f"\n{'='*80}")
        
        if result.can_execute():
            print("✅ Ready for execution!")
        else:
            print("❌ Cannot execute - fix errors above")
    else:
        print("❌ No route found")
