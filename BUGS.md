# Pacman Bug Registry

**Created:** 2026-03-17 03:20 AEST
**Purpose:** Track bugs, known issues, and fixes for the Pacman trading CLI.
**Usage:** Ask me to update this file when bugs are discovered or resolved.

---

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

---

## Resolved Bugs

### [BUG-001] LimitOrderEngine missing `is_running` property
**Resolved:** 2026-03-17 07:01 AEST
**Fix:** Added `is_running` property and background thread management to `LimitOrderEngine`.

### [BUG-002] Robot portfolio mismatch
**Resolved:** 2026-03-17 07:01 AEST
**Fix:** Added live portfolio snapshot refresh to the `robot status` command.

### [BUG-004] Incorrect Simulation Balance Check
**Resolved:** 2026-03-17 07:01 AEST
**Fix:** Corrected logic in `executor.py` to ensure strict balance checks during dry-runs.

### [BUG-005] Hedera ID to EVM Address Mapping
**Resolved:** 2026-03-17 07:01 AEST
**Fix:** Implemented Mirror Node lookup in `transfers.py` for robust address resolution.

---

## Notes

- Use this file to track all Pacman bugs, including those from user reports and testing.
- Assign unique IDs (BUG-NNN) and update status when fixed.
- Keep reproduction steps clear and include error messages verbatim.
