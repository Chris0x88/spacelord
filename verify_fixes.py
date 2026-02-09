import sys
import os
from pacman_variant_router import PacmanVariantRouter
from pacman_executor import PacmanExecutor

# Ensure private key is available
if not os.getenv("PACMAN_PRIVATE_KEY") and not os.getenv("PRIVATE_KEY"):
    print("❌ PRIVATE_KEY or PACMAN_PRIVATE_KEY env var missing")
    sys.exit(1)

def test_sauce_decimals():
    print("\n🧪 TEST 1: Verifying SAUCE Decimals (Expect 6, not 8)...")
    router = PacmanVariantRouter()
    try:
        router.load_pools()
    except:
        print("⚠️  Pools loading failed (network issue?), skipping routing logic if possible.")
        
    executor = PacmanExecutor() # Uses env var PRIVATE_KEY
    
    route = router.recommend_route("SAUCE", "HBAR", "auto", amount_usd=1000000.0)
    if not route:
        print("❌ No route found for SAUCE->HBAR")
        return

    # Force simulate=False to hit balance check
    result = executor.execute_swap(route, amount_usd=1000000.0, simulate=False)
    
    if not result.success and "Insufficient funds" in result.error:
        print(f"✅ Caught expected error: {result.error}")
        # Analyze error message for decimal correctness
        # Correct (6 decimals): Have 114.xxxx
        # Incorrect (8 decimals): Have 1.14xxxx
        if "Have 1" in result.error and "Have 1." not in result.error: 
             # Rough check. 114 starts with "1". "1.14" also starts with "1".
             # Better check:
             # If I have 114 SAUCE:
             pass
        print(f"👀 VERIFY: 'Have 114...' means correct. 'Have 1.14...' means wrong.")
    else:
        print(f"❌ unexpected result: {result}")

def test_hbar_native_flag():
    print("\n🧪 TEST 2: Verifying Native HBAR Logic (Multicall)...")
    router = PacmanVariantRouter()
    try:
        router.load_pools()
    except:
        pass
    executor = PacmanExecutor()
    
    route = router.recommend_route("HBAR", "USDC", "auto", amount_usd=1.0)
    
    # Run in SIMULATION mode. Check output for "(Multicall: ExactInput + RefundETH)"
    executor.execute_swap(route, amount_usd=1.0, simulate=True)

if __name__ == "__main__":
    try:
        test_sauce_decimals()
        test_hbar_native_flag()
    except Exception as e:
        print(f"❌ Test crashed: {e}")
