#!/usr/bin/env python3
"""
PACMAN - MEGA VISION DOCUMENT
==============================

The definitive architectural specification for Pacman: an AI swap router
for SaucerSwap V2 on Hedera. This document is written so that any
developer or AI agent can pick up a component and build it correctly.

Author: Chris + Claude
Date: 2026-02-08
Status: Active specification
"""

# =============================================================================
# 1. WHAT PACMAN IS
# =============================================================================
#
# Pacman is an open-source swap router that saves users 0.25% on every
# SaucerSwap V2 trade by bypassing the SaucerSwap web app and calling
# pool contracts directly.
#
# It is NOT a trading bot. It is NOT an arbitrage tool. It is a ROUTER:
# you tell it "I have USDC, I want WBTC, here's my amount" and it finds
# the cheapest path through SaucerSwap's liquidity pools and executes
# the swap transaction on Hedera.
#
# The "AI" part: Pacman uses pre-computed routing intelligence to handle
# Hedera's complex token system (dual types, wrapping, association) so
# the caller doesn't have to. The routing table is rebuilt weekly from
# live pool data. No LLM needed at runtime.


# =============================================================================
# 2. THE THREE LAYERS
# =============================================================================
#
# ┌─────────────────────────────────────────────────────┐
# │  LAYER 1: TRANSLATOR (optional, replaceable)        │
# │  Converts human text to structured swap request.    │
# │  Could be regex, LLM, Telegram bot, voice, etc.     │
# │  File: pacman_translator.py                         │
# │                                                     │
# │  Input:  "swap 1 USDC for bitcoin"                  │
# │  Output: {from: "USDC", to: "WBTC_HTS",            │
# │           amount: 1.0, mode: "exact_in"}            │
# └──────────────────────┬──────────────────────────────┘
#                        │
# ┌──────────────────────▼──────────────────────────────┐
# │  LAYER 2: AGENT (the product, the brain)            │
# │  Takes structured input. Looks up route. Calls      │
# │  tools. Returns result. No NL, no guessing.         │
# │  File: pacman_agent.py                              │
# │                                                     │
# │  Input:  {from: "USDC", to: "WBTC_HTS",            │
# │           amount: 1.0, mode: "exact_in"}            │
# │  Output: SwapResult(success, tx_hash, amount_out)   │
# └──────────────────────┬──────────────────────────────┘
#                        │
# ┌──────────────────────▼──────────────────────────────┐
# │  LAYER 3: ENGINE (proven, DO NOT MODIFY)            │
# │  Battle-tested swap execution from btc-rebalancer2. │
# │  Handles all Hedera quirks: millisecond deadlines,  │
# │  multicall wrap/unwrap, HTS association, approvals.  │
# │  File: btc_rebalancer_swap_engine.py                │
# └─────────────────────────────────────────────────────┘


# =============================================================================
# 3. CRITICAL: WHBAR IS NOT A TOKEN
# =============================================================================
#
# THIS IS THE MOST IMPORTANT THING IN THIS DOCUMENT.
#
# Token 0.0.1456986 (symbol "HBAR" in pool data, actually "WHBAR [new]")
# is a TECHNICAL CONTRACT MECHANISM. It is the ERC20-wrapped version of
# native HBAR, used internally by the SaucerSwap router contract.
#
# IT IS NOT A TRADEABLE ASSET.
# SWAPPING TO WHBAR = LOST MONEY.
# RECEIVING WHBAR IN YOUR WALLET = STUCK FUNDS.
#
# How it actually works:
#
#   User wants: "swap USDC to HBAR"
#   What happens at contract level:
#     1. USDC → WHBAR (pool swap)
#     2. WHBAR → native HBAR (unwrapWHBAR via multicall)
#     The user receives native HBAR, never touches WHBAR.
#
#   User wants: "swap HBAR to USDC"
#   What happens:
#     1. Native HBAR sent as tx.value
#     2. Router wraps HBAR → WHBAR automatically
#     3. WHBAR → USDC (pool swap)
#     The user sends native HBAR, never touches WHBAR.
#
# The proven engine (btc_rebalancer_swap_engine.py) handles this correctly:
#   - Lines 371-372: detects HBAR by checking token_id.upper() == "HBAR"
#   - Lines 438-454: uses multicall(exactInput + unwrapWHBAR) for HBAR output
#   - Lines 455-465: sends native HBAR as tx.value for HBAR input
#
# RULES FOR ALL COMPONENTS:
#   1. WHBAR (0.0.1456986) MUST NEVER appear as a tradeable token
#   2. WHBAR MUST NEVER be a route source or destination
#   3. If a user wants to trade native HBAR, use token_id="HBAR" (string)
#      and the engine handles wrapping/unwrapping internally
#   4. WHBAR appears in SaucerSwap pool data because pools pair against it,
#      but from the user's perspective they are trading native HBAR
#   5. Routes that go THROUGH WHBAR pools are fine - the agent must flag
#      the first/last hop as "HBAR" to trigger the engine's multicall logic
#
# CURRENTLY: HBAR trading is DISABLED in the route table because the agent
# doesn't yet handle the multicall orchestration. This is a TODO (see §8).


