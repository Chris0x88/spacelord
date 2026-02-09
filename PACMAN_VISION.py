#!/usr/bin/env python3
"""
PACMAN - MEGA VISION DOCUMENT (v2.0 - OPERATIONAL MODE)
=======================================================

The definitive architectural specification for Pacman: an AI swap router
for SaucerSwap V2 on Hedera.

Author: Chris + Claude + Antigravity
Date: 2026-02-09
Status: Active specification
"""

# =============================================================================
# 1. WHAT PACMAN IS
# =============================================================================
#
# Pacman is a CLI tool for executing swaps on SaucerSwap V2.
# It prioritizes "HashPack Visibility" (HTS tokens) over raw ERC20s, ensuring
# users actually see their assets in their wallets.
#
# It is NOT a chatbot. It is NOT a research tool. It IS an executor.
#
# Core Philosophy:
#   1. Operational: "Swap 100 USDC for WBTC" -> Done.
#   2. Variant-Aware: Handles the HTS vs ERC20 bridged token complexity automatically.
#   3. Robust: Uses millisecond deadlines and multicall for HBAR wrapping.


# =============================================================================
# 2. THE NEW ARCHITECTURE (Consolidated)
# =============================================================================
#
# ┌─────────────────────────────────────────────────────┐
# │  ENTRY: pacman_cli.py                               │
# │  Single source of truth. REPL or One-shot.          │
# └─────────────┬───────────────────────────────────────┘
#               │
#               ▼
# ┌─────────────────────────────────────────────────────┐
# │  LAYER 1: TRANSLATOR (pacman_translator.py)         │
# │  Input: "swap 100 USDC for bitcoin"                 │
# │  Output: {intent="swap", from="USDC", to="WBTC"...} │
# └─────────────┬───────────────────────────────────────┘
#               │
#               ▼
# ┌─────────────────────────────────────────────────────┐
# │  LAYER 2: ROUTER (pacman_variant_router.py)         │
# │  "The Brain". Knows about HTS vs ERC20 variants.    │
# │  Calculates routes that ensure HashPack visibility. │
# │  Auto-inserts Unwrap steps if cheapest route is ERC20.
# └─────────────┬───────────────────────────────────────┘
#               │
#               ▼
# ┌─────────────────────────────────────────────────────┐
# │  LAYER 3: EXECUTOR (pacman_executor.py)             │
# │  "The Muscle". Executes the complex multi-step plan.│
# │  Handles Approvals -> Swaps -> Unwraps.             │
# │  Records data for training.                         │
# └─────────────────────────────────────────────────────┘


# =============================================================================
# 3. PACMAN OPERATIONAL DIRECTIVES (THE RULES)
# =============================================================================
#
# 1. SINGLE PURPOSE
#    This tool executes swaps. It is not a general assistant.
#
# 2. ONE ROUTER
#    Always use `PacmanVariantRouter`. Never create new routing logic or
#    bypasses. The static `routes.json` is deprecated in favor of this
#    dynamic, variant-aware router.
#
# 3. ONE EXECUTOR
#    Always use `PacmanExecutor`. It records performance data.
#    Do not use `SaucerSwapV2Engine` directly unless debugging low-level issues.
#
# 4. HASHPACK VISIBILITY IS PARAMOUNT
#    Always prefer routes that result in HTS-native tokens (e.g., WBTC[hts])
#    over raw ERC20s, unless the user explicitly asks for "cheapest".
#    Users panic when they can't see their tokens. Prevent panic.
#
# 5. NO "PRO/ULTRA" VERSIONS
#    Improve the core files (`pacman_executor.py`). Do not fork them.
#    Delete any file named `*_pro.py` or `*_ultra.py` on sight.


# =============================================================================
# 4. HEDERA & SAUCERSWAP GOTCHAS
# =============================================================================
#
# 1. WHBAR IS NOT A TOKEN
#    0.0.1456986 is a contract wrapper. Never trade to it as a final destination.
#    Always unwrap to native HBAR.
#
# 2. MILLISECOND DEADLINES
#    Hedera requires deadlines in milliseconds: `int(time.time() * 1000) + 600000`
#
# 3. HTS ASSOCIATION
#    Accounts must associate with tokens before receiving them.
#
# 4. DECIMALS MATTER
#    USDC is 6 decimals. WBTC is 8 decimals.
#    Don't assume 18. Check `tokens.json` or pool data.

# =============================================================================
# 5. DEPRECATED / ARCHIVED
# =============================================================================
#
# - pacman_agent.py (The old static agent)
# - btc_rebalancer_swap_engine.py (Old standalone engine)
# - routes.json (Static routing table - replaced by dynamic Router)
# - build_routes.py (Replaced by Router's load_pools)
