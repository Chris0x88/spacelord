#!/usr/bin/env python3
"""
Simulate All Pairs
Iterates through the token registry and simulates swaps for all pairs
to identify coding or mismatch issues.
"""

import json
import logging
from pacman_variant_router import PacmanVariantRouter
from pacman_executor import PacmanExecutor

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    router = PacmanVariantRouter()
    try:
        router.load_pools()
    except Exception as e:
        logger.error(f"Failed to load pools: {e}")
        return

    executor = PacmanExecutor()
    
    with open("token_registry.json", "r") as f:
        registry = json.load(f)
    
    tokens = [t["symbol"] for t in registry]
    # Add HBAR manually as it's the native token
    tokens.append("HBAR")
    
    results = []
    
    print(f"\n🔍 Starting Full Simulation Audit ({len(tokens)} tokens)...")
    
    # We'll test HBAR against others and USDC against others
    test_token_groups = ["HBAR", "USDC", "SAUCE"]
    
    for from_sym in test_token_groups:
        for to_sym in tokens:
            if from_sym == to_sym:
                continue
                
            print(f"🧪 Testing: {from_sym} -> {to_sym}")
            try:
                # 1. Routing
                route = router.recommend_route(from_sym, to_sym, "auto", amount_usd=1.0)
                if not route:
                    print(f"   ⚠️  No route found.")
                    results.append({"pair": f"{from_sym}->{to_sym}", "status": "NO_ROUTE"})
                    continue
                
                # 2. Simulation
                res = executor.execute_swap(route, amount_usd=1.0, simulate=True)
                if res.success:
                    print(f"   ✅ SUCCESS (Simulated)")
                    results.append({"pair": f"{from_sym}->{to_sym}", "status": "OK"})
                else:
                    print(f"   ❌ FAILED: {res.error}")
                    results.append({"pair": f"{from_sym}->{to_sym}", "status": "FAIL", "error": res.error})
                    
            except Exception as e:
                print(f"   💥 CRASHED: {e}")
                results.append({"pair": f"{from_sym}->{to_sym}", "status": "CRASH", "error": str(e)})

    # Summary
    print("\n" + "="*40)
    print("📊 SIMULATION AUDIT SUMMARY")
    print("="*40)
    
    failed = [r for r in results if r["status"] in ["FAIL", "CRASH"]]
    no_route = [r for r in results if r["status"] == "NO_ROUTE"]
    
    print(f"Total Tested: {len(results)}")
    print(f"Successful:   {len(results) - len(failed) - len(no_route)}")
    print(f"Failed:       {len(failed)}")
    print(f"No Route:     {len(no_route)}")
    
    if failed:
        print("\n❌ FAILED PAIRS:")
        for f in failed:
            print(f"  - {f['pair']}: {f.get('error')}")

if __name__ == "__main__":
    main()

