# AI Agent Guide: Pacman CLI

> [!CAUTION]
> ## CRITICAL: HBAR vs. WHBAR HANDLING
> **AI Agents frequently fail this!** 
> WHBAR (`0.0.1456986`) is an **INTERNAL ROUTING TOOL**, not a user-facing asset.
>
> 1. **NEVER** manually call `WHBAR.deposit()` or `WHBAR.withdraw()` before a swap or LP deposit.
> 2. **NEVER** suggest an ERC20 `approve()` for HBAR.
> 3. **AI agents must use the native HBAR path**: The contracts (Router/PositionManager) handle wrapping internally via `multicall` with native `value`.
> 4. **Failure to follow this will cause transaction reverts and 100% loss of gas.**
>
> Refer to the [HBAR vs. WHBAR — Critical Distinction](#-hbar-vs-whbar--critical-distinction) section at the bottom of this guide.

This document provides instructions for AI agents on how to interact with the Pacman CLI for Hedera-based token swaps and conversions.

## Core Objective
Pacman provides a natural language interface to the SaucerSwap V2 liquidity pools. Your goal as an agent is to interpret user intent and generate high-precision command strings for the `pacman_cli.py` or interactive prompt.

## Command Syntax

### 1. Swaps (HTS/ERC20)
Swaps use liquidity pools to exchange one token for another.
- **Exact Input**: `swap [amount] [tokenA] for [tokenB]` (e.g., `swap 10 HBAR for USDC`)
- **Exact Output**: `swap [tokenA] for [amount] [tokenB]` (e.g., `swap USDC for 0.001 WBTC`)

### 2. Conversions (Native Wrap/Unwrap)
**⚠️ CURRENT STATUS: THIS FEATURE IS TEMPORARILY BROKEN**

Pacman supports converting between native-to-bridged variants (e.g., WBTC LZ ↔ WBTC HTS), but these operations currently fail due to an approval bug with the wrapper contract.

- **Format**: Use `swap` for all conversions. Example: `swap WBTC_LZ for WBTC_HTS`
  - The router automatically detects that these tokens are wrapper-related and will add a wrap/unwrap step to the route.
- **Deprecated**: The standalone `convert` command was removed (Feb 2026) because automatic routing simplifies the UI.
- **Known Failure**: Wrap/unwrap steps require approval of HTS tokens to the wrapper contract (`0.0.9675688`). The current `approve_token()` implementation uses standard EVM `approve()`, which fails for HTS tokens. The wrapper requires the Hedera HTS precompile `grantTokenApproval()` instead. This issue is tracked in `docs/HTS_APPROVAL_BUG.md`.
- **Workaround**: None yet. Direct swaps between different assets (e.g., `USDC → WBTC_HTS`) via the SaucerSwap Router are unaffected and work normally.

### 3. Information Intents
- **Balance**: `balance` (Shows wallet holdings and HTS readiness/associations).
- **History**: `history` (Shows recent local transactions).
- **Tokens**: `tokens` (Lists all strictly supported tokens and their IDs).
- **Help**: `help` (Shows the built-in command menu).

## Best Practices for Agents

### 🛡️ Safety & Simulation
- **Proactive Simulation**: Always ensure `PACMAN_SIMULATE=true` is set in the environment before testing new routes.
- **Dry Runs**: You can use the `pacman_translator.py` directly to see how your command will be parsed without executing any logic.

### 🔍 Metadata & Variants
- **Token IDs**: If a user provides a raw Hedera ID (e.g., `0.0.12345`), the CLI will attempt to resolve it. Prefer using canonical symbols (`USDC`, `WBTC_HTS`) for clarity.
- **Variant Logic**: Hedera has multiple versions of the same asset (e.g., Circle USDC vs Bridge USDC). Pacman's `PacmanVariantRouter` handles this automatically, but you should encourage users to specify if they have a preference.

### 📝 Reading Receipts
The CLI outputs professional transaction records. When reporting back to a user:
- Cite the **NET SETTLEMENT** (the actual amount received after fees/gas).
- Quote the **Net Effective Rate** (the real price paid).
- Mention **HTS Readiness** if the tool associated a new token for them.

## Operational Modes
- **Interactive**: Just run `python3 cli/main.py` and type commands.
- **One-Shot**: `python3 cli/main.py "swap 10 HBAR for USDC"` for direct pipeline execution.

---
*Note: This CLI handles proactive HTS token association and approval hardening automatically. You do not need to manually associate tokens before suggesting a swap.*

---

## 8. Agent Error Recovery Best Practices

As an AI agent, you will encounter transient failures. Handle them gracefully.

### 8.1 RPC Failures & Rate Limiting
- **Symptom**: `HTTP 502`, `429 Too Many Requests`, or long timeouts.
- **Agent Action**:
  1. Retry up to 3 times with exponential backoff (2s, 4s, 8s).
  2. If still failing, suggest user run `echo $RPC_URL` and verify endpoint is reachable.
  3. Offer fallback: `pacman --rpc https://mainnet.hashio.io/api swap ...`

### 8.2 Simulation Revert Diagnosis
- **Symptom**: Transaction simulation fails (gas revert).
- **Agent Response**: Do NOT proceed to broadcast. Instead:
  1. Identify the revert reason from `eth_call` error (e.g., `INSUFFICIENT_BALANCE`, `TOKEN_NOT_ASSOCIATED`).
  2. Provide one-line remediation:
     - `INSUFFICIENT_BALANCE` → "You don't have enough HBAR for gas + swap amount."
     - `TOKEN_NOT_ASSOCIATED` → "You need to associate USDC. Run: `associate USDC` first."
     - `SLIPPAGE_EXCEEDED` → "Current price moved. Increase slippage with `--slippage 2`."
  3. Never suggest retrying the exact same transaction without changes.

### 8.3 Nonce Stale Detection
- **Symptom**: `nonce too low` or `replacement transaction underpriced`.
- **Agent Action**:
  - Query current nonce from chain: `hedera account info --id $HEDERA_ACCOUNT_ID`
  - Re-run the command with updated nonce (Pacman does this automatically if you use the CLI — trust the CLI).
  - If agent is generating raw transactions, always `getTransactionCount` right before signing.

### 8.4 Partial Failure in Multicall
- **Symptom**: Swap fails but association succeeded.
- **Agent Response**:
  - Explain: "Your funds are safe. The association transaction succeeded but the swap reverted."
  - Suggest: "Retry the swap with a slightly higher gas limit or lower amount."
  - Do not panic — this is expected behavior.

### 8.5 Graceful Degradation
If Pacman cannot reach any RPC:
- Stop suggesting new trades.
- Show cached price data if available (read `~/.pacman/cache/latest_prices.json`).
- Instruct: "Network issues. Try again in 30 seconds or switch RPC."

---

## 9. Tax Automation via AI

Pacman users incur taxable events. The agent can assist in record-keeping.

### 9.1 Suggest Trade Export
When a user asks "What trades did I do this month?":
- Recommend: `pacman export --start 2026-02-01 --end 2026-02-28 --format csv > trades_feb.csv`
- Explain the file is suitable for Koinly/CoinTracking import.

### 9.2 Cost Basis Calculation
- Do NOT attempt real-time capital gains calculations (AI hallucination risk).
- Instead: `pacman tax-report --year 2025 --method fifo` generates a PDF summary.
- Offer to run it if user requests tax summary.

### 9.3 Privacy Reminder
- All tax data stays local. No external API calls.
- Suggest redacting wallet address before sharing with accountant.

---

## ⚠️ HBAR vs. WHBAR — Critical Distinction

WHBAR (Wrapped HBAR, `0.0.1456986`) is an **internal routing mechanism**, not a user-facing asset.

| Operation | Correct Pattern |
|---|---|
| Swap involving HBAR | Router multicall with `value` field — Router wraps internally |
| LP deposit with HBAR | PositionManager multicall `[mint, refundETH]` with `value` field — PM wraps internally |
| **WRONG** | Calling `WHBAR.deposit()` manually before any of the above |

**Rules for any transaction involving HBAR:**
1. The contract (Router or PositionManager) always wraps HBAR to WHBAR internally.
2. You send HBAR as the transaction `value` (in pseudo-Wei: tinybars × 10¹⁰).
3. Include `refundETH()` in the multicall to return any unused HBAR.
4. **Never** send an ERC20 `approve` for the HBAR side — it has no ERC20 contract from the user's perspective.
5. Deadlines must be in **milliseconds** on Hedera: `int(time.time() * 1000) + 600_000`.

See `docs/SAUCERSWAP_V2_RULES.md` Rules 7 & 8 for the full specification.
