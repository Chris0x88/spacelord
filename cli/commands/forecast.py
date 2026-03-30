#!/usr/bin/env python3
"""
CLI Command: forecast
=====================

Strategic Power Law projection tool — two modes:

  Mode 1 (date forward):  forecast 01/07/2026
      → Floor, model price, ceiling at that date vs today's live BTC price.
        Plus cycle phase and valuation regime.

  Mode 2 (price reverse): forecast $66000
      → When does each model line (floor / model / ceiling) reach that price?
        Key use: "if I buy at $66K, when does the floor catch up?"

Usage:
  ./launch.sh forecast 01/07/2026
  ./launch.sh forecast $66,000
  ./launch.sh forecast 2027-01-01 --json
"""

from datetime import datetime, timedelta
from cli.display import C


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def cmd_forecast(app, args):
    """Dispatcher: strip flags, detect mode, route."""
    import json as _json

    json_mode = "--json" in args
    args = [a for a in args if a != "--json"]

    if not args or args[0].lower() in ("help", "?", "-h"):
        _print_help()
        return

    token = args[0]

    kind, value = _parse_input(token)

    if kind == "error":
        print(f"\n  {C.ERR}✗{C.R} {value}")
        _print_help()
        return

    if kind == "date":
        _mode_date_forward(app, value, json_mode)
    else:
        _mode_price_reverse(app, value, json_mode)


# ─────────────────────────────────────────────────────────────────────────────
# Input parsing
# ─────────────────────────────────────────────────────────────────────────────

def _parse_input(token: str):
    """
    Returns ('date', datetime) | ('price', float) | ('error', str).

    Date formats supported: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD,
                            DD/MM/YY, DD-MM-YY.
    Price formats: 66000, $66000, $66,000, 66,000.
    """
    # Strip $ and commas to try price first
    cleaned = token.replace("$", "").replace(",", "").strip()

    # If it has a / or - it might be a date — try date first
    if "/" in token or (token.count("-") >= 2):
        dt = _try_parse_date(token)
        if dt:
            return ("date", dt)
        # If it looked like a date but failed, error clearly
        if "/" in token or token.count("-") >= 2:
            return ("error", f"Could not parse '{token}' as a date. "
                    f"Try DD/MM/YYYY or YYYY-MM-DD.")

    # Try as price
    try:
        price = float(cleaned)
        if price <= 0:
            return ("error", f"Target price must be greater than zero.")
        return ("price", price)
    except ValueError:
        pass

    return ("error", f"Could not parse '{token}'. "
            f"Provide a date (01/07/2026) or a price ($66000).")


def _try_parse_date(token: str) -> datetime | None:
    """Try to parse token as a date. Returns datetime or None."""
    formats = [
        "%d/%m/%Y",   # 01/07/2026
        "%d-%m-%Y",   # 01-07-2026
        "%Y-%m-%d",   # 2026-07-01
        "%d/%m/%y",   # 01/07/26
        "%d-%m-%y",   # 01-07-26
        "%Y/%m/%d",   # 2026/07/01
    ]
    for fmt in formats:
        try:
            return datetime.strptime(token, fmt)
        except ValueError:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Mode 1: Date forward
# ─────────────────────────────────────────────────────────────────────────────

