import requests

# The Position Manager contract
contract_id = "0.0.4053945"

# 1. Check if the contract is associated with any tokens (usually the one it mints)
url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{contract_id}/tokens"
r = requests.get(url)
print(f"Tokens associated with PositionManager {contract_id}:")
if r.status_code == 200:
    for t in r.json().get("tokens", []):
        print(f"  {t.get('token_id')}")

# 2. Check for any token where the treasury is the contract or a related address
# Use a broad search for V2 LP NFTs
url = "https://mainnet-public.mirrornode.hedera.com/api/v1/tokens"
params = {"limit": 100, "type": "NON_FUNGIBLE_UNIQUE"}
r = requests.get(url, params=params)
if r.status_code == 200:
    for t in r.json().get("tokens", []):
        if "SaucerSwap V2" in t.get("name", ""):
            print(f"Found V2 NFT: {t.get('token_id')} | Name: {t.get('name')}")
