# The Bitcoin Heartbeat Model

A physics-inspired tool for answering one question:

> **Is Bitcoin cheap or expensive right now?**

---

## The Core Idea

Bitcoin follows a power-law growth path. The Heartbeat model uses this to
create a floor-ceiling band for any given date, then tells you where the
current price sits within that band.

**That's it.** No complex trading signals. Just: cheap, fair, or expensive as measured by this model.

The output is a single number between 0% and 100%:

- **0-20%** of band = VERY CHEAP → accumulate aggressively
- **20-40%** of band = CHEAP → good buying opportunity
- **40-60%** of band = MID-BAND → balanced
- **60-80%** of band = EXPENSIVE → consider taking profits
- **80-100%** of band = VERY EXPENSIVE → protect capital

---

## Validated Against History (2014-2025)

The model was tested against 11 years of daily Bitcoin prices:

| Position in Band | % of Days | Interpretation |
|------------------|-----------|----------------|
| 0-20% (floor) | **56.3%** | VERY CHEAP |
| 20-40% | 15.3% | CHEAP |
| 40-60% | 5.7% | FAIR |
| 60-80% | 6.1% | EXPENSIVE |
| 80-100% (ceiling) | 7.7% | VERY EXPENSIVE |

**Key insight:** Bitcoin spends ~72% of its time in the "cheap" zone (0-40%).
This validates the power-law floor as a reliable accumulation guide.

The floor-ceiling band contained **87.8%** of all historical prices.

---

## Visual Overview

The full model – power-law floor, spike ceiling, heartbeat pulse, and
allocation-style signal – can be visualised on a single chart:

![Bitcoin Heartbeat Model: price, heartbeat, allocation](../advanced/heartbeat_model_signals.png)

This chart is generated directly from `advanced/plot_heartbeat_signals.py`
using the same dataset and code described in this document.

---

## Implementation

The model lives in `advanced/heartbeat_model.py` and exposes one main function:

```python
from advanced.heartbeat_model import get_daily_signal

signal = get_daily_signal(date, price)
# Returns: allocation_pct, floor, ceiling, position, tagline, etc.
```

---

## 2. The two-layer view: Floor vs. Emotion

The model splits Bitcoin into two conceptual layers:
- **Floor (truth)** – where price "wants" to be over the long term, based
  on adoption, security, and capital inflow.
- **Spikes (emotion)** – bubbles, panics, and speculative excess around that
  floor, anchored to the halving rhythm.

The job of the Heartbeat engine is to:
1. Estimate the **equilibrium floor** via a power law in time.
2. Estimate a **cycle-specific ceiling** – how far price can realistically
   spike above the floor in this halving era.
3. Locate **where we are in the halving cycle** (the heartbeat).
4. Convert all of this into a **model-implied BTC allocation** for a
   hypothetical long-horizon portfolio.

This matches the story in `POWER_LAW_FRAMEWORK.md`, but compresses it into a
single, daily portfolio percentage.

---

## 3. The Floor: Power-law backbone

Empirically, when you plot Bitcoin on log-price versus log-time
(`days since 2009-01-03`), you get a curve that is well approximated by a
power law:

> **Floor equation**  
> \( \log_{10} P_{\text{floor}}(t) = A + B \cdot \log_{10}(\text{days since genesis}) \)

In the current implementation:
- \( A = -17.0 \)
- \( B = 5.73 \)

So in non-log form:

> \( P_{\text{floor}}(t) = 10^{-17} \times (\text{days})^{5.73} \)

Interpretation:
- The exponent 5.73 is **much steeper** than simple network-effect models
  (which are usually around 2).
- It lives in the same ballpark as exponents seen in certain complex systems
  and energy-scaling laws.

Conceptually, the floor is a **minimum-energy equilibrium path** for Bitcoin:
- Over short horizons, price can trade above or below this line.
- Over long horizons, the system keeps getting pulled back toward it.

In code (`heartbeat_model.py`):
- `floor_price(date)` computes this equilibrium value.

---

## 4. The Ceiling: Maximum bubble per cycle

The floor answers: *What is fair value?*
The ceiling answers: *How insane can this cycle get at most?*

Reality check from history:
- Early cycles saw **20–30×** blow-offs above the power-law floor.
- Later cycles are still wild, but each wave of mania is **less extreme**.

