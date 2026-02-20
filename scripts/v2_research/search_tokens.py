import requests

url = "https://mainnet-public.mirrornode.hedera.com/api/v1/tokens"
params = {"limit": 100, "type": "NON_FUNGIBLE_UNIQUE"}
r = requests.get(url, params=params)
data = r.json()
found = False
for t in data.get("tokens", []):
    if "SaucerSwap" in t.get("name", ""):
        print(f"Token: {t.get('token_id')} | Name: {t.get('name')} | Symbol: {t.get('symbol')}")
        found = True

if not found:
    print("No SaucerSwap NFTs found in first 100.")
    # Try next page
    next_url = data.get("links", {}).get("next")
    if next_url:
        r = requests.get(f"https://mainnet-public.mirrornode.hedera.com{next_url}")
        data = r.json()
        for t in data.get("tokens", []):
            if "SaucerSwap" in t.get("name", ""):
                print(f"Token: {t.get('token_id')} | Name: {t.get('name')} | Symbol: {t.get('symbol')}")
