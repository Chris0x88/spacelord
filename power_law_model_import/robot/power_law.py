"""
Bitcoin Power Law Integration
=============================

This module handles Power Law calculations and allocation targets.
It determines how much BTC vs USDC the portfolio should hold based
on where Bitcoin's current price sits relative to its historical
Power Law trend.

POWER LAW CONCEPT:
Bitcoin's price has historically followed a power law relationship
with time since genesis. When price is:
- Below the trend: BTC is "cheap" -> accumulate more BTC
- Above the trend: BTC is "expensive" -> accumulate more USDC
- At the trend: neutral allocation

ALLOCATION BANDS:
The further from the trend, the more aggressive the allocation:
- Deep below (-50%): 90% BTC, 10% USDC
- Moderately below (-25%): 75% BTC, 25% USDC
- At trend (0%): 50% BTC, 50% USDC
- Moderately above (+25%): 25% BTC, 75% USDC
- Deep above (+50%): 10% BTC, 90% USDC

INTEGRATION:
This module provides the target allocation. The actual allocation
engine (your external model) can override these defaults by
providing its own targets via the API.
"""

import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# POWER LAW CONSTANTS
# =============================================================================

# Bitcoin genesis block timestamp (January 3, 2009)
GENESIS_TIMESTAMP = datetime(2009, 1, 3, tzinfo=timezone.utc)

# Power Law parameters (these are approximate - adjust based on your model)
# Price = A * (days_since_genesis ^ B)
# These values are illustrative - your allocation engine should provide actuals
POWER_LAW_A = 0.0001  # Coefficient
POWER_LAW_B = 5.83    # Exponent (approximately 5.8-5.9 historically)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PowerLawPosition:
    """
    Current position relative to Power Law.
    
    Attributes:
        current_price: Current BTC price in USD
        power_law_price: Expected price according to Power Law
        deviation_percent: How far from Power Law (-100 to +inf)
                          Negative = below PL (cheap)
                          Positive = above PL (expensive)
        days_since_genesis: Days since Bitcoin genesis
    """
    current_price: Decimal
    power_law_price: Decimal
    deviation_percent: Decimal
    days_since_genesis: int
    
    @property
    def is_below_trend(self) -> bool:
        """True if price is below Power Law (BTC is cheap)."""
        return self.deviation_percent < 0
    
    @property
    def is_above_trend(self) -> bool:
        """True if price is above Power Law (BTC is expensive)."""
        return self.deviation_percent > 0


@dataclass
class AllocationTarget:
    """
    Target allocation based on Power Law position.
    
    Attributes:
        btc_percent: Target BTC allocation (0-100)
        usdc_percent: Target USDC allocation (0-100)
        power_law_position: The Power Law analysis
        confidence: Confidence in this target (0-1)
        source: Where this target came from
    """
    btc_percent: Decimal
    usdc_percent: Decimal
    power_law_position: Optional[PowerLawPosition] = None
    confidence: Decimal = Decimal("1.0")
    source: str = "power_law"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "btc_percent": float(self.btc_percent),
            "usdc_percent": float(self.usdc_percent),
            "confidence": float(self.confidence),
            "source": self.source,
            "power_law": {
                "current_price": float(self.power_law_position.current_price) if self.power_law_position else None,
                "power_law_price": float(self.power_law_position.power_law_price) if self.power_law_position else None,
                "deviation_percent": float(self.power_law_position.deviation_percent) if self.power_law_position else None,
            } if self.power_law_position else None
        }


# =============================================================================
# POWER LAW CALCULATOR
# =============================================================================