# =============================================================================
# 4. TOKEN SYSTEM
# =============================================================================
#
# Hedera has TWO types of tokens that look like the same asset:
#
# ┌─────────────┬────────────────┬────────────────┬──────────────┐
# │ Asset       │ ERC20 (bridged)│ HTS (native)   │ Notes        │
# ├─────────────┼────────────────┼────────────────┼──────────────┤
# │ Bitcoin     │ WBTC_LZ        │ WBTC_HTS       │ LZ=LayerZero │
# │             │ 0.0.1055483    │ 0.0.10082597   │              │
# ├─────────────┼────────────────┼────────────────┼──────────────┤
# │ Ethereum    │ WETH_LZ        │ WETH_HTS       │              │
# │             │ 0.0.9770617    │ 0.0.541564     │              │
# ├─────────────┼────────────────┼────────────────┼──────────────┤
# │ USDC        │ USDC           │ USDC_HTS       │ Both visible │
# │             │ 0.0.456858     │ 0.0.1055459    │ in HashPack  │
# └─────────────┴────────────────┴────────────────┴──────────────┘
#
# ERC20 bridged tokens:
#   - Cheaper to swap (more liquidity in older pools)
#   - Often INVISIBLE in HashPack wallet
#   - User thinks they lost their money
#
# HTS native tokens:
#   - Visible in HashPack
#   - May be slightly more expensive
#   - User-friendly
#
# RULE: Default to HTS variants for user-facing swaps.
#       Only use ERC20 if user explicitly requests cheapest route.
#
# TOKEN AUTO-DISCOVERY (TODO - see §8):
#   The current TOKEN_REGISTRY is hand-coded. It should be auto-generated
#   from the pool data (pacman_data_raw.json), which already contains
#   name, symbol, decimals, id, priceUsd for every token.


# =============================================================================
# 5. ROUTING
# =============================================================================
#
# Route computation is OFFLINE (not at swap time):
#
#   1. Download pool data from SaucerSwap API
#   2. Run build_routes.py → generates routes.json
#   3. Agent loads routes.json at startup (instant lookup)
#
# Route table format:
#   "USDC->WBTC_HTS": {
#     "path": ["USDC", "WBTC_HTS"],
#     "hops": [
#       {
#         "from": "USDC",
#         "to": "WBTC_HTS",
#         "pool_id": 44,
#         "fee": 1500,              // hundredths of basis points
#         "fee_percent": 0.15,
#         "token_in_id": "0.0.456858",
#         "token_out_id": "0.0.10082597",
#         "decimals_in": 6,
#         "decimals_out": 8,
#         "liquidity": 40109042905
#       }
#     ],
#     "total_fee_percent": 0.15,
#     "num_hops": 1
#   }
#
# Multi-hop example:
#   "SAUCE->WBTC_HTS": {
#     "path": ["SAUCE", "USDC", "WBTC_HTS"],
#     "hops": [hop1, hop2],
#     "total_fee_percent": 0.45,
#     "num_hops": 2
#   }
#
# SCORING: cheapest = sum(fee/1_000_000) + liquidity_penalty
#   - Liquidity < 1M: +1% penalty
#   - Liquidity < 10M: +0.5% penalty
#
# BLACKLIST: WHBAR never appears as src or dst (see §3).
#            It CAN appear as a hop in paths (the pools exist),
#            but the agent must detect this and use the engine's
#            HBAR-aware multicall logic.


