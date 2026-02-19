# Pacman CLI - Product Specification & Developer Manifesto

**Version**: 0.9.3 (Pre-Release)
**Maintainer**: Chris0x88
**Status**: Active Development
**Repository Size**: ~200k Tokens
**Target Audience**: Power Users, Algo Traders, Developers

---

# 1. Executive Summary & Philosophy

Pacman is a terminal-based trading engine designed specifically for the Hedera Hashgraph network. It bypasses traditional web interfaces to interact directly with the SaucerSwap V2 smart contracts via JSON-RPC.

## 1.1 The "Why"
Traditional DEX interfaces (`app.saucerswap.finance`) are built for the average user. They are safe, slow, and heavy. They rely on indexers (Graph/Mirror Nodes) that can fall behind the chain state.
Pacman was built to be:
1.  **Faster**: It talks directly to the nodes. No indexer latency.
2.  **Leaner**: No browser overhead. No React hydration. Just raw data.
3.  **Local**: Your keys, your config, your rules.

## 1.2 Design Pillars
1.  **Terminal Supremacy**: The CLI is the first-class citizen. If it can't be done in the terminal, it's not a feature. ASCII art, semantic coloring, and raw text output are the UI.
2.  **Speed > Safety (with Guardrails)**: The user is assumed to be an expert. We prioritize execution speed but enforce mandatory simulation checks to prevent gas waste.
3.  **"Guerilla Trading"**: The tool is designed for rapid entry and exit. It is not a portfolio manager; it is a sniper rifle.
4.  **No-Nonsense Aesthetics**: A "Retro-Cyberpunk" visual identity that focuses on high-contrast readability (Cyan/Magenta/Green) rather than web 2.0 gradients.

---

# 2. Historical Context (The "War Stories")

Understanding the *history* of Pacman is crucial to understanding its *code*.

## 2.1 The "Indexer" Problem (Jan 2026)
**Initial Approach**: We started by querying the SaucerSwap API for quotes.
**The Failure**: The API was rate-limited, often 1-2 blocks behind the chain during high congestion, and required an API key that 90% of users didn't have.
**The Solution**: We built a custom **Client-Side Router**.
- **Action**: Pacman downloads the entire V2 pool registry (~600 pools) on startup from `pools.json`.
- **Action**: It builds an in-memory graph using `networkx` logic (custom implementation).
- **Action**: It queries the blockchain state *directly* via `eth_call` to `getReserves`.
- **Result**: Zero API dependencies for routing. 100% uptime (as long as the RPC is up).

## 2.2 The "Gas Revert" Crisis (Feb 2026)
**The Incident**: Users reported transactions failing with "Out of Gas" errors despite having sufficient HBAR.
**The Mechanism**: Hedera has two address formats:
- **Long-Zero**: `0x00000000000000000000000000000000000004d2` (Matches Account ID `0.0.1234`)
- **EVM Alias**: `0x348...` (The actual public key hash)
**The Root Cause**: The SaucerSwap V2 contracts (Uniswap V2 forks) use `CREATE2` to determine pair addresses. This calculation depends on the *sender's address* for some operations. When a user signed with their Long-Zero address, the contract calculated a different pair address than what existed, causing a revert.
**The Fix**:
- We implemented a strict **Alias-Only Policy**.
- `src/executor.py`: `self.eoa` is ALWAYS the Alias address.
- We added `eth_call` simulation as a mandatory pre-flight check. If the simulation fails, we *never* broadcast.

## 2.3 The "Nested Token" Confusion
**The Problem**: Hedera has "Native HTS" tokens and "EVM Bridged" tokens.
- `WBTC` exists as `0.0.X` (HTS) and `0x...` (ERC20).
- Users were confused about which one they held.
**The Solution**: The **Variant Router**.
- We treat tokens as "Variants". `WBTC[HTS]` and `WBTC[ERC20]` are nodes in the graph.
- The router automatically adds `Wrap` or `Unwrap` steps if the most liquid pool requires a specific format.
- To the user, it's transparent. They just swap "WBTC".

