import requests

url = "https://mainnet-public.mirrornode.hedera.com/api/v1/contracts/0.0.4053945/results"
r = requests.get(url, params={"limit": 20, "order": "desc"})
for tx in r.json().get("results", []):
    if tx.get("result") == "SUCCESS":
        tx_hash = tx.get("hash")
        print("Success TX:", tx_hash)
        tx_url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/transactions/{tx_hash}"
        tx_r = requests.get(tx_url)
        if tx_r.status_code == 200:
            tx_data = tx_r.json()
            for t in tx_data.get("transactions", []):
                for nft in t.get("nft_transfers", []):
                    # We are looking for the token_id of the NFT
                    print("  Found NFT Token ID:", nft.get("token_id"))
                    break
        break
