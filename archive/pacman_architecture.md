# 🧠 Pacman Ultimate Router Architecture

## The Core Problem

Hedera has **dual-token types** for wrapped assets:
- **ERC20 Bridged**: LayerZero tokens (cheap to acquire, invisible in HashPack)
- **HTS Native**: Hedera native tokens (visible in HashPack, more expensive)

## 3-Dimensional Routing

Pacman must optimize across THREE dimensions:
1. **Swap Path**: Which pools to use
2. **Token Format**: ERC20 vs HTS output
3. **Post-Processing**: Wrap/unwrap requirements

## Token Variant System

```python
class TokenVariant:
    """A token exists in multiple "flavors" on Hedera."""
    
    WBTC_LZ = {  # LayerZero (ERC20)
        "id": "0.0.1055483",
        "type": "ERC20_BRIDGED",
        "visible_in": ["debank", "etherscan"],
        "invisible_in": ["hashpack", "saucerswap_ui"],
        "liquidity_depth": "HIGH",
        "cost_premium": -0.05,  # Cheaper by 5%
    }
    
    WBTC_HTS = {  # Native Hedera
        "id": "0.0.10082597", 
        "type": "HTS_NATIVE",
        "visible_in": ["hashpack", "saucerswap_ui"],
        "invisible_in": [],
        "liquidity_depth": "LOW",
        "cost_premium": 0.0,  # Baseline
    }
```

## Complete Route Matrix

### Route A: Direct to ERC20 (Cheapest)
```
USDC ──[0.05%]──► USDC[hts] ──[0.15%]──► WBTC_LZ (ERC20)
Total: 0.20% + $0 gas
Output: Bridged WBTC (invisible in HashPack)
Price Quote: Use WBTC_LZ/HTS_LZ pool price
```

### Route B: Via HTS with Wrap (User-Friendly)
```
USDC ──[0.15%]──► HTS-WBTC ──[gas: 0.03 HBAR]──► [Unwrap] ──► WBTC_HTS
Total: 0.15% + 0.03 HBAR + wrap gas
Output: Native HTS WBTC (visible in HashPack)
Price Quote: Use SaucerSwap HTS price
```

### Route C: Market Price with Auto-Unwrap (Optimal)
```
USDC ──[0.20%]──► WBTC_LZ ──[auto-unwrap]──► WBTC_HTS
Total: 0.20% + unwrap gas (~0.02 HBAR)
Logic: If ERC20_LZ price < HTS_price - unwrap_cost, take it
Output: Native HTS WBTC
Price Quote: min(HTS_quote, LZ_quote + unwrap_cost)
```

## AI Training Targets

### 1. Token Recognition Layer
```json
{
  "input": "Swap 500 USDC for wBTC",
  "token_resolution": {
    "from": ["USDC", "USDC[hts]"],  // Acceptable variants
    "to_preference": "WBTC_HTS",   // User wants visible balance
    "to_fallback": "WBTC_LZ",      // Accept if much cheaper
    "to_price_source": "coingecko", // External price validation
    "threshold": 0.02              // Accept 2% variance for cheaper route
  }
}
```

### 2. Route Optimization Algorithm
```python
def find_best_route(user_intent):
    candidates = []
    
    # Generate all token variants
    for from_variant in get_variants(user_intent.token_from):
        for to_variant in get_variants(user_intent.token_to):
            # Check if route exists
            route = calculate_route(from_variant, to_variant)
            if route:
                # Add wrap/unwrap if needed
                if needs_conversion(to_variant, user_intent.desired_format):
                    route = add_conversion_step(route)
                
                # Score by total cost
                score = route.fees + route.gas + route.slippage
                candidates.append((score, route))
    
    # Return lowest cost that meets user constraints
    return min(candidates, key=lambda x: x[0])
```

### 3. Price Quotation Engine
```python
class PriceOracle:
    """Quotes prices for ALL token variants."""
    
    def get_price(self, token_variant, amount):
        if token_variant.type == "HTS_NATIVE":
            # Use SaucerSwap HTS pool
            return self.saucerswap_hts_quote(token_variant.id, amount)
        
        elif token_variant.type == "ERC20_BRIDGED":
            # Use ERC20 pool + convert to HTS equivalent
            lz_price = self.saucerswap_erc20_quote(token_variant.id, amount)
            hts_price = self.get_price(WBTC_HTS, amount)  # Recursive
            
            # If spread > conversion_cost, quote conversion
            if lz_price * 1.02 < hts_price:  # 2% spread
                return {
                    "raw": lz_price,
                    "converted": hts_price,
                    "suggestion": "ACCEPT_ERC20_AND_UNWRAP",
                    "savings": hts_price - lz_price - conversion_cost
                }
            
            return lz_price
```

## Implementation Plan

### Phase 1: Variant Router (This Session)
1. Extend matrix with ERC20 vs HTS variants
2. Add wrap/unwrap edges to graph
3. Build route cost calculator including post-swap actions
4. Test with live quotes

### Phase 2: Price Oracle (Next Session)
1. Query all SaucerSwap pools (both ERC20 and HTS)
2. Build price normalization layer
3. Detect arbitrage opportunities between variants
4. Provide floor/ceiling price ranges

### Phase 3: AI Training (Post-Validation)
1. Generate 10,000+ training examples with variant routing
2. Train specialized model on cost optimization
3. Add "teaching mode" where AI explains its routing choice

## Key Insight for AI

The AI must understand:
- **Token variants are fungible economically** but **different UX-wise**
- **Cheapest != Best** if user can't see the balance
- **Post-swap actions are part of the route**, not separate
- **Price quotients change based on format** (ERC20_LZ ≈ HTS - spread)

## Wrap/Unwrap Cost Model

```python
WRAP_COSTS = {
    "WBTC": {
        "unwrap": 0.02,    # HBAR for gas
        "additional_time": 6,  # seconds
        "success_rate": 0.99,
    },
    "WETH": {
        "unwrap": 0.02,
        "additional_time": 6,
        "success_rate": 0.99,
    }
}
```

## User Preference Integration

```python
class UserPreferences:
    """How to route for this user."""
    
    prefer_visible_tokens = True  # Prefer HTS over ERC20
    max_hops = 2
    max_fee_percent = 0.5
    auto_unwrap = True  # Accept ERC20 if cheaper, auto-unwrap
    min_savings_to_swap = 0.01  # 1% - only swap if saves >1%
```

This is the architecture. Want me to build Phase 1 now?