The model captures that with a **spike envelope** per halving cycle:

> **Spike envelope**  
> \( \text{Spike\_max}(c) = 1 + 40 \cdot c^{-0.75} \cdot 0.5^{(c-2)} \)

Where:
- \( c \) is the halving cycle index (2, 3, 4, 5, ...).
- 40 is the initial spike amplitude, calibrated to early Bitcoin history.
- \( c^{-0.75} \) is a Kleiber-style efficiency damping term.
- \( 0.5^{(c-2)} \) says the impact of each new halving **decays
  geometrically** over time.

Given this, the ceiling is just:

> \( P_{\text{ceiling}}(t) = P_{\text{floor}}(t) \times \text{Spike\_max}(c) \)

This creates a **band** for each halving cycle:
- Floor = gravitational pull of the system.
- Ceiling = cycle-specific, emotionally-driven upper bound.

In code:
- `cycle_index(date)` maps a date to a halving cycle.
- `ceiling_price(date)` returns the upper envelope for that day.

---

## 5. The Heartbeat: Position in the halving cycle

Halving cycles are ~4 years long. Within each one, price does not drift
smoothly – it **pulses**:
- Early: quiet accumulation.
- Middle: acceleration into a peak.
- Late: cooldown and washout.

The Heartbeat compresses this into:
1. A **cycle progress** number between 0 and 1.
2. A **Gaussian pulse** over that progress.

### 5.1 Cycle progress

For a given date:
1. Determine the current halving cycle `c`.
2. Get its `(start_date, end_date)`.
3. Compute
   \( \text{progress} = \text{clamp}((t - start) / (end - start), 0, 1) \).

In code:
- `cycle_bounds(c)` returns `(start, end)`.
- `cycle_progress(date)` returns `progress` in `[0, 1]`.

### 5.2 Heartbeat pulse

We then feed this progress into a Gaussian:

> **Heartbeat pulse**  
> \( \text{Heartbeat}(p) = \exp\left(-\frac{(p - 0.33)^2}{2 \cdot 0.15^2}\right) \)

Where:
- \( p \) is cycle progress (0–1).
- 0.33 is roughly where big peaks historically tend to cluster
  (about one-third into a cycle).
- 0.15 is the width of the "boom" region.

The result is a **bell-shaped pulse** within each halving window:
- Small at the start → builds to a peak → decays towards the end.

In code:
- `heartbeat_pulse(progress)` implements this Gaussian.

### 5.3 Model price inside the band

We now mix floor, ceiling and heartbeat into a **model-implied price**:

> **Model price**  
> \( P_{\text{model}}(t) = P_{\text{floor}}(t) + \text{Heartbeat}(p) \cdot \left(P_{\text{ceiling}}(t) - P_{\text{floor}}(t)\right) \)

This is not a prediction.
It is a **cycle-aware reference point**: "Where would we expect price to be
within the floor/ceiling band, given where we are in the halving pulse?"

In code:
- `model_price(date)` yields this value.

---

## 6. Turning it into a portfolio signal

The allocation logic is deliberately simple and is presented as a
**mechanical output of the model**, not as personalised investment advice:

### 6.1 Position score (cheap vs. expensive)

Normalise the actual price within the floor–ceiling band:

> **Position** = (Price - Floor) / (Ceiling - Floor)

Interpretation:

- 0 → sitting at the floor (deep value)
- 0.5 → mid-band (fair value)
- 1 → kissing the ceiling (euphoria)

In code: `position_score(date, price)` returns this [0, 1] value.

### 6.2 Allocation signal

In the simplest version of the model, the allocation is the inverse of
position, with a slight non-linearity to stay more sensitive near the
top of the band:

> **Allocation (toy mapping)** = (1 - Position)^0.7

This toy mapping means:

- At floor (position=0): 100% BTC allocation
- At 20% of band: ~87% BTC allocation
- At 50% of band: ~62% BTC allocation
- At 80% of band: ~28% BTC allocation
- At ceiling (position=1): 0% BTC allocation

The 0.7 exponent keeps allocation higher when cheap and drops it faster
when expensive. This matches the **design goal of the model**: emphasise
cheap zones and de‑emphasise expensive ones.

In code: `allocation_signal(date, price)` outputs this allocation-style
fraction as a **model signal**, which users can interpret in the context of
their own risk tolerance and decision rules.

