# Model Tab — UI Context & Component Guide

This document explains every section/card on the Model Tab (`ModelTab.jsx`) so you can faithfully reproduce it in a new app.

---

## Tab Structure (top to bottom)

### 1. Hero Price Section
- Large BTC price (6xl font, white, font-black)
- 24h % change (green if positive, red if negative, with ↑/↓ arrow)
- Token label + link to Binance Futures
- Optional: Hedera WBTC price badge (yellow warning if >1% premium)

**Data needed:** `price`, `priceChangePercent`, `hederaWbtcPrice`

---

### 2. Historical Chart
Component: `<HistoricalChart currentPrice={price} />`

A chart showing Bitcoin's entire price history with:
- Power-law **floor** line (green)
- Cycle **ceiling** line (red)
- Bitcoin price (white/cyan)
- The current price highlighted

Buttons below open two modal views:
- **30yr View** (cyan) — full 30-year power law projection
- **20yr Zoom** (purple) — recent + near-future zoom

---

### 3. Bot Status Card *(clickable → navigates to Wallet tab)*

Shows when a rebalancer bot is connected. Displays:
- Bot name + running/paused status badge (green pulse animation when running)
- Start/pause button (only for authorized users)
- **Portfolio card** (3 columns): Total value ($), BTC %, Target %
- **HBAR Gas meter**: current HBAR balance + estimated trades remaining
  - Green: >5 HBAR
  - Yellow: 1–5 HBAR
  - Red + warning: <2 HBAR
- "Tap to view Wallet →" hint text

**Data needed:** `botStatus`, `portfolioStatus`, `marketStatus`

---

### 4. Model Allocation Card *(the most important card)*

**Shows:** How much BTC the model recommends (0–100%)

Displays:
- Large allocation % number (cyan, 6xl)
- Stance label + description text
- **Allocation bar**: gradient bar from defensive (0%) to aggressive (100%) with a dot marker

**Info button text:**
- *"What is Model Allocation?"*
- "The model's target BTC allocation based on current price relative to the power-law floor and cycle ceiling."
- Color zones: 0–30% = near ceiling, defensive | 30–60% = mid-band | 60–100% = near floor, aggressive
- "V3 uses 15% rebalance threshold."

**Data needed:** `signal.allocation_pct`, `signal.stance`

---

### 5. Price Position Card

Shows where the current price sits between floor and ceiling.

Displays:
- Valuation label (e.g. "Undervalued") + position % of range
- Contextual description:
  - 0–20%: "Near historical accumulation zone — strong buy signal"
  - 20–50%: "Moderate premium to floor — mid-band territory"
  - 50–80%: "Elevated pricing — approaching ceiling, reduce exposure"
  - 80–100%: "Near cycle ceiling — maximum caution, protect capital"
- **Band bar** (gradient, blue→cyan) with position dot
- Floor price label / Ceiling price label at each end

#### Sub-section: Wave Chart *(toggle: Show/Hide cycle)*

SVG sine-wave visualization of the halving cycle:
- Wave peaks at 33% into cycle
- Current position dot (glowing cyan)
- Labels: Halving date (start), Peak date (top at 33%), Next Halving (end)
- Below chart: phase description text + "X% through Cycle N"

**Info button text (Price Position):**
- "Shows where BTC trades between the power-law floor (0%) and cycle ceiling (100%)."
- 0–20%: Deep value (accumulation zone)
- 20–50%: Mid-band range
- 50–80%: Elevated (caution)
- 80–100%: Near ceiling (distribution)
- "Historically, BTC trades near floor ~76% of time."

**Data needed:** `signal.position_in_band_pct`, `signal.floor`, `signal.ceiling`, `signal.cycle_progress_pct`, `signal.cycle`

---

### 6. Data Grid — 4 Cards (2×2)

#### Floor Card (green border)
- Value: `signal.floor` (green, xl)
- Label: "At floor = 100% BTC"
- **Info:** "Power Law Floor — the theoretical minimum price based on Bitcoin's network growth. `10^-17 × days^5.73`. Price has never stayed below this floor for long. When price touches floor = maximum buying opportunity."

#### Ceiling Card (red border)
- Value: `signal.ceiling` (red, xl)
- Label: "At ceiling = 0% BTC"
- **Info:** "Cycle Ceiling — the estimated peak price for this halving cycle. Calculated using Kleiber's Law (biological scaling). Each cycle, the ceiling-to-floor ratio decreases as Bitcoin matures."

#### Fair Value Card (cyan border)
- Value: `signal.model_price` (cyan, xl)
- Sub-label: "+X% above fair value" (orange) or "-X% below fair value" (green)
- **Info:** "Model Fair Value — the 'heartbeat' price — where the model expects BTC to trade based on cycle timing. Peaks at 33% into cycle (~16 months post-halving), then declines. Current price vs fair value indicates over/undervaluation."

