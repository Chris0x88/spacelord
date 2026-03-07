# Bitcoin Power Law Model — Export Package

> **Purpose**: This folder contains the complete, self-contained Bitcoin Power Law allocation model, rebalancer bot logic, and all supporting documentation. It is designed to be dropped into a new application as-is.

---

## What's In Here

```
power_law_model_export/
├── README.md                   ← You are here
├── .env.example                ← All configurable settings with comments
│
├── model/
│   └── heartbeat_model.py      ← THE CORE MODEL — floor, ceiling, heartbeat, allocation signal
│
├── robot/
│   ├── power_law.py            ← Allocation integration layer (wraps heartbeat model)
│   ├── config.py               ← All env-driven config (rebalance threshold, slippage, etc.)
│   └── bot.py                  ← Rebalancer bot orchestration logic
│
├── ui/
│   ├── ModelTab.jsx            ← Complete Model Tab UI (all tables, charts, cards)
│   ├── HistoricalChart.jsx     ← Power law chart (30yr / 20yr views)
│   ├── FullHistoryModal.jsx    ← Modal for full BTC history with floor/ceiling
│   └── CommonUI.jsx            ← Shared UI components (InfoButton, etc.)
│
└── docs/
    ├── heartbeat_model.md      ← Explainer: what the model is + all equations
    ├── heartbeat_v3_paper.md   ← Full technical paper: V3 architecture, backtest, trade-offs
    ├── heartbeat_v3.2_paper.md ← V3.2 update paper
    ├── backtest_report.md      ← Detailed backtest results
    ├── heartbeat_model_signals.png ← Visual of the model signals
    └── Bitcoins_Journey_Toward_Thermal_Stability (1).pdf ← The background research paper
```

---

## The Model in 30 Seconds

The **Heartbeat Model** answers one question: **Is Bitcoin cheap or expensive right now?**

It uses three reference points calculated deterministically from just `date` and `price`:

```
FLOOR     = 10^(-17) × days_since_genesis^5.73     ← Power-law equilibrium (~40%/yr growth)
CEILING   = FLOOR × Spike(cycle)                    ← Cycle peak envelope (Kleiber's Law decay)
MODEL     = FLOOR + (CEILING - FLOOR) × Heartbeat   ← Where price "should" be in cycle
```

The **Heartbeat pulse** is a Gaussian peaking at 33% into each halving cycle — matching historical peaks in 2013, 2017, and 2021.

**Allocation signal** (`0–100% BTC`) = f(price position in band + cycle phase penalty + momentum)

**No historical data required.** The model is fully stateless — it only needs today's date and today's BTC price.

---

## Primary API

```python
from model.heartbeat_model import get_daily_signal, get_future_projections

# Get today's signal
signal = get_daily_signal(datetime.now(), btc_price=85000)

# Returns:
# {
#   "allocation_pct": 72.0,       ← How much BTC to hold (0-100%)
#   "floor": 42000,               ← Power-law floor price
#   "ceiling": 320000,            ← Cycle ceiling price
#   "model_price": 95000,         ← Model fair value (heartbeat midpoint)
#   "position_in_band_pct": 35.0, ← Where price sits (0=floor, 100=ceiling)
#   "cycle": 5,                   ← Current halving cycle number
#   "cycle_progress_pct": 28.3,   ← How far through current cycle (%)
#   "phase": "pre_peak_build_up", ← Named cycle phase
#   "valuation": "undervalued",   ← Valuation label
#   "stance": "accumulate",       ← Recommended stance
#   "tagline": "..."              ← Human-readable summary sentence
# }

# Get forward projections (what if price stays here?)
projections = get_future_projections(datetime.now(), current_price=85000)
# Returns floor, fair value, and allocation % for: 1M, 3M, 6M, 12M, 24M, 36M
```

---

## Key Settings (from `.env.example`)