## 2.4 The "Legacy" Bridge (Feb 2026)
**The Need**: Hot meme coins (like DOSA) launched on SaucerSwap V1 and never migrated liquidity to V2.
**The Challenge**: V1 uses a completley different math curve ($x*y=k$) and contract interface than V2.
**The Solution**: The **Sidecar Adapter**.
- We built `lib/v1_saucerswap.py` as a standalone client.
- It is *strictly isolated* from the V2 engine to prevent regression.
- Users access it via `swap-v1`. It's there when you need it, invisible when you don't.

## 2.5 Banking & Security Arc (Feb 2026)
**The Pivot**: Pacman evolved from a "swapper" to a "bank".
- **Staking**: Implemented native HBAR staking (HIP-406) so users earn ~1% APY while holding.
- **Whitelisting**: Implemented a strict `settings.json` whitelist. The tool now refuses to send funds to unknown addresses, protecting users from clipboard hijacking or typos.

---

# 3. Directory Structure & File Manifest

A complete breakdown of every file's responsibility.

## `/cli` (The Interface)
-   **`main.py`**: The entry point. Handles `argparse`, the main input loop, and command dispatch. It contains the logic for `exact_in` vs `exact_out` detection.
-   **`display.py`**: The rendering engine. Contains the `C` class (Colors) and helper functions for stylized output (frames, banners, tables). It is the *only* place where `print` formatting should happen.

## `/src` (The Logic)
-   **`controller.py`**: The SDK / Facade. The primary interface for the CLI. Coordinates all other modules.
-   **`router.py`**: The Pathfinding Engine.
    -   `PacmanVariantRouter`: The main class.
    -   `find_routes()`: Returns a list of `VariantRoute` objects.
-   **`executor.py`**: The Execution Engine.
    -   `PacmanExecutor`: Handles Web3 connections and state machine.
    -   `execute_swap()`: The main execution entry point.
-   **`translator.py`**: The NLP Engine.
    -   `translate_command()`: Converts string -> JSON intent.
-   **`config.py`**: Configuration & Safety logic (`SecureString`).
-   **`errors.py`**: Centralized exception hierarchy.

## `/lib` (The Drivers)
-   **`saucerswap.py`**: SaucerSwap V2 low-level client.
-   **`v1_saucerswap.py`**: SaucerSwap V1 legacy client.
-   **`prices.py`**: `PriceManager` singleton for token USD quotes.
-   **`multicall.py`**: Batch request handler (Multicall3).
-   **`transfers.py`**: Native HBAR and HTS transfer logic.
-   **`staking.py`**: Native HBAR staking (HIP-406).

---

# 4. Data Schemas

## 4.1 `data/tokens.json`
The source of truth for token precision and IDs.
```json
{
  "USDC": {
    "id": "0.0.456858",
    "decimals": 6,
    "symbol": "USDC",
    "name": "USD Coin"
  },
  "HBAR": {
    "id": "0.0.1456986",
    "decimals": 8,
    "symbol": "HBAR",
    "name": "Hedera"
  }
}
```

## 4.2 `data/variants.json`
Defines the relationship between HTS and ERC20 tokens.
```json
{
  "WBTC_HTS": {
    "id": "0.0.10082597",
    "symbol": "HTS-WBTC",
    "type": "HTS_NATIVE",
    "wrap_to": "WBTC_LZ",    // Pointer to the other variant
    "visible_in_hashpack": true
  },
  "WBTC_LZ": {
    "id": "0.0.1055483",
    "symbol": "WBTC[hts]",   // Confusing name, verified by ID
    "type": "ERC20_BRIDGED",
    "unwrap_to": "WBTC_HTS", // Pointer back
    "unwrap_contract": "0.0.9675688",
    "visible_in_hashpack": false
  }
}
```

---

# 5. Configuration & Environment Variables

Pacman prioritizes configuration in this order:
1.  **Runtime Args** (e.g., `--verbose`, `--rpc`)
2.  **Environment Variables** (`.env`)
3.  **Hardcoded Defaults** (`src/config.py`)

