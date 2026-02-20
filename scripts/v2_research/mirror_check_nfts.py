import sys, os, requests
from dotenv import load_dotenv
load_dotenv()
acc = os.getenv("HEDERA_ACCOUNT_ID")
url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/contracts/results/f63dd5e699130444821b2d58bcb4bd89f71702482ad7921468c793985bbaf27b"
print(f"URL: {url}")
r = requests.get(url)
print(r.status_code)
print(r.json())
