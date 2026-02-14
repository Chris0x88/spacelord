"""
Valid Swap Pairs Configuration
===============================

This module defines which token pairs have direct pools on SaucerSwap V2.
Only pairs listed here will be shown in the UI.

GOVERNANCE RULE: Only add pairs after verifying the pool exists on-chain.
This keeps the UI clean and prevents "No pool found" errors.

To verify a pool exists:
1. Check on SaucerSwap.finance UI
2. Or query factory: factory.getPool(token0, token1, feeTier)
3. Confirm pool address is not zero address

Last updated: 2026-01-12
"""

# =============================================================================
# VALID DIRECT POOLS
# =============================================================================
# Format: (token0_symbol, token1_symbol) -> fee_tier (basis points)
# Fee tiers: 500 = 0.05%, 1500 = 0.15%, 3000 = 0.30%, 10000 = 1.00%

VALID_DIRECT_PAIRS = {
    # =======================================================================
    # TIER 1: PRIORITY PAIRS - Your main trading pairs (Large pools)
    # =======================================================================

    # USDC pairs (Base currency for most trading)
    ('USDC', 'WBTC'): 1500,   # 0.15% - PRIMARY BTC PAIR
    ('WBTC', 'USDC'): 1500,   # Reverse

    ('USDC', 'WHBAR'): 1500,   # 0.15% - PRIMARY HBAR PAIR
    ('WHBAR', 'USDC'): 1500,   # Reverse (via WHBAR)

    ('USDC', 'WETH'): 1500,   # 0.15% - PRIMARY ETH PAIR
    ('WETH', 'USDC'): 1500,   # Reverse

    ('USDC', 'USDT'): 500,    # 0.05% - STABLECOIN PAIR (low fee)
    ('USDT', 'USDC'): 500,    # Reverse

    ('USDC', 'SAUCE'): 3000,  # 0.30% - SAUCERSWAP NATIVE
    ('SAUCE', 'USDC'): 3000,  # Reverse

    # =======================================================================
    # TIER 2: SECONDARY PAIRS - DeFi tokens and altcoins
    # =======================================================================

    ('USDC', 'LINK'): 3000,   # 0.30% - CHAINLINK
    ('LINK', 'USDC'): 3000,   # Reverse

    ('USDC', 'AVAX'): 3000,   # 0.30% - AVALANCHE
    ('AVAX', 'USDC'): 3000,   # Reverse

    ('USDC', 'DAI'): 500,     # 0.05% - DAI STABLECOIN
    ('DAI', 'USDC'): 500,     # Reverse

    # HBAR pairs (Native Hedera pairs)
    ('WHBAR', 'SAUCE'): 3000,  # 0.30% - HBAR native token
    ('SAUCE', 'WHBAR'): 3000,  # Reverse

    # =======================================================================
    # TIER 3: EXOTIC PAIRS - Lower priority, may have lower liquidity
    # =======================================================================

    # Additional HBAR pairs for comprehensive coverage
    # These are secondary priority but useful for users who want full access
    ('WHBAR', 'LINK'): 3000,   # 0.30% - HBAR to DeFi
    ('LINK', 'WHBAR'): 3000,   # Reverse
    
    ('WHBAR', 'AVAX'): 3000,   # 0.30% - HBAR to major crypto
    ('AVAX', 'WHBAR'): 3000,   # Reverse
    
    ('WHBAR', 'QNT'): 3000,    # 0.30% - HBAR to DeFi
    ('QNT', 'WHBAR'): 3000,    # Reverse
    
    ('WHBAR', 'MATIC'): 3000,  # 0.30% - HBAR to major crypto
    ('MATIC', 'WHBAR'): 3000, # Reverse
    
    ('WHBAR', 'DOVU'): 3000,   # 0.30% - HBAR to ecosystem
    ('DOVU', 'WHBAR'): 3000,   # Reverse
    
    ('WHBAR', 'PACK'): 3000,   # 0.30% - HBAR to ecosystem
    ('PACK', 'WHBAR'): 3000,   # Reverse
    
    ('WHBAR', 'GRELF'): 10000,  # 1.00% - HBAR to meme (high volatility)
    ('GRELF', 'WHBAR'): 10000, # Reverse
    
    ('WHBAR', 'SENTX'): 5000,   # 0.50% - HBAR to ecosystem
    ('SENTX', 'WHBAR'): 5000,   # Reverse
    
    ('WHBAR', 'HBARX'): 3000,  # 0.30% - HBAR to liquid staking
    ('HBARX', 'WHBAR'): 3000, # Reverse
    
    ('WHBAR', 'XSAUCE'): 3000,  # 0.30% - HBAR to ecosystem
    ('XSAUCE', 'WHBAR'): 3000, # Reverse
    
    # Additional stablecoin pairs
    # HBAR Pairs (V2 pools)
    ('WHBAR', 'LINK'): 3000,    # 0.30% - HBAR to LINK (V2 pool)
    ('LINK', 'WHBAR'): 3000,    # Reverse
    
    ('WHBAR', 'QNT'): 3000,     # 0.30% - HBAR to QNT (V2 pool, $500k liquidity)
    ('QNT', 'WHBAR'): 3000,     # Reverse
    
    ('WHBAR', 'AVAX'): 3000,    # 0.30% - HBAR to AVAX (V2 pool, $30k liquidity)
    ('AVAX', 'WHBAR'): 3000,    # Reverse
    
    ('WHBAR', 'USDT'): 1500,    # 0.15% - HBAR to stablecoin
    ('USDT', 'WHBAR'): 1500,    # Reverse
    
    ('WHBAR', 'DAI'): 1500,      # 0.15% - HBAR to stablecoin (HTS DAI V2 pool)
    ('DAI', 'WHBAR'): 1500,      # Reverse
    
    ('WHBAR', 'WBTC'): 3000,     # 0.30% - HBAR to major crypto
    ('WBTC', 'WHBAR'): 3000,     # Reverse
    
    ('WHBAR', 'WETH'): 3000,     # 0.30% - HBAR to major crypto
    ('WETH', 'WHBAR'): 3000,     # Reverse
    
    # Add more pairs here as they're verified on-chain
}


