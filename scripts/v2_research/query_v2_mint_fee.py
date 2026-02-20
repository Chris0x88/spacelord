import os, requests, json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()
rpc_url = "https://mainnet.hashio.io/v1/ad9ec0ef05ac4311894be6f6" # Use a known working RPC or from env
# Actually I'll use the one from config if I can find it, but I'll just hardcode a public one for the script
w3 = Web3(Web3.HTTPProvider("https://mainnet.hashio.io/v1/ad9ec0ef05ac4311894be6f6"))

factory_id = "0.0.3946833"
pm_id = "0.0.4053945"

# Factory ABI with mintFee()
factory_abi = [{"inputs":[],"name":"mintFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

def hedera_id_to_evm(hedera_id: str) -> str:
    parts = hedera_id.split(".")
    num = int(parts[2])
    return Web3.to_checksum_address(f"0x{num:040x}")

factory_addr = hedera_id_to_evm(factory_id)
factory = w3.eth.contract(address=factory_addr, abi=factory_abi)

try:
    mint_fee_tinycent = factory.functions.mintFee().call()
    print(f"Mint Fee (Tinycent): {mint_fee_tinycent}")
except Exception as e:
    print(f"Failed to query mintFee from factory: {e}")
    mint_fee_tinycent = 0

# Check exchange rate
r = requests.get("https://mainnet-public.mirrornode.hedera.com/api/v1/network/exchangerate")
data = r.json()
curr = data.get("current_rate")
cent_eq = curr.get("cent_equivalent")
hbar_eq = curr.get("hbar_equivalent")
print(f"Exchange Rate: {cent_eq} cents / {hbar_eq} HBAR")

# tinybar = tinycent / (cent_eq / hbar_eq)
if mint_fee_tinycent > 0:
    tinybar = (mint_fee_tinycent * hbar_eq) // cent_eq
    print(f"Mint Fee (Tinybar): {tinybar}")
    print(f"Mint Fee (HBAR): {tinybar / 10**8}")
else:
    print("No mint fee found.")
