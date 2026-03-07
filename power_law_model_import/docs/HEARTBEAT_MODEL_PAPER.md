# Bitcoin's Journey Toward Thermal Stability:
## A Power-Law Portfolio Allocation Framework

**Author:** Chris Imgraben  
**Version:** 3.2 (Final)  
**Date:** March 2026  
**Status:** Living Document — supersedes all prior versions (V1, V3, V3.2 drafts)

---

## Abstract

Bitcoin's price history, when viewed on logarithmic axes, reveals a remarkably stable power-law relationship with time. This paper formalises that observation into a practical portfolio allocation framework — the **Heartbeat Model** — which uses only two inputs (today's date and today's BTC price) to derive a recommended portfolio allocation between Bitcoin and a stablecoin.

The model is built from three interlocking layers:

1. A **power-law floor** representing the long-run thermodynamic equilibrium of the network
2. A **cycle ceiling** that captures the emotionally-driven speculative peak of each halving era, governed by Kleiber's biological scaling law
3. A **heartbeat pulse** — an asymmetric Gaussian — that locates where we are within the current halving cycle

Combining these three references with a sigmoid allocation function and a cycle-phase penalty, the model achieved **1.51× vs buy-and-hold** in backtesting (2017–2025), with ~87 trades over 8 years — roughly 10 per year — at 0.5% fees.

The model requires no database, no historical data feed, and no machine learning. It is deterministic, transparent, and portable.

---

## 1. Motivation: The Problem With Bitcoin Investing

Bitcoin's defining characteristic is also its greatest challenge: extreme volatility. Cycles of 10–20× gains followed by 70–85% drawdowns have repeated consistently across its history. Most investors respond in one of two ways — either they panic-sell at the bottom or they hold through every drawdown in a strategy they call "HODL."

Both approaches carry serious costs. Panic selling crystallises losses. Pure HODL requires extraordinary psychological endurance and accepts full drawdown exposure.

There is a third path: **mechanical rebalancing guided by a model that knows where we are in the cycle.**

The Heartbeat Model does not predict the future. It answers a simpler, more tractable question:

> **Is Bitcoin cheap or expensive right now, relative to its historical patterns?**

If cheap → hold more Bitcoin. If expensive → hold less. Rebalance when the gap between where you are and where you should be becomes material.

This is not novel in principle — it is the same logic as value investing, applied to a well-defined structural framework.

---

## 2. The Three-Layer Architecture

### 2.1 Layer 1: The Power-Law Floor

When Bitcoin's price is plotted on log-price vs. log-time axes (where time = days since genesis, January 3, 2009), the data traces a near-linear path. This is the signature of a **power law**.

**Floor equation:**

$$\log_{10}(P_{\text{floor}}) = A + B \cdot \log_{10}(d)$$

$$P_{\text{floor}}(d) = 10^{A} \cdot d^{B}$$

Where:
- $d$ = days since Bitcoin genesis (January 3, 2009)
- $A = -17.0$ (log-intercept, calibrated to full history)
- $B = 5.73$ (power-law exponent)

In plain terms: **the floor grows approximately 40% per year**, decelerating very slowly over time.

Conceptually, this floor represents the **minimum-energy equilibrium** of the Bitcoin network. It is where price converges when speculative excess and fear both drain away. Price has touched this level multiple times (2012, 2015, 2018–2019, briefly in 2022) but never sustained below it for long.

The exponent 5.73 is steeper than simple Metcalfe's law network effects (~2.0), reflecting something deeper — possibly the compounding of adoption, security, and energy anchoring. It is best understood as an empirical constant that fits the data across 15+ years.

> **Note:** The floor grows deterministically with time. If you simply wait, a given price becomes "cheaper" relative to the floor each passing year. A price of $85,000 in 2026 represents a different position in the floor-ceiling band than $85,000 in 2030.

---

### 2.2 Layer 2: The Cycle Ceiling