| Variable | Default | What It Does |
|----------|---------|--------------|
| `REBALANCE_THRESHOLD_PERCENT` | **15.0** | Min deviation from target before rebalancing. **15% is the research-optimal value** (1.51x vs HODL). |
| `EXTREME_THRESHOLD_PERCENT` | 5.0 | Triggers an immediate rebalance on large sudden moves |
| `REBALANCE_INTERVAL_SECONDS` | 3600 | How often the bot checks (1hr default) |
| `SLIPPAGE_PERCENT` | 0.5 | Max acceptable slippage per trade |
| `MIN_TRADE_USDC` | 1.0 | Minimum trade size (prevents dust) |
| `ALLOCATION_MODEL` | `POWER_LAW` | Set to `HEARTBEAT` to use the full heartbeat model instead of the basic power law |

---

## The Model Tab UI

The `ui/ModelTab.jsx` contains the complete "Model" tab from the app, including:

- **Hero price** with 24h change
- **Historical chart** (power law floor + ceiling + price)
- **Bot status card** (running, portfolio %, target %, HBAR gas)
- **Model allocation card** — big allocation %, stance label, bar visualization
- **Cycle position card** — where price is in the floor-ceiling band
- **Wave chart** — visual halving cycle timeline with current position dot
- **Data grid** — Floor, Ceiling, Fair Value, Peak Date (all with info explainers)
- **Model Outlook table** — 1M/3M/6M/12M/24M/36M projections table
- **Phase status card** — Next phase countdown + floor at phase start
- **Daily quote** — contextual message based on allocation %

### Key signal fields consumed by the UI:

```js
signal.allocation_pct     // 0-100, the main number
signal.position_in_band_pct // 0-100, where in floor-ceiling band
signal.floor              // Power law floor price
signal.ceiling            // Cycle ceiling price
signal.model_price        // Heartbeat fair value
signal.cycle_progress_pct // % through current halving cycle
signal.phase              // Named phase string
signal.valuation          // "deep_value" | "undervalued" | "mid_band" | "overvalued" | "euphoria"
signal.stance             // "max_accumulate" | "accumulate" | "balanced" | "trim_exposure" | "capital_protection"
signal.cycle              // Cycle number (5 = current)
```

---

## Allocation Band Zones

| Position in Band | Valuation | Default Action |
|-----------------|-----------|----------------|
| 0–20% | Deep Value | Max accumulate (90%+ BTC) |
| 20–40% | Undervalued | Accumulate (60–90% BTC) |
| 40–60% | Mid-band | Balanced (~50% BTC) |
| 60–80% | Overvalued | Trim exposure (10–40% BTC) |
| 80–100% | Euphoria / Near Ceiling | Capital protection (0–10% BTC) |

**Note:** A cycle phase penalty of 35–50% is applied from 35%–85% into the halving cycle to prevent catching falling knives in bear markets.

---

## Backtest Results (2017–2025)

| Threshold | Trades | vs HODL |
|-----------|--------|---------|
| 5% | 200+ | 0.90x |
| 10% | 145 | 1.20x |
| **15%** | **87** | **1.51x** |
| 20% | 47 | 1.50x |

**Starting $10,000 in 2017:**
- HODL → $213,203
- Heartbeat Strategy (15% threshold) → $322,012

---

## Research & Background

- **`docs/heartbeat_model.md`** — Plain English explainer of every equation
- **`docs/heartbeat_v3_paper.md`** — Full technical paper with architecture, backtest, tax analysis
- **`docs/heartbeat_v3.2_paper.md`** — V3.2 update: continuous ceiling (no halving discontinuities)
- **`docs/backtest_report.md`** — Detailed rolling-window backtest analysis
- **`docs/Bitcoins_Journey_Toward_Thermal_Stability.pdf`** — The research paper that inspired the model

---

## CRITICAL: Do Not Change the Model Constants

The model is **locked** — the constants below were calibrated to Bitcoin history and must not be changed without re-running the full backtest:

```python
FLOOR_A = -17.0    # Power-law intercept
FLOOR_B = 5.73     # Power-law exponent
SPIKE_A = 40.0     # Initial spike amplitude
KLEIBER = 0.75     # 3/4 scaling law (Kleiber's Law)
HALVING_BASE = 0.5 # Geometric halving decay
```

These are hardcoded in `model/heartbeat_model.py` and marked with a lock comment.
