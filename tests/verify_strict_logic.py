#!/usr/bin/env python3
import sys
from pacman_app import PacmanApp
from pacman_logger import set_verbose

def test_strict_logic():
    print("--- Testing Strict Logic Separation ---")
    set_verbose(False)
    app = PacmanApp()
    
    # 1. Test Strict Convert (Should Succeed)
    print("\n[TEST 1] Convert HTS-WBTC -> WBTC_LZ (Should SUCCEED)")
    route = app.get_wrap_route("WBTC_HTS", "WBTC_LZ", 100)
    if route:
        print(f"PASS: Route found: {route.explain().splitlines()[0]}")
    else:
        print("FAIL: Route not found")

    # 2. Test Strict Convert (Should Fail)
    print("\n[TEST 2] Convert USDC -> WBTC_LZ (Should FAIL)")
    route = app.get_wrap_route("USDC", "WBTC_LZ", 100)
    if not route:
        print("PASS: Route correctly not found (Strict Mode Enforced)")
    else:
        print(f"FAIL: Logic Error! Route found: {route.explain()}")

    # 3. Test Smart Swap (Should Succeed via Graph)
    print("\n[TEST 3] Swap USDC -> WBTC_LZ (Should SUCCEED)")
    route = app.get_route("USDC", "WBTC_LZ", 100)
    if route:
        print(f"PASS: Route found via Smart Swap: {route.explain().splitlines()[0]}")
    else:
        print("FAIL: Smart Swap failed to find route")

    # 4. Test Smart Swap (Should use Direct Wrap if efficient)
    print("\n[TEST 4] Swap WBTC_HTS -> WBTC_LZ (Should SUCCEED via Direct Wrap optimization)")
    route = app.get_route("WBTC_HTS", "WBTC_LZ", 100)
    if route and route.total_fee_percent == 0:
        print("PASS: Smart Swap used Direct Wrap (0% fee)")
    else:
        print(f"FAIL: Smart Swap did not optimize? Route: {route}")

if __name__ == "__main__":
    test_strict_logic()