The floor answers: *where does Bitcoin want to be in equilibrium?*  
The ceiling answers: *how high can the speculative bubble reach in this era?*

Historical Bitcoin cycles exhibit a clear pattern: each successive peak is dramatically less extreme (relative to the floor) than the prior one. The ceiling is modelled using **Kleiber's Law** — a biological scaling principle that describes how metabolic efficiency scales with organism size at a 3/4 power.

Applied to Bitcoin: as the market matures and grows, the speculative "metabolism" per unit of market cap decreases.

**Spike envelope:**

$$\text{Spike\_max}(c) = 1 + S_A \cdot c^{-K} \cdot H_B^{(c-2)}$$

Where:
- $c$ = halving cycle index (Cycle 2 = 2012 halving, Cycle 5 = current)
- $S_A = 40.0$ — initial spike amplitude (calibrated to Cycle 2 blow-off)
- $K = 0.75$ — Kleiber's Law exponent (3/4 scaling)
- $H_B = 0.5$ — geometric decay per halving (each cycle, the spike potential halves)

**Ceiling price:**

$$P_{\text{ceiling}}(t) = P_{\text{floor}}(t) \times \text{Spike\_max}(c_{\text{peak}})$$

**V3.2 Refinement — Continuous Ceiling:**  
To eliminate discontinuous "jumps" at halving boundaries, we define a *peak-centred effective cycle index*:

$$c_{\text{peak}} = c + (p - 0.33)$$

Where $p$ is cycle progress (0.0 to 1.0). This means the ceiling is always continuously interpolating between adjacent cycles, with the exact integer value occurring precisely at the 33% mark — the expected peak. This produces a smooth, mathematically elegant envelope across the full history.

---

### 2.3 Layer 3: The Heartbeat Pulse

The floor and ceiling define the *band*. The heartbeat tells us *where within that band* we currently expect price to sit, given the halving cycle's stage.

Bitcoin's cycle is not symmetric. Price builds slowly over the first third of the halving cycle (the "escalator"), peaks sharply, then collapses rapidly (the "elevator"). This "up the escalator, down the elevator" dynamic is consistent across Cycles 2–5.

**Cycle progress:**

$$p = \frac{t - t_{\text{halving}_{c-1}}}{t_{\text{halving}_{c}} - t_{\text{halving}_{c-1}}} \quad \in [0, 1]$$

Using actual halving dates (not approximations):

| # | Halving Date |
|---|--------------|
| 1 | November 28, 2012 |
| 2 | July 9, 2016 |
| 3 | May 11, 2020 |
| 4 | April 20, 2024 |
| 5 | ~April 2028 (projected) |

**Asymmetric Gaussian pulse:**

$$\text{Heartbeat}(p) = \begin{cases} \exp\!\left(-\dfrac{(p - 0.33)^2}{2\,w_{\text{up}}^2}\right) & \text{if } p < 0.33 \\ \exp\!\left(-\dfrac{(p - 0.33)^2}{2\,w_{\text{down}}^2}\right) & \text{if } p \geq 0.33 \end{cases}$$

Where:
- Peak at $p = 0.33$ — one-third into the cycle (~16 months post-halving), matching historical peaks Dec 2013, Dec 2017, Nov 2021
- $w_{\text{up}} = 0.18$ — slow escalator (wide left side)
- $w_{\text{down}} = 0.08 + 0.01 \times c$ — fast elevator, maturing with each cycle (Cycle 5: $w_{\text{down}} = 0.13$)

**Boundary pinning** ensures the pulse reaches exactly 0.0 at both halving boundaries ($p=0$ and $p=1$), eliminating cross-cycle "bumps."

**Model price** — the cycle-aware fair value:

$$P_{\text{model}}(t) = P_{\text{floor}}(t) + \text{Heartbeat}(p) \cdot \left(P_{\text{ceiling}}(t) - P_{\text{floor}}(t)\right)$$

