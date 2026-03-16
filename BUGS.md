# Pacman Bug Registry

**Created:** 2026-03-17 03:20 AEST
**Purpose:** Track bugs, known issues, and fixes for the Pacman trading CLI.
**Usage:** Ask me to update this file when bugs are discovered or resolved.

---

## Active Bugs

### [BUG-001] LimitOrderEngine missing `is_running` property
**Date:** 2026-03-17 03:13 AEST
**Severity:** High (blocks daemon status checks)
**Status:** Open
**Affects:** `order status` command
**Error:** `AttributeError: 'LimitOrderEngine' object has no attribute 'is_running'`
**Details:** The `order status` CLI command attempts to check `engine.is_running` but `LimitOrderEngine` class does not define this property.
**Reproduction:** Run `pacman order status` or `./launch.sh order status`
**Fix needed:** Add `is_running` property to `LimitOrderEngine` (probably in `src/limit_order_engine.py`) that returns whether the daemon thread/process is active.
**Related:** Also see BUG-002 (Robot portfolio mismatch)

---

### [BUG-002] Robot portfolio mismatch
**Date:** 2026-03-17 03:15 AEST
**Severity:** Medium
**Status:** Open
**Affects:** `robot status` command
**Details:** `robot status --json` reports `usdc_balance=0` and `wbtc_balance=0` even though the wallet holds USDC and WBTC. The `balance` command correctly shows holdings.
**Reproduction:** Run `balance --json` (shows holdings) then `robot status --json` (shows zeros)
**Fix needed:** Robot's portfolio fetch logic should use current balance data, not cached/stale values. Check `src/executor.py` or robot daemon portfolio calculation.
**Note:** Robot daemon last rebalance: 2026-03-08 (4 days ago) despite `running: true`. May be stuck or interval misconfigured.

---

### [BUG-003] Unknown token ID in balance
**Date:** 2026-03-17 03:15 AEST
**Severity:** Low
**Status:** Open
**Affects:** `balance` command
**Details:** Balance shows token ID `0.0.1055459` (value $17.62) which is not resolved by `tokens` command. Needs identification.
**Reproduction:** Run `balance --json` and look for token ID `0.0.1055459`
**Fix needed:** Investigate token registry or add token mapping. Determine what token this is (possibly HTS token on Hedera).

---

## Resolved Bugs

*(None yet)*

---

## Notes

- Use this file to track all Pacman bugs, including those from user reports and testing.
- Assign unique IDs (BUG-NNN) and update status when fixed.
- Keep reproduction steps clear and include error messages verbatim.
