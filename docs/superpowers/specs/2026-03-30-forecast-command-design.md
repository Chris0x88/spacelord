# Design Spec: `forecast` Command
**Date:** 2026-03-30
**Status:** Approved

---

## Overview

A standalone `forecast` CLI command that exposes the Bitcoin Heartbeat Model's projections in two modes: date-forward lookup and price-reverse lookup. Designed for strategic planning questions like "what does the model say about July 2026?" and "if I buy at $66K, when does the floor catch up?"

---

## Command

```
./launch.sh forecast <date|price> [--json]
```

**Aliases:** `forecast`, `fl` (short alias)

**Help:** `./launch.sh forecast help`

---

## Two Modes

### Mode 1: Date Forward — `forecast 01/07/2026`

Input: a date in `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, or natural short forms (`01/07/26`).

Output: full model snapshot at that date, compared to today's live BTC price.

```
  📐 Power Law Forecast — 01 Jul 2026
  ─────────────────────────────────────────────
  Floor:          $63,788     (+8.8% from today's price)
  Model Price:    $76,338     (+30.2% from today's price)
  Ceiling:        $143,151    (+144.1% from today's price)

  BTC Now:        $86,500     (live)
  Days Away:      93 days (~3.1 months)

  Cycle:          5 (54.9% complete)
  Phase:          Post-Peak Cooldown
  Valuation:      Undervalued
```

The "from today" percentages are: `((future_level / live_btc_price) - 1) * 100`. This can be negative if the model level is below current price (e.g. floor is below your entry). This answers: "If I buy now, where does the model say each line will be on that date?"

If the target date is in the past, show historical model values with a note that this is a retrospective.

### Mode 2: Price Reverse — `forecast $66000`

Input: a dollar amount (with or without `$` and commas).

Output: when floor, model price, and ceiling each reach that level, with days/months to each crossing.

```
  📐 Power Law Projection — $66,000
  ─────────────────────────────────────────────
  BTC Now:        $86,500     (live)
  Today's Floor:  $58,647
  Today's Model:  $88,978
  Today's Ceiling:$135,610

  Floor reaches $66,000:    09 Aug 2026  (132 days, ~4.3 months)
  Model reaches $66,000:    Already above — today is $88,978
  Ceiling reaches $66,000:  Already above — today is $135,610
```

If the target is above the current value of a line, find the crossing date using binary search over the monotonically increasing floor function. Model price and ceiling are NOT strictly monotonic (they depend on halving cycle progress), so for those, iterate day-by-day from today forward up to 20 years, finding first crossing.

**Edge cases:**
- Target already exceeded by all three lines → show current values and note all above target
- Target unreachable within 20 years → surface that clearly (this is only realistic for extreme ceiling values far out)
- Negative or zero target → show error

### Mode Detection

```python
if input contains '/' or '-' and parses as a date:
    → Mode 1 (date forward)
else if input parses as a number (strip $, commas):
    → Mode 2 (price reverse)
else:
    → show usage error + help
```

Ambiguous cases (e.g. bare `2026`) default to error with guidance.

---

## Data Sources

- **Floor, ceiling, model price, cycle data:** `heartbeat_model.py` — pure deterministic functions, no network
  - Use `get_daily_signal(date, price)` for Mode 1 (returns all fields in one call)
  - Note: `get_future_projections(date, price)` also exists but is fixed at 1/3/6/12/24/36M intervals — not suitable for arbitrary date/price lookups
- **Live BTC price:** same Binance path used by `robot signal` — `adapter.get_btc_price()` from `src/plugins/power_law/adapter.py`
- **Today's date:** `datetime.now()` — no UTC, matches local date display

---

## Implementation

### New file: `cli/commands/forecast.py`

Single responsibility: parse input, call heartbeat model functions, fetch live price, format output.

Functions:
- `cmd_forecast(app, args)` — top-level dispatcher, strips `--json`, detects mode
- `_parse_input(token)` → `('date', datetime)` or `('price', float)` or `('error', str)`
  - Date parsing: try `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD/MM/YY` manually (no external libs); fall through to error if none match
- `_mode_date_forward(app, target_date, json_mode)` — Mode 1 output
  - Calls `get_daily_signal(target_date, live_price)` from `heartbeat_model` to get all fields (floor, ceiling, model_price, cycle, cycle_progress_pct, phase, valuation) in one call — do NOT call individual functions piecemeal
- `_mode_price_reverse(app, target_price, json_mode)` — Mode 2 output
- `_fetch_live_price(app)` → `float` — wraps `adapter.get_btc_price()`, returns `0.0` on failure (matching adapter behaviour); caller checks `> 0` before using
- `_find_floor_crossing(target, from_date, max_years=20)` → `datetime | None` — binary search (floor IS monotonic)
- `_find_crossing_day_by_day(fn, target, from_date, max_years=20)` → `datetime | None` — day-by-day for model_price and ceiling (NOT monotonic due to halving cycle)
- `_format_pct(future_level, reference)` → `str` — `((future_level/reference)-1)*100`, coloured green (positive) / red (negative)
- `_print_help()` — usage text

### Changes to existing files

| File | Change |
|------|--------|
| `cli/main.py` | Import `cmd_forecast`; add `"forecast": cmd_forecast, "fl": cmd_forecast` to `COMMANDS` dict |
| `SKILL.md` | Add `forecast` command to the Power Law section with examples and when to use |

### No changes to

- `heartbeat_model.py` — model is locked, use as-is
- `cli/commands/robot.py` — robot commands unaffected
- Any governance/config files

---

## JSON Output

`--json` flag emits a structured dict for agent consumption.

**Mode 1 JSON:**
```json
{
  "mode": "date_forward",
  "target_date": "2026-07-01",
  "days_away": 93,
  "btc_live": 86500.0,
  "floor": 63788.28,
  "model_price": 76338.34,
  "ceiling": 143151.09,
  "floor_pct_from_live": 8.8,
  "model_pct_from_live": 30.2,
  "ceiling_pct_from_live": 144.1,
  "cycle": 5,
  "cycle_progress_pct": 54.9,
  "phase": "post_peak_cooldown",
  "valuation": "undervalued"
}
```

**Mode 2 JSON:**
```json
{
  "mode": "price_reverse",
  "target_price": 66000.0,
  "btc_live": 86500.0,
  "today": {
    "floor": 58646.97,
    "model_price": 88978.0,
    "ceiling": 135610.0
  },
  "floor_crossing": { "date": "2026-08-09", "days_away": 132 },
  "model_crossing": { "date": null, "note": "already above" },
  "ceiling_crossing": { "date": null, "note": "already above" }
}
```

---

## Help Text (in-command)

```
  📐 forecast — Power Law Date & Price Projections
  ─────────────────────────────────────────────────
  forecast 01/07/2026     What will floor/model/ceiling be on 1 Jul 2026?
  forecast 2027-06-01     Same, ISO date format
  forecast $66,000        When does each model line reach $66K?
  forecast 100000         Same without $ or commas

  --json                  Emit structured JSON (for agents)

  Examples:
    ./launch.sh forecast 01/07/2026
    ./launch.sh forecast $66000
    ./launch.sh forecast 2028-01-01 --json
```

---

## SKILL.md Addition

In the Power Law section, add:

```
forecast <date|price>   Strategic power law projection tool (≠ robot signal)
  robot signal → shows TODAY's model snapshot only
  forecast     → shows FUTURE projections and price crossing dates

  forecast 01/07/2026   What does the model say for 1 Jul 2026?
                        Shows floor, model price, ceiling at that date
                        + % change from today's live BTC price at each level
                        + cycle phase and valuation regime at that date

  forecast $66000       When does each model line (floor/model/ceiling) reach $66K?
                        Key use case: "I'm buying at $66K — when does the floor
                        catch up, making me safe from the model's perspective?"

  Use when:
    - Agent is asked about future price levels or model projections
    - User asks "when does floor reach X?" or "what's the ceiling in [month]?"
    - User wants to plan entry/exit around the power law model
    - Break-even analysis ("if I buy at X, when does the model catch up?")

  --json for structured output parseable by agent
```

---

## Error Handling

- Live price fetch fails → `_fetch_live_price()` returns `0.0`; display note "live price unavailable — model values shown without % comparison"
- Invalid date format → show usage error + help
- Past date → show values with `(historical)` label, no "days away"
- Target price ≤ 0 → show error

---

## Out of Scope

- No changes to the power law model constants or logic
- No charting output (that's `charting.py`'s job)
- No changes to robot daemon behaviour
- No TOOLS.md or AGENTS.md update (TODO.md mentioned it but SKILL.md is the authoritative agent reference)