def _mode_date_forward(app, target_date: datetime, json_mode: bool):
    """Show floor/model/ceiling at target_date vs today's live BTC price."""
    import json as _json
    from src.plugins.power_law.heartbeat_model import get_daily_signal

    today = datetime.now()
    live_price = _fetch_live_price(app)

    # Compute today's snapshot for context
    today_sig = get_daily_signal(today, live_price if live_price > 0 else 1.0)

    # Compute target date snapshot (live_price used as reference; model values
    # at a future date don't depend on today's price except for allocation signal)
    target_sig = get_daily_signal(target_date, live_price if live_price > 0 else 1.0)

    is_past = target_date.date() < today.date()
    days_away = (target_date.date() - today.date()).days

    if json_mode:
        out = {
            "mode": "date_forward",
            "target_date": target_date.strftime("%Y-%m-%d"),
            "is_past": is_past,
            "days_away": days_away,
            "btc_live": live_price if live_price > 0 else None,
            "floor": target_sig["floor"],
            "model_price": target_sig["model_price"],
            "ceiling": target_sig["ceiling"],
            "floor_pct_from_live": _pct_diff(target_sig["floor"], live_price) if live_price > 0 else None,
            "model_pct_from_live": _pct_diff(target_sig["model_price"], live_price) if live_price > 0 else None,
            "ceiling_pct_from_live": _pct_diff(target_sig["ceiling"], live_price) if live_price > 0 else None,
            "cycle": target_sig["cycle"],
            "cycle_progress_pct": target_sig["cycle_progress_pct"],
            "phase": target_sig["phase"],
            "valuation": target_sig["valuation"],
            "allocation_pct": target_sig["allocation_pct"],
        }
        print(_json.dumps(out, indent=2))
        return

    label = target_date.strftime("%d %b %Y")
    marker = f"  {C.MUTED}(historical){C.R}" if is_past else ""

    print(f"\n  {C.BOLD}📐 Power Law Forecast — {label}{C.R}{marker}")
    print(f"  {'─' * 50}")

    if live_price > 0:
        print(f"  {C.BOLD}BTC Now:{C.R}        ${live_price:>12,.0f}  (live)")
    else:
        print(f"  {C.MUTED}BTC Now:         unavailable{C.R}")

    if is_past:
        print(f"  {C.MUTED}Date:            {days_away * -1:,} days ago{C.R}")
    else:
        months = days_away / 30.44
        if months >= 1:
            print(f"  {C.MUTED}Date:            {days_away:,} days away (~{months:.1f} months){C.R}")
        else:
            print(f"  {C.MUTED}Date:            {days_away} days away{C.R}")

    print()

    # Model levels at target date
    floor_v  = target_sig["floor"]
    model_v  = target_sig["model_price"]
    ceil_v   = target_sig["ceiling"]

    if live_price > 0:
        floor_pct = _format_pct(floor_v, live_price)
        model_pct = _format_pct(model_v, live_price)
        ceil_pct  = _format_pct(ceil_v, live_price)
        print(f"  {C.BOLD}Floor:{C.R}          ${floor_v:>12,.0f}  {floor_pct}")
        print(f"  {C.BOLD}Model Price:{C.R}    ${model_v:>12,.0f}  {model_pct}")
        print(f"  {C.BOLD}Ceiling:{C.R}        ${ceil_v:>12,.0f}  {ceil_pct}")
        print(f"  {C.MUTED}(% vs today's live price){C.R}")
    else:
        print(f"  {C.BOLD}Floor:{C.R}          ${floor_v:>12,.0f}")
        print(f"  {C.BOLD}Model Price:{C.R}    ${model_v:>12,.0f}")
        print(f"  {C.BOLD}Ceiling:{C.R}        ${ceil_v:>12,.0f}")

    print()

    # Cycle / regime info
    phase_label = target_sig["phase"].replace("_", " ").title()
    val_label   = target_sig["valuation"].replace("_", " ").title()
    cycle_n     = target_sig["cycle"]
    cycle_pct   = target_sig["cycle_progress_pct"]
    alloc       = target_sig["allocation_pct"]

    print(f"  {C.BOLD}Cycle:{C.R}          {cycle_n}  ({cycle_pct:.1f}% complete)")
    print(f"  {C.BOLD}Phase:{C.R}          {phase_label}")
    print(f"  {C.BOLD}Valuation:{C.R}      {val_label}")
    print(f"  {C.BOLD}Model Alloc:{C.R}    {alloc:.0f}% BTC")

    if target_sig.get("tagline"):
        print(f"\n  {C.ACCENT}💬{C.R} {target_sig['tagline']}")


# ─────────────────────────────────────────────────────────────────────────────
# Mode 2: Price reverse
# ─────────────────────────────────────────────────────────────────────────────

