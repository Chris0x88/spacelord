import requests
import json
import sys

def pull_tx_data(tx_hash):
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash
        
    print(f"Fetching contract result for: {tx_hash}")
    
    # URL for Mirror Node contract result data
    url = f"https://mainnet.mirrornode.hedera.com/api/v1/contracts/results/{tx_hash}"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            # Try regular transaction endpoint as fallback
            tx_url = f"https://mainnet.mirrornode.hedera.com/api/v1/transactions/{tx_hash}"
            print(f"Trying transaction endpoint: {tx_url}")
            response = requests.get(tx_url)
            if response.status_code != 200:
                print(f"Fallback also failed with {response.status_code}")
                return
            
        data = response.json()
        print(json.dumps(data, indent=2))
        
        # Extract revert reason if present
        if "error_message" in data and data["error_message"]:
            print(f"\nError Message: {data['error_message']}")
        elif "result" in data:
            print(f"\nResult: {data['result']}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    hash_to_check = "f40ec4e6f416b109d277c933eb059a9528c518c48e2cd5dcb7e7898defd8c062"
    if len(sys.argv) > 1:
        hash_to_check = sys.argv[1]
    pull_tx_data(hash_to_check)
