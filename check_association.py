import requests
import json

def check_association(account_id, token_id):
    print(f"Checking association for Account: {account_id}, Token: {token_id}")
    
    # URL for Mirror Node account tokens
    url = f"https://mainnet.mirrornode.hedera.com/api/v1/accounts/{account_id}/tokens?token.id={token_id}"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return
            
        data = response.json()
        print(json.dumps(data, indent=2))
        
        if "tokens" in data and len(data["tokens"]) > 0:
            token_data = data["tokens"][0]
            print(f"\nAssociation Status: FOUND")
            # print(f"Balance: {token_data.get('balance')}")
        else:
            print(f"\nAssociation Status: NOT FOUND")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    account = "0.0.8213379"
    tokens = ["0.0.10082597", "0.0.1055483"] # HTS and ERC20 versions
    for t in tokens:
        check_association(account, t)
