# AI Agent Guide: Pacman CLI

This document provides instructions for AI agents on how to interact with the Pacman CLI for Hedera-based token swaps and conversions.

## Core Objective
Pacman provides a natural language interface to the SaucerSwap V2 liquidity pools. Your goal as an agent is to interpret user intent and generate high-precision command strings for the `pacman_cli.py` or interactive prompt.

## Command Syntax

### 1. Swaps (HTS/ERC20)
Swaps use liquidity pools to exchange one token for another.
- **Exact Input**: `swap [amount] [tokenA] for [tokenB]` (e.g., `swap 10 HBAR for USDC`)
- **Exact Output**: `swap [tokenA] for [amount] [tokenB]` (e.g., `swap USDC for 0.001 WBTC`)

### 2. Conversions (Native Wrap/Unwrap)
Conversions are for native-to-bridged variants (e.g., HBAR to WHBAR, or WBTC LZ to WBTC HTS).
- **Format**: `convert [amount] [tokenA] to [tokenB]` (e.g., `convert 10 HBAR to WHBAR`)
- **Distinction**: Use `convert` when you are moving between the *same asset* in different technical wrappers. Use `swap` when changing asset types.

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
