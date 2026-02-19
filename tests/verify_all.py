import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.controller import PacmanController
from src.translator import translate

# Force Simulation Mode
os.environ["PACMAN_SIMULATE"] = "true"
os.environ["PACMAN_CONFIRM"] = "false"

app = PacmanController()
print(f"✅ PacmanController initialized for verification.")

tests = [
    ("Native to HTS", "swap 1 hbar to USDC"),
    ("HTS to Native (Exact Out)", "swap USDC to 1 hbar"),
    ("Variant to Variant", "swap 1 USDC to USDC[hts]"),
    ("Cross-Token (Exact Out)", "swap HTS-WBTC to 1 USDC")
]

for name, cmd in tests:
    print(f"\n{'='*40}")
    print(f"TEST: {name}")
    print(f"COMMAND: {cmd}")
    print('='*40)
    
    req = translate(cmd)
    if not req:
        print(f"❌ Translation failed for: {cmd}")
        continue
        
    try:
        res = app.swap(
            from_token=req["from_token"],
            to_token=req["to_token"],
            amount=req["amount"],
            mode=req["mode"]
        )
        if res.success:
            print(f"✅ SUCCESS: Sent {res.amount_in_raw} -> Received {res.amount_out_raw}")
            print(f"   Quoted: {res.quoted_rate:.6f} | Effective: {res.effective_rate:.6f}")
        else:
            print(f"❌ FAILED: {res.error}")
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")

print("\n--- Verification Complete ---")
