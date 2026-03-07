"""
Main Bot Orchestration
======================

This module ties everything together into a running bot.
It handles:
- Scheduled rebalancing checks
- Extreme price spike detection
- Integration with external allocation engine
- Logging and status reporting

ARCHITECTURE:
The bot runs a main loop that:
1. Fetches current BTC price
2. Gets allocation target (from Power Law or external engine)
3. Checks if rebalancing is needed
4. Executes trades if profitable
5. Waits for next interval

DEPLOYMENT:
This bot is designed to run on Railway or similar platforms.
It reads configuration from environment variables and runs
continuously until stopped.

SAFETY FEATURES:
- Only trades when profitable after fees
- Respects minimum trade sizes
- Has configurable rebalance thresholds
- Logs all decisions and trades
"""

import logging
import time
import signal
import sys
import json
import os
from datetime import datetime
from typing import Optional, Callable
from decimal import Decimal
from pathlib import Path

from config import Config, get_config

# Persistent storage file for bot state (survives restarts)
BOT_STATE_FILE = Path(__file__).parent / "bot_state.json"
from tokens import TOKENS
from hts_swap_engine import SwapEngine, create_engine
from portfolio import PortfolioManager, create_manager
from power_law import AllocationProvider, AllocationTarget

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# BOT CLASS
# =============================================================================

