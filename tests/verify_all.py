import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.controller import SpaceLordController
from src.translator import translate

# Force Simulation Mode
os.environ["SPACELORD_SIMULATE"] = "true"
os.environ["SPACELORD_CONFIRM"] = "false"

# Load token metadata for human-readable names and decimals
TOKEN_META = {}
try:
    with open("data/tokens.json") as f:
        TOKEN_META = json.load(f)
except Exception:
    pass

# Load aliases for reverse lookup
ALIASES = {}
try:
    with open("data/aliases.json") as f:
        ALIASES = json.load(f)
except Exception:
    pass


def token_name(token_id: str) -> str:
    """Resolve token ID to human-readable name."""
    if token_id in ("0.0.0", "HBAR"):
        return "HBAR"
    meta = TOKEN_META.get(token_id, {})
    if meta:
        return meta.get("symbol", token_id)
    # Reverse lookup from aliases
    for alias, tid in ALIASES.items():
        if tid == token_id:
            return alias.upper()
    return token_id


def token_decimals(token_id: str) -> int:
    """Get decimals for a token ID."""
    if token_id in ("0.0.0", "HBAR"):
        return 8
    meta = TOKEN_META.get(token_id, {})
    return meta.get("decimals", 8)


def fmt_amount(raw: int, token_id: str) -> str:
    """Convert raw integer amount to human-readable string."""
    dec = token_decimals(token_id)
    readable = raw / (10 ** dec)
    name = token_name(token_id)
    if readable >= 1:
        return f"{readable:.4f} {name}"
    else:
        return f"{readable:.8f} {name}"


app = SpaceLordController()
print(f"Space Lord Test Suite (simulation mode)")
print(f"Account: {app.account_id} | Network: {app.network}")
print()

tests = [
    ("Native to HTS", "swap 1 hbar to USDC"),
    ("HTS to Native (Exact Out)", "swap USDC to 1 hbar"),
    ("Variant to Variant", "swap 1 USDC to USDC[hts]"),
    ("Variant to Variant (Reverse)", "swap 5 USDC[hts] for USDC"),
    ("Cross-Token (Exact Out)", "swap HTS-WBTC to 1 USDC"),
    ("Flags before command", "--yes --json swap 10 hbar for usdc"),
    ("Flags after command (defensive)", "swap 10 hbar for usdc --yes --json"),
]

passed = 0
failed = 0

for name, cmd in tests:
    print(f"  {name}")
    print(f"  $ {cmd}")

    req = translate(cmd)
    if not req:
        print(f"  FAIL: Could not parse command\n")
        failed += 1
        continue

    from_id = req["from_token"]
    to_id = req["to_token"]
    from_name = token_name(from_id)
    to_name = token_name(to_id)

    try:
        res = app.swap(
            from_token=from_id,
            to_token=to_id,
            amount=req["amount"],
            mode=req["mode"]
        )
        if res.success:
            sent = fmt_amount(res.amount_in_raw, from_id)
            received = fmt_amount(res.amount_out_raw, to_id)
            print(f"  PASS: {sent} -> {received}")
            if res.gas_cost_usd > 0:
                print(f"        Gas: ${res.gas_cost_usd:.4f} | Rate: {res.effective_rate:.6f}")
            passed += 1
        else:
            print(f"  FAIL: {res.error}")
            failed += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        failed += 1
    print()

print(f"--- {passed}/{passed + failed} tests passed ---")
if failed > 0:
    sys.exit(1)
