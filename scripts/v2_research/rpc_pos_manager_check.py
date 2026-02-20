import requests
url = "https://mainnet-public.mirrornode.hedera.com/api/v1/contracts/0.0.4053945"
r = requests.get(url)
print(r.json())