def _mode_price_reverse(app, target_price: float, json_mode: bool):
    """Find when floor, model price, and ceiling each reach target_price."""
    import json as _json
    from src.plugins.power_law.heartbeat_model import (
        floor_price, model_price, ceiling_price, get_daily_signal
    )

    today = datetime.now()
    live_price = _fetch_live_price(app)

    # Today's snapshot
    today_sig = get_daily_signal(today, live_price if live_price > 0 else 1.0)

    # Find crossings
    floor_crossing  = _find_floor_crossing(target_price, today)          # binary search (monotonic)
    model_crossing  = _find_crossing_day_by_day(model_price, target_price, today)   # non-monotonic
    ceil_crossing   = _find_crossing_day_by_day(ceiling_price, target_price, today) # non-monotonic

    def _crossing_json(result):
        if result is None:
            return {"date": None, "days_away": None, "note": "unreachable within 20 years"}
        if result == "above":
            return {"date": None, "days_away": 0, "note": "already above"}
        days = (result.date() - today.date()).days
        return {"date": result.strftime("%Y-%m-%d"), "days_away": days}

    if json_mode:
        out = {
            "mode": "price_reverse",
            "target_price": target_price,
            "btc_live": live_price if live_price > 0 else None,
            "today": {
                "floor": today_sig["floor"],
                "model_price": today_sig["model_price"],
                "ceiling": today_sig["ceiling"],
            },
            "floor_crossing":  _crossing_json(floor_crossing),
            "model_crossing":  _crossing_json(model_crossing),
            "ceiling_crossing": _crossing_json(ceil_crossing),
        }
        print(_json.dumps(out, indent=2))
        return

    print(f"\n  {C.BOLD}📐 Power Law Projection — ${target_price:,.0f}{C.R}")
    print(f"  {'─' * 50}")

    if live_price > 0:
        pct_from_live = _format_pct(target_price, live_price)
        print(f"  {C.BOLD}BTC Now:{C.R}        ${live_price:>12,.0f}  (live)")
        print(f"  {C.BOLD}Target vs Now:{C.R}  {pct_from_live}")
    else:
        print(f"  {C.MUTED}BTC Now:         unavailable{C.R}")

    print()
    print(f"  {C.MUTED}Today's model levels:{C.R}")
    print(f"  {C.MUTED}  Floor:       ${today_sig['floor']:>12,.0f}{C.R}")
    print(f"  {C.MUTED}  Model Price: ${today_sig['model_price']:>12,.0f}{C.R}")
    print(f"  {C.MUTED}  Ceiling:     ${today_sig['ceiling']:>12,.0f}{C.R}")
    print()

    def _fmt_crossing(label, result, note=None):
        if result == "above":
            today_val_str = ""
            print(f"  {C.BOLD}{label}:{C.R}  {C.MUTED}Already above ${target_price:,.0f}{C.R}")
        elif result is None:
            print(f"  {C.BOLD}{label}:{C.R}  {C.ERR}Unreachable within 20 years{C.R}")
        else:
            days = (result.date() - today.date()).days
            months = days / 30.44
            date_str = result.strftime("%d %b %Y")
            if months >= 1:
                time_str = f"{days:,} days (~{months:.1f} months)"
            else:
                time_str = f"{days} days"
            print(f"  {C.BOLD}{label}:{C.R}  {C.ACCENT}{date_str}{C.R}  ({time_str})")

    _fmt_crossing("Floor reaches target  ", floor_crossing)
    _fmt_crossing("Model reaches target  ", model_crossing)
    _fmt_crossing("Ceiling reaches target", ceil_crossing)

    # Interpretation hint
    if floor_crossing and floor_crossing != "above" and floor_crossing is not None:
        days = (floor_crossing.date() - today.date()).days
        if days > 0:
            print(f"\n  {C.MUTED}💡 The floor catches up to ${target_price:,.0f} in ~{days:,} days.{C.R}")
            print(f"  {C.MUTED}   If you buy at that level now, the model's lower bound")
            print(f"  {C.MUTED}   reaches your entry price on {floor_crossing.strftime('%d %b %Y')}.{C.R}")