# =============================================================================
# ROUTING CONFIGURATION
# =============================================================================
# Preferred intermediary tokens for routing (in priority order)
ROUTING_INTERMEDIARIES = ['USDC', 'USDT']  # USDC is most liquid, try first


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_valid_pair(token0_symbol: str, token1_symbol: str, allow_routing: bool = True) -> bool:
    """
    Check if a swap is possible between two tokens.

    Args:
        token0_symbol: From token symbol
        token1_symbol: To token symbol
        allow_routing: If True, also returns True for pairs that can route through intermediaries

    Returns:
        True if swap is possible (directly or via routing)
    """
    # Check direct pool
    if (token0_symbol, token1_symbol) in VALID_DIRECT_PAIRS:
        return True

    # Check routing if enabled
    if allow_routing:
        return find_routing_path(token0_symbol, token1_symbol) is not None

    return False


def has_direct_pool(token0_symbol: str, token1_symbol: str) -> bool:
    """Check if a direct pool exists (no routing)."""
    return (token0_symbol, token1_symbol) in VALID_DIRECT_PAIRS


def get_fee_tier(token0_symbol: str, token1_symbol: str) -> int:
    """Get the fee tier for a token pair (in basis points)."""
    return VALID_DIRECT_PAIRS.get((token0_symbol, token1_symbol), 1500)


