#!/usr/bin/env python3
"""
Pacman Cross-Check Suite
========================
Tests the AI interpretation logic against a suite of known variants.
Ensures intent, tokens, amounts, and direction (exact input/output) are correct.
"""

import sys
import os
from pacman_chat_v4 import PacmanBrainInterface, TOKEN_METADATA

def run_crosscheck():
    print("🔍 Starting Pacman AI Cross-Check Suite...")
    print("="*60)
    
    # Initialize Brain (Mainnet paths as per pacman_chat_v4)
    PACMAN_DIR = '/Users/cdi/Documents/Github/pacman'
    brain = PacmanBrainInterface(f"{PACMAN_DIR}/model/pacman_v1_brain")
    
    test_cases = [
        # Standard Swaps
        {
            "input": "swap 10 hbar for usdc",
            "expected": {"intent": "swap", "from": "HBAR", "to": "USDC", "amount": 10.0, "exact_input": True}
        },
        {
            "input": "trade 0.005 bitcoin for ethereum",
            "expected": {"intent": "swap", "from": "WBTC", "to": "WETH", "amount": 0.005, "exact_input": True}
        },
        {
            "input": "buy exactly 50 dollars of bitcoin using ethereum",
            "expected": {"intent": "swap", "from": "WETH", "to": "WBTC", "amount": 50.0, "exact_input": False}
        },
        {
            "input": "flip my wrapped hbar into dollars",
            "expected": {"intent": "swap", "from": "WHBAR", "to": "USDC", "amount": 1.0, "exact_input": True}
        },
        # Exact Output (Reverse)
        {
            "input": "swap wBTC for $1.00 USDC",
            "expected": {"intent": "swap", "from": "WBTC", "to": "USDC", "amount": 1.0, "exact_input": False}
        },
        {
            "input": "get 100 dollars using bitcoin",
            "expected": {"intent": "swap", "from": "WBTC", "to": "USDC", "amount": 100.0, "exact_input": False}
        },
        # Balance / Wallet
        {
            "input": "how much money do i have",
            "expected": {"intent": "balance"}
        },
        {
            "input": "check wallet",
            "expected": {"intent": "balance"}
        },
        # History
        {
            "input": "show my last 10 transactions",
            "expected": {"intent": "history"}
        },
        {
            "input": "tx history",
            "expected": {"intent": "history"}
        },
        # Error Cases (Graceful Handling)
        {
            "input": "swap 10 hbar for gib",
            "expected": {"intent": "swap", "from": "HBAR", "to": None}
        },
        {
            "input": "hello pacman",
            "expected": {"intent": "swap", "from": None, "to": None}
        }
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        inp = case["input"]
        exp = case["expected"]
        
        intent, from_t, to_t, amount, is_exact = brain.inference(inp)
        
        result = {
            "intent": intent,
            "from": from_t,
            "to": to_t,
            "amount": amount,
            "exact_input": is_exact
        }
        
        # Determine if pass
        is_pass = True
        for key, val in exp.items():
            if result.get(key) != val:
                is_pass = False
                break
        
        status = "✅ PASS" if is_pass else "❌ FAIL"
        if is_pass: passed += 1
        else: failed += 1
        
        print(f"{status} | Input: \"{inp}\"")
        if not is_pass:
            print(f"      Expected: {exp}")
            print(f"      Actual:   {result}")
            
    print("="*60)
    print(f"📊 Results: {passed} Passed, {failed} Failed")
    
    if failed == 0:
        print("🚀 AI logic is robust and verified!")
    else:
        print("⚠️  Logic refinement needed. See failures above.")

if __name__ == "__main__":
    run_crosscheck()