# ─────────────────────────────────────────────────────────────────────────────
# Crossing finders
# ─────────────────────────────────────────────────────────────────────────────

def _find_floor_crossing(target: float, from_date: datetime, max_years: int = 20):
    """
    Binary search for when floor_price(date) >= target.
    Floor is monotonically increasing so binary search is exact.
    Returns datetime | 'above' (already there) | None (unreachable).
    """
    from src.plugins.power_law.heartbeat_model import floor_price

    if floor_price(from_date) >= target:
        return "above"

    max_days = max_years * 365
    if floor_price(from_date + timedelta(days=max_days)) < target:
        return None

    lo, hi = 0, max_days
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if floor_price(from_date + timedelta(days=mid)) >= target:
            hi = mid
        else:
            lo = mid

    return from_date + timedelta(days=hi)


def _find_crossing_day_by_day(fn, target: float, from_date: datetime, max_years: int = 20):
    """
    Day-by-day search for when fn(date) >= target.
    Used for model_price and ceiling_price which are NOT monotonic.
    Returns datetime | 'above' | None.
    """
    if fn(from_date) >= target:
        return "above"

    max_days = max_years * 365
    # Step in 7-day increments first for speed, then narrow
    step = 7
    prev_day = 0
    for day in range(step, max_days, step):
        if fn(from_date + timedelta(days=day)) >= target:
            # Found window — narrow day by day
            for d in range(prev_day + 1, day + 1):
                if fn(from_date + timedelta(days=d)) >= target:
                    return from_date + timedelta(days=d)
        prev_day = day

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Live price
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_live_price(app) -> float:
    """
    Fetch live BTC price via the power law adapter.
    Returns 0.0 if unavailable (caller must check > 0).
    """
    try:
        from src.plugins.power_law.adapter import PowerLawAdapter
        adapter = PowerLawAdapter(app)
        price = adapter.get_btc_price()
        return price if price and price > 0 else 0.0
    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pct_diff(value: float, reference: float) -> float:
    """Raw % difference: ((value / reference) - 1) * 100."""
    if not reference or reference == 0:
        return 0.0
    return ((value / reference) - 1) * 100


def _format_pct(value: float, reference: float) -> str:
    """Coloured percentage string: green if positive, red if negative."""
    if not reference or reference == 0:
        return ""
    pct = _pct_diff(value, reference)
    sign = "+" if pct >= 0 else ""
    color = C.OK if pct >= 0 else C.ERR
    return f"{color}{sign}{pct:.1f}%{C.R}"


# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

def _print_help():
    print(f"\n  {C.BOLD}📐 forecast — Power Law Date & Price Projections{C.R}")
    print(f"  {'─' * 50}")
    print(f"  {C.ACCENT}forecast 01/07/2026{C.R}    What will floor/model/ceiling be on 1 Jul 2026?")
    print(f"  {C.ACCENT}forecast 2027-06-01{C.R}    Same, ISO date format")
    print(f"  {C.ACCENT}forecast $66,000{C.R}       When does each model line reach $66K?")
    print(f"  {C.ACCENT}forecast 100000{C.R}        Same without $ or commas")
    print()
    print(f"  {C.MUTED}Flags:{C.R}")
    print(f"  {C.MUTED}  --json    Emit structured JSON (for agents){C.R}")
    print()
    print(f"  {C.MUTED}Date mode:{C.R}  Shows floor, model price, and ceiling at that date,")
    print(f"  {C.MUTED}            compared to today's live BTC price (+/- %).{C.R}")
    print(f"  {C.MUTED}            Also shows cycle phase, valuation, and model allocation.{C.R}")
    print()
    print(f"  {C.MUTED}Price mode:{C.R} Shows when the floor, model price, and ceiling each")
    print(f"  {C.MUTED}            reach your target. Key question: 'if I buy at $X,{C.R}")
    print(f"  {C.MUTED}            when does the floor catch up?' (i.e. model break-even).{C.R}")
