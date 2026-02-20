import os, requests
from dotenv import load_dotenv
load_dotenv()
acc = os.getenv("HEDERA_ACCOUNT_ID")
# Position Manager
spender = "0.0.4053945"
url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{acc}/allowances/tokens"
r = requests.get(url)
data = r.json()
for a in data.get("allowances", []):
    if a.get("spender") == spender:
        print(a)
    elif a.get("token_id") == "0.0.456858":
        print("USDC allowance to", a.get("spender"), ":", a.get("amount"))
print("Done")
