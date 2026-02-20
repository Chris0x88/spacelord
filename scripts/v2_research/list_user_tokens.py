import os, requests
from dotenv import load_dotenv
load_dotenv()
acc = os.getenv("HEDERA_ACCOUNT_ID")
url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{acc}/tokens"
r = requests.get(url, params={"limit": 100})
data = r.json()
print(f"Balances for {acc}:")
for t in data.get("tokens", []):
    tid = t.get("token_id")
    bal_raw = t.get("balance", 0)
    decimals = t.get("decimals", 8)
    bal_readable = bal_raw / (10**decimals)
    # Fetch token symbol
    r_t = requests.get(f"https://mainnet-public.mirrornode.hedera.com/api/v1/tokens/{tid}")
    sym = r_t.json().get("symbol", "Unknown")
    print(f"  {tid} | {sym:<10} | {bal_readable:.6f}")
