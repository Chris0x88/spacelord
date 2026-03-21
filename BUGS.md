# Pacman Bug Registry

**Created:** 2026-03-17 03:20 AEST
**Purpose:** Track bugs, known issues, and fixes for the Pacman trading CLI.
**Usage:** Ask me to update this file when bugs are discovered or resolved.

---

### [BUG-021] Swap fails with "Have 0.000000" when user holds USDC[hts] not USDC
**Resolved:** 2026-03-20
**Root Cause:** Hedera has two USDC variants: EVM USDC (0.0.456858, marked `preferred`) and HTS-native USDC[hts] (0.0.1055459). The translator always resolves "USDC" → 0.0.456858. The executor then calls ERC20 `balanceOf(0.0.456858)` which returns 0 when the user only holds 0.0.1055459. Result: `InsufficientFundsError: Have 0.000000, Need 0.500000` even with 6.58 USDC[hts] in the wallet. Both "Quick Buy HBAR" and text-based "swap 0.5 USDC for HBAR" were broken.
**Fix:** Added `_preferred_usdc_id()` and `_usdc_balance_fallback()` helpers to the Telegram `InboundRouter`. These check actual balances via `_normalize_balances()` and silently switch to the USDC variant the user actually holds. Applied in three places: `_cmd_swap_parse()` (text commands), `qs:HBAR` callback (quick-buy HBAR), and `qs:USDC` callback (quick-buy USDC). Base app untouched.
**Files:** `src/plugins/telegram/router.py`

### [BUG-020] Stale confirm_swap callbacks replay trades on bot restart
**Resolved:** 2026-03-20
**Root Cause:** Telegram's getUpdates long-polling offset is stored in-memory only. On bot restart, offset resets to 0, causing Telegram to re-deliver any pending updates from the previous session — including `confirm_swap:` and `confirm_send:` callbacks that had not yet been flushed. This could silently replay a trade the user had confirmed minutes (or hours) ago.
**Fix:** Added `_drain_stale_updates()` called immediately after webhook deletion at startup. It fetches all pending updates with `timeout=0, offset=-1` to find the most recent ID, then calls getUpdates with `offset=last_id+1` to acknowledge and discard them all without dispatch.
**Files:** `src/plugins/telegram/poller.py`

### [BUG-019] Double-tap on Confirm Swap/Send button executes trade twice
**Resolved:** 2026-03-20
**Root Cause:** No deduplication on confirm callbacks. If a user double-tapped the ✅ Confirm button, or Telegram re-delivered the callback, `execute_swap_callback` / `execute_send_callback` would run twice, submitting two on-chain transactions.
**Fix:** Added `_is_confirm_already_processed(callback_query_id)` guard with a 30-second TTL dedup cache (`_recent_confirm_ids` dict). On duplicate, the poller answers the callback with "Already processing…" and returns early.
**Files:** `src/plugins/telegram/poller.py`

### [BUG-018] Telegram button spinner times out before fast-lane response arrives
**Resolved:** 2026-03-20
**Root Cause:** For non-confirm callbacks (portfolio, prices, gas, etc.), `_answer_callback()` was called AFTER `_router.handle_callback()`. Since portfolio/prices make network calls (1–4 seconds), Telegram's 5-second spinner timeout could fire, showing an error indicator on the button even though the response was about to arrive.
**Fix:** Moved `_answer_callback()` to execute BEFORE `handle_callback()` in the fast-lane path. The spinner now clears immediately on tap; the updated message arrives shortly after.
**Files:** `src/plugins/telegram/poller.py`

### [BUG-017] Text-based swap command missing estimated_out in confirm card
**Resolved:** 2026-03-20
**Root Cause:** `_cmd_swap_parse()` built the confirm card without passing `estimated_out=`. The button-driven path (`_cmd_swap_confirm_from_callback`) passed it correctly. This caused "Est. receive" to be absent from the confirm screen when using typed commands like `swap 5 USDC for HBAR`.
**Fix:** Added `estimated_out` extraction from route object in `_cmd_swap_parse()`, matching the button path.
**Files:** `src/plugins/telegram/router.py`

### [BUG-016] Token approval no-op causes on-chain swap reverts
**Resolved:** 2026-03-19
**Root Cause:** `executor.py` line 704 had `pass` where `self.client.ensure_approval()` should have been called. The executor detected that a token (e.g. USDC[hts] / 0.0.1055459) needed allowance approval for the SaucerSwap router, logged "Approving...", then did nothing. The swap was broadcast without approval → on-chain revert burning gas. Historical logs (March 11) show the same pattern 3x: "Approving 0.0.1055459..." → "Transaction REVERTED on-chain". Tokens with pre-existing approval (USDC, HBAR) worked, masking the bug.
**Fix:** Replaced `pass` with `self.client.ensure_approval(from_token_id, needed_balance)` + 2-second propagation wait. The `ensure_approval()` method calls `approve_token_dual()` which handles both EVM and HTS precompile approval.
**Files:** `src/executor.py`

### [BUG-015] Route explanation missing pool depth (informational)
**Resolved:** 2026-03-19
**Root Cause:** Route `explain()` output didn't show pool liquidity, making it impossible for agents to assess trade feasibility before execution. Router also had no minimum liquidity gate.
**Fix:** Route `explain()` now shows pool depth per hop. Added `MIN_POOL_LIQUIDITY_USD = 50.0` threshold in `find_swap_step()` — pools below this are skipped.
**Files:** `src/router.py`

