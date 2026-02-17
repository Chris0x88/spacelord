# Pacman Router Evolution: The "Real Router" Build

## Current State Analysis
The current `PacmanVariantRouter` is a **2-Hop Hub-and-Spoke** engine. While functional for common pairs, it has significant technical debt that prevents optimal execution:

1.  **Limited Traversal**: It can only route via a hardcoded set of hubs (`USDC`, `HBAR`, etc.). It cannot find a 3-hop or 4-hop route (e.g., `TokenA -> TokenB -> HBAR -> TokenC`).
2.  **Inaccurate Gas Pricing**: It assumes every swap step costs `0.02 HBAR`. Real-world SaucerSwap V2 transactions cost between `0.5 and 1.5 HBAR`.
3.  **Data Isolation**: The router relies on a JSON file (`pacman_data_raw.json`) populated by an API script.
4.  **API Failure**: The SaucerSwap V2 API (`/pools`) is currently returning **401 Unauthorized**, meaning the router is potentially "starved" of updated pool data.

---

## The "Real Router" Architecture

### 1. BFS/Dijkstra Graph Traversal (True Multi-hop)
We will move to a standard graph search algorithm to discover paths of any depth.
- **Node**: Token Symbol / ID.
- **Edge**: Verified SaucerSwap Pool.
- **Goal**: Enable routes like `USDC -> HBAR -> GIB` without hardcoding GIB as a special case.

### 2. Dynamic Cost Function
The router will select paths based on the **Effective Price**, not just pool fees.
> `Total_Cost = Sum(Pool_Fees) + Sum(Gas_Estimate * HBAR_Price)`

- **Step-Specific Gas**: 
    - `Wrap/Unwrap`: ~0.05 HBAR
    - `Swap (Direct)`: ~0.8 HBAR
    - `Swap (Multicall/Native)`: ~1.2 HBAR

### 3. RPC-First Discovery (Bypassing API 401)
Since the SaucerSwap API is restricted, we will shift responsibility to the **Hedera JSON-RPC Relay**.
- **Static Registry**: Maintain a list of "Classic" Verified Pool IDs in `data/pools.json`.
- **On-Chain Check**: Use Multicall to verify pool reserves directly from the pool contract IDs.
- **Reserves Fetching**: Fetch `slot0` or `reserves` to calculate Price Impact locally.

### 4. Safety Guardrails
- **Max Hop Limit**: Cap routes at 3 hops to prevent excessive gas waste.
- **Slippage Check**: Auto-rejection of routes where Price Impact (Reserves) > 2%.

---

## Future Roadmap: Price Impact (Slip-Detection)
To provide true depth, we must query the Ledger directly.
1.  **Multicall Reserves**: Batch fetch `token0` and `token1` balances for every pool in the proposed route.
2.  **Constant Product Rule**: Calculate the output amount manually before simulating, providing a "Pre-Simulation" sanity check for slippage.
