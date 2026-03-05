from __future__ import annotations

"""
═══════════════════════════════════════════════════════════════════════════════
                    THE BITCOIN HEARTBEAT MODEL
                 Power-Law Floor + Halving Spikes + Heartbeat
═══════════════════════════════════════════════════════════════════════════════

Single task: for a given DATE and BTCUSDT PRICE, tell us what % of a
portfolio "should" be in Bitcoin.

Core ideas:
  FLOOR     = physics-style equilibrium (where price wants to be)
  SPIKE     = cycle-dependent upside potential  
  HEARTBEAT = where we are in the halving cycle
  SIGNAL    = how much BTC to hold (0-100%)

This module is designed to be app/backend ready:
- Pure Python, no environment-specific paths
- Works with Binance-style BTCUSDT candles or your master CSV
- Backtest helper functions included
- LLM-friendly taglines for natural language output

═══════════════════════════════════════════════════════════════════════════════
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Project root (for loading data files when run as a script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ============================================================================
# CONSTANTS & HALVING SCHEDULE
# ============================================================================

GENESIS = datetime(2009, 1, 3)

# Power-law floor: log10(Floor) = FLOOR_A + FLOOR_B * log10(days_since_genesis)
FLOOR_A = -17.0       # log10 intercept, calibrated to BTC history
FLOOR_B = 5.73        # power-law exponent (critical network / energy scaling)

# Spike envelope: max multiple above floor for a given halving cycle
# Spike_max(cycle) = 1 + SPIKE_A * cycle^(-KLEIBER) * HALVING_BASE^(cycle-2)
SPIKE_A: float = 40.0   # initial spike amplitude (calibrated to early cycles)
KLEIBER: float = 0.75   # 3/4 scaling law (fractal / biological efficiency)
HALVING_BASE: float = 0.5    # impact of halvings decays geometrically

# Halving schedule - ACTUAL dates for known halvings, formula for future
# Using discrete dates is critical for accurate cycle progress calculation!
HALVINGS = [
    datetime(2012, 11, 28),  # Halving 1
    datetime(2016, 7, 9),    # Halving 2
    datetime(2020, 5, 11),   # Halving 3
    datetime(2024, 4, 20),   # Halving 4
]
# For future halvings, estimate ~4 years (1461 days) per cycle
DAYS_PER_CYCLE = 1461  # ~4 years

# Halving transition smoothing: blend old/new cycle values over this window
# V3.2: Transition now natively handled by revised ceiling logic.
HALVING_TRANSITION_DAYS = 30  # Days to smooth across halving boundary (legacy)

# Allocation smoothing around halving: legacy constants
HALVING_FREEZE_DAYS = 90   
HALVING_BLEND_DAYS = 90    


def get_halving_date(n: int) -> datetime:
    """Get the date of the nth halving (1-indexed).
    
    Uses ACTUAL dates for known halvings (1-4), projects future ones.
    """
    if n < 1:
        raise ValueError("Halving number must be >= 1")
    if n <= len(HALVINGS):
        return HALVINGS[n - 1]
    # Project future halvings from last known
    last_known = HALVINGS[-1]
    cycles_ahead = n - len(HALVINGS)
    return last_known + timedelta(days=cycles_ahead * DAYS_PER_CYCLE)


# ============================================================================
# CORE MODEL FUNCTIONS
# ----------------------------------------------------------------------------
# CRITICAL: THIS MODEL IS LOCKED. 
# NO CHANGES TO CONSTANTS OR LOGIC WITHOUT EXPLICIT USER APPROVAL.
# ============================================================================

def days_since_genesis(date: datetime) -> int:
    return max(1, (date - GENESIS).days)


def floor_price(date: datetime) -> float:
    """Power-law floor: where Bitcoin "wants" to be in equilibrium."""
    d = days_since_genesis(date)
    return 10 ** (FLOOR_A + FLOOR_B * math.log10(d))


def cycle_index(date: datetime) -> int:
    """Halving cycle index using actual halving dates."""
    for i, h in enumerate(HALVINGS):
        if date < h:
            return i + 1
    # After all known halvings - project forward
    last_halving = HALVINGS[-1]
    days_since_last = (date - last_halving).days
    return len(HALVINGS) + 1 + int(days_since_last / DAYS_PER_CYCLE)


def spike_max(c: int) -> float:
    """Maximum spike multiple above floor for a given cycle."""
    kleiber_term = c ** (-KLEIBER)
    halving_term = HALVING_BASE ** (c - 2)
    return 1 + SPIKE_A * kleiber_term * halving_term


def cycle_progress_raw(date: datetime) -> float:
    """Calculate raw cycle progress (0.0 to 1.0) within current halving cycle.
    
    Uses actual halving dates for accuracy.
    """
    c = cycle_index(date)
    
    # Get current cycle start (previous halving)
    if c <= len(HALVINGS):
        if c == 1:
            # First cycle starts at genesis
            cycle_start = GENESIS
        else:
            cycle_start = HALVINGS[c - 2]
        cycle_end = HALVINGS[c - 1] if c <= len(HALVINGS) else get_halving_date(c)
    else:
        # Future cycle - project from last known halving
        cycle_start = get_halving_date(c - 1) if c > 1 else GENESIS
        cycle_end = get_halving_date(c)
    
    cycle_length = (cycle_end - cycle_start).days
    days_in = (date - cycle_start).days
    
    if cycle_length <= 0:
        return 0.0
    
    return min(1.0, max(0.0, days_in / cycle_length))


def ceiling_price(date: datetime) -> float:
    """Elegant continuous ceiling that intersects the speculative peaks (at 33% progress).
    
    This replaces the piecewise logic with a single decaying envelope indexed to the peak.
    """
    c = cycle_index(date)
    p = cycle_progress_raw(date)
    
    # Peak-centered effective cycle index: 
    # C_peak is exactly an integer (e.g., 4.0, 5.0) when p=0.33
    c_peak = c + (p - 0.33)
    
    return floor_price(date) * spike_max(c_peak)


# Alias for backwards compatibility - ceiling_price now contains the revised logic
revised_ceiling_price = ceiling_price


def heartbeat_pulse(progress: float, cycle: int = 5) -> float:
    """Asymmetric 'Up the Escalator, Down the Elevator' Pulse.
    
    progress: 0.0 to 1.0 within halving cycle.
    cycle: current halving cycle (used for maturity scaling).
    
    Peak ~0.33: speculative peak occurs ~1/3 into each cycle.
    w_up: slow build-up (escalator).
    w_down: sharp crash (elevator), matures with each cycle.
    """
    peak = 0.33
    w_up = 0.18
    
    # Maturity Scaling: Crashes become slightly less violent (wider) each cycle
    # Cycle 2: 0.10, Cycle 5: 0.13, Cycle 10: 0.18 (symmetric)
    w_down = 0.08 + (cycle * 0.01)
    
    # 1. Calculate asymmetric gaussian
    if progress < peak:
        val = math.exp(-((progress - peak) ** 2) / (2 * w_up ** 2))
    else:
        val = math.exp(-((progress - peak) ** 2) / (2 * w_down ** 2))
    
    # 2. Boundary Pinning: Ensure pulse hits exactly 0 at halving boundaries (p=0 and p=1)
    # This eliminates "bumps" between cycles.
    v0 = math.exp(-((-peak)**2) / (2 * w_up**2))
    v1 = math.exp(-((1-peak)**2) / (2 * w_down**2))
    
    # Linear interpolation of the offset to pin boundaries to 0
    offset = (v0 * (1 - progress) + v1 * progress)
    
    return max(0.0, val - offset)


def cycle_progress(date: datetime) -> float:
    """Cycle progress (0.0 to 1.0)."""
    return cycle_progress_raw(date)


def model_price(date: datetime) -> float:
    """Model fair value price.
    
    Now natively continuous thanks to the revised ceiling logic and 
    boundary-pinned skewed heartbeat.
    """
    fl = floor_price(date)
    ceil = ceiling_price(date)
    p = cycle_progress(date)
    c = cycle_index(date)
    hb = heartbeat_pulse(p, c)
    return fl + (ceil - fl) * hb


def position_score(date: datetime, price: float) -> float:
    """Normalised position of price between floor and ceiling.

    0 → at floor, 1 → at ceiling.
    """
    fl = floor_price(date)
    ceil = ceiling_price(date)
    if price <= fl:
        return 0.0
    if price >= ceil:
        return 1.0
    return (price - fl) / (ceil - fl)


def shifted_heartbeat(date: datetime, shift_days: int = 90) -> float:
    """Heartbeat value at a future date (e.g. +90 days) as a leading indicator."""
    future_date = date + timedelta(days=shift_days)
    p = cycle_progress(future_date)
    c = cycle_index(future_date)
    return heartbeat_pulse(p, c)


def allocation_signal(date: datetime, price: float, shift_days: int = 90) -> float:
    """Recommended BTC allocation fraction (0.0 – 1.0).

    Core principle: "Is Bitcoin cheap or expensive right now?"
    
    V3.2 UPDATE (Jan 2026): REVISED CEILING INTEGRATION
    - Ceiling now trends towards next cycle's max from midpoint of current cycle.
    - This eliminates halving discontinuities, making price positioning continuous.
    - Legacy 180-day halving smoothing (freeze/blend) removed as the model is now
      natively continuous through the revised ceiling logic.
    
    LOCKED: NO CHANGES TO THIS LOGIC WITHOUT EXPLICIT USER APPROVAL.
    """
    return _allocation_signal_core(date, price, shift_days)


def _allocation_signal_core(date: datetime, price: float, shift_days: int = 90) -> float:
    """Core allocation calculation without halving smoothing.
    
    This is the raw signal based on current date/price. The main allocation_signal()
    function wraps this with halving smoothing.
    """
    pos = position_score(date, price)  # 0 (at floor) → 1 (at ceiling)
    prog = cycle_progress(date)  # 0-1 within halving cycle
    
    # 1. VALUE COMPONENT: Sigmoid on position (like Kelly on z-score)
    # Convert position (0-1) to z-score equivalent (-2 to +2)
    z_equiv = (pos - 0.5) * 4  # Maps 0→-2, 0.5→0, 1→+2
    
    # Sigmoid with sensitivity=2.0 (from alpha hunt)
    # z=-2 → 98%, z=-1 → 88%, z=0 → 50%, z=+1 → 12%, z=+2 → 2%
    value_alloc = 1.0 / (1.0 + math.exp(z_equiv * 2.0))
    
    # 2. CYCLE PHASE PENALTY: Post-peak caution ("don't catch falling knives")
    # Peak typically occurs around 33% of cycle (heartbeat peak)
    # From 35% to 85% of cycle, we're in "post-peak cooldown"
    # Apply a STRONG penalty - even if price looks cheap, wait for cycle reset
    phase_penalty = 0.0
    if 0.35 <= prog <= 0.85:
        # Penalty ramps up to 50% at deepest bear (55-60%), then slowly recovers
        if prog <= 0.55:
            phase_penalty = (prog - 0.35) / 0.20 * 0.50  # 0 to 50%
        elif prog <= 0.70:
            phase_penalty = 0.50  # Stay at max penalty through bear
        else:
            phase_penalty = (0.85 - prog) / 0.15 * 0.50  # 50% back to 0
    
    # 3. MOMENTUM COMPONENT: Heartbeat direction (smaller weight now)
    c = cycle_index(date)
    hb_now = heartbeat_pulse(prog, c)
    hb_future = shifted_heartbeat(date, shift_days)
    
    # Momentum tilt: smaller range ±0.10
    momentum_delta = (hb_future - hb_now) * 0.3
    momentum_delta = max(-0.10, min(0.10, momentum_delta))
    
    # 4. COMBINE: Value - Phase Penalty + Momentum
    raw_alloc = value_alloc - phase_penalty + momentum_delta
    
    # 5. V3 FLOOR BOOST: Extra allocation when in deep value zone
    # BUT: Scale boost inversely with phase penalty to maintain uniform caution
    # During max penalty (0.50), floor boost is disabled - don't catch falling knives!
    FLOOR_BOOST = 0.30  # +30% boost at floor
    DEEP_VALUE_THRESHOLD = 0.15  # Bottom 15% of range
    VALUE_THRESHOLD = 0.30  # Bottom 30% of range
    
    # Scale floor boost inversely with phase penalty (0.50 penalty = 0% boost)
    boost_scale = max(0.0, 1.0 - phase_penalty * 2)
    
    if pos < DEEP_VALUE_THRESHOLD:
        # Deep value zone - maximum boost (scaled by phase)
        boost_factor = (DEEP_VALUE_THRESHOLD - pos) / DEEP_VALUE_THRESHOLD
        raw_alloc = min(1.0, raw_alloc + FLOOR_BOOST * boost_factor * boost_scale)
    elif pos < VALUE_THRESHOLD:
        # Value zone - partial boost (scaled by phase)
        boost_factor = (VALUE_THRESHOLD - pos) / (VALUE_THRESHOLD - DEEP_VALUE_THRESHOLD)
        raw_alloc = min(1.0, raw_alloc + FLOOR_BOOST * 0.5 * boost_factor * boost_scale)
    
    return max(0.0, min(1.0, raw_alloc))


# ============================================================================
# TAGGING FOR APP / LLM-FRIENDLY MESSAGING
# ============================================================================

def sentiment_tags(date: datetime, price: float) -> Dict[str, str]:
    """Return coarse tags for LLM/app messaging."""
    c = cycle_index(date)
    prog = cycle_progress(date)
    pos = position_score(date, price)
    alloc = allocation_signal(date, price)

    # Cycle phase tag
    if prog < 0.15:
        phase = "early_cycle_reset"
    elif prog < 0.35:
        phase = "pre_peak_build_up"
    elif prog < 0.55:
        phase = "late_cycle_peak_zone"
    elif prog < 0.8:
        phase = "post_peak_cooldown"
    else:
        phase = "late_cycle_washout"

    # Valuation tag (relative to floor/ceiling)
    if pos < 0.2:
        valuation = "deep_value"
    elif pos < 0.4:
        valuation = "undervalued"
    elif pos < 0.6:
        valuation = "mid_band"
    elif pos < 0.8:
        valuation = "overvalued"
    else:
        valuation = "euphoria"

    # Allocation stance
    if alloc > 0.8:
        stance = "max_accumulate"
    elif alloc > 0.6:
        stance = "accumulate"
    elif alloc > 0.4:
        stance = "balanced"
    elif alloc > 0.2:
        stance = "trim_exposure"
    else:
        stance = "capital_protection"

    return {
        "cycle_phase": phase,
        "valuation_state": valuation,
        "allocation_stance": stance,
        "cycle_index": f"cycle_{c}",
        "cycle_progress_pct": round(prog * 100, 1),
        "position_pct": round(pos * 100, 1),
        "allocation_pct": round(alloc * 100, 1),
    }


def generate_tagline(date: datetime, price: float) -> str:
    """Generate a human-readable tagline for LLM/app display.
    
    Returns a single sentence summarizing the model's view.
    """
    tags = sentiment_tags(date, price)
    alloc = tags["allocation_pct"]
    pos = tags["position_pct"]
    prog = tags["cycle_progress_pct"]
    phase = tags["cycle_phase"].replace("_", " ")
    valuation = tags["valuation_state"].replace("_", " ")
    stance = tags["allocation_stance"].replace("_", " ")
    c = cycle_index(date)
    
    # Build natural sentence
    if alloc >= 70:
        action = "Strong accumulation zone"
    elif alloc >= 50:
        action = "Favorable accumulation"
    elif alloc >= 35:
        action = "Neutral positioning"
    elif alloc >= 20:
        action = "Reduce exposure"
    else:
        action = "Capital protection mode"
    
    return (
        f"Cycle {c} | {prog:.0f}% complete | {phase.title()} | "
        f"Price at {pos:.0f}% of range ({valuation}) | "
        f"{action}: {alloc:.0f}% BTC recommended"
    )


def get_daily_signal(date: datetime, price: float) -> Dict:
    """Primary API for trading bot integration.
    
    Returns a complete signal package ready for bot consumption.
    """
    alloc = allocation_signal(date, price)
    tags = sentiment_tags(date, price)
    tagline = generate_tagline(date, price)
    
    fl = floor_price(date)
    ceil = ceiling_price(date)
    rev_ceil = revised_ceiling_price(date)
    model = model_price(date)
    
    return {
        "date": date.strftime("%Y-%m-%d"),
        "price": price,
        "allocation_pct": round(alloc * 100, 1),
        "floor": round(fl, 2),
        "ceiling": round(ceil, 2),
        "revised_ceiling": round(rev_ceil, 2),
        "model_price": round(model, 2),
        "position_in_band_pct": tags["position_pct"],
        "cycle": cycle_index(date),
        "cycle_progress_pct": tags["cycle_progress_pct"],
        "phase": tags["cycle_phase"],
        "valuation": tags["valuation_state"],
        "stance": tags["allocation_stance"],
        "tagline": tagline,
    }


def get_future_projections(date: datetime, current_price: float) -> Dict:
    """Get model projections for 1, 3, 6, and 12 months out.
    
    Returns floor price, model fair value, and model allocation % for each period.
    Allocation assumes TODAY'S PRICE persists at those future dates - this shows
    how the model would view the same price as time progresses.
    """
    periods = [
        {"label": "1M", "days": 30},
        {"label": "3M", "days": 91},
        {"label": "6M", "days": 182},
        {"label": "12M", "days": 365},
        {"label": "24M", "days": 730},
        {"label": "36M", "days": 1095},
    ]
    
    projections = []
    for period in periods:
        future_date = date + timedelta(days=period["days"])
        fl = floor_price(future_date)
        model = model_price(future_date)
        rev_ceil = revised_ceiling_price(future_date)
        # Allocation assumes current price persists at future date
        # This shows: "If price stays here, what would model say in X months?"
        alloc = allocation_signal(future_date, current_price)
        
        projections.append({
            "period": period["label"],
            "days_out": period["days"],
            "date": future_date.strftime("%Y-%m-%d"),
            "floor": round(fl, 0),
            "model_price": round(model, 0),
            "revised_ceiling": round(rev_ceil, 0),
            "allocation_pct": round(alloc * 100, 0),
        })
    
    return {
        "as_of": date.strftime("%Y-%m-%d"),
        "current_price": current_price,
        "projections": projections,
    }


# ============================================================================
# PORTFOLIO / BACKTEST SUPPORT
# ============================================================================

@dataclass
class PortfolioState:
    btc: float
    usd: float

    def total_value(self, price: float) -> float:
        return self.btc * price + self.usd


def rebalance_to_target(
    state: PortfolioState,
    price: float,
    target_alloc: float,
    fee_rate: float = 0.003,
) -> PortfolioState:
    """Rebalance portfolio to target BTC allocation, applying trading fees.

    fee_rate: e.g. 0.003 = 0.30% on traded notional.
    """
    total = state.total_value(price)
    if total <= 0:
        return state

    target_btc = (total * target_alloc) / price
    target_usd = total * (1.0 - target_alloc)

    delta_btc = target_btc - state.btc
    trade_notional = abs(delta_btc) * price
    fee = trade_notional * fee_rate

    new_usd = target_usd - fee
    new_btc = target_btc

    return PortfolioState(btc=new_btc, usd=new_usd)


def _normalise_price_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    if "date" not in data.columns:
        raise ValueError("DataFrame must contain a 'date' column")
    if "close" in data.columns:
        price_col = "close"
    elif "btc_close_usdt" in data.columns:
        price_col = "btc_close_usdt"
    else:
        raise ValueError("DataFrame must contain a 'close' or 'btc_close_usdt' column")

    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)
    data["price"] = data[price_col].astype(float)
    return data


def backtest_heartbeat_strategy(
    df: pd.DataFrame,
    start_date: Optional[datetime] = None,
    fee_rate: float = 0.003,
    rebalance_days: int = 30,
    spike_threshold: float = 0.0,  # 0 = disabled, e.g. 0.05 = 5% move triggers rebalance
) -> Dict[str, float]:
    """Backtest the allocation strategy on a daily BTCUSDT series.

    df must have columns: ['date', 'close'] or ['date', 'btc_close_usdt'].
    - start_date: if provided, only use data from that date onwards.
    - rebalance_days: fixed rebalance interval (e.g. 7, 30, 90).
    - spike_threshold: if > 0, also rebalance on price moves exceeding this %.
    
    Returns dict with performance metrics.
    """
    data = _normalise_price_data(df)

    if start_date is not None:
        data = data[data["date"] >= start_date].reset_index(drop=True)

    if len(data) < rebalance_days + 5:
        raise ValueError("Not enough data for backtest with this rebalance period")

    initial_price = float(data["price"].iloc[0])
    initial_capital = 100.0

    # Strategy: start in cash, then follow model
    strat_state = PortfolioState(btc=0.0, usd=initial_capital)

    # Buy-and-hold benchmark: 100% BTC from day 1, one fee at entry
    bh_fee = initial_capital * fee_rate
    bh_btc = (initial_capital - bh_fee) / initial_price
    bh_state = PortfolioState(btc=bh_btc, usd=0.0)

    last_rebalance_index = 0
    last_rebalance_price = initial_price
    trade_count = 0
    
    # Track portfolio values for metrics
    portfolio_values: List[float] = [initial_capital]
    bh_values: List[float] = [initial_capital]

    for i, row in data.iterrows():
        dt = row["date"].to_pydatetime()
        price = float(row["price"])

        if i == 0:
            continue
        
        # Check if we should rebalance
        days_since = i - last_rebalance_index
        price_move = abs(price - last_rebalance_price) / last_rebalance_price if last_rebalance_price > 0 else 0
        
        should_rebalance = False
        if days_since >= rebalance_days:
            should_rebalance = True
        elif spike_threshold > 0 and price_move >= spike_threshold:
            should_rebalance = True
        
        if should_rebalance:
            target_alloc = allocation_signal(dt, price)
            strat_state = rebalance_to_target(strat_state, price, target_alloc, fee_rate)
            last_rebalance_index = i
            last_rebalance_price = price
            trade_count += 1
        
        # Track values
        portfolio_values.append(strat_state.total_value(price))
        bh_values.append(bh_state.total_value(price))

    final_price = float(data["price"].iloc[-1])
    strat_final = strat_state.total_value(final_price)
    bh_final = bh_state.total_value(final_price)
    
    # Calculate metrics
    pv = np.array(portfolio_values)
    bv = np.array(bh_values)
    n_days = len(data)
    
    # CAGR
    years = n_days / 365.0
    strat_cagr = (strat_final / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    bh_cagr = (bh_final / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    
    # Max Drawdown
    strat_peak = np.maximum.accumulate(pv)
    strat_dd = (pv - strat_peak) / strat_peak
    strat_max_dd = float(np.min(strat_dd))
    
    bh_peak = np.maximum.accumulate(bv)
    bh_dd = (bv - bh_peak) / bh_peak
    bh_max_dd = float(np.min(bh_dd))
    
    # Sharpe (annualized, assuming 0% risk-free)
    strat_returns = np.diff(pv) / pv[:-1]
    strat_sharpe = float(np.mean(strat_returns) / np.std(strat_returns) * np.sqrt(365)) if np.std(strat_returns) > 0 else 0

    return {
        "rebalance_days": rebalance_days,
        "spike_threshold": spike_threshold,
        "trade_count": trade_count,
        "strategy_final": round(strat_final, 2),
        "buy_and_hold_final": round(bh_final, 2),
        "strategy_vs_bh_ratio": round(strat_final / bh_final, 3) if bh_final > 0 else float("nan"),
        "strategy_cagr_pct": round(strat_cagr * 100, 1),
        "bh_cagr_pct": round(bh_cagr * 100, 1),
        "strategy_max_dd_pct": round(strat_max_dd * 100, 1),
        "bh_max_dd_pct": round(bh_max_dd * 100, 1),
        "strategy_sharpe": round(strat_sharpe, 2),
    }


def scan_rebalance_periods(
    df: pd.DataFrame,
    start_date: Optional[datetime] = None,
    fee_rate: float = 0.003,
    periods: List[int] = (7, 14, 30, 60, 90, 180),
    spike_thresholds: List[float] = (0.0,),
) -> pd.DataFrame:
    """Evaluate multiple rebalance periods and spike thresholds.
    
    Returns a DataFrame with performance per configuration.
    """
    results: List[Dict[str, float]] = []
    for p in periods:
        for spike in spike_thresholds:
            try:
                res = backtest_heartbeat_strategy(
                    df=df,
                    start_date=start_date,
                    fee_rate=fee_rate,
                    rebalance_days=p,
                    spike_threshold=spike,
                )
                results.append(res)
            except ValueError:
                continue
    return pd.DataFrame(results)


def rolling_backtest(
    df: pd.DataFrame,
    window_days: int = 365 * 2,
    step_days: int = 90,
    fee_rate: float = 0.003,
    rebalance_days: int = 60,
    spike_threshold: float = 0.0,
) -> pd.DataFrame:
    """Run backtest from multiple start dates to test robustness.
    
    Args:
        df: Price data with 'date' and 'btc_close_usdt' or 'close' columns
        window_days: Length of each backtest window
        step_days: Days between start dates
        fee_rate: Trading fee per rebalance
        rebalance_days: Fixed rebalance interval
        spike_threshold: Reactive trigger threshold
    
    Returns:
        DataFrame with one row per start date showing performance
    """
    data = _normalise_price_data(df)
    
    min_date = data["date"].min()
    max_date = data["date"].max()
    
    results: List[Dict] = []
    current_start = min_date
    
    while current_start + timedelta(days=window_days) <= max_date:
        end_date = current_start + timedelta(days=window_days)
        
        try:
            window_data = data[(data["date"] >= current_start) & (data["date"] <= end_date)].copy()
            
            if len(window_data) < rebalance_days + 10:
                current_start += timedelta(days=step_days)
                continue
            
            res = backtest_heartbeat_strategy(
                df=window_data,
                start_date=None,  # Already filtered
                fee_rate=fee_rate,
                rebalance_days=rebalance_days,
                spike_threshold=spike_threshold,
            )
            
            res["start_date"] = current_start.strftime("%Y-%m-%d")
            res["end_date"] = end_date.strftime("%Y-%m-%d")
            results.append(res)
            
        except (ValueError, IndexError):
            pass
        
        current_start += timedelta(days=step_days)
    
    return pd.DataFrame(results)


def comprehensive_backtest(
    df: pd.DataFrame,
    fee_rate: float = 0.003,
    window_years: int = 2,
    step_days: int = 90,
) -> Dict[str, pd.DataFrame]:
    """Run comprehensive backtest with rolling windows for multiple configurations.
    
    Returns dict with:
        - 'fixed': Results for fixed rebalancing periods
        - 'reactive': Results for reactive rebalancing
        - 'summary': Aggregated statistics per configuration
    """
    data = _normalise_price_data(df)
    window_days = window_years * 365
    
    # Test configurations
    fixed_periods = [7, 14, 30, 60, 90, 180]
    reactive_configs = [
        (90, 0.10),   # 90-day base + 10% spike trigger
        (90, 0.15),   # 90-day base + 15% spike trigger
        (120, 0.10),  # 120-day base + 10% spike trigger
        (120, 0.15),  # 120-day base + 15% spike trigger
    ]
    
    all_results: List[Dict] = []
    
    # Fixed rebalancing tests
    for period in fixed_periods:
        rolling_df = rolling_backtest(
            df=data,
            window_days=window_days,
            step_days=step_days,
            fee_rate=fee_rate,
            rebalance_days=period,
            spike_threshold=0.0,
        )
        if len(rolling_df) > 0:
            rolling_df["config"] = f"fixed_{period}d"
            rolling_df["config_type"] = "fixed"
            all_results.append(rolling_df)
    
    # Reactive rebalancing tests
    for base_period, spike in reactive_configs:
        rolling_df = rolling_backtest(
            df=data,
            window_days=window_days,
            step_days=step_days,
            fee_rate=fee_rate,
            rebalance_days=base_period,
            spike_threshold=spike,
        )
        if len(rolling_df) > 0:
            rolling_df["config"] = f"reactive_{base_period}d_{int(spike*100)}pct"
            rolling_df["config_type"] = "reactive"
            all_results.append(rolling_df)
    
    if not all_results:
        return {"fixed": pd.DataFrame(), "reactive": pd.DataFrame(), "summary": pd.DataFrame()}
    
    combined = pd.concat(all_results, ignore_index=True)
    
    # Create summary statistics per configuration
    summary = combined.groupby("config").agg({
        "strategy_vs_bh_ratio": ["mean", "std", "min", "max", "count"],
        "strategy_cagr_pct": ["mean", "std"],
        "strategy_max_dd_pct": ["mean", "min"],  # min is worst drawdown
        "strategy_sharpe": ["mean", "std"],
        "trade_count": ["mean"],
    }).round(3)
    
    # Flatten column names
    summary.columns = ["_".join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    
    # Calculate win rate (how often strategy beats HODL)
    win_rates = combined.groupby("config").apply(
        lambda x: (x["strategy_vs_bh_ratio"] > 1.0).mean()
    ).reset_index(name="win_rate")
    
    summary = summary.merge(win_rates, on="config")
    summary = summary.sort_values("strategy_vs_bh_ratio_mean", ascending=False)
    
    return {
        "all_windows": combined,
        "summary": summary,
    }


# ============================================================================
# CLI / EXAMPLE USAGE
# ============================================================================

def _load_master_btc_csv() -> pd.DataFrame:
    """Load the master BTC dataset from the outputs folder.

    You can swap this out for Binance data in your app code.
    """
    csv_path = PROJECT_ROOT / "outputs/bitcoin_viz_package/data/master_btc_dataset_final_2014_today.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"BTC CSV not found at {csv_path}")
    return pd.read_csv(csv_path)


def run_basic_backtest(
    lookback_years: int = 4,
    fee_rate: float = 0.003,
    periods: List[int] = (7, 14, 30, 60, 90, 180),
    spike_thresholds: List[float] = (0.0,),
) -> pd.DataFrame:
    """Convenience wrapper: run scan_rebalance_periods on the master CSV."""
    df = _load_master_btc_csv()
    end_date = pd.to_datetime(df["date"]).max()
    start_date = end_date - timedelta(days=365 * lookback_years)
    results = scan_rebalance_periods(
        df, start_date=start_date, fee_rate=fee_rate, 
        periods=periods, spike_thresholds=spike_thresholds
    )
    return results.sort_values("strategy_vs_bh_ratio", ascending=False)


def validate_model_against_history(df: pd.DataFrame) -> pd.DataFrame:
    """Check how well the model's floor/ceiling captured actual prices."""
    data = _normalise_price_data(df)
    
    results = []
    for _, row in data.iterrows():
        dt = row["date"].to_pydatetime()
        price = float(row["price"])
        fl = floor_price(dt)
        ceil = ceiling_price(dt)
        pos = position_score(dt, price)
        alloc = allocation_signal(dt, price)
        
        results.append({
            "date": dt,
            "price": price,
            "floor": fl,
            "ceiling": ceil,
            "position_pct": pos * 100,
            "allocation_pct": alloc * 100,
            "below_floor": price < fl,
            "above_ceiling": price > ceil,
        })
    
    return pd.DataFrame(results)


