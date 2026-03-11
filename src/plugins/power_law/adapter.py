#!/usr/bin/env python3
"""
Power Law Adapter — Bridges Heartbeat Model to Pacman Controller
================================================================

This adapter wraps PacmanController so the rebalancer bot can:
- Get BTC price (from Pacman's price manager)
- Get portfolio state (WBTC + USDC balances)
- Execute rebalance swaps (via Pacman's swap engine)

This is the ONLY integration point between the Power Law bot and Pacman.
The heartbeat model and bot logic remain standalone.
"""

import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from src.logger import logger
# Price manager is a module-level singleton from lib.prices
from lib.prices import price_manager as _pm

# Default token IDs for the rebalancer (highest-liquidity HTS pools)
WBTC_TOKEN_ID = "0.0.1055483"
WETH_TOKEN_ID = "0.0.541564"
USDC_TOKEN_ID = "0.0.456858"


@dataclass
class PortfolioState:
    """Current portfolio snapshot for the rebalancer."""
    wbtc_balance: float       # WBTC amount
    usdc_balance: float       # USDC amount
    hbar_balance: float       # HBAR amount (for gas)
    wbtc_price_usd: float     # Current BTC price in USD
    total_value_usd: float    # Total portfolio in USD
    wbtc_percent: float       # Current BTC allocation %
    usdc_percent: float       # Current USDC allocation %


class PacmanAdapter:
    """
    Adapts PacmanController for the Power Law rebalancer bot.
    
    The bot calls adapter methods instead of talking to Web3 directly.
    This keeps one source of truth for all swap/balance/price logic.
    """
    
    def __init__(self, controller):
        """
        Args:
            controller: An initialized PacmanController instance.
        """
        self.controller = controller
        self._last_price_fetch = None
        self._cached_price = 0.0
    
    def get_btc_price(self) -> float:
        """Get current BTC price in USD from Pacman's price manager."""
        try:
            # Try the local pool price data first (fastest)
            price = _pm.get_price(WBTC_TOKEN_ID)
            if price and price > 0:
                self._cached_price = price
                return price
            
            # Fallback: try legacy WBTC token ID
            price = _pm.get_price("0.0.1055483")
            if price and price > 0:
                self._cached_price = price
                return price
                
            # Fallback: try get_price_with_source
            price, source = _pm.get_price_with_source(WBTC_TOKEN_ID)
            if price and price > 0:
                self._cached_price = price
                return price
        except Exception as e:
            logger.warning(f"[PowerLaw] Price fetch failed: {e}")
        
        if self._cached_price > 0:
            return self._cached_price
        
        logger.error("[PowerLaw] Cannot get BTC price — no data available")
        return 0.0
    
    def get_portfolio_state(self) -> Optional[PortfolioState]:
        """Get current portfolio balances and allocation percentages."""
        try:
            # Get balances from controller — highlight essential tokens for rebalancer
            highlights = [WBTC_TOKEN_ID, USDC_TOKEN_ID, "0.0.0"] # 0.0.0 is native HBAR
            
            # Use dedicated robot account if configured
            robot_id = getattr(self.controller.config, "robot_account_id", None)
            balances = self.controller.get_balances(token_highlights=highlights, account_id=robot_id)
            if not balances:
                # Fallback: try alternate method name
                try:
                    balances = self.controller.get_all_balances()
                except Exception:
                    pass
            if not balances:
                logger.error("[PowerLaw] Cannot fetch balances")
                return None
            
            # Extract WBTC, USDC, and HBAR balances
            # get_balances returns Dict[str, float] mapping token ID -> balance amounts
            wbtc_bal = balances.get(WBTC_TOKEN_ID, 0.0)
            usdc_bal = balances.get(USDC_TOKEN_ID, 0.0)
            hbar_bal = balances.get("0.0.0", balances.get("HBAR", 0.0))
            
            # Get BTC price
            btc_price = self.get_btc_price()
            if btc_price <= 0:
                logger.error("[PowerLaw] BTC price is zero, cannot compute allocation")
                return None
            
            # Calculate totals
            wbtc_value = wbtc_bal * btc_price
            total_value = wbtc_value + usdc_bal
            
            if total_value <= 0:
                return PortfolioState(
                    wbtc_balance=wbtc_bal, usdc_balance=usdc_bal,
                    hbar_balance=hbar_bal, wbtc_price_usd=btc_price,
                    total_value_usd=0, wbtc_percent=0, usdc_percent=0
                )
            
            return PortfolioState(
                wbtc_balance=wbtc_bal,
                usdc_balance=usdc_bal,
                hbar_balance=hbar_bal,
                wbtc_price_usd=btc_price,
                total_value_usd=total_value,
                wbtc_percent=(wbtc_value / total_value) * 100,
                usdc_percent=(usdc_bal / total_value) * 100,
            )
        except Exception as e:
            logger.error(f"[PowerLaw] Portfolio state error: {e}")
            return None
    
    def execute_rebalance(self, direction: str, amount_usd: float, 
                          simulate: bool = True) -> dict:
        """
        Execute a rebalance swap via Pacman's controller.
        
        Args:
            direction: "buy_btc" (USDC → WBTC) or "sell_btc" (WBTC → USDC)
            amount_usd: Trade size in USD
            simulate: If True, only simulate (default safe mode)
            
        Returns:
            Dict with success, tx_hash, amount_in, amount_out, error
        """
        try:
            btc_price = self.get_btc_price()
            
            if direction == "buy_btc":
                from_token = USDC_TOKEN_ID
                to_token = WBTC_TOKEN_ID
                amount = amount_usd  # USDC amount
            elif direction == "sell_btc":
                from_token = WBTC_TOKEN_ID
                to_token = USDC_TOKEN_ID
                amount = amount_usd / btc_price if btc_price > 0 else 0
            else:
                return {"success": False, "error": f"Unknown direction: {direction}"}
            
            logger.info(f"[PowerLaw] Rebalance: {direction} ${amount_usd:.2f} "
                       f"({amount:.6f} {from_token} → {to_token})")
            
            if simulate:
                logger.info("[PowerLaw] SIMULATION MODE — no transaction broadcast")
                return {
                    "success": True,
                    "simulated": True,
                    "direction": direction,
                    "amount_usd": amount_usd,
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount": amount,
                }
            
            # Live swap via controller
            # Use dedicated robot account if configured
            robot_id = getattr(self.controller.config, "robot_account_id", None)
            
            route = self.controller.get_route(from_token, to_token, amount)
            if not route or route.confidence == 0.0:
                return {"success": False, "error": "No route found for rebalance"}
            
            # Pass account_id to swap if supported (I need to check controller.swap)
            result = self.controller.swap(from_token, to_token, amount, account_id=robot_id)
            
            # The controller returns an ExecutionResult object, not a dict.
            # Convert it to a dict first if it has a to_dict method, or access properties directly.
            result_dict = result.to_dict() if hasattr(result, 'to_dict') else {
                "success": getattr(result, "success", False),
                "tx_hash": getattr(result, "tx_hash", None),
                "amount_in": getattr(result, "amount_in", amount),
                "amount_out": getattr(result, "amount_out", 0),
                "error": getattr(result, "error", "Unknown error"),
            }
            
            return {
                "success": result_dict.get("success", False),
                "tx_hash": result_dict.get("tx_hash"),
                "amount_in": result_dict.get("amount_in"),
                "amount_out": result_dict.get("amount_out"),
                "direction": direction,
                "amount_usd": amount_usd,
                "error": result_dict.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"[PowerLaw] Rebalance execution error: {e}")
            return {"success": False, "error": str(e)}
