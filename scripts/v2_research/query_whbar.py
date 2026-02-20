import os, requests

url = "https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/0.0.4053945/tokens"
r = requests.get(url, params={"token.id": "0.0.1456986"})
print("Position Manager WHBAR Balance:")
print(r.json())

url2 = "https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/0.0.3946830/tokens" # Router
r2 = requests.get(url2, params={"token.id": "0.0.1456986"})
print("Router WHBAR Balance:")
print(r2.json())