# =============================================================================
# 6. EXECUTION FLOW (step by step)
# =============================================================================
#
# What happens when someone calls agent.swap("USDC", "WBTC_HTS", 1.0):
#
#   Step 1: ROUTE LOOKUP
#     Look up "USDC->WBTC_HTS" in routes.json
#     Result: direct swap via pool 44, fee 0.15%
#
#   Step 2: LIVE QUOTE
#     Call SaucerSwap V2 quoter contract (0.0.3949424)
#     Input: 1,000,000 raw (1 USDC at 6 decimals)
#     Output: ~1,415 raw (0.00001415 WBTC_HTS at 8 decimals)
#
#   Step 3: PREFLIGHT CHECKS
#     - Amount within $1.00 limit? YES
#     - User has 1+ USDC balance? CHECK
#     - User has HBAR for gas? CHECK
#     - Slippage within 1%? CHECK
#     - Output token associated? CHECK (HTS requirement)
#
#   Step 4: TOKEN APPROVAL
#     If router doesn't have allowance to spend user's USDC:
#     Call USDC.approve(router_address, amount)
#     Wait for confirmation, sleep 5s for propagation
#
#   Step 5: BUILD TRANSACTION
#     Encode path: [USDC_addr + fee_bytes + WBTC_HTS_addr]
#     Set deadline: int(time.time() * 1000) + 600000 (MILLISECONDS!)
#     Calculate min_out: quote * (1 - slippage)
#     Call router.exactInput(path, recipient, deadline, amountIn, minOut)
#
#   Step 6: SIGN AND SEND
#     Sign with private key, send raw transaction
#     Wait for receipt (timeout 120s)
#
#   Step 7: RETURN RESULT
#     SwapResult(success=True, tx_hash="abc...", amount_in=1.0, amount_out=0.00001415)
#
# SPECIAL CASE - HBAR involved (NOT YET IMPLEMENTED):
#   If swapping FROM HBAR:
#     - Don't approve anything
#     - Send native HBAR as tx.value
#     - Engine wraps HBAR→WHBAR internally
#   If swapping TO HBAR:
#     - Use multicall: [exactInput, unwrapWHBAR]
#     - Swap outputs WHBAR to router
#     - unwrapWHBAR sends native HBAR to user


# =============================================================================
# 7. SAFETY INVARIANTS (NON-NEGOTIABLE)
# =============================================================================
#
# These are HARD-CODED. No config, no env var, no flag can override them:
#
#   MAX_SWAP_USD    = $1.00    (per transaction)
#   MAX_DAILY_USD   = $10.00   (rolling 24h window)
#   MAX_SLIPPAGE    = 1%       (min_out = quote * 0.99)
#   REQUIRE_CONFIRM = True     (human must approve before execution)
#   DEADLINE_MS     = True     (Hedera requires milliseconds, NOT seconds)
#
# HTS ASSOCIATION: Before receiving ANY HTS token for the first time,
# the account must explicitly associate with it. This is a Hedera
# requirement. The agent must check association before swapping.
#
# The file pacman_config.py enforces these. Do not bypass.


