import os
import json
from web3 import Web3
from dotenv import load_dotenv

def hedera_id_to_evm(hedera_id: str) -> str:
    parts = hedera_id.split(".")
    num = int(parts[2])
    return Web3.to_checksum_address(f"0x{num:040x}")

def test_approve():
    load_dotenv()
    rpc_url = os.getenv("RPC_URL", "https://mainnet.hashio.io/api")
    private_key = os.getenv("PACMAN_PRIVATE_KEY")
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    acct = w3.eth.account.from_key(private_key)
    eoa = acct.address
    lz_addr = hedera_id_to_evm("0.0.8213379")
    
    token_id = "0.0.10082597"
    spender_id = "0.0.9675688"
    
    token_addr = hedera_id_to_evm(token_id)
    spender_addr = hedera_id_to_evm(spender_id)
    
    abi = [
        {"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
    ]
    token_contract = w3.eth.contract(address=token_addr, abi=abi)
    
    print(f"Checking allowance for Alias ({eoa})...")
    all_alias = token_contract.functions.allowance(eoa, spender_addr).call()
    print(f"Allowance (Alias): {all_alias}")
    
    print(f"Checking allowance for LZ ({lz_addr})...")
    all_lz = token_contract.functions.allowance(lz_addr, spender_addr).call()
    print(f"Allowance (LZ):    {all_lz}")
    
    if all_alias > 0 or all_lz > 0:
        print("Spender is already approved!")
    else:
        print("No allowance found.")

if __name__ == "__main__":
    test_approve()