if __name__ == "__main__":
    from datetime import timezone
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    # =========================================================================
    # CURRENT SIGNAL - "IS BITCOIN CHEAP OR EXPENSIVE?"
    # =========================================================================
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    example_price = 96000.0  # Replace with live BTCUSDT
    
    print("=" * 79)
    print("         BITCOIN HEARTBEAT MODEL - IS BITCOIN CHEAP OR EXPENSIVE?")
    print("=" * 79)
    
    signal = get_daily_signal(today, example_price)
    fl = signal['floor']
    ceil = signal['ceiling']
    pos = signal['position_in_band_pct']
    
    print(f"\n  Date:     {signal['date']}")
    print(f"  Price:    ${signal['price']:,.0f}")
    print(f"\n  Floor:    ${fl:,.0f}  (power-law equilibrium)")
    print(f"  Ceiling:  ${ceil:,.0f}  (cycle peak potential)")
    print(f"\n  Position: {pos:.0f}% of the way from floor to ceiling")
    print(f"  Cycle:    {signal['cycle']} ({signal['cycle_progress_pct']:.0f}% complete)")
    
    # Simple cheap/expensive verdict
    if pos < 20:
        verdict = "VERY CHEAP - Strong accumulation zone"
    elif pos < 40:
        verdict = "CHEAP - Good accumulation opportunity"
    elif pos < 60:
        verdict = "FAIR VALUE - Neutral"
    elif pos < 80:
        verdict = "EXPENSIVE - Consider taking profits"
    else:
        verdict = "VERY EXPENSIVE - Euphoria zone, protect capital"
    
    print(f"\n  >>> {verdict} <<<")
    print(f"  >>> Recommended BTC allocation: {signal['allocation_pct']:.0f}% <<<")
    print(f"\n  {signal['tagline']}")
    
    # Show allocation breakdown
    c = cycle_index(today)
    prog = cycle_progress(today)
    hb_now = heartbeat_pulse(prog, c)
    hb_future = shifted_heartbeat(today, 90)
    z_equiv = (pos/100 - 0.5) * 4
    value_alloc = 1.0 / (1.0 + math.exp(z_equiv * 2.0))
    
    # Phase penalty calculation
    phase_penalty = 0.0
    if 0.35 <= prog <= 0.85:
        if prog <= 0.55:
            phase_penalty = (prog - 0.35) / 0.20 * 0.50
        elif prog <= 0.70:
            phase_penalty = 0.50
        else:
            phase_penalty = (0.85 - prog) / 0.15 * 0.50
    
    momentum_delta = (hb_future - hb_now) * 0.3
    momentum_delta = max(-0.10, min(0.10, momentum_delta))
    
    print(f"\n  Allocation breakdown:")
    print(f"    Value component (sigmoid):  {value_alloc*100:.0f}%")
    print(f"    Phase penalty (post-peak):  {-phase_penalty*100:+.0f}%")
    print(f"    Heartbeat now:              {hb_now:.2f}")
    print(f"    Heartbeat +90d:             {hb_future:.2f}")
    print(f"    Momentum tilt:              {momentum_delta*100:+.0f}%")
    print(f"    Final allocation:           {signal['allocation_pct']:.0f}%")
    
    # Scenario: What if we're at same price but different cycle phases?
    # Use cycle 5 (current) for all scenarios to show phase penalty effect
    print(f"\n  Scenario comparison at ${example_price:,.0f} (same cycle, different phases):")
    for prog_pct, label in [(40, "Now (40% cycle)"), (50, "Peak zone (50%)"), (65, "Post-peak (65%)"), (80, "Late bear (80%)")]:
        # Simulate different cycle progress within CURRENT cycle (cycle 5)
        test_date = HALVINGS[-1] + timedelta(days=(prog_pct/100) * DAYS_PER_CYCLE)
        test_alloc = allocation_signal(test_date, example_price)
        test_pos = position_score(test_date, example_price)
        
        # Calculate phase penalty for display
        test_penalty = 0.0
        test_prog = prog_pct / 100
        if 0.35 <= test_prog <= 0.85:
            if test_prog <= 0.55:
                test_penalty = (test_prog - 0.35) / 0.20 * 0.50
            elif test_prog <= 0.70:
                test_penalty = 0.50
            else:
                test_penalty = (0.85 - test_prog) / 0.15 * 0.50
        
        print(f"    {label:20s}: {test_alloc*100:.0f}% (pos={test_pos*100:.0f}%, penalty={-test_penalty*100:+.0f}%)")
    
    # =========================================================================
    # MODEL VALIDATION - Does the floor/ceiling actually contain prices?
    # =========================================================================
    print("\n" + "=" * 79)
    print("                    MODEL VALIDATION")
    print("=" * 79)
    
    try:
        df = _load_master_btc_csv()
        print(f"Data range: {df['date'].min()} to {df['date'].max()}\n")
        
        validation = validate_model_against_history(df)
        
        below_floor_pct = validation["below_floor"].mean() * 100
        above_ceiling_pct = validation["above_ceiling"].mean() * 100
        in_band_pct = 100 - below_floor_pct - above_ceiling_pct
        
        print(f"  Price BELOW floor:    {below_floor_pct:.1f}% of days")
        print(f"  Price IN BAND:        {in_band_pct:.1f}% of days")
        print(f"  Price ABOVE ceiling:  {above_ceiling_pct:.1f}% of days")
        
        # Position distribution
        print(f"\n  Position distribution (0%=floor, 100%=ceiling):")
        for bucket in [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]:
            count = ((validation["position_pct"] >= bucket[0]) & 
                     (validation["position_pct"] < bucket[1])).sum()
            pct = count / len(validation) * 100
            label = {(0,20): "VERY CHEAP", (20,40): "CHEAP", (40,60): "FAIR", 
                     (60,80): "EXPENSIVE", (80,100): "VERY EXPENSIVE"}[bucket]
            print(f"    {bucket[0]:3d}-{bucket[1]:3d}%: {pct:5.1f}% of days ({label})")
        
        # =========================================================================
        # BACKTEST - Simple single config test
        # =========================================================================
        print("\n" + "=" * 79)
        print("                    BACKTEST (60-day rebalancing)")
        print("=" * 79)
        print("Testing strategy vs buy-and-hold across rolling 2-year windows\n")
        
        results = comprehensive_backtest(
            df=df,
            fee_rate=0.003,
            window_years=2,
            step_days=90,
        )
        
        summary = results["summary"]
        all_windows = results["all_windows"]
        
        # Just show fixed periods
        fixed_only = summary[summary["config"].str.startswith("fixed_")].head(6)
        
        print("Fixed rebalancing periods (sorted by avg performance vs HODL):\n")
        for _, row in fixed_only.iterrows():
            config = row["config"]
            win_rate = row["win_rate"] * 100
            avg_ratio = row["strategy_vs_bh_ratio_mean"]
            min_ratio = row["strategy_vs_bh_ratio_min"]
            max_ratio = row["strategy_vs_bh_ratio_max"]
            print(f"  {config:12s}  Win: {win_rate:4.0f}%  Avg: {avg_ratio:.2f}x  Range: {min_ratio:.2f}x - {max_ratio:.2f}x")
        
        # Key insight
        print("\n" + "-" * 79)
        print("KEY INSIGHT:")
        print("-" * 79)
        print("""
  The model is NOT designed to beat buy-and-hold in bull markets.
  It's designed to answer: "Is Bitcoin cheap or expensive RIGHT NOW?"
  
  When cheap (near floor):  Accumulate aggressively (80-100% allocation)
  When expensive (near ceiling): Protect capital (0-20% allocation)
  
  This reduces volatility and protects against drawdowns, but may
  underperform during parabolic runs. The trade-off is worth it for
  most investors who can't stomach 70%+ drawdowns.
""")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