### [BUG-014] CLI flags after destination token cause IndexError
**Resolved:** 2026-03-19
**Root Cause:** NLP commands parsed by regex in `translator.py`. The final capture group `(.+)` in Pattern 2 (exact-in swap) is greedy and captures everything to end-of-line, including flags like `--yes --json`. Result: `to_token` becomes `"usdc --yes --json"`, which fails to resolve → IndexError. The `trading.py` handler stripped `--yes` from raw text via `str.replace()`, but this happened AFTER the text was already mangled by the regex.
**Fix:** Added `strip_cli_flags()` in `translator.py` that removes all `--flag` and `-f` tokens BEFORE regex matching. Flags are returned in a separate `flags` dict. Updated `trading.py` to read `yes` from `req['flags']` instead of doing its own stripping. Updated SKILL.md to show correct flag placement (before the NLP command, not after tokens).
**Files:** `src/translator.py`, `cli/commands/trading.py`, `SKILL.md`

### [BUG-013] `_cmd_start` in robot.py uses `_json` from wrong scope
**Resolved:** 2026-03-18
**Root Cause:** `import json as _json` was scoped inside `cmd_robot()` but `_cmd_start()` is a separate function that called `_json.load()`. Silently failed via `except: pass`, meaning robot-account-by-nickname lookup in accounts.json never worked.
**Fix:** Added `import json` inside `_cmd_start()`. Also replaced bare `input()` at line 169 with `_safe_input()`.
**Files:** `cli/commands/robot.py`

### [BUG-012] `whitelist add` bare `input()` crashes in OpenClaw
**Resolved:** 2026-03-18
**Root Cause:** `input()` for nickname at line 687 not wrapped in `_safe_input()`. Crashes with `EOFError` when driven via pipes.
**Fix:** Replaced with `_safe_input(prompt, args, default="")`.
**Files:** `cli/commands/wallet.py`

### [BUG-011] `max_slippage` NameError in config.py
**Resolved:** 2026-03-18
**Root Cause:** If `PACMAN_MAX_SLIPPAGE` env var is unset AND `data/settings.json` read fails, the `max_slippage` variable was never defined. Line 154 (`min(max_slippage, 5.0)`) would crash with `NameError`.
**Fix:** Added `max_slippage = 2.0` default before the conditional branches.
**Files:** `src/config.py`

### [BUG-010] OpenClaw EOFError on interactive prompts
**Resolved:** 2026-03-18
**Root Cause:** `input()` calls in wallet, trading, and account commands crash with `EOFError` when driven via OpenClaw `exec` (non-interactive stdin).
**Fix:** Added `_safe_input()` helper and auto-detection of non-TTY stdin. `--yes` flag now works on ALL commands (not just swap). Non-interactive mode auto-confirms.
**Files:** `cli/main.py`, `cli/commands/wallet.py`, `cli/commands/trading.py`

### [BUG-009] Sub-account shares parent EVM address (all operations target parent)
**Resolved:** 2026-03-18
**Root Cause:** `create_sub_account()` reused the parent's ECDSA key, meaning the derived EVM address was identical. All EVM calls (balances, swaps) routed to the parent account regardless of which `HEDERA_ACCOUNT_ID` was set.
**Fix:** New sub-accounts now generate their own unique ECDSA key pair. Robot accounts store `ROBOT_PRIVATE_KEY` in `.env`. The adapter creates a dedicated executor for robot operations.
**Files:** `cli/commands/wallet.py`, `src/config.py`, `src/plugins/power_law/adapter.py`

### [BUG-008] Token association missing on sub-account creation
**Resolved:** 2026-03-18
**Root Cause:** New sub-accounts were created with `set_max_automatic_token_associations(-1)` but base tokens (USDC, WBTC, WETH) were never explicitly associated, blocking transfers to the account.
**Fix:** `account --new --purpose robot` now auto-associates all base tokens from `data/base_tokens.json` after creation.
**Files:** `cli/commands/wallet.py`

### [BUG-007] Robot daemon operates on wrong account
**Resolved:** 2026-03-18
**Root Cause:** The Power Law adapter queried balances via `account_id` (correct for reads), but executed swaps via the main executor's key (wrong account). The robot's trades were debiting the parent wallet.
**Fix:** Adapter now creates a dedicated `PacmanExecutor` using `ROBOT_PRIVATE_KEY` when available. Swaps execute from the robot's own EVM address.
**Files:** `src/plugins/power_law/adapter.py`, `src/config.py`

### [BUG-006] OpenClaw agent loses track of active account
**Resolved:** 2026-03-18
**Root Cause:** Command outputs did not include account context. After switching accounts, the agent had no way to confirm which account was active without running a separate command.
**Fix:** Added `_print_account_context()` header to `balance`, `send`, `associate` commands. Added `account --json` for structured context. Account switch now supports partial nickname matching.
**Files:** `cli/commands/wallet.py`

---

### [BUG-003] Unknown token ID in balance
**Resolved:** 2026-03-17 07:45 AEST
**Fix:** Verified token ID `0.0.1055459` as **USDC[hts]**. Corrected balance retrieval via Mirror Node fallback to ensure visibility.

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