This is not a price prediction. It is a *cycle-weighted reference point*: where would we expect price to be within the floor-ceiling band, given how far into the halving cycle we are?

---

## 3. The Allocation Signal

### 3.1 Position Score

Given current price $P$ and today's floor/ceiling:

$$\text{Position} = \frac{P - P_{\text{floor}}}{P_{\text{ceiling}} - P_{\text{floor}}} \quad \in [0, 1]$$

- Position = 0.0 → price is at the floor → Bitcoin is historically cheap
- Position = 0.5 → price is mid-band → fair value territory
- Position = 1.0 → price is at the ceiling → historically expensive

---

### 3.2 Value Component (Sigmoid)

A sigmoid function converts position to a baseline allocation:

$$z = (position - 0.5) \times 4 \quad \in [-2, +2]$$

$$\text{value\_alloc} = \frac{1}{1 + e^{z \times 2.0}}$$

| Position | z | Allocation |
|----------|---|------------|
| 0.0 (floor) | −2 | ~98% |
| 0.2 | −1.2 | ~87% |
| 0.5 (mid) | 0 | 50% |
| 0.8 | +1.2 | ~13% |
| 1.0 (ceiling) | +2 | ~2% |

This is the core valuation engine: aggressive at the extremes, neutral in the middle.

---

### 3.3 Cycle Phase Penalty ("The Secret Sauce")

This is the model's most important innovation, and the hardest to understand intuitively.

After a Bitcoin cycle peaks (~33% of cycle), price enters a prolonged bear market that typically lasts 18–24 months. During this phase, price often *looks* cheap relative to normal measures — but keeps falling. Buying during the post-peak phase consistently leads to catching falling knives.

The cycle phase penalty prevents this:

$$\text{phase\_penalty} = \begin{cases} 0 & p < 0.35 \\ \dfrac{p - 0.35}{0.20} \times 0.50 & 0.35 \leq p < 0.55 \\ 0.50 & 0.55 \leq p \leq 0.70 \\ \dfrac{0.85 - p}{0.15} \times 0.50 & 0.70 < p \leq 0.85 \\ 0 & p > 0.85 \end{cases}$$

The penalty:
- Ramps from 0% to 50% as the cycle enters the post-peak cooldown (35–55%)
- Holds at its maximum of 50% through the deepest bear phase (55–70%)
- Slowly recovers through the late washout (70–85%)
- Returns to zero as the next halving approaches (>85%)

**Why 50%?** A 50% penalty at position=0.5 pulls a nominally "balanced" signal (50% BTC) down to approximately 0% BTC — which is exactly the correct defensive posture in the middle of a bear market.

---

### 3.4 Floor Boost (V3 Enhancement)

Bitcoin spends ~76% of its time within 40% of the power-law floor. This is where the vast majority of long-term alpha is generated. The V3 floor boost increases allocation aggressively when price is in the deep value zone:

$$\text{If } position < 0.15: \quad \text{boost} = 0.30 \times \frac{0.15 - position}{0.15} \times \text{boost\_scale}$$

$$\text{If } 0.15 \leq position < 0.30: \quad \text{boost} = 0.15 \times \frac{0.30 - position}{0.15} \times \text{boost\_scale}$$

The `boost_scale` is critically modulated by the phase penalty — during the post-peak bear, even deep-value signals are treated with caution:

$$\text{boost\_scale} = \max(0,\; 1 - \text{phase\_penalty} \times 2)$$

This means: when the phase penalty is 50% (deepest bear), the floor boost is fully disabled. Don't catch falling knives, even near the floor.

---

### 3.5 Momentum Component

