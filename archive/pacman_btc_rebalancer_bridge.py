#!/usr/bin/env python3
"""
Pacman using EXACT btc_rebalancer2 code
No modifications - just import and run.
"""

import os
import sys

# Add current dir to path for imports
sys.path.insert(0, '/Users/cdi/Documents/Github/pacman')

# Import the EXACT btc_rebalancer2 modules
from btc_rebalancer_swap_engine import SaucerSwapV2Engine, SwapResult
from v2_tokens import WHBAR_ID, DEFAULT_FEE

# Token definitions (from btc_rebalancer2)
USDC_ID = "0.0.456858"
WBTC_ID = "0.0.10082597"

def main():
    print("="*80)
    print("🚀 PACMAN using btc_rebalancer2's EXACT code")
    print("="*80)
    
    # Initialize using btc_rebalancer2's engine
    engine = SaucerSwapV2Engine()
    
    print(f"✅ Engine initialized")
    print(f"   Account: {engine.eoa}")
    
    # Execute swap using EXACT btc_rebalancer2 method
    # This is the exact same code that works in production
    
    print("\n🎯 Executing $1 USDC → WBTC using btc_rebalancer2 pattern...")
    
    result = engine.swap(
        token_in_id=USDC_ID,
        token_out_id=WBTC_ID,
        amount=1.0,
        decimals_in=6,
        decimals_out=8,
        fee=DEFAULT_FEE,
        slippage=0.01,
        is_exact_input=True
    )
    
    print("\n" + "="*80)
    if result.success:
        print(f"✅ SWAP SUCCESSFUL!")
        print(f"   TX Hash: {result.tx_hash}")
        print(f"   Amount In: {result.amount_in}")
        print(f"   Amount Out: {result.amount_out}")
        print(f"   Gas Used: {result.gas_used}")
    else:
        print(f"❌ SWAP FAILED")
        print(f"   Error: {result.error}")
    print("="*80)
    
    return 0 if result.success else 1

if __name__ == "__main__":
    exit(main())