def get_priority_pairs() -> list:
    """Get priority pairs that should always be shown in UI."""
    priority_pairs = []
    
    # TIER 1: Core pairs (always show)
    tier1_pairs = [
        ('USDC', 'WBTC'), ('WBTC', 'USDC'),
        ('USDC', 'WHBAR'), ('WHBAR', 'USDC'),
        ('USDC', 'WETH'), ('WETH', 'USDC'),
        ('USDC', 'USDT'), ('USDT', 'USDC'),
        ('USDC', 'SAUCE'), ('SAUCE', 'USDC')
    ]
    
    # TIER 2: Secondary pairs (show by default)
    tier2_pairs = [
        ('USDC', 'LINK'), ('LINK', 'USDC'),
        ('USDC', 'AVAX'), ('AVAX', 'USDC'),
        ('USDC', 'DAI'), ('DAI', 'USDC'),
        ('WHBAR', 'SAUCE'), ('SAUCE', 'WHBAR')
    ]
    
    priority_pairs.extend(tier1_pairs)
    priority_pairs.extend(tier2_pairs)
    
    return priority_pairs


def get_hbar_pairs() -> list:
    """Get all HBAR pairs (for advanced users)."""
    hbar_pairs = []
    
    for (token0, token1), fee in VALID_DIRECT_PAIRS.items():
        if 'WHBAR' in (token0, token1):
            hbar_pairs.append((token0, token1, fee))
    
    return hbar_pairs


def get_exotic_pairs() -> list:
    """Get exotic pairs (lower liquidity, higher fees)."""
    exotic_pairs = []
    
    # High fee pairs (> 3000 bps)
    for (token0, token1), fee in VALID_DIRECT_PAIRS.items():
        if fee > 3000:
            exotic_pairs.append((token0, token1, fee))
    
    return exotic_pairs


def get_all_valid_pairs(include_routed: bool = True, show_hbar_pairs: bool = False, show_exotic: bool = False) -> list:
    """
    Get all valid token pairs with filtering options.

    Args:
        include_routed: If True, includes pairs that can route through intermediaries
        show_hbar_pairs: If True, includes all HBAR pairs (not just priority)
        show_exotic: If True, includes exotic pairs with high fees

    Returns:
        List of tuples: (token0, token1, fee_tier or 'routed')
    """
    seen = set()
    pairs = []

    # Start with priority pairs
    priority_pairs = get_priority_pairs()
    for (token0, token1) in priority_pairs:
        if (token0, token1) in VALID_DIRECT_PAIRS:
            fee = VALID_DIRECT_PAIRS[(token0, token1)]
            pair_key = tuple(sorted([token0, token1]))
            if pair_key not in seen:
                seen.add(pair_key)
                pairs.append((token0, token1, fee))

    # Add HBAR pairs if requested
    if show_hbar_pairs:
        hbar_pairs = get_hbar_pairs()
        for (token0, token1, fee) in hbar_pairs:
            pair_key = tuple(sorted([token0, token1]))
            if pair_key not in seen:
                seen.add(pair_key)
                pairs.append((token0, token1, fee))

    # Add exotic pairs if requested
    if show_exotic:
        exotic_pairs = get_exotic_pairs()
        for (token0, token1, fee) in exotic_pairs:
            pair_key = tuple(sorted([token0, token1]))
            if pair_key not in seen:
                seen.add(pair_key)
                pairs.append((token0, token1, fee))

    # Add remaining direct pairs
    for (token0, token1), fee in VALID_DIRECT_PAIRS.items():
        pair_key = tuple(sorted([token0, token1]))
        if pair_key not in seen:
            seen.add(pair_key)
            pairs.append((token0, token1, fee))

    if include_routed:
        # Get all unique tokens
        all_tokens = set()
        for (token0, token1) in VALID_DIRECT_PAIRS.keys():
            all_tokens.add(token0)
            all_tokens.add(token1)

        # Check all possible combinations for routing
        from itertools import combinations
        for token0, token1 in combinations(sorted(all_tokens), 2):
            pair_key = tuple(sorted([token0, token1]))

            # Skip if already added as direct pair
            if pair_key in seen:
                continue

            # Check if routing possible
            route_info = find_routing_path(token0, token1)
            if route_info and not route_info['is_direct']:
                seen.add(pair_key)
                # Mark as 'routed' instead of fee tier
                pairs.append((token0, token1, 'routed'))

    return pairs