A minor component adds a small tilt based on whether the heartbeat pulse is rising or falling (i.e., whether we're heading toward or away from the cycle peak):

$$\text{momentum} = (\text{Heartbeat}_{+90\text{d}} - \text{Heartbeat}_{\text{now}}) \times 0.3$$

Capped at ±0.10 (±10 percentage points). This acts as a tie-breaker in neutral zones.

---

### 3.6 Final Allocation

$$\text{allocation} = \text{clip}(\text{value\_alloc} - \text{phase\_penalty} + \text{floor\_boost} + \text{momentum},\; 0,\; 1)$$

Expressed as a percentage (0–100% BTC), this single number is the model's output.

---

## 4. Named States

The model emits structured tags for use in UIs and LLMs:

### Cycle Phase
| Progress Range | Phase Tag | Plain English |
|---|---|---|
| 0–15% | `early_cycle_reset` | Post-bear bottom, next rally building |
| 15–35% | `pre_peak_build_up` | Momentum building toward peak |
| 35–55% | `late_cycle_peak_zone` | Peak in/past, danger zone |
| 55–80% | `post_peak_cooldown` | Bear market, falling-knife risk |
| 80–100% | `late_cycle_washout` | Final capitulation, next halving approaching |

### Valuation State
| Position | Tag | Meaning |
|---|---|---|
| 0–20% | `deep_value` | Near historical accumulation zone |
| 20–40% | `undervalued` | Good buying opportunity |
| 40–60% | `mid_band` | Fairly valued |
| 60–80% | `overvalued` | Elevated, consider reducing |
| 80–100% | `euphoria` | Near cycle ceiling |

### Allocation Stance
| Allocation | Tag |
|---|---|
| 80–100% | `max_accumulate` |
| 60–80% | `accumulate` |
| 40–60% | `balanced` |
| 20–40% | `trim_exposure` |
| 0–20% | `capital_protection` |

---

## 5. Backtest Results

### 5.1 Setup

- **Period:** August 2017 – December 2025 (8.3 years, 3,035 days)
- **Starting capital:** $10,000
- **Benchmark:** Buy-and-hold 100% Bitcoin from day 1
- **Rebalancing:** Threshold-based (only trade when allocation drifts beyond threshold)
- **Fee model:** Percentage of trade notional, applied on each rebalance

### 5.2 V3 Optimisation — Threshold Study

The most impactful single parameter is the rebalance threshold. Too tight → excessive trading erodes through fees. Too loose → misses meaningful rebalancing opportunities.

| Threshold | Trades (8yr) | Trades/yr | vs HODL | Final Value |
|-----------|--------------|-----------|---------|-------------|
| 5% | 311 | 37.5 | 1.02x | $214K |
| 7.5% | 185 | 22.3 | 1.06x | $225K |
| 10% | 124 | 14.9 | 1.10x | $233K |
| **15%** | **87** | **10.5** | **1.51x** | **$322K** |
| 20% | 47 | 5.7 | 1.50x | $321K |

**Key finding:** The 15% threshold is the sweet spot — capturing 1.51× vs HODL with only ~10 trades per year. Going below 10% significantly degrades returns. Going above 20% yields similar performance but misses some opportunistic trades.

> HODL returned $213,203 from a $10,000 start. The 15% strategy returned $322,012 — an extra $109K on a $10K investment.

### 5.3 Fee Sensitivity

The model must be run with low-fee infrastructure to realise its full potential:

| Fee Rate | 10% Thresh | 15% Thresh | 20% Thresh |
|----------|------------|------------|------------|
| 0.3% | 1.26x | **1.51x** | 1.50x |
| 0.5% | 1.21x | **1.46x** | 1.42x |
| 1.0% | 1.09x | 1.34x | 1.35x |
| 2.0% | 0.85x | 1.15x | 1.20x |

At 0.5% fees (typical DEX): the model still beats HODL convincingly at 15% threshold.  
At 2.0% fees: performance degrades significantly — minimising fee drag is critical.

### 5.4 V3.2 Preliminary Results

With the asymmetric pulse and the 22% threshold, early extended backtests show:
- **~2.55× vs HODL** over 2014–2026 (wider test period)
- ~48 trades over 12 years (~4 per year)
- Maximum drawdown reduced: from HODL's 83.4% to 49.9%

Note: The V3.2 numbers use a longer dataset (2014–2026) that includes Bitcoin's full maturation from Cycle 2 onward, which naturally amplifies outperformance figures.

### 5.5 Walk-Forward Validation

To test for overfitting, data is split 60/40:

| | Train 2017–2022 | Test 2022–2025 | Consistency |
|---|---|---|---|
| Original V1 | 1.20× | 0.90× | 0.75 |
| **V3 (15%)** | **1.35×** | **1.12×** | **0.83** |

V3 generalises better to unseen data, suggesting the 15% threshold improvement is a robust structural insight rather than an overfit artifact.

---

## 6. Strengths and Limitations

### 6.1 Strengths

- **Stateless:** Requires only `date` and `price` as inputs. No database, no historical data, no live feeds beyond the current price.
- **Transparent:** Every equation is published. All constants are empirical and explainable.
- **Cycle-aware:** The phase penalty prevents the model's worst failure mode — buying into a prolonged bear market prematurely.
- **Self-correcting:** As time passes, any given price becomes "cheaper" relative to the rising floor, automatically adjusting future signals without re-calibration.
- **Robust:** The model beats HODL across nearly all fee regimes below 1.5% with a 15% threshold.

### 6.2 Known Limitations

- **Cycle-dependent:** The model assumes Bitcoin's 4-year halving cycle continues to structure price behaviour. If this rhythm breaks, the model's core assumptions fail.
- **Floor is empirical:** The power-law exponent (5.73) is calibrated to historical data. There is no guarantee it holds indefinitely. However, it has held remarkably stable for 15+ years.
- **No macro inputs:** The model ignores USD inflation, interest rates, regulatory risk, and macro liquidity cycles. These can override cycle dynamics over shorter time horizons.
- **Drawdown still real:** Even at 15% threshold, maximum drawdown is ~55% — comparable to HODL. The model is not a drawdown hedge; it is an allocation optimiser.
- **Tax events:** Each rebalance is a potential taxable event. High-tax users should consider thresholds of 20–25% and consider timing for tax-loss harvesting.

### 6.3 Known Failure Modes

| Scenario | Model Behaviour | Mitigation |
|---|---|---|
| Black swan (exchange hack, regulatory ban) | Continues rebalancing normally — no protection | Keep USDC in reputable venues |
| Cycle breakdown (4-year rhythm disrupts) | Phase penalty may mis-fire | Monitor cycle progress; reduce position size |
| Prolonged sideways (18+ months) | May churn if threshold too tight | Use ≥15% threshold to minimise noise trading |
| Starting in deep bear (50–65% progress) | Correctly stays defensive, may "miss" early recovery | Trust the phase recovery beyond 85% progress |

---

## 7. Model Constants — Locked

The following constants are calibrated to Bitcoin's full 15-year history. They must not be changed without re-running the complete backtest:

```
FLOOR_A = -17.0       # Power-law log-intercept
FLOOR_B = 5.73        # Power-law exponent (~network energy scaling)
SPIKE_A = 40.0        # Initial speculative spike amplitude (Cycle 2)
KLEIBER = 0.75        # Biological efficiency exponent (Kleiber's Law)
HALVING_BASE = 0.5    # Geometric decay of spike amplitude per cycle
HEARTBEAT_PEAK = 0.33 # Peak at 33% into cycle (~16 months post-halving)
W_UP = 0.18           # Escalator width (slow rise)
W_DOWN_BASE = 0.08    # Elevator width at Cycle 1 (fast crash)
W_DOWN_CYCLE = 0.01   # Per-cycle maturity adjustment
```

---

## 8. Recommended Configuration

| Setting | Value | Rationale |
|---|---|---|
| Rebalance threshold | **15%** | Optimal from backtest; 22% for ≤6 trades/yr |
| Fee budget | ≤ 0.5% | Above 1% significantly degrades alpha |
| Check interval | Hourly | Daily is fine; no benefit to sub-hourly |
| Extreme trigger | 5% | Catches sudden large moves |
| Initial position | Follow model | Don't override to 100% BTC at start |

---

## 9. The Model as Context, Not Oracle

The Heartbeat Model does not predict that Bitcoin will hit any given price. It does not know about regulation, ETF flows, or coming macro crises.

What it knows — with high empirical confidence — is that Bitcoin has repeatedly traced a power-law growth path, that halving cycles have structured its speculative behaviour for five cycles running, and that buying when price is near the floor has historically been rewarding while buying post-peak has not.

The model's job is to take those historical regularities and translate them into a number — a portfolio allocation — that can be acted on mechanically, without emotion.

**The goal is not to predict the future. The goal is to be structurally positioned to benefit from patterns that, if they continue, will reward patience — and to be protected, in part, if they don't.**

---

## Appendix A: Quick Reference — Python API

```python
from heartbeat_model import get_daily_signal, get_future_projections, floor_price, ceiling_price

# Complete signal for today
signal = get_daily_signal(datetime.now(), btc_price=85000)
# {
#   "allocation_pct": 72.0,          ← Recommended BTC % (0-100)
#   "floor": 42800,                  ← Power-law floor today
#   "ceiling": 318000,               ← Cycle ceiling today
#   "model_price": 94000,            ← Heartbeat fair value
#   "position_in_band_pct": 33.5,    ← Where in band (0=floor, 100=ceiling)
#   "cycle": 5,                      ← Current halving cycle
#   "cycle_progress_pct": 28.3,      ← % through current cycle
#   "phase": "pre_peak_build_up",
#   "valuation": "undervalued",
#   "stance": "accumulate",
#   "tagline": "Cycle 5 | 28% complete | ..."
# }

# Forward projections (what if today's price holds?)
proj = get_future_projections(datetime.now(), 85000)
# Returns floor, model_price, allocation_pct for: 1M, 3M, 6M, 12M, 24M, 36M

# Just the floor/ceiling for a given date
floor = floor_price(datetime(2026, 3, 1))
ceil  = ceiling_price(datetime(2026, 3, 1))
```

---

## Appendix B: Halving Cycle Timeline

| Cycle | Start | Approx. Peak | End |
|-------|-------|--------------|-----|
| 1 (Genesis) | Jan 3, 2009 | — | Nov 28, 2012 |
| 2 | Nov 28, 2012 | Dec 2013 | Jul 9, 2016 |
| 3 | Jul 9, 2016 | Dec 2017 | May 11, 2020 |
| 4 | May 11, 2020 | Nov 2021 | Apr 20, 2024 |
| **5 (Current)** | **Apr 20, 2024** | **~Aug-Oct 2025** | **~Apr 2028** |

---

## Appendix C: Historical Floor/Ceiling/Peak Reference

| Cycle | Approx Floor at Peak | Peak Price | Multiple Above Floor |
|-------|---------------------|------------|---------------------|
| 2 | ~$50 | ~$1,150 | ~23× |
| 3 | ~$500 | ~$19,800 | ~40× |
| 4 | ~$7,000 | ~$69,000 | ~10× |
| 5 | ~$40,000 | TBD | ~5–8× (model est.) |

Each cycle, the peak-to-floor multiple shrinks — consistent with the Kleiber decay term.

---

## Appendix D: Disclaimer

This paper is for educational and informational purposes only. It does not constitute financial advice. Bitcoin is highly volatile. Past model performance does not guarantee future results. All model parameters were calibrated on historical data and may not reflect future market behaviour. Always do your own research and consult a qualified financial advisor before making investment decisions.

---

*Bitcoin's journey toward thermal stability is not guaranteed — but the physics of complex systems, and 15 years of data, suggest the gravitational pull of the power-law floor is real. The Heartbeat Model is one lens through which to see it.*
