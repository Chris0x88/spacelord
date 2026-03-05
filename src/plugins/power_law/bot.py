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
from src.plugins.power_law.config import RobotConfig, get_robot_config
from src.plugins.power_law.adapter import PacmanAdapter, PortfolioState

# State persistence
STATE_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "robot_state.json"


class PowerLawBot:
    """
    Rebalancer bot that uses the Bitcoin Heartbeat Model to determine
    optimal BTC allocation and rebalances via Pacman's swap engine.
    """
    
    def __init__(self, controller, config: Optional[RobotConfig] = None):
        """
        Args:
            controller: An initialized PacmanController instance.
            config: Robot configuration. If None, loads from .env.
        """
        self.config = config or get_robot_config()
        self.adapter = PacmanAdapter(controller)
        
        # State
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.last_check: Optional[datetime] = None
        self.last_rebalance: Optional[datetime] = None
        self.trades_executed = 0
        self._activity_log: list = []
        self._max_log_entries = 25
        
        # Load persisted state
        self._load_state()
        
        logger.info("=" * 50)
        logger.info("🤖 Power Law Rebalancer Bot initialized")
        logger.info(f"   Model: {self.config.model}")
        logger.info(f"   Threshold: {self.config.threshold_percent}%")
        logger.info(f"   Interval: {self.config.interval_seconds}s")
        logger.info(f"   Simulate: {self.config.simulate}")
        logger.info("=" * 50)
    
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
        
        # 1. Get portfolio state
        state = self.adapter.get_portfolio_state()
        if not state:
            reason = "Cannot fetch portfolio state"
            self._log("error", reason)
            return {"success": False, "reason": reason, "traded": False}
        
        # Check HBAR gas reserve
        if state.hbar_balance < self.config.hbar_reserve_min:
            reason = (f"HBAR too low for gas: {state.hbar_balance:.2f} "
                     f"< {self.config.hbar_reserve_min}")
            logger.warning(f"⚠️ {reason}")
            self._log("blocked", reason)
            return {"success": False, "reason": reason, "traded": False, 
                    "hbar_blocked": True}
        
        logger.info(f"   WBTC: {state.wbtc_balance:.8f} (${state.wbtc_balance * state.wbtc_price_usd:,.2f})")
        logger.info(f"   USDC: {state.usdc_balance:.2f}")
        logger.info(f"   Total: ${state.total_value_usd:,.2f}")
        logger.info(f"   Current allocation: {state.wbtc_percent:.1f}% BTC / {state.usdc_percent:.1f}% USDC")
        
        # 2. Get heartbeat signal
        signal = self.get_signal()
        if not signal:
            reason = "Cannot compute heartbeat signal"
            self._log("error", reason)
            return {"success": False, "reason": reason, "traded": False}
        
        target_btc_pct = signal.get("allocation_pct", 50.0)
        
        logger.info(f"   🧠 Heartbeat signal:")
        logger.info(f"      Target: {target_btc_pct:.1f}% BTC")
        logger.info(f"      Valuation: {signal.get('valuation', 'unknown')}")
        logger.info(f"      Stance: {signal.get('stance', 'unknown')}")
        logger.info(f"      Band position: {signal.get('position_in_band_pct', 0):.1f}%")
        
        # 3. Check deviation
        deviation = abs(state.wbtc_percent - target_btc_pct)
        logger.info(f"   📊 Deviation: {deviation:.1f}% (threshold: {self.config.threshold_percent}%)")
        
        if deviation < self.config.threshold_percent:
            reason = f"Within threshold ({deviation:.1f}% < {self.config.threshold_percent}%)"
            logger.info(f"   ✅ {reason} — no action needed")
            self._log("check", reason, {
                "current_btc_pct": state.wbtc_percent,
                "target_btc_pct": target_btc_pct,
                "deviation": deviation,
            })
            return {
                "success": True, "reason": reason, "traded": False,
                "current_btc_pct": state.wbtc_percent,
                "target_btc_pct": target_btc_pct,
                "deviation": deviation,
                "signal": signal,
            }
        
        # 4. Execute rebalance
        if state.wbtc_percent < target_btc_pct:
            # Need more BTC — buy
            direction = "buy_btc"
            # How much USDC to swap → BTC
            target_btc_value = (target_btc_pct / 100) * state.total_value_usd
            current_btc_value = state.wbtc_balance * state.wbtc_price_usd
            trade_usd = target_btc_value - current_btc_value
        else:
            # Too much BTC — sell
            direction = "sell_btc"
            target_btc_value = (target_btc_pct / 100) * state.total_value_usd
            current_btc_value = state.wbtc_balance * state.wbtc_price_usd
            trade_usd = current_btc_value - target_btc_value
        
        # Enforce minimum trade size
        if trade_usd < self.config.min_trade_usd:
            reason = f"Trade too small (${trade_usd:.2f} < ${self.config.min_trade_usd})"
            logger.info(f"   ⏭️ {reason}")
            self._log("skip", reason)
            return {"success": True, "reason": reason, "traded": False}
        
        logger.info(f"   🔄 Rebalancing: {direction} ${trade_usd:.2f}")
        
        result = self.adapter.execute_rebalance(
            direction=direction,
            amount_usd=trade_usd,
            simulate=self.config.simulate
        )
        
        if result.get("success"):
            self.trades_executed += 1
            self.last_rebalance = datetime.now()
            self._save_state()
            
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
    
    def start(self):
        """Start the bot daemon in a background thread."""
        if self.running:
            logger.warning("[PowerLaw] Bot is already running")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("🤖 Power Law bot started (background thread)")
    
    def stop(self):
        """Stop the bot daemon."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("🤖 Power Law bot stopped")
    
    def _run_loop(self):
        """Background loop: check_and_rebalance at configured interval."""
        while self.running:
            try:
                self.check_and_rebalance()
            except Exception as e:
                logger.error(f"[PowerLaw] Bot loop error: {e}")
                self._log("error", str(e))
            
            # Sleep in small intervals so we can stop quickly
            for _ in range(self.config.interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
    
    def get_status(self) -> dict:
        """Get comprehensive bot status."""
        signal = self.get_signal()
        state = self.adapter.get_portfolio_state()
        
        return {
            "running": self.running,
            "simulate": self.config.simulate,
            "model": self.config.model,
            "threshold": self.config.threshold_percent,
            "interval_seconds": self.config.interval_seconds,
            "trades_executed": self.trades_executed,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
            "signal": signal,
            "portfolio": {
                "wbtc_balance": state.wbtc_balance if state else 0,
                "usdc_balance": state.usdc_balance if state else 0,
                "hbar_balance": state.hbar_balance if state else 0,
                "total_value_usd": state.total_value_usd if state else 0,
                "wbtc_percent": state.wbtc_percent if state else 0,
            } if state else None,
            "activity_log": self._activity_log[-10:],
        }
    
    # --- Persistence ---
    
    def _load_state(self):
        """Load persisted state from file."""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE) as f:
                    data = json.load(f)
                self.trades_executed = data.get("trades_executed", 0)
                self._activity_log = data.get("activity_log", [])
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
