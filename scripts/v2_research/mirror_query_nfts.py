import sys, os, requests
from dotenv import load_dotenv
load_dotenv()
acc = os.getenv("HEDERA_ACCOUNT_ID")
url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{acc}/nfts?token.id=0.0.4054027"
print(url)
r = requests.get(url)
print(r.status_code)
print(r.json())
