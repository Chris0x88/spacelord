#!/usr/bin/env python3
import sys
from pacman_translator import translate, resolve_token
from pacman_agent import PacmanAgent

def verify():
    print("Verification: Token Discovery & Price Integration")
    print("=" * 60)
    
    # 1. GIB discovery
    print("\n1. Testing GIB Discovery")
    res = resolve_token("gib")
    if res == "GIB":
        print("  PASS: 'gib' resolved to 'GIB'")
    else:
        print(f"  FAIL: 'gib' resolved to {res}")
        
    res_alt = resolve_token("༼ つ ◕_◕ ༽つ")
    if res_alt == "GIB":
        print("  PASS: full name resolved to 'GIB'")
    else:
        print(f"  FAIL: full name resolved to {res_alt}")

    # 2. Translation
    print("\n2. Testing Translation for GIB")
    tx = translate("swap 1 USDC for GIB")
    if tx and tx["to_token"] == "GIB":
        print("  PASS: 'swap 1 USDC for GIB' parsed correctly")
    else:
        print(f"  FAIL: parse result: {tx}")

    # 3. Agent Explain with Prices
    print("\n3. Testing Agent Explain with Prices")
    agent = PacmanAgent()
    explanation = agent.explain("USDC", "GIB", 10.0)
    print(explanation)
    
    if "Est. Output:" in explanation and "($10.0" in explanation:
        print("\n  PASS: Explanation includes USD estimates")
    else:
        print("\n  FAIL: Explanation missing estimates or incorrect")
        
    # 4. WHBAR Blacklist check
    print("\n4. Testing WHBAR Blacklist")
    tokens = agent.tokens()
    if "WHBAR" not in tokens:
        print("  PASS: WHBAR not in tradeable tokens list")
    else:
        print("  FAIL: WHBAR FOUND in tradeable tokens list")
        
    res_whbar = resolve_token("0.0.1456986")
    if res_whbar is None:
        print("  PASS: WHBAR token ID does not resolve (blacklisted)")
    else:
        print(f"  FAIL: WHBAR token ID resolved to {res_whbar}")

if __name__ == "__main__":
    verify()