class PowerLawCalculator:
    """
    Calculates Power Law position and allocation targets.
    
    This provides a default implementation. Your external allocation
    engine can override these calculations by providing targets directly.
    
    Usage:
        calc = PowerLawCalculator()
        
        # Get Power Law position
        position = calc.get_position(current_btc_price=95000)
        
        # Get allocation target
        target = calc.get_allocation_target(current_btc_price=95000)
    """
    
    def __init__(
        self,
        power_law_a: float = POWER_LAW_A,
        power_law_b: float = POWER_LAW_B,
        neutral_btc_percent: float = 50.0,
        max_btc_percent: float = 90.0,
        min_btc_percent: float = 10.0
    ):
        """
        Initialize the calculator.
        
        Args:
            power_law_a: Power Law coefficient
            power_law_b: Power Law exponent
            neutral_btc_percent: BTC % when at Power Law
            max_btc_percent: Maximum BTC % (when very cheap)
            min_btc_percent: Minimum BTC % (when very expensive)
        """
        self.a = power_law_a
        self.b = power_law_b
        self.neutral = Decimal(str(neutral_btc_percent))
        self.max_btc = Decimal(str(max_btc_percent))
        self.min_btc = Decimal(str(min_btc_percent))
    
    def get_days_since_genesis(self, dt: Optional[datetime] = None) -> int:
        """
        Calculate days since Bitcoin genesis.
        
        Args:
            dt: Datetime to calculate from. If None, uses now.
            
        Returns:
            Number of days since genesis
        """
        dt = dt or datetime.now(timezone.utc)
        delta = dt - GENESIS_TIMESTAMP
        return delta.days
    
    def get_power_law_price(self, days: Optional[int] = None) -> Decimal:
        """
        Calculate expected Power Law price.
        
        Args:
            days: Days since genesis. If None, uses current.
            
        Returns:
            Expected BTC price according to Power Law
        """
        days = days or self.get_days_since_genesis()
        price = self.a * (days ** self.b)
        return Decimal(str(price))
    
    def get_position(self, current_btc_price: float) -> PowerLawPosition:
        """
        Calculate current position relative to Power Law.
        
        Args:
            current_btc_price: Current BTC price in USD
            
        Returns:
            PowerLawPosition with deviation analysis
        """
        days = self.get_days_since_genesis()
        pl_price = self.get_power_law_price(days)
        current = Decimal(str(current_btc_price))
        
        # Calculate deviation: (current - expected) / expected * 100
        if pl_price > 0:
            deviation = ((current - pl_price) / pl_price) * 100
        else:
            deviation = Decimal("0")
        
        return PowerLawPosition(
            current_price=current,
            power_law_price=pl_price,
            deviation_percent=deviation,
            days_since_genesis=days
        )
    
    def get_allocation_target(
        self, 
        current_btc_price: float
    ) -> AllocationTarget:
        """
        Calculate target allocation based on Power Law position.
        
        The allocation scales linearly between min and max based on
        how far the price is from the Power Law trend.
        
        Args:
            current_btc_price: Current BTC price in USD
            
        Returns:
            AllocationTarget with model allocation signal
        """
        position = self.get_position(current_btc_price)
        
        # Calculate BTC allocation based on deviation
        # Deviation of -50% -> max_btc (90%)
        # Deviation of 0% -> neutral (50%)
        # Deviation of +50% -> min_btc (10%)
        
        deviation = float(position.deviation_percent)
        
        if deviation <= -50:
            btc_percent = self.max_btc
        elif deviation >= 50:
            btc_percent = self.min_btc
        else:
            # Linear interpolation
            # Map deviation from [-50, 50] to [max_btc, min_btc]
            normalized = (deviation + 50) / 100  # 0 to 1
            btc_percent = self.max_btc - (normalized * (self.max_btc - self.min_btc))
        
        usdc_percent = Decimal("100") - btc_percent
        
        return AllocationTarget(
            btc_percent=btc_percent,
            usdc_percent=usdc_percent,
            power_law_position=position,
            confidence=Decimal("0.8"),  # Default confidence
            source="power_law"
        )


# =============================================================================
# EXTERNAL ALLOCATION INTERFACE
# =============================================================================