# =============================================================================
# 8. BUILD PLAN (ordered by priority)
# =============================================================================
#
# STATUS KEY: [DONE] [TODO] [BLOCKED]
#
# --- PHASE 1: FOUNDATION (tonight) ---
#
# [DONE] 1.1 build_routes.py
#   Pre-compute all routes from pool data.
#   812 routes across 29 tradeable tokens.
#   WHBAR blacklisted as trade endpoint.
#
# [DONE] 1.2 pacman_agent.py
#   Structured-input agent. route(), quote(), swap(), explain().
#   Uses routes.json for instant lookup.
#   Delegates execution to btc_rebalancer_swap_engine.
#
# [DONE] 1.3 pacman_translator.py
#   Isolated NL → struct converter. Token aliases, exact_in/out detection.
#   Completely replaceable. Agent never depends on it.
#
# [DONE] 1.4 test_agent.py
#   80 tests covering route table, agent, translator, integration.
#
#
# --- PHASE 2: AUTO-DISCOVERY (next session) ---
#
# [TODO] 2.1 Auto-discover tokens from pool data
#   PROBLEM: TOKEN_REGISTRY is hand-coded. When SaucerSwap adds new
#   tokens/pools, we miss them (like GIB was missing).
#
#   SOLUTION: build_routes.py should auto-scan pacman_data_raw.json
#   and create TOKEN_REGISTRY from it. Every pool token has:
#     - id, name, symbol, decimals, priceUsd
#   All already in the JSON. Just read and register.
#
#   BLACKLIST only: maintain a small list of tokens to EXCLUDE
#   (WHBAR, zero-liquidity tokens, fee-on-transfer scams).
#   Everything else auto-registers.
#
#   This also fixes the GIB-style problem permanently: any token
#   in the pool data with any weird name/symbol gets registered
#   automatically with all its metadata for searching.
#
# [TODO] 2.2 Token search/discovery in translator
#   With auto-discovered tokens (including name, symbol, priceUsd),
#   the translator should support fuzzy matching:
#     "swap 1 USDC for that donkey coin" → fuzzy match on name
#   Or at minimum, match by:
#     - canonical name (BONZO)
#     - pool symbol (BONZO)
#     - full name ("BONZO")
#     - token ID (0.0.8279134)
#
# [TODO] 2.3 Pool data refresh script
#   Script that downloads fresh pool data from SaucerSwap API:
#     GET https://api.saucerswap.finance/v2/pools
#   Saves to pacman_data_raw.json, then runs build_routes.py.
#   Cron it weekly or run manually.
#
#
# --- PHASE 3: HBAR SUPPORT (requires careful testing) ---
#
# [TODO] 3.1 Add HBAR as a tradeable token
#   HBAR is currently excluded because swaps involving it need
#   the engine's multicall logic (wrap/unwrap WHBAR).
#
#   IMPLEMENTATION:
#   a) In routes.json, include routes where HBAR is src or dst
#      but internally the path goes through WHBAR pools
#   b) In pacman_agent.py, detect when a route's first or last
#      hop uses WHBAR (0.0.1456986) and pass token_id="HBAR"
#      to the engine (not the WHBAR token ID)
#   c) Engine already handles this correctly (lines 371-465 of
#      btc_rebalancer_swap_engine.py)
#
#   TESTING: Must test with real $0.01 swaps:
#     - USDC → HBAR (should receive native HBAR, not WHBAR)
#     - HBAR → USDC (should send native HBAR)
#     - SAUCE → HBAR (multi-hop: SAUCE → USDC → WHBAR → unwrap)
#
# [TODO] 3.2 Exact output mode for HBAR
#   Engine line 491-492: "exactOutput with HBAR input not yet supported"
#   Needs implementation if users want "buy exactly 100 HBAR with USDC"
#
#
# --- PHASE 4: PRODUCTION HARDENING ---
#
# [TODO] 4.1 HTS token association check
#   Before any swap, verify user's account is associated with the
#   output token. If not, auto-associate (costs ~0.05 HBAR).
#   The engine has partial code for this but it's not wired up.
#
# [TODO] 4.2 Balance verification
#   Check user has enough input token AND enough HBAR for gas
#   before attempting swap. Currently in pacman_preflight.py but
#   not integrated with the agent.
#
# [TODO] 4.3 Transaction recording
#   Log every swap (success or failure) to execution_records/.
#   Include: timestamp, route, amounts, tx_hash, gas, slippage.
#   This data feeds future improvements.
#
# [TODO] 4.4 Daily volume tracking
#   Track cumulative daily swap volume in USD.
#   Reject swaps that would exceed $10 daily limit.
#
#
# --- PHASE 5: API LAYER ---
#
# [TODO] 5.1 HTTP API (Flask or FastAPI, ~30 lines)
#   POST /quote   {from, to, amount, mode}  → Quote
#   POST /swap    {from, to, amount, mode}  → SwapResult
#   GET  /tokens                            → token list
#   GET  /route?from=X&to=Y                → route details
#
#   This is how external apps, bots, and UIs call Pacman.
#
# [TODO] 5.2 WebSocket for live quotes (optional)
#   Stream price updates for a given pair.
#
#
# --- PHASE 6: VARIANT INTELLIGENCE ---
#
# [TODO] 6.1 ERC20 vs HTS variant routing
#   For assets that exist in both forms (WBTC_LZ vs WBTC_HTS):
#   - Default: route to HTS (visible in HashPack)
#   - If ERC20 route is >5% cheaper, offer both options
#   - Auto-unwrap ERC20→HTS if user prefers (extra gas)
#   pacman_variant_router.py has the logic, needs integration.
#
#
# --- PHASE 7: DISTRIBUTION ---
#
# [TODO] 7.1 Telegram bot
#   Thin wrapper around the HTTP API.
#   Uses translator for NL input.
#   Shows route, asks confirmation, executes.
#
# [TODO] 7.2 npm package / Python package
#   So other Hedera apps can `pip install pacman` and call
#   agent.swap() directly.
#
# [TODO] 7.3 Documentation site
#   API docs, token list, fee comparison vs SaucerSwap app.


# =============================================================================
# 9. DATA FLOW DIAGRAM
# =============================================================================
#
# WEEKLY (offline):
#   SaucerSwap API → pacman_data_raw.json → build_routes.py → routes.json
#
# AT RUNTIME (per swap):
#   User input
#     │
#     ▼
#   Translator (optional)
#     │ {from_token, to_token, amount, mode}
#     ▼
#   Agent.swap()
#     │
#     ├─ routes.json lookup (instant, no network)
#     │
#     ├─ SaucerSwap Quoter contract (live quote)
#     │
#     ├─ Preflight checks (balance, gas, association)
#     │
#     ├─ User confirmation (if require_confirm=True)
#     │
#     └─ Engine.swap() (proven, battle-tested)
#          │
#          ├─ Token approval (if needed)
#          ├─ Path encoding
#          ├─ Deadline in MILLISECONDS
#          ├─ Multicall if HBAR involved
#          └─ Sign, send, wait for receipt
#     │
#     ▼
#   SwapResult → logged to execution_records/


