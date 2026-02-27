import sys
from web3 import Web3
from src.config import PacmanConfig
from lib.saucerswap import SaucerSwapV2

config = PacmanConfig.from_env()
w3 = Web3(Web3.HTTPProvider(config.rpc_url))
ss2 = SaucerSwapV2(w3, network="mainnet", private_key=config.private_key.reveal())

# HBAR to USDC
hbar_id = "0.0.1456986" # WHBAR
usdc_id = "0.0.456858"

print("Balance:", w3.eth.get_balance(ss2.eoa) / 10**18)

try:
    print("Sim 1 HBAR...")
    res1 = ss2.swap_exact_input_multicall(hbar_id, usdc_id, int(1 * 1e8), 50000, input_is_native=True, fee=1500, dry_run=True)
    print("Success 1:", res1)
except Exception as e:
    print("Fail 1:", e)

try:
    print("\nSim 5 HBAR...")
    res5 = ss2.swap_exact_input_multicall(hbar_id, usdc_id, int(5 * 1e8), 500000, input_is_native=True, fee=1500, dry_run=True)
    print("Success 5:", res5)
except Exception as e:
    print("Fail 5:", e)

