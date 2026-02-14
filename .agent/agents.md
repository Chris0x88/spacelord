# AI Agent Guide for Pacman CLI

Never ever use fallbacks or fake fixed data for things like live prices. 

This repository is a specialized Hedera swap engine built around SaucerSwap V2. It is strictly optimized for **Hedera Token Service (HTS)** and native HBAR interactions.

## 🛠 Repository Structure
- `pacman_cli.py`: The main entry point. Handles user intent and swap execution.
- `saucerswap_v2_client.py`: Low-level Web3.py client with Hedera-specific overrides.
- `pacman_executor.py`: High-level execution logic, balance checks, and security.
- `pacman_variant_router.py`: Routing logic with support for HTS-preferred paths.
- `docs/`: Critical technical documentation (See [SAUCERSWAP_V2_RULES.md](file:///Users/cdi/Documents/Github/pacman/docs/SAUCERSWAP_V2_RULES.md)).

## ⚠️ Non-Negotiable Rules

### 1. Milliseconds for Deadlines
Hedera's V2 SwapRouter requires deadlines in **milliseconds**. Using seconds will result in immediate reverts.

### 2. HBAR Value Scaling
Transactions sending native HBAR must scale the `value` field to **18 pseudo-decimals (pseudo-Wei)** for the Hashio Relay.
`scaled_value = tinybars * 10**10`

### 3. Token Approvals
Standard EVM `approve()` calls often fail for HTS tokens. Always verify or use the Hedera SDK-based wrapper `approve_hts_token.js`.

### 4. Multicall Recipient Context
When swapping **Token → HBAR**, the `exactInput` step MUST specify the **Router Address** as the recipient. This allows the subsequent `unwrapWHBAR` call to access the funds within the Router's own context.

### 5. Private Key Environment Variable
The **only** environment variable used for account private keys is `PACMAN_PRIVATE_KEY`. Do not use `PRIVATE_KEY` or `HEDERA_PRIVATE_KEY`. All scripts and clients must prioritize `PACMAN_PRIVATE_KEY`.

## 🤝 Collaboration
Always log `amount_in` and `min_out` for transparency. Ensure dual account IDs (EVM and Hedera) are displayed during initialization to avoid user confusion.
Mode:AGENT_MODE_VERIFICATION
