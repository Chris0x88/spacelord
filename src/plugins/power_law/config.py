#!/usr/bin/env python3
"""
Power Law Bot Configuration — Merged with Pacman .env
=====================================================

All settings are read from the same .env file Pacman uses.
Prefixed with ROBOT_ to avoid collision.
"""

import os
from dataclasses import dataclass, field


@dataclass
class RobotConfig:
    """
    Configuration for the Power Law rebalancer bot.
    
    All values read from .env with ROBOT_ prefix.
    """
    # --- Rebalance Strategy ---
    # 15% threshold achieves 1.51x vs HODL in backtesting
    threshold_percent: float = field(default_factory=lambda: float(
        os.getenv("ROBOT_THRESHOLD_PERCENT", "15.0")
    ))
    # Extreme moves trigger immediate rebalance
    extreme_threshold_percent: float = field(default_factory=lambda: float(
        os.getenv("ROBOT_EXTREME_THRESHOLD", "5.0")
    ))
    # Check interval in seconds (3600 = hourly)
    interval_seconds: int = field(default_factory=lambda: int(
        os.getenv("ROBOT_INTERVAL_SECONDS", "3600")
    ))
    
    # --- Trading Safety ---
    min_trade_usd: float = field(default_factory=lambda: float(
        os.getenv("ROBOT_MIN_TRADE_USD", "1.0")
    ))
    hbar_reserve_min: float = field(default_factory=lambda: float(
        os.getenv("ROBOT_HBAR_RESERVE", "5.0")
    ))
    # Minimum portfolio balance (USD) to justify rebalancing.
    # A 15% price move on a $5 portfolio = $0.75 rebalance trade.
    # Costs: ~$0.30 EVM execution + ~$0.01 HBAR gas + LP fee (0.3% of trade).
    # At $5, costs eat ~42% of the trade — borderline but viable.
    # Below $5, costs exceed the rebalance benefit.
    min_portfolio_usd: float = field(default_factory=lambda: float(
        os.getenv("ROBOT_MIN_PORTFOLIO_USD", "5.0")
    ))
    # Estimated fixed cost per rebalance trade (EVM execution + gas)
    estimated_trade_cost_usd: float = 0.30
    
    # --- Model Selection ---
    model: str = field(default_factory=lambda:
        os.getenv("ROBOT_MODEL", "POWER_LAW")
    )
    
    # --- Simulation Mode ---
    # Default True for safety. Set ROBOT_SIMULATE=false for live trading.
    simulate: bool = field(default_factory=lambda:
        os.getenv("ROBOT_SIMULATE", "true").lower() != "false"
    )


def get_robot_config() -> RobotConfig:
    """Factory function to create robot configuration."""
    return RobotConfig()