#### Peak Date Card (amber border)
- Value: Formatted peak date string (amber, xl)
- Sub-label: "X days away" OR "Peak zone passed"
- **Info:** "Expected Cycle Peak — based on the Gaussian heartbeat model, the cycle peak typically occurs at 33% into the halving cycle. Historical peaks: Dec 2013, Dec 2017, Nov 2021. This is an estimate — actual peak timing varies ±3 months."

---

### 7. Model Outlook Table

Title: "Model Outlook" | Right subtitle: "If price stays at $X"

A table showing forward projections **if price holds constant** at today's level:

| Period | Floor | Fair Value | Alloc% |
|--------|-------|------------|--------|
| 1M (30d) | $... | $... | X% |
| 3M (91d) | ... | ... | ... |
| 6M (182d) | ... | ... | ... |
| 12M (365d) | ... | ... | ... |
| 24M (730d) | ... | ... | ... |
| 36M (1095d) | ... | ... | ... |

Color coding: green ≥60%, yellow ≥30%, red <30%
Footer: "Allocation assumes current price held constant • Floor grows ~40%/year"

**Info button text:**
- "Shows how the model would view TODAY'S PRICE at future dates."
- Floor: Power-law minimum (grows ~40%/yr)
- Fair Value: Heartbeat model price
- Alloc%: Model allocation at that date
- "As time passes, today's price becomes relatively cheaper vs the rising floor."

**Data needed:** `projections.projections[]` array with `{period, days_out, floor, model_price, allocation_pct}`

---

### 8. Phase Status Card

Shows current cycle phase + countdown to next phase.

Displays:
- Phase icon (⚡) + phase label (e.g. "Pre-Peak Build Up")
- "Cycle 5 • Day 6,026"

#### Next Phase Box (colorized based on next phase):
- "Next Phase" label + phase name (color: red for Bear Market, amber for Peak Zone, cyan for others)
- Large days countdown number
- Grid: "Floor at phase start" (green) | "Floor growth rate" (+X%/yr cyan)

#### Footer:
- "Next halving: [DATE]" | "[N] days"

**Data needed:** `signal.phase`, `signal.cycle`, `nextPhaseInfo`, `nextHalving`

---

### 9. Daily Quote

A purple-bordered card with an italic contextual quote.
Quote is generated from `getDailyQuote(signal.allocation_pct)` — a lookup of inspirational/practical Bitcoin wisdom based on allocation band.

---

## Helper Functions Used By ModelTab

These functions are passed as props and need to be implemented:

```js
getPhase(phaseString)     // Returns { label, color } from phase tag
getVal(valuationString)   // Returns { label, color } from valuation tag  
getStance(stanceString)   // Returns { label, color, desc } from stance tag
getDailyQuote(allocPct)   // Returns a quote string based on allocation %
getNextPhaseInfo()        // Returns { nextPhase, days, futureFloor, annualizedGrowth }
getNextHalving()          // Returns { date, days }
getDaysSinceGenesis()     // Returns number (days since 2009-01-03)
getCycleDates()           // Returns { start, peak, end } dates for current cycle
fmtPrice(value, decimals) // Formats number as $X,XXX
fmtDate(date)             // Formats date as "Nov 2025" etc.
getTokenMeta(symbol)      // Returns { name, ... } for a token symbol
```

---

## Phase Tags → UI Labels

| Phase String | Label | 
|-------------|-------|
| `early_cycle_reset` | Early Cycle Reset |
| `pre_peak_build_up` | Pre-Peak Build Up |
| `late_cycle_peak_zone` | Peak Zone |
| `post_peak_cooldown` | Post-Peak Cooldown |
| `late_cycle_washout` | Late Cycle Washout |

## Valuation Tags → UI Labels + Colors

| Valuation | Label | Color |
|-----------|-------|-------|
| `deep_value` | Deep Value | text-green-400 |
| `undervalued` | Undervalued | text-green-300 |
| `mid_band` | Mid-Band | text-yellow-400 |
| `overvalued` | Overvalued | text-orange-400 |
| `euphoria` | Near Ceiling | text-red-400 |

## Stance Tags → UI Labels + Colors

| Stance | Label | Color |
|--------|-------|-------|
| `max_accumulate` | Max Accumulate | text-green-400 |
| `accumulate` | Accumulate | text-green-300 |
| `balanced` | Balanced | text-yellow-400 |
| `trim_exposure` | Trim Exposure | text-orange-400 |
| `capital_protection` | Capital Protection | text-red-400 |