class AllocationProvider:
    """
    Interface for external allocation engines.
    
    Your allocation engine should implement this interface to provide
    custom allocation targets to the bot.
    
    The default implementation uses the PowerLawCalculator.
    Override get_target() to use your own model.
    """
    
    def __init__(self):
        """Initialize with Power Law calculator and optional heartbeat model."""
        self.calculator = PowerLawCalculator()
        self._override_target: Optional[AllocationTarget] = None
        
        # Allocation model selection via environment variable
        # ALLOCATION_MODEL=HEARTBEAT -> use heartbeat model
        # ALLOCATION_MODEL=POWER_LAW -> use power law (default)
        self._mode = os.getenv("ALLOCATION_MODEL", "POWER_LAW").strip().upper()
        self._heartbeat_available = False
        self._heartbeat_get_daily_signal = None
        
        if self._mode == "HEARTBEAT":
            try:
                # Add project root to path for model import
                project_root = Path(__file__).resolve().parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                from model.heartbeat_model import get_daily_signal
                
                self._heartbeat_get_daily_signal = get_daily_signal
                self._heartbeat_available = True
                logger.info("AllocationProvider: Using HEARTBEAT model")
            except ImportError as e:
                logger.warning(f"Heartbeat model not available ({e}), using POWER_LAW")
                self._mode = "POWER_LAW"
        else:
            logger.info("AllocationProvider: Using POWER_LAW model")
    
    def set_target_override(
        self, 
        btc_percent: float,
        confidence: float = 1.0,
        source: str = "external"
    ):
        """
        Set a manual target override.
        
        Use this to inject targets from your external allocation engine.
        
        Args:
            btc_percent: Target BTC percentage (0-100)
            confidence: Confidence in this target (0-1)
            source: Description of target source
        """
        self._override_target = AllocationTarget(
            btc_percent=Decimal(str(btc_percent)),
            usdc_percent=Decimal(str(100 - btc_percent)),
            confidence=Decimal(str(confidence)),
            source=source
        )
        logger.info(
            f"Target override set: {btc_percent}% BTC from {source}"
        )
    
    def clear_override(self):
        """Clear any manual target override."""
        self._override_target = None
        logger.info("Target override cleared")
    
    def get_target(self, current_btc_price: float) -> AllocationTarget:
        """
        Get the current allocation target.
        
        Returns override if set, otherwise calculates from Power Law.
        
        Args:
            current_btc_price: Current BTC price in USD
            
        Returns:
            AllocationTarget with model allocation signal
        """
        if self._override_target is not None:
            return self._override_target
        
        # Use heartbeat model if available and enabled
        if self._heartbeat_available and self._heartbeat_get_daily_signal:
            try:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                signal = self._heartbeat_get_daily_signal(now, float(current_btc_price))
                
                allocation_pct = signal.get("allocation_pct")
                if allocation_pct is None:
                    raise ValueError("No allocation_pct in signal")
                
                btc_percent = Decimal(str(allocation_pct))
                usdc_percent = Decimal("100") - btc_percent
                
                return AllocationTarget(
                    btc_percent=btc_percent,
                    usdc_percent=usdc_percent,
                    power_law_position=None,
                    confidence=Decimal("0.9"),
                    source="heartbeat_model",
                )
            except Exception as e:
                logger.error(f"Heartbeat model failed ({e}), falling back to power law")
        
        # Fallback: Power Law calculator
        return self.calculator.get_allocation_target(current_btc_price)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_power_law_price() -> float:
    """Get current Power Law expected price."""
    calc = PowerLawCalculator()
    return float(calc.get_power_law_price())


def get_allocation_for_price(btc_price: float) -> dict:
    """
    Quick function to get allocation for a given BTC price.
    
    Args:
        btc_price: Current BTC price in USD
        
    Returns:
        Dictionary with allocation signal
    """
    provider = AllocationProvider()
    target = provider.get_target(btc_price)
    return target.to_dict()


# =============================================================================
# QUICK REFERENCE
# =============================================================================
#
# Using the Power Law calculator:
#
#   calc = PowerLawCalculator()
#   
#   # Get expected price
#   pl_price = calc.get_power_law_price()
#   
#   # Get position relative to Power Law
#   position = calc.get_position(current_price=95000)
#   print(f"Deviation: {position.deviation_percent}%")
#   
#   # Get allocation target
#   target = calc.get_allocation_target(current_price=95000)
#   print(f"Target: {target.btc_percent}% BTC")
#
# Using external allocation:
#
#   provider = AllocationProvider()
#   
#   # Use Power Law (default)
#   target = provider.get_target(95000)
#   
#   # Override with external target
#   provider.set_target_override(btc_percent=70, source="my_model")
#   target = provider.get_target(95000)  # Returns 70% BTC
#
# =============================================================================