def get_tokens_with_usdc_pairs() -> list:
    """Get all tokens that have direct pools with USDC."""
    tokens = set()
    for (token0, token1) in VALID_DIRECT_PAIRS.keys():
        if token0 == 'USDC':
            tokens.add(token1)
        elif token1 == 'USDC':
            tokens.add(token0)
    return sorted(list(tokens))


def find_optimal_routing_path(token0_symbol: str, token1_symbol: str, amount: float = 1000) -> dict:
    """
    Find the optimal routing path based on mathematically calculated slippage.
    
    Args:
        token0_symbol: Source token symbol
        token1_symbol: Target token symbol
        amount: Trade amount in USD (for slippage calculation)
    
    Returns:
        dict with optimal routing path info, or None if no route found
    """
    if token0_symbol == token1_symbol:
        return None
    
    # Check direct pool first
    if has_direct_pool(token0_symbol, token1_symbol):
        direct_slippage = estimate_slippage(token0_symbol, token1_symbol, amount, True)
        return {
            'path': [token0_symbol, token1_symbol],
            'fee_tiers': [get_fee_tier(token0_symbol, token1_symbol)],
            'is_direct': True,
            'total_fee_pct': get_fee_tier(token0_symbol, token1_symbol) / 10000 * 100,
            'calculated_slippage': direct_slippage,
            'intermediary': None
        }
    
    # Check all possible routing paths and calculate actual slippage for each
    best_route = None
    lowest_total_slippage = float('inf')
    
    for intermediary in ROUTING_INTERMEDIARIES:
        # Don't route through self
        if intermediary == token0_symbol or intermediary == token1_symbol:
            continue
        
        # Check if both legs exist
        leg1 = (token0_symbol, intermediary)
        leg2 = (intermediary, token1_symbol)
        
        if leg1 in VALID_DIRECT_PAIRS and leg2 in VALID_DIRECT_PAIRS:
            fee1 = VALID_DIRECT_PAIRS[leg1]
            fee2 = VALID_DIRECT_PAIRS[leg2]
            
            # Calculate actual slippage for each leg
            # For routing, we need to consider the output amount from leg1 as input to leg2
            slippage1 = estimate_slippage(token0_symbol, intermediary, amount, False)
            
            # Estimate output from first leg to calculate second leg slippage
            # This is a simplified approach - in reality would use actual quote calculations
            estimated_output_amount = amount * (1 - slippage1 / 100)
            slippage2 = estimate_slippage(intermediary, token1_symbol, estimated_output_amount, False)
            
            # Total slippage for routed trade (compounded)
            # For multi-hop: total_slippage = 1 - (1 - slippage1) * (1 - slippage2)
            total_slippage = 1 - (1 - slippage1 / 100) * (1 - slippage2 / 100)
            total_slippage_pct = total_slippage * 100
            
            # Keep the route with lowest total slippage
            if total_slippage_pct < lowest_total_slippage:
                lowest_total_slippage = total_slippage_pct
                best_route = {
                    'path': [token0_symbol, intermediary, token1_symbol],
                    'fee_tiers': [fee1, fee2],
                    'is_direct': False,
                    'total_fee_pct': (fee1 / 10000 * 100) + (fee2 / 10000 * 100),
                    'calculated_slippage': total_slippage_pct,
                    'leg1_slippage': slippage1,
                    'leg2_slippage': slippage2,
                    'intermediary': intermediary
                }
    
    return best_route