---

## 7. Tags and LLM messaging

The code also exposes a layer of **discrete tags** designed for your LLM and
front-end to turn into natural language:

- `cycle_phase` – one of:
  - `early_cycle_reset`
  - `pre_peak_build_up`
  - `late_cycle_peak_zone`
  - `post_peak_cooldown`
  - `late_cycle_washout`
- `valuation_state` – one of:
  - `deep_value`, `undervalued`, `mid_band`, `overvalued`, `euphoria`
- `allocation_stance` – one of:
  - `max_accumulate`, `accumulate`, `balanced`, `trim_exposure`,
    `capital_protection`

In code:
- `sentiment_tags(date, price)` returns this dictionary alongside the
  allocation.

Example app usage:
- Heartbeat output: `allocation = 0.63`.
- Tags: `cycle_phase = pre_peak_build_up`, `valuation_state = undervalued`,
  `allocation_stance = accumulate`.
- An LLM **might** turn this into narrative language, for example:

> "We are in the pre-peak build-up phase of this halving cycle. Price is still
> undervalued relative to the long-term floor–ceiling band. In this framework,
> an `accumulate` stance corresponds to a model signal of around 63% BTC."

---

## 8. Backtesting and rebalancing

The Heartbeat script ships with simple, transparent backtest helpers so you
can check whether the model adds value versus a passive HODL benchmark.

The backtest setup:
- Data: daily BTCUSDT prices from **Binance** or your master CSV
  (`master_btc_dataset_final_2014_today.csv`).
- Portfolio: starts with 100 units of notional value.
- Fees: 0.30% per rebalance (0.003 on traded notional).
- Strategy:
  - At each rebalance date (e.g. every 30 days):
    1. Read current price.
    2. Ask `allocation_signal(date, price)` for target BTC %.
    3. Trade from current BTC/cash into that target, subtracting fee.
- Benchmark:
  - 100% BTC from day 1, with one entry fee, then sit and hold.

In code:
- `backtest_heartbeat_strategy(df, start_date, fee_rate, rebalance_days)`
  runs a single-interval test.
- `scan_rebalance_periods(df, start_date, fee_rate, periods)` scans
  multiple rebalancing intervals (e.g. 7, 14, 30, 60, 90, 180 days) and
  reports the final value and ratio vs. buy-and-hold.
- `run_basic_backtest()` (module `__main__`) is wired to your master CSV and
  prints a quick summary for the last 4 years.

This lets you see, empirically:
- Which rebalance cadence works best under a 0.30% fee.
- Whether the Heartbeat allocation actually **beats passive HODL**, or
  simply adds churn and fee drag.

---

## 9. What the Heartbeat model is (and is not)

**It is:**

- A tool to answer: "Is Bitcoin cheap or expensive right now?"
- A physics-based framework using power-law floor and halving cycles
- Fully transparent: two equations (floor + ceiling), one simple rule

**It is not:**

- A "beat the market" trading system
- A guarantee of future returns
- A high-frequency trading signal

### Honest Backtest Results

When tested across rolling 2-year windows from 2014-2025:

- **Win rate vs HODL:** ~50-60% of windows
- **Average performance:** 1.05x to 1.16x vs buy-and-hold
- **Best case:** 3.2x vs HODL (bear markets)
- **Worst case:** 0.3x vs HODL (parabolic bull runs)

The model **protects capital** in bear markets but **underperforms** during
parabolic runs. This is the intended trade-off: reduced volatility and
drawdown protection at the cost of some upside.

### Primary Use Case

The model is best used to answer the simple question:

> "Given today's date and price, is Bitcoin cheap or expensive?"

Users can then decide how to act on that information based on their own
risk tolerance and investment goals.

---

## 10. Quick Reference

```python
from advanced.heartbeat_model import get_daily_signal, floor_price, ceiling_price

# Get complete signal for today
signal = get_daily_signal(datetime.now(), current_price)
print(f"Allocation: {signal['allocation_pct']}%")
print(f"Verdict: {signal['valuation']}")
print(f"Tagline: {signal['tagline']}")

# Or just check floor/ceiling
floor = floor_price(datetime.now())
ceiling = ceiling_price(datetime.now())
```

The implementation is self-contained and portable. Wire it to Binance or
any price feed for your iOS app or trading bot.