## 5.1 Environment Variables
| Variable | Description | Default |
| :--- | :--- | :--- |
| `PACMAN_PRIVATE_KEY` | Hex private key (0x...) | None (Sim Mode) |
| `HEDERA_ACCOUNT_ID` | Format 0.0.1234 | None |
| `RPC_URL` | The JSON-RPC endpoint | `https://mainnet.hashio.io/api` |
| `NETWORK` | `mainnet` or `testnet` | `mainnet` |
| `SAUCERSWAP_API_KEY` | Optional key for extended rate limits | None |

## 5.2 Hardcoded Safety Limits (`src/config.py`)
These can only be changed by editing the code.
-   `max_swap_amount_usd`: **$1.00** (Protection against reckless testing)
-   `max_daily_volume_usd`: **$10.00**
-   `max_slippage_percent`: **1.0%**

---

# 6. Workflow Logic: The Life of a Swap

## 6.1 The Input
User types: `swap 100 HBAR to USDC`

## 6.2 The Translation (`src/translator.py`)
1.  **Regex Match**: Matches `Pattern 2` (Exact In).
    -   `amount`: 100
    -   `from_token`: HBAR
    -   `to_token`: USDC
2.  **Resolution**:
    -   `HBAR` -> `0.0.1456986` (WHBAR ID used for routing)
    -   `USDC` -> `0.0.456858`
3.  **Validation**: Checks if `amount > 0`.

## 6.3 The Routing (`src/router.py`)
1.  **Graph Search**: `find_routes("HBAR", "USDC", 100)`
2.  **Breadth-First Search**:
    -   Path 1: `HBAR -> USDC` (Direct Pool `0.0.x`)
    -   Path 2: `HBAR -> SAUCE -> USDC` (Multi-hop)
3.  **Quoting**:
    -   For each path, calls `client.get_quote_single()` or `client.get_quote_exact_output()`.
    -   Selection: Sorts by `AmountOut`.

## 6.4 The UI (`cli/display.py`)
Prints the "Proposed Route" box:
```
  ⟳ Analyzing: 100.0 HBAR → USDC (exact_in)
  
  Proposed Route:
  HBAR → USDC
  Total Cost: 0.15% + 0.020 HBAR
```

## 6.5 The Execution (`src/executor.py`)
User types `y`.
1.  **Association Check**: Does `self.hedera_account_id` have `USDC` associated?
    -   If No: Triggers `associateToken(USDC)` transaction first.
2.  **Approval Check**: (Only for ERC20 involves). HBAR is native, so no approval needed.
3.  **Simulation**: Calls `w3.eth.call(transaction)`.
    -   If Revert: Abort with error.
4.  **Signing**: `w3.eth.account.sign_transaction(tx, private_key)`.
5.  **Broadcast**: `w3.eth.send_raw_transaction(signed_tx)`.
6.  **Monitoring**: Loops `w3.eth.get_transaction_receipt` every 1s.

---

# 7. Known Issues & Workarounds

## 7.1 The "Dust" Issue
-   **Problem**: Swapping Max HBAR often fails because you need HBAR for gas.
-   **Workaround**: Pacman subtracts `2 HBAR` buffer automatically when maxing out HBAR.

## 7.2 The "Decimals" Trap
-   **Problem**: USDC is 6 decimals. SAUCE is 6. HBAR is 8. WBTC is 8.
-   **Risk**: Hardcoding `10**18` everywhere will break math.
-   **Defense**: `data/tokens.json` is the singular authority. We never guess decimals; we look them up.

## 7.3 RPC Flakiness
-   **Problem**: Hashio (public RPC) sometimes returns `502 Bad Gateway` or `429 Too Many Requests`.
-   **Defense**: `lib/multicall.py` has a retry mechanism with exponential backoff.

---

# 8. Future Roadmap

## 8.1 Limit Orders (The "Sentinel")
SaucerSwap V2 supports limit orders. We want to implement:
`swap HBAR for USDC at 0.15`
- This requires a daemon mode to monitor prices.

## 8.2 Portfolio Analytics
`pnl` command.
- Needs to read history from a Mirror Node (dragonglass/hedera-mirror) to calculate cost basis.

## 8.3 Advanced Routing
- **Multi-Hop Custom**: `swap HBAR -> SAUCE -> CLXY -> USDC`
- **Split Routing**: sending 50% to V1 and 50% to V2 (Future optimization).