# =============================================================================
# 10. FILES (current state)
# =============================================================================
#
# CORE (the product):
#   pacman_agent.py          - Structured swap agent (Layer 2)
#   build_routes.py          - Route table generator
#   routes.json              - Pre-computed routing table (generated)
#   pacman_translator.py     - NL converter (Layer 1, optional)
#   pacman_config.py         - Config + safety limits
#
# ENGINE (proven, do not modify):
#   btc_rebalancer_swap_engine.py  - Production swap engine (Layer 3)
#   saucerswap_v2_client.py        - Low-level V2 client
#   v2_tokens.py                   - Token ID constants
#
# DATA:
#   pacman_data_raw.json     - Pool snapshot from SaucerSwap API
#
# SAFETY:
#   pacman_preflight.py      - Pre-swap validation (needs integration)
#   pacman_associate.py      - HTS token association
#
# TESTS:
#   test_agent.py            - Agent test suite (80 tests)
#
# LEGACY (may be retired):
#   pacman_chat.py           - Old regex chat interface
#   pacman_chat_v3.py        - Old v3 chat
#   pacman_chat_v4.py        - Old AI-native chat
#   pacman_variant_router.py - Old variant router (logic moving to agent)
#   pacman_executor.py       - Old executor (replaced by engine)
#   pacman_executor_pro.py   - Old pro executor
#   pacman_executor_ultra.py - Old ultra executor
#   pool_graph.py            - Old graph (replaced by build_routes.py)


# =============================================================================
# 11. HEDERA GOTCHAS (for any AI building components)
# =============================================================================
#
# 1. DEADLINES ARE MILLISECONDS
#    deadline = int(time.time() * 1000) + 600000
#    NOT seconds. Seconds = instant transaction rejection.
#
# 2. WHBAR IS NOT A TOKEN (see §3)
#    0.0.1456986 is a contract wrapper. Never trade to it.
#
# 3. HTS ASSOCIATION REQUIRED
#    Before receiving any HTS token, your account must associate with it.
#    This is a one-time 0.05 HBAR cost per token. Without it, the
#    swap transaction reverts.
#
# 4. POOL FEES ARE IN HUNDREDTHS OF BASIS POINTS
#    500 = 0.05%, 1500 = 0.15%, 3000 = 0.30%, 10000 = 1.00%
#    To get decimal: fee / 1_000_000
#    To get percent: fee / 10_000
#
# 5. DUAL TOKEN TYPES
#    Same asset exists as ERC20 (bridged) and HTS (native).
#    Different token IDs, different pools, different visibility.
#    Default to HTS for user-facing swaps.
#
# 6. APPROVAL PROPAGATION
#    After approving a token, wait 3-5 seconds before swapping.
#    Hedera consensus needs time to propagate the approval.
#
# 7. PRIVATE KEY FORMAT
#    64 hex chars, no 0x prefix. ECDSA secp256k1.
#
# 8. CHAIN ID
#    Mainnet: 295. Testnet: 296.


# =============================================================================
# 12. FOR AI AGENTS BUILDING COMPONENTS
# =============================================================================
#
# If you are an AI agent assigned to build a specific component:
#
# 1. READ THIS DOCUMENT FIRST. Especially §3 (WHBAR) and §11 (gotchas).
#
# 2. DO NOT MODIFY btc_rebalancer_swap_engine.py. It is proven and working.
#    If you need different behavior, wrap it, don't change it.
#
# 3. The agent takes STRUCTURED inputs. {from_token, to_token, amount, mode}.
#    If you're building a UI or bot, your job is to produce these 4 fields.
#    The agent handles everything else.
#
# 4. Token names are CANONICAL. Use the exact names from routes.json:
#    USDC, USDC_HTS, WBTC_HTS, WBTC_LZ, WETH_HTS, SAUCE, etc.
#    Never use pool symbols (USDC[hts], HTS-WBTC, etc.) in the API.
#
# 5. routes.json is the source of truth for what's tradeable.
#    If a token isn't in routes.json, it can't be traded.
#
# 6. Test with test_agent.py. All tests must pass before merging.
#
# 7. Safety limits are non-negotiable. See §7.
