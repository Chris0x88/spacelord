# Pacman Data Directory

This directory contains the central source of truth for token metadata, liquidity pool registries, and application logic rules.

## ⚙️ Settings ([settings.json](file:///Users/cdi/Documents/Github/pacman/data/settings.json))

The `settings.json` file is your "Control Panel". It allows you to tune the UI and data fetching logic without touching code.

### Display Rules
- **`wallet_balance_order`**: An array of symbols. Tokens matching these symbols (or containing them) will be pinned to the top of your wallet balance display in the order specified.
- **`priority_symbols`**: Controls the sort order of the `tokens` command gallery.
- **`blacklist_ids`**: A system-wide "Mute" list. Any Hedera Token ID added here will be hidden from all CLI displays (balances, token lists, etc.).

### Refresh Rules (The "Limiting Factor")
The `refresh_strategy` defines how `scripts/refresh_data.py` builds the local liquidity map:

- **`curated`**: (Default) Only fetches data for pools where **BOTH** tokens are in your verified `tokens.json` or `pools_v2.json`. This keeps the routing graph lean and avoids "garbage" or low-liquidity pools.
- **`comprehensive`**: Fetches every single V2 pool available on SaucerSwap. Use this if you want to research new pools or want the app to discover every possible routing path on the network.

---

## 📂 Source of Truth Files

- **[tokens.json](file:///Users/cdi/Documents/Github/pacman/data/tokens.json)**: Core metadata (Name, Symbol, Decimals) for officially supported tokens.
- **[aliases.json](file:///Users/cdi/Documents/Github/pacman/data/aliases.json)**: Mapping of nicknames (e.g., "stables") to canonical symbols or IDs.
- **[pools_v2.json](file:///Users/cdi/Documents/Github/pacman/data/pools_v2.json)**: Static registry of verified liquidity pool Contract IDs and fees.
- **[variants.json](file:///Users/cdi/Documents/Github/pacman/data/variants.json)**: Maps relationship between ERC20 bridged tokens and HTS native variants.

## 🛠 Variables Registry
- **`pacman_data_raw.json`**: The live cache. This file is generated/updated by `scripts/refresh_data.py`. It contains the actual reserves and pricing data used by the router.

> [!NOTE]
> Always run `scripts/refresh_data.py` after modifying `settings.json` refresh strategies to update your local map.