def estimate_slippage(token0: str, token1: str, amount: float, is_direct: bool) -> float:
    """
    Calculate slippage using AMM constant product formula.
    
    Args:
        token0: Source token symbol
        token1: Target token symbol
        amount: Trade amount in USD
        is_direct: Whether this is a direct pool or routed
    
    Returns:
        Calculated slippage as percentage (0-100)
    """
    try:
        # Get pool reserves from SaucerSwap if available
        from api import saucerswap_client, SAUCERSWAP_AVAILABLE
        from token_whitelist import get_token
        
        if not SAUCERSWAP_AVAILABLE or not saucerswap_client:
            # Fallback to simple estimation if SaucerSwap not available
            return _fallback_slippage_estimate(token0, token1, amount, is_direct)
        
        token0_info = get_token(token0)
        token1_info = get_token(token1)
        
        if not token0_info or not token1_info:
            return _fallback_slippage_estimate(token0, token1, amount, is_direct)
        
        # Get pool reserves
        try:
            pool_address = saucerswap_client.get_pool(
                token0_info.evm_address,
                token1_info.evm_address,
                1500  # Most common fee tier
            )
            
            if not pool_address or pool_address == "0x0000000000000000000000000000000000000000":
                return _fallback_slippage_estimate(token0, token1, amount, is_direct)
            
            # Get pool data (reserves)
            slot0 = saucerswap_client.get_slot0(pool_address)
            liquidity = saucerswap_client.get_liquidity(pool_address)
            
            if not slot0 or not liquidity:
                return _fallback_slippage_estimate(token0, token1, amount, is_direct)
            
            # Calculate current reserves from sqrtPriceX96
            # This is simplified - in reality would need more precise calculations
            sqrt_price_x96 = int(slot0['sqrtPriceX96'])
            current_price = (sqrt_price_x96 / (2 ** 96)) ** 2
            
            # Estimate reserves based on price and typical pool composition
            # This is an approximation - real implementation would query actual reserves
            estimated_reserve0 = liquidity / (2 * sqrt_price_x96) * (2 ** 96)
            estimated_reserve1 = liquidity * sqrt_price_x96 / (2 ** 96)
            
            # Convert amount to token units
            if token0_info.symbol in ['USDC', 'USDT']:
                amount_in_tokens = amount * (10 ** token0_info.decimals)
            else:
                # For non-USD tokens, use price to convert
                token0_price_usd = _get_token_price(token0_info.symbol)
                if token0_price_usd:
                    amount_in_tokens = (amount / token0_price_usd) * (10 ** token0_info.decimals)
                else:
                    return _fallback_slippage_estimate(token0, token1, amount, is_direct)
            
            # Calculate slippage using constant product formula
            # Amount out = (reserve_out * amount_in) / (reserve_in + amount_in)
            reserve_in = estimated_reserve0
            reserve_out = estimated_reserve1
            
            if amount_in_tokens >= reserve_in:
                return 10.0  # Cap at 10% for very large trades
            
            amount_out = (reserve_out * amount_in_tokens) / (reserve_in + amount_in_tokens)
            
            # Calculate price before and after trade
            price_before = reserve_out / reserve_in
            price_after = (reserve_out - amount_out) / (reserve_in + amount_in_tokens)
            
            # Slippage is the percentage change in price
            price_change = abs(price_after - price_before)
            slippage_pct = (price_change / price_before) * 100
            
            # Adjust for routing (multi-hop trades compound slippage)
            if not is_direct:
                slippage_pct *= 1.0  # No penalty - actual calculation accounts for both hops
            
            return min(slippage_pct, 10.0)  # Cap at 10%
            
        except Exception as e:
            print(f"Error calculating slippage from pool data: {e}")
            return _fallback_slippage_estimate(token0, token1, amount, is_direct)
            
    except ImportError:
        return _fallback_slippage_estimate(token0, token1, amount, is_direct)