class RebalancerBot:
    """
    Main bot that orchestrates portfolio rebalancing.
    
    This bot:
    - Monitors BTC price and portfolio allocation
    - Determines target allocation based on Power Law or external input
    - Executes rebalancing trades when profitable
    - Runs on a configurable schedule
    
    Usage:
        bot = RebalancerBot()
        
        # Run once
        bot.run_once()
        
        # Run continuously
        bot.run_forever()
        
        # With external allocation
        bot.set_allocation_target(btc_percent=70)
        bot.run_once()
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the bot.
        
        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or get_config()
        
        # Initialize components
        self.engine = create_engine(self.config)
        self.portfolio = create_manager(self.config)
        self.allocation_provider = AllocationProvider()
        
        # State
        self.running = False
        self.last_rebalance: Optional[datetime] = None
        self.trades_executed = 0
        
        # Activity log (last 25 entries) - persisted to file
        self._activity_log: list = []
        self._max_log_entries = 25
        
        # Load persisted state (trade count + activity log)
        self._load_state()
        
        # Callbacks for external integration
        self._on_rebalance: Optional[Callable] = None
        self._on_status: Optional[Callable] = None
        
        logger.info("=" * 60)
        logger.info("BTC Power Law Rebalancer Bot")
        logger.info("=" * 60)
        logger.info(f"Account: {self.engine.eoa}")
        logger.info(f"USDC Token: {TOKENS['USDC'].hedera_id}")
        logger.info(f"WBTC Token: {TOKENS['WBTC'].hedera_id}")
        logger.info(f"Rebalance Interval: {self.config.rebalance.interval_seconds}s")
        logger.info(f"Threshold: {self.config.rebalance.threshold_percent}%")
        logger.info("=" * 60)
    
    # =========================================================================
    # ALLOCATION MANAGEMENT
    # =========================================================================
    
    def set_allocation_target(
        self, 
        btc_percent: float,
        confidence: float = 1.0,
        source: str = "external"
    ):
        """
        Set target allocation from external source.
        
        Call this method to inject allocation targets from your
        external allocation engine.
        
        Args:
            btc_percent: Target BTC percentage (0-100)
            confidence: Confidence in this target (0-1)
            source: Description of where this target came from
        """
        self.allocation_provider.set_target_override(
            btc_percent=btc_percent,
            confidence=confidence,
            source=source
        )
        self.portfolio.set_target(btc_percent)
    
    def clear_allocation_override(self):
        """Clear external allocation and use Power Law."""
        self.allocation_provider.clear_override()
    
    def get_current_target(self) -> AllocationTarget:
        """
        Get current allocation target.
        
        Returns target from external source if set,
        otherwise calculates from Power Law.
        """
        # Get current BTC price
        state = self.portfolio.get_state()
        btc_price = float(state.wbtc_price_usdc)
        
        return self.allocation_provider.get_target(btc_price)
    
    # =========================================================================
    # REBALANCING
    # =========================================================================
    
    def check_and_rebalance(self) -> dict:
        """
        Check portfolio and rebalance if needed.
        
        This is the main rebalancing logic:
        1. Check HBAR reserve (gas) - block trading if too low
        2. Get current portfolio state
        3. Get target allocation
        4. Check if rebalance is needed
        5. Execute trade if profitable
        
        Returns:
            Dictionary with rebalance result
        """
        logger.info("-" * 40)
        logger.info("Checking portfolio...")
        
        # HBAR Reserve Check - auto top-up if low
        hbar_balance = self.engine.get_hbar_balance()
        hbar_reserve_min = self.config.trading.hbar_reserve_min
        hbar_per_trade = self.config.trading.hbar_per_trade
        
        logger.info(f"HBAR Balance: {hbar_balance:.4f} (reserve min: {hbar_reserve_min})")
        
        if hbar_balance < hbar_reserve_min:
            logger.warning(f"⚠️ HBAR low ({hbar_balance:.2f} < {hbar_reserve_min}), initiating auto top-up...")
            
            # Calculate how much HBAR we need (10 trades worth)
            target_hbar = hbar_per_trade * 10  # 10 trades worth
            hbar_needed = target_hbar - hbar_balance
            
            # Estimate USDC needed (HBAR ~$0.25, add 20% buffer for slippage/fees)
            hbar_price_usd = 0.25  # Conservative estimate
            usdc_needed = hbar_needed * hbar_price_usd * 1.2  # 20% buffer
            usdc_needed = max(usdc_needed, 1.0)  # Minimum $1 swap
            
            logger.info(f"⛽ Auto top-up: Need ~{hbar_needed:.2f} HBAR, swapping ~${usdc_needed:.2f} USDC")
            
            # Check if we have enough USDC
            state = self.portfolio.get_state()
            if float(state.usdc_balance) < usdc_needed:
                reason = f"Cannot auto top-up: USDC balance ({state.usdc_balance:.2f}) < needed ({usdc_needed:.2f})"
                logger.error(f"❌ {reason}")
                self.log_activity("blocked", reason, {
                    "hbar_balance": hbar_balance,
                    "usdc_balance": float(state.usdc_balance),
                    "usdc_needed": usdc_needed,
                })
                return {
                    "timestamp": datetime.now().isoformat(),
                    "state": state.to_dict(),
                    "target": None,
                    "decision": {
                        "should_rebalance": False,
                        "direction": None,
                        "amount_usdc": 0,
                        "reason": reason,
                    },
                    "trade_executed": False,
                    "tx_hash": None,
                    "hbar_blocked": True,
                }
            
            # Execute the HBAR top-up
            from hts_swap_engine import topup_hbar_from_usdc
            topup_result = topup_hbar_from_usdc(usdc_needed, slippage_percent=1.0)
            
            if topup_result["success"]:
                logger.info(f"✅ Auto top-up successful! Received {topup_result['hbar_received']:.4f} HBAR")
                self.log_activity("topup", f"Auto HBAR top-up: ${usdc_needed:.2f} → {topup_result['hbar_received']:.2f} HBAR", {
                    "usdc_spent": topup_result["usdc_spent"],
                    "hbar_received": topup_result["hbar_received"],
                    "tx_hash": topup_result["tx_hash"],
                })
                # Update HBAR balance after top-up
                hbar_balance = self.engine.get_hbar_balance()
                logger.info(f"New HBAR balance: {hbar_balance:.4f}")
            else:
                reason = f"Auto top-up failed: {topup_result['error']}"
                logger.error(f"❌ {reason}")
                self.log_activity("blocked", reason, {
                    "hbar_balance": hbar_balance,
                    "error": topup_result["error"],
                })
                return {
                    "timestamp": datetime.now().isoformat(),
                    "state": None,
                    "target": None,
                    "decision": {
                        "should_rebalance": False,
                        "direction": None,
                        "amount_usdc": 0,
                        "reason": reason,
                    },
                    "trade_executed": False,
                    "tx_hash": None,
                    "hbar_blocked": True,
                    "topup_failed": True,
                }
        
        # Get current state
        state = self.portfolio.get_state()
        
        logger.info(f"Balances: {state.usdc_balance:.2f} USDC, "
                   f"{state.wbtc_balance:.8f} WBTC")
        logger.info(f"WBTC Price: ${state.wbtc_price_usdc:,.2f}")
        logger.info(f"Total Value: ${state.total_value_usdc:.2f}")
        logger.info(f"Current Allocation: {state.wbtc_percent:.1f}% BTC, "
                   f"{state.usdc_percent:.1f}% USDC")
        
        # Get target allocation
        target = self.get_current_target()
        self.portfolio.set_target(float(target.btc_percent))
        
        logger.info(f"Target Allocation: {target.btc_percent:.1f}% BTC, "
                   f"{target.usdc_percent:.1f}% USDC "
                   f"(source: {target.source})")
        
        # Check if rebalance needed
        decision = self.portfolio.calculate_rebalance(state)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "state": state.to_dict(),
            "target": target.to_dict(),
            "decision": {
                "should_rebalance": decision.should_rebalance,
                "direction": decision.direction,
                "amount_usdc": float(decision.amount_usdc),
                "reason": decision.reason,
            },
            "trade_executed": False,
            "tx_hash": None,
        }
        
        if not decision.should_rebalance:
            logger.info(f"No rebalance needed: {decision.reason}")
            # Log the decision
            self.log_activity("check", f"No rebalance: {decision.reason}", {
                "current_btc_pct": float(state.wbtc_percent),
                "target_btc_pct": float(target.btc_percent),
                "total_value": float(state.total_value_usdc),
            })
            return result
        
        logger.info(f"Rebalance needed: {decision.direction} ${decision.amount_usdc:.2f}")
        
        # Execute rebalance
        tx_hash = self.portfolio.execute_rebalance(decision)
        
        if tx_hash:
            self.trades_executed += 1
            self.last_rebalance = datetime.now()
            result["trade_executed"] = True
            result["tx_hash"] = tx_hash
            
            logger.info(f"Trade executed: {tx_hash}")
            
            # Log the trade
            self.log_activity("trade", f"{decision.direction} ${decision.amount_usdc:.2f}", {
                "direction": decision.direction,
                "amount_usdc": float(decision.amount_usdc),
                "tx_hash": tx_hash,
                "current_btc_pct": float(state.wbtc_percent),
                "target_btc_pct": float(target.btc_percent),
            })
            
            # Call callback if set
            if self._on_rebalance:
                self._on_rebalance(result)
        
        return result
    
    # =========================================================================
    # EXTREME PRICE DETECTION
    # =========================================================================
    
    def check_extreme_move(self) -> bool:
        """
        Check if there's been an extreme price move.
        
        Extreme moves trigger immediate rebalancing regardless
        of the normal schedule.
        
        Returns:
            True if extreme move detected
        """
        state = self.portfolio.get_state()
        
        # Calculate deviation from target
        target = self.get_current_target()
        deviation = abs(float(state.wbtc_percent) - float(target.btc_percent))
        
        threshold = self.config.rebalance.extreme_threshold_percent
        
        if deviation >= threshold:
            logger.warning(
                f"Extreme deviation detected: {deviation:.1f}% "
                f"(threshold: {threshold}%)"
            )
            return True
        
        return False
    
    # =========================================================================
    # RUNNING THE BOT
    # =========================================================================
    
    def run_once(self) -> dict:
        """
        Run a single rebalance check.
        
        Returns:
            Dictionary with rebalance result
        """
        return self.check_and_rebalance()
    
    def run_forever(self, in_thread: bool = False):
        """
        Run the bot continuously.
        
        The bot will:
        1. Check for rebalancing at configured intervals
        2. Check for extreme moves more frequently
        3. Handle graceful shutdown on SIGINT/SIGTERM (main thread only)
        
        Args:
            in_thread: If True, skip signal handler setup (for background threads)
        """
        self.running = True
        
        # Set up signal handlers for graceful shutdown (main thread only)
        if not in_thread:
            def signal_handler(signum, frame):
                logger.info("Shutdown signal received...")
                self.running = False
            
            try:
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
            except ValueError:
                # Signal handlers only work in main thread
                logger.warning("Could not set signal handlers (not main thread)")
        
        logger.info("Bot started, running forever...")
        logger.info(f"Check interval: {self.config.rebalance.interval_seconds}s")
        
        last_check = 0
        extreme_check_interval = 60  # Check for extreme moves every minute
        last_extreme_check = 0
        error_cooldown = 0  # Cooldown after errors to avoid hammering RPC
        
        while self.running:
            now = time.time()
            
            # Skip if in error cooldown
            if now < error_cooldown:
                time.sleep(5)
                continue
            
            try:
                # Check for extreme moves frequently
                if now - last_extreme_check >= extreme_check_interval:
                    if self.check_extreme_move():
                        logger.info("Extreme move - triggering immediate rebalance")
                        self.check_and_rebalance()
                        last_check = now
                    last_extreme_check = now
                
                # Regular rebalance check
                if now - last_check >= self.config.rebalance.interval_seconds:
                    self.check_and_rebalance()
                    last_check = now
                
                # Call status callback if set
                if self._on_status:
                    self._on_status(self.get_status())
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                # Set cooldown: wait 60 seconds before retrying after an error
                error_cooldown = now + 60
                logger.info("Waiting 60 seconds before retrying due to error...")
            
            # Sleep briefly to prevent busy-waiting
            time.sleep(1)
        
        logger.info("Bot stopped")
    
    # =========================================================================
    # STATUS AND CALLBACKS
    # =========================================================================
    
    def _load_state(self):
        """Load persisted state from file (trade count + activity log)."""
        try:
            if BOT_STATE_FILE.exists():
                with open(BOT_STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.trades_executed = state.get('trades_executed', 0)
                    self._activity_log = state.get('activity_log', [])
                    logger.info(f"Loaded state: {self.trades_executed} trades, {len(self._activity_log)} log entries")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
    
    def _save_state(self):
        """Save state to file for persistence across restarts."""
        try:
            state = {
                'trades_executed': self.trades_executed,
                'activity_log': self._activity_log[-self._max_log_entries:],
                'last_saved': datetime.now().isoformat(),
            }
            with open(BOT_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")
    
    def log_activity(self, activity_type: str, message: str, data: dict = None):
        """
        Log an activity entry and persist to file.
        
        Args:
            activity_type: "check", "trade", "error", "startup"
            message: Human-readable message
            data: Additional data dict
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,
            "message": message,
            "data": data or {},
        }
        self._activity_log.append(entry)
        
        # Keep only last N entries
        if len(self._activity_log) > self._max_log_entries:
            self._activity_log = self._activity_log[-self._max_log_entries:]
        
        # Persist to file
        self._save_state()
    
    def get_activity_log(self) -> list:
        """Get the activity log (last 25 entries)."""
        return list(reversed(self._activity_log))  # Most recent first
    
    def get_status(self) -> dict:
        """
        Get comprehensive bot status.
        
        Returns:
            Dictionary with all bot information
        """
        state = self.portfolio.get_state()
        target = self.get_current_target()
        
        return {
            "bot": {
                "running": self.running,
                "trades_executed": self.trades_executed,
                "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
            },
            "account": {
                "address": self.engine.eoa,
                "hedera_account": getattr(self.engine, 'hedera_account_id', None),
            },
            "portfolio": state.to_dict(),
            "target": target.to_dict(),
            "config": {
                "interval_seconds": self.config.rebalance.interval_seconds,
                "threshold_percent": self.config.rebalance.threshold_percent,
                "extreme_threshold_percent": self.config.rebalance.extreme_threshold_percent,
                "min_trade_usdc": self.config.trading.min_trade_usdc,
                "slippage_percent": self.config.trading.slippage_percent,
            }
        }
    
    def on_rebalance(self, callback: Callable):
        """
        Set callback for when a rebalance trade is executed.
        
        Args:
            callback: Function that takes rebalance result dict
        """
        self._on_rebalance = callback
    
    def on_status(self, callback: Callable):
        """
        Set callback for status updates.
        
        Args:
            callback: Function that takes status dict
        """
        self._on_status = callback


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """
    Command-line interface for the bot.
    
    Usage:
        python bot.py                    # Run forever
        python bot.py --once             # Run once
        python bot.py --status           # Show status
        python bot.py --target 60        # Set 60% BTC target and run once
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="BTC Power Law Rebalancer Bot"
    )
    parser.add_argument(
        "--once", 
        action="store_true",
        help="Run once and exit"
    )
    parser.add_argument(
        "--status",
        action="store_true", 
        help="Show status and exit"
    )
    parser.add_argument(
        "--target",
        type=float,
        help="Set BTC target percentage (0-100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing"
    )
    
    args = parser.parse_args()
    
    # Create bot
    bot = RebalancerBot()
    
    # Set target if provided
    if args.target is not None:
        bot.set_allocation_target(args.target, source="cli")
    
    # Handle commands
    if args.status:
        status = bot.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.dry_run:
        # Just show what would happen
        state = bot.portfolio.get_state()
        target = bot.get_current_target()
        decision = bot.portfolio.calculate_rebalance(state)
        
        print("\n=== DRY RUN ===")
        print(f"Current: {state.wbtc_percent:.1f}% BTC, {state.usdc_percent:.1f}% USDC")
        print(f"Target: {target.btc_percent:.1f}% BTC, {target.usdc_percent:.1f}% USDC")
        print(f"Decision: {decision.direction} ${decision.amount_usdc:.2f}")
        print(f"Reason: {decision.reason}")
        print(f"Would execute: {decision.should_rebalance}")
        return
    
    if args.once:
        result = bot.run_once()
        print(json.dumps(result, indent=2))
        return
    
    # Run forever
    bot.run_forever()


if __name__ == "__main__":
    main()


# =============================================================================
# QUICK REFERENCE
# =============================================================================
#
# Running the bot:
#
#   # From command line
#   python bot.py                    # Run forever
#   python bot.py --once             # Run once
#   python bot.py --status           # Show status
#   python bot.py --target 60        # Set 60% BTC and run once
#   python bot.py --dry-run          # Preview without executing
#
#   # From code
#   bot = RebalancerBot()
#   bot.set_allocation_target(60)    # 60% BTC
#   bot.run_once()                   # Single check
#   bot.run_forever()                # Continuous
#
# Integrating with external allocation engine:
#
#   bot = RebalancerBot()
#   
#   # Your engine provides target
#   target_btc = your_engine.get_daily_target()
#   bot.set_allocation_target(target_btc, source="my_engine")
#   
#   # Run rebalance
#   result = bot.run_once()
#
# =============================================================================
