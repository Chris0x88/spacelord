# CLAUDE.md — Pacman AI Agent Guide
*Single source of truth for any AI agent working in this repo.*

---

## What Is Pacman?
A terminal-based SaucerSwap V2 trading CLI for the Hedera network.
No browser. No indexer. Direct RPC → smart contracts.

---

## Architecture Map (read this before touching anything)

```
cli/main.py          → Entry point. Command dispatch. Calls PacmanController.
cli/display.py       → Pure rendering. No logic. Only printing.

src/controller.py    → SDK / facade. The only thing CLI talks to.
src/executor.py      → Web3 transaction engine. execute_swap() is the main entry.
src/router.py        → Pathfinding. Builds swap routes from the pool graph.
src/translator.py    → NLP. String → {intent, token, amount} dict.
src/config.py        → SecureString + PacmanConfig (from .env). Hard safety caps.
src/errors.py        → Exception hierarchy. Use these, never raw Exception.
src/logger.py        → Centralized logger. setup_mirror() tees stdout to file.
src/types.py         → SwapIntent, SwapStrategy. Rarely used directly.

lib/saucerswap.py    → SaucerSwapV2 client. Web3 contract calls.
lib/v1_saucerswap.py → SaucerSwap V1 (legacy, isolated).
lib/prices.py        → PriceManager singleton. Caches token USD prices.
lib/transfers.py     → HBAR / HTS transfer logic.
lib/staking.py       → HIP-406 native staking via hiero-sdk-python.
lib/multicall.py     → Batch balanceOf calls via Multicall3.

data/tokens.json     → Token registry: {symbol → {id, decimals, name}}
data/pools.json      → Approved V2 pool registry: [{contractId, tokenA, tokenB, fee}]
data/variants.json   → Token variant metadata: HTS vs ERC20 variants + wrap/unwrap info
data/aliases.json    → NLP nicknames: {"btc": "WBTC_HTS", ...}
data/settings.json   → User config: transfer_whitelist
data/v1_pools_approved.json → Approved V1 pool registry
```

---

## Critical Hedera Rules (violating these burns gas or causes silent reverts)

> [!CAUTION]
> ### 🛑 STOP: HBAR vs. WHBAR (AI AGENTS ALWAYS FORGET THIS)
> **WHBAR (`0.0.1456986`) IS A ROUTING TOOL, NOT AN ASSET.**
> Any AI agent suggesting manual `WHBAR.deposit()` or `WHBAR.withdraw()` is **FAILING THE TASK**.
>
> 1. **MANDATORY**: Users deposit/swap native **HBAR**. 
> 2. **NEVER** suggest `approve()` for HBAR.
> 3. **CONTRACT WRAPPING**: The PositionManager and Router wrap HBAR internally. 
> 4. **IMPLEMENTATION**: Use `multicall([main_call, refundETH_call])` and send native HBAR in the transaction `value` field (scaled x10¹⁰).
> 5. **FAILURE TO FOLLOW THIS = REVERT & 100% GAS LOSS.**


### 1. ALWAYS use alias address (self.eoa) — NEVER long-zero
```python
# WRONG — will revert on Hedera EVM
"from": hedera_id_to_evm("0.0.5219304")   # 0x0000...0004FB2C (long-zero)

# CORRECT — always use the ECDSA alias (starts 0x3...)
"from": self.eoa   # e.g. 0x348f...
```

### 2. HTS Token Approval = NOT standard ERC20
HTS tokens (like WBTC_HTS) need the HTS Precompile (`0x0000...000167`) for
`grantTokenApproval()`. Standard `approve()` via the EVM redirect shim
works for SaucerSwap's router pattern BUT may fail for the wrapper contract.
**Current workaround:** Use `approve_token()` which calls the EVM redirect
and hope the SaucerSwap router accepts it. This is the known broken path —
see MEMORY.md for the full bug report.

### 3. WHBAR (0.0.1456986) is internal routing only
Never show WHBAR in the UI. Never let users hold WHBAR. It's a routing 
intermediary for HBAR↔ERC20 pairs only. The blacklist in `router.py` 
enforces this.

### 4. Always eth_call simulate before broadcast on wrap/unwrap
Simulation is mandatory for `_execute_wrap_step` and `_execute_unwrap_step`.
The SaucerSwap router handles its own simulation internally.

---

## Data Flow: swap command → on-chain

```
User: "swap 10 HBAR for USDC"
  │
  ▼
cli/main.py → process_input() → _do_swap()
  │
  ▼
PacmanController.get_route("HBAR", "USDC", 10.0)
  │  PacmanVariantRouter.recommend_route()
  │  → pool_graph lookup → returns VariantRoute(steps=[RouteStep(swap)])
  ▼
PacmanController.swap() → executor.execute_swap(route, raw_amount=10.0)
  │
  ▼
PacmanExecutor._process_step() → _execute_swap_step()
  │  → client.get_quote_single()      [RPC eth_call to Quoter]
  │  → client.approve_token()         [only if allowance insufficient]
  │  → client.swap_exact_input()      [broadcast EIP-1559 tx]
  │  → w3.eth.wait_for_transaction_receipt()
  ▼
ExecutionResult → _record_execution() → execution_records/ + training_data/
  │
  ▼
cli/display.py → print_receipt()
```

---

## Known Bugs & Status

| Bug | File | Status |
|-----|------|--------|
| HTS approval reverts on wrapper | lib/saucerswap.py:approve_token() | OPEN — needs HTS Precompile ABI |
| `training_file` NameError | executor.py:_record_execution | **FIXED** (this session) |
| `sim_gas_used` NameError in live mode | executor.py:_execute_swap_step | **FIXED** (this session) |
| `get_all_balances` wrong method name | controller.py:get_balances | **FIXED** (this session) |
| Missing `Tuple` import | controller.py | **FIXED** (this session) |
| CLI passes `amount_usd=` (old kwarg) | cli/main.py:_do_swap | **FIXED** (this session) |

---

## Adding a New Feature — Checklist

1. Create `lib/<feature>.py` OR `src/plugins/<feature>.py` (isolated module)
2. Add config toggle to `PacmanConfig` in `src/config.py`
3. Implement mandatory `eth_call` simulation before any broadcast
4. Add command handler `cmd_<name>()` in `cli/main.py`
5. Register in `COMMANDS` dict at the bottom of `cli/main.py`
6. Add help entry to `HELP_COMMANDS` + `HELP_EXPLAINERS` in `data/text_content.py`
7. Test in `PACMAN_SIMULATE=true` mode first

---

## HCS Chat / P2P (future feature — Phase 3)
The Hedera Consensus Service (HCS) allows publishing messages to a topic.
To add P2P negotiation:
- Create a topic ID via `hiero-sdk-python`
- Subscribe via the Mirror Node gRPC streaming API
- Messages are: JSON `{type: "offer", from: "0.0.xxx", token: "WBTC", qty: 0.5, price: 95000}`
- Daemon polls topic, auto-matches, fires `controller.swap()`
Implementation lives in `lib/hcs_chat.py` (not yet created).

---

## File Archiving Policy
Active docs: `CLAUDE.md` (this file), `docs/PRODUCT_SPEC.md`, `docs/TECHNICAL_ROADMAP.md`
Everything else in `docs/` is historical context — don't delete, don't actively load.
The only docs an AI agent needs to load on startup: `CLAUDE.md`.
