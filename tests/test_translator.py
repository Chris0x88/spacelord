import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.translator import translate

def test():
    test_cases = [
        ("swap 10 HBAR for USDC", {"intent": "swap", "amount": 10.0, "from_token": "0.0.0", "to_token": "0.0.456858", "mode": "exact_in"}),
        ("swap HBAR for 10 USDC", {"intent": "swap", "amount": 10.0, "from_token": "0.0.0", "to_token": "0.0.456858", "mode": "exact_out"}),
        ("swap HTS-WBTC to 1 USDC", {"intent": "swap", "amount": 1.0, "from_token": "0.0.10082597", "to_token": "0.0.456858", "mode": "exact_out"}),
        ("buy 0.5 WBTC with USDC", {"intent": "swap", "amount": 0.5, "from_token": "0.0.456858", "to_token": "0.0.10082597", "mode": "exact_out"}),
        ("swap SAUCE for HBAR", {"intent": "swap", "amount": 1.0, "from_token": "0.0.731861", "to_token": "0.0.0", "mode": "exact_in"}),
    ]

    success = True
    for cmd, expected in test_cases:
        result = translate(cmd)
        
        # Check if basic fields match
        match = True
        for k, v in expected.items():
            if result.get(k) != v:
                match = False
                break
        
        if match:
             print(f"✅ PASS: '{cmd}'")
        else:
             print(f"❌ FAIL: '{cmd}'")
             print(f"   Expected: {expected}")
             print(f"   Actual:   {result}")
             success = False
    
    if success:
        print("\n✨ All tests passed!")
    else:
        sys.exit(1)

if __name__ == "__main__":
    test()