def _fallback_slippage_estimate(token0: str, token1: str, amount: float, is_direct: bool) -> float:
    """
    Fallback slippage estimation when pool data not available.
    Uses conservative estimates based on typical pool depths.
    """
    try:
        from token_whitelist import get_token, TokenCategory
        
        token0_info = get_token(token0)
        token1_info = get_token(token1)
        
        if not token0_info or not token1_info:
            return 2.0
        
        # Conservative pool depth estimates by category (in USD)
        pool_depths = {
            (TokenCategory.STABLECOIN, TokenCategory.STABLECOIN): 5000000,  # $5M
            (TokenCategory.STABLECOIN, TokenCategory.MAJOR_CRYPTO): 2000000,  # $2M
            (TokenCategory.MAJOR_CRYPTO, TokenCategory.STABLECOIN): 2000000,
            (TokenCategory.MAJOR_CRYPTO, TokenCategory.MAJOR_CRYPTO): 1000000,  # $1M
            (TokenCategory.DEFI, TokenCategory.STABLECOIN): 500000,     # $500k
            (TokenCategory.DEFI, TokenCategory.MAJOR_CRYPTO): 300000,    # $300k
            (TokenCategory.DEFI, TokenCategory.DEFI): 200000,           # $200k
            (TokenCategory.HEDERA_ECOSYSTEM, TokenCategory.STABLECOIN): 100000,  # $100k
            (TokenCategory.HEDERA_ECOSYSTEM, TokenCategory.MAJOR_CRYPTO): 75000,   # $75k
        }
        
        cat0 = token0_info.category
        cat1 = token1_info.category
        
        # Get pool depth
        depth = pool_depths.get((cat0, cat1), pool_depths.get((cat1, cat0), 100000))
        
        # Calculate slippage using constant product approximation
        # For small trades: slippage ≈ (amount / depth) * 100
        if amount < depth:
            slippage = (amount / depth) * 100
        else:
            # For large trades, slippage increases non-linearly
            slippage = (amount / depth) * 100 * (1 + (amount / depth))
        
        # Adjust for routing (actual calculation, not penalty)
        if not is_direct:
            slippage *= 1.0  # No artificial penalty
        
        return min(slippage, 10.0)
        
    except ImportError:
        # Very conservative fallback
        return min((amount / 100000) * 100, 10.0)


def _get_token_price(symbol: str) -> Optional[float]:
    """
    Get token price for amount conversion.
    This would integrate with the live pricing API.
    """
    try:
        # This would integrate with the /api/prices endpoint
        # For now, return some reasonable estimates
        price_estimates = {
            'USDC': 1.0,
            'USDT': 1.0,
            'WBTC': 95000,
            'WETH': 2000,
            'HBAR': 0.05,
            'LINK': 20,
            'AVAX': 25,
            'QNT': 83.33,
            'MATIC': 0.5,
            'SAUCE': 0.1,
            'DOVU': 0.005,
            'PACK': 0.02,
        }
        return price_estimates.get(symbol)
    except Exception:
        return None


def find_routing_path(token0_symbol: str, token1_symbol: str) -> dict:
    """
    Find a routing path between two tokens using intermediaries.

    Returns dict with:
        - path: List of token symbols in order [tokenA, intermediary, tokenB]
        - fee_tiers: List of fee tiers for each hop
        - is_direct: False (indicates routing required)
        - total_fee_pct: Approximate total fee percentage

    Returns None if no route found.
    """
    # Don't route if same token
    if token0_symbol == token1_symbol:
        return None

    # Check if direct pool exists
    if (token0_symbol, token1_symbol) in VALID_DIRECT_PAIRS:
        fee_tier = VALID_DIRECT_PAIRS[(token0_symbol, token1_symbol)]
        return {
            'path': [token0_symbol, token1_symbol],
            'fee_tiers': [fee_tier],
            'is_direct': True,
            'total_fee_pct': fee_tier / 10000 * 100
        }

    # Try routing through intermediaries (USDC, USDT)
    for intermediary in ROUTING_INTERMEDIARIES:
        # Don't route through self
        if intermediary == token0_symbol or intermediary == token1_symbol:
            continue

        # Check if both legs exist
        leg1 = (token0_symbol, intermediary)
        leg2 = (intermediary, token1_symbol)

        if leg1 in VALID_DIRECT_PAIRS and leg2 in VALID_DIRECT_PAIRS:
            fee1 = VALID_DIRECT_PAIRS[leg1]
            fee2 = VALID_DIRECT_PAIRS[leg2]

            return {
                'path': [token0_symbol, intermediary, token1_symbol],
                'fee_tiers': [fee1, fee2],
                'is_direct': False,
                'total_fee_pct': (fee1 / 10000 * 100) + (fee2 / 10000 * 100),
                'intermediary': intermediary
            }

    # No route found
    return None


