#!/usr/bin/env python3
"""
Power Law Rebalancer Bot — Pacman Integration
==============================================

Adapted from the standalone Bitcoin Power Law rebalancer.
Uses Pacman's controller via adapter.py instead of direct Web3 calls.

Core logic: get heartbeat signal → compare to portfolio → rebalance if deviation > threshold.
"""

import logging
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from src.logger import logger
from src.core.base_plugin import BasePlugin
from src.plugins.power_law.config import RobotConfig, get_robot_config
from src.plugins.power_law.adapter import PacmanAdapter, PortfolioState

# State persistence
STATE_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "robot_state.json"


class PowerLawBot(BasePlugin):
    """
    Rebalancer bot that uses the Bitcoin Heartbeat Model to determine
    optimal BTC allocation and rebalances via Pacman's swap engine.
    """
    
    def __init__(self, app, config: Optional[RobotConfig] = None):
        """
        Args:
            app: An initialized PacmanController instance.
            config: Robot configuration. If None, loads from .env.
        """
        super().__init__(app, "PowerLaw")
        self.config = config or get_robot_config()
        self.adapter = PacmanAdapter(app)
        
        # State
        self.last_check: Optional[datetime] = None
        self.last_rebalance: Optional[datetime] = None
        self.trades_executed = 0
        self._activity_log: list = []
        self._max_log_entries = 25
        
        # Cached values for non-blocking status
        self._last_signal = {}
        self._last_portfolio = {}
        
        # Debounce for simulated trades
        self._last_simulated_direction = None
        self._last_simulated_usd = 0.0
        
        # Load persisted state
        self._load_state()
        
        logger.debug("=" * 50)
        logger.debug("🤖 Power Law Rebalancer Bot initialized")
        logger.debug(f"   Model: {self.config.model}")
        logger.debug(f"   Threshold: {self.config.threshold_percent}%")
        logger.debug(f"   Interval: {self.config.interval_seconds}s")
        logger.debug(f"   Simulate: {self.config.simulate}")
        logger.debug("=" * 50)
    
    def get_signal(self) -> Optional[dict]:
        """
        Get today's heartbeat model signal.
        
        Returns dict with allocation_pct, floor, ceiling, model_price,
        position_in_band_pct, valuation, stance, tagline, etc.
        """
        try:
            from src.plugins.power_law.heartbeat_model import get_daily_signal
            
            btc_price = self.adapter.get_btc_price()
            if btc_price <= 0:
                logger.error("[PowerLaw] Cannot get BTC price for signal")
                return None
            
            signal = get_daily_signal(datetime.now(), btc_price)
            return signal
        except Exception as e:
            logger.error(f"[PowerLaw] Signal error: {e}")
            return None
    
    def check_and_rebalance(self) -> dict:
        """
        Main rebalancing loop iteration.
        
        1. Get portfolio state
        2. Get heartbeat signal (target allocation)
        3. Check if deviation exceeds threshold
        4. Execute rebalance swap if needed
        
        Returns dict with result details.
        """
        self.last_check = datetime.now()
        logger.info("-" * 40)
        logger.info("🤖 Checking portfolio...")
        
        try:
            state: Optional[PortfolioState] = self.adapter.get_portfolio_state()
            if not state:
                logger.error("   ❌ Failed to get portfolio state.")
                return {"success": False, "error": "Could not fetch portfolio"}
            
            # Cache for status dashboard immediately
            self._last_portfolio = {
                "wbtc_balance": state.wbtc_balance,
                "usdc_balance": state.usdc_balance,
                "hbar_balance": state.hbar_balance,
                "total_value_usd": state.total_value_usd,
                "wbtc_percent": state.wbtc_percent,
            }
            
            logger.info(f"   💰 Portfolio: ${state.total_value_usd:.2f} | HBAR: {state.hbar_balance:.2f}ℏ")
            
            # Check HBAR gas reserve
            if state.hbar_balance < self.config.hbar_reserve_min:
                robot_id = getattr(self.app.config, "robot_account_id", None)
                parent_id = self.app.config.hedera_account_id
                
                if robot_id and robot_id != parent_id:
                    logger.info(f"   ⛽ HBAR low ({state.hbar_balance:.2f}). Attempting top-up from parent...")
                    try:
                        from lib.prices import price_manager
                        hbar_price = price_manager.get_price("HBAR")
                        if hbar_price > 0:
                            # Target $1.00 USD worth of HBAR
                            topup_amount = 1.0 / hbar_price
                            # Round to 1 decimal place to be safe
                            topup_amount = round(topup_amount, 1)
                            
                            logger.info(f"   💸 Current HBAR price: ${hbar_price:.4f}. Targeting $1.00 top-up ({topup_amount} HBAR)...")
                            
                            transfer_res = self.app.transfer("HBAR", topup_amount, robot_id, memo="Robot Gas Top-up ($1 USD)")
                            if transfer_res.get("success"):
                                if transfer_res.get("simulated"):
                                    logger.info(f"   ⚠️  [Simulated] Would top up robot with {topup_amount} HBAR.")
                                else:
                                    logger.info(f"   ✅ Topped up robot with {topup_amount} HBAR.")
                                # Refresh state
                                state = self.adapter.get_portfolio_state()
                            else:
                                logger.warning(f"   ⚠️ Top-up failed: {transfer_res.get('error')}")
                        else:
                            logger.warning("   ⚠️ Could not fetch HBAR price for smart top-up.")
                    except Exception as e:
                        logger.error(f"   ❌ Top-up error: {e}")

                if state.hbar_balance < self.config.hbar_reserve_min:
                    reason = (f"HBAR too low for gas: {state.hbar_balance:.2f} "
                              f"< {self.config.hbar_reserve_min}")
                    logger.warning(f"   ⚠️ {reason}")
                    return {"success": False, "error": reason}
            
            signal = self.get_signal()
            if not signal:
                return {"success": False, "error": "Could not fetch heartbeat signal"}
                
            self._last_signal = signal
            
            # ... Log Model Output ...
            logger.info(f"   📈 Model Price: ${signal['model_price']:,.2f}")
            logger.info(f"   🎯 Target: {signal['allocation_pct']}% BTC | Current: {state.wbtc_percent:.1f}% BTC")
            logger.info(f"   🏷️  Stance: {signal['stance']} - {signal['tagline']}")
            
            target_btc_pct = signal["allocation_pct"]
            deviation = state.wbtc_percent - target_btc_pct
            
            log_dev = f"{abs(deviation):.1f}%"
            logger.info(f"   📏 Deviation: {log_dev} (Threshold: {self.config.threshold_percent}%)")
            
            # Rebalance Logic
            if abs(deviation) < self.config.threshold_percent:
                reason = f"Deviation {log_dev} < {self.config.threshold_percent}%"
                logger.info(f"   ⏭️ {reason}")
                self._log("skip", reason)
                return {
                    "success": True, 
                    "reason": reason, 
                    "traded": False,
                    "signal": signal,
                    "current_btc_pct": state.wbtc_percent,
                    "target_btc_pct": target_btc_pct
                }
            
            # Calculate Trade Size
            direction = "buy_btc" if deviation < 0 else "sell_btc"
            
            if direction == "buy_btc":
                target_btc_value = (target_btc_pct / 100) * state.total_value_usd
                current_btc_value = state.wbtc_balance * state.wbtc_price_usd
                trade_usd = target_btc_value - current_btc_value
            else:
                target_btc_value = (target_btc_pct / 100) * state.total_value_usd
                current_btc_value = state.wbtc_balance * state.wbtc_price_usd
                trade_usd = current_btc_value - target_btc_value
            
            # Enforce minimum trade size
            if trade_usd < self.config.min_trade_usd:
                reason = f"Trade too small (${trade_usd:.2f} < ${self.config.min_trade_usd})"
                logger.info(f"   ⏭️ {reason}")
                self._log("skip", reason)
                return {"success": True, "reason": reason, "traded": False}
            
            # Debounce repeated identical simulated trades
            if self.config.simulate and self._last_simulated_direction == direction:
                if abs(trade_usd - self._last_simulated_usd) / max(self._last_simulated_usd, 1) < 0.05:
                    reason = f"Simulated {direction} ${trade_usd:.2f} unchanged from last cycle."
                    logger.info(f"   ⏭️ {reason}")
                    return {"success": True, "reason": reason, "traded": False}
                    
            logger.info(f"   🔄 Rebalancing: {direction} ${trade_usd:.2f}")
            
            result = self.adapter.execute_rebalance(
                direction=direction,
                amount_usd=trade_usd,
                simulate=self.config.simulate
            )
            
            if result.get("success"):
                if self.config.simulate:
                    self._last_simulated_direction = direction
                    self._last_simulated_usd = trade_usd
                else:
                    self._last_simulated_direction = None
                    
                self.trades_executed += 1
                self.last_rebalance = datetime.now()
                
                sim_tag = " (SIMULATED)" if result.get("simulated") else ""
                logger.info(f"   ✅ Rebalance executed{sim_tag}")
                self._log("trade", f"{direction} ${trade_usd:.2f}{sim_tag}", {
                    "direction": direction,
                    "amount_usd": trade_usd,
                    "simulated": result.get("simulated", False),
                })
            else:
                logger.error(f"   ❌ Rebalance failed: {result.get('error')}")
                self._log("error", f"Trade failed: {result.get('error')}")
            
            result["signal"] = signal
            result["current_btc_pct"] = state.wbtc_percent
            result["target_btc_pct"] = target_btc_pct
            result["deviation"] = deviation
            result["traded"] = result.get("success", False)
            
            return result
        finally:
            # Always save state to persist the latest portfolio and signal cache,
            # even if we exited early due to an error.
            self._save_state()
    
    def run_loop(self):
        """Standard work loop called by BasePlugin."""
        result = self.check_and_rebalance()
        
        # Determine sleep interval: 
        # If check failed or we have no portfolio data, retry much sooner (60s)
        # otherwise use the full configured interval (usually 1 hour).
        success = result.get("success", False)
        has_data = bool(self._last_portfolio)
        
        sleep_interval = self.config.interval_seconds
        if not success or not has_data:
            sleep_interval = 60
            logger.info(f"   ⏳ {self.plugin_name} in retry mode: checking again in 60s")
            
        # Sleep in small segments to allow quick exit
        for _ in range(sleep_interval):
            if not self.running:
                break
            time.sleep(1)
    
    def get_status(self) -> dict:
        """Get comprehensive bot status (non-blocking)."""
        status = super().get_status()
        status.update({
            "simulate": self.config.simulate,
            "model": self.config.model,
            "threshold": self.config.threshold_percent,
            "trades_executed": self.trades_executed,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
            "signal": self._last_signal,
            "portfolio": self._last_portfolio,
        })
        return status
    
    # --- Persistence ---
    
    def _load_state(self):
        """Load persisted state from file."""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE) as f:
                    data = json.load(f)
                self.trades_executed = data.get("trades_executed", 0)
                self._activity_log = data.get("activity_log", [])
                self._last_portfolio = data.get("last_portfolio", {})
                self._last_signal = data.get("last_signal", {})
                if data.get("last_rebalance"):
                    self.last_rebalance = datetime.fromisoformat(data["last_rebalance"])
        except Exception:
            pass
    
    def _save_state(self):
        """Save state to file for persistence across restarts."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump({
                    "trades_executed": self.trades_executed,
                    "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
                    "activity_log": self._activity_log[-self._max_log_entries:],
                    "last_portfolio": self._last_portfolio,
                    "last_signal": self._last_signal,
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"[PowerLaw] Could not save state: {e}")
    
    def _log(self, activity_type: str, message: str, data: dict = None):
        """Log an activity entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,
            "message": message,
        }
        if data:
            entry["data"] = data
        self._activity_log.append(entry)
        if len(self._activity_log) > self._max_log_entries:
            self._activity_log = self._activity_log[-self._max_log_entries:]
