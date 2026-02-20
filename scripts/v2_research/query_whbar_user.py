import os, requests
from dotenv import load_dotenv
load_dotenv()
acc = os.getenv("HEDERA_ACCOUNT_ID")
url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{acc}/tokens"
r = requests.get(url, params={"token.id": "0.0.1456986"})
print("User WHBAR Balance:")
print(r.json())