def requires_routing(token0_symbol: str, token1_symbol: str) -> bool:
    """Check if a pair requires multi-hop routing (no direct pool)."""
    if (token0_symbol, token1_symbol) in VALID_DIRECT_PAIRS:
        return False

    # Check if routing is possible
    return find_routing_path(token0_symbol, token1_symbol) is not None


def get_routing_path(token0_symbol: str, token1_symbol: str) -> dict:
    """
    Get the routing path for a pair.

    Returns dict with path info, or None if not possible.
    Use this in API/UI to show users the routing path.
    """
    return find_routing_path(token0_symbol, token1_symbol)


# =============================================================================
# VALIDATION
# =============================================================================

def validate_configuration():
    """
    Validate the configuration for inconsistencies.
    Called on module import to catch errors early.
    """
    from token_whitelist import get_token

    errors = []

    # Check that all tokens in valid pairs exist in whitelist
    for (token0, token1) in VALID_DIRECT_PAIRS.keys():
        if not get_token(token0):
            errors.append(f"Token not in whitelist: {token0}")
        if not get_token(token1):
            errors.append(f"Token not in whitelist: {token1}")

    # Check for duplicate reverse pairs
    seen = set()
    for (token0, token1) in VALID_DIRECT_PAIRS.keys():
        pair_key = tuple(sorted([token0, token1]))
        if pair_key in seen:
            # This is OK - we intentionally have both directions
            pass
        seen.add(pair_key)

    if errors:
        print("⚠️  Valid pairs configuration errors:")
        for error in errors:
            print(f"   • {error}")

    return len(errors) == 0


# Run validation on import
if __name__ != "__main__":
    validate_configuration()


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("VALID SWAP PAIRS CONFIGURATION (WITH ROUTING)")
    print("="*80)

    direct_pairs = get_all_valid_pairs(include_routed=False)
    all_pairs = get_all_valid_pairs(include_routed=True)
    routed_pairs = [p for p in all_pairs if p[2] == 'routed']

    print(f"\n📊 Total unique pairs: {len(all_pairs)}")
    print(f"   • Direct pools: {len(direct_pairs)}")
    print(f"   • Routed pairs: {len(routed_pairs)}")
    print(f"📊 Total directional pairs: {len(VALID_DIRECT_PAIRS)}")
    print(f"📊 Tokens with USDC pairs: {len(get_tokens_with_usdc_pairs())}")

    print("\n✅ Direct Pools:")
    for token0, token1, fee in direct_pairs:
        fee_pct = fee / 10000 * 100
        print(f"   {token0} ↔ {token1} ({fee_pct:.2f}%)")

    print(f"\n🔀 Routed Pairs ({len(routed_pairs)}):")
    for token0, token1, _ in routed_pairs:
        route_info = get_routing_path(token0, token1)
        if route_info:
            path_str = ' → '.join(route_info['path'])
            print(f"   {token0} ↔ {token1}: {path_str} ({route_info['total_fee_pct']:.2f}% total)")

    print("\n🎯 Tokens with USDC Pairs:")
    print(f"   {', '.join(get_tokens_with_usdc_pairs())}")

    # Test some specific routes
    print("\n🧪 Testing Specific Routes:")
    test_pairs = [
        ('WBTC', 'WETH'),
        ('SAUCE', 'LINK'),
        ('HBAR', 'AVAX'),
        ('WETH', 'SAUCE'),
    ]

    for token0, token1 in test_pairs:
        route_info = get_routing_path(token0, token1)
        if route_info:
            if route_info['is_direct']:
                print(f"   ✅ {token0} → {token1}: Direct pool ({route_info['total_fee_pct']:.2f}%)")
            else:
                path_str = ' → '.join(route_info['path'])
                print(f"   🔀 {token0} → {token1}: {path_str} ({route_info['total_fee_pct']:.2f}%)")
        else:
            print(f"   ❌ {token0} → {token1}: No route found")

    # Test validation
    print("\n🔍 Running validation...")
    if validate_configuration():
        print("   ✅ Configuration valid!")
    else:
        print("   ❌ Configuration has errors!")
