import requests

url = "https://mainnet-public.mirrornode.hedera.com/api/v1/tokens"
params = {"limit": 100, "type": "NON_FUNGIBLE_UNIQUE"}
r = requests.get(url, params=params)
data = r.json()
for t in data.get("tokens", []):
    if "SaucerSwap" in t.get("name", ""):
        print(t)
