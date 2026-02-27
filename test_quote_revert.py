import os
import sys
from web3 import Web3
from src.config import PacmanConfig
from lib.saucerswap import SaucerSwapV2

config = PacmanConfig.from_env()
w3 = Web3(Web3.HTTPProvider(config.rpc_url))
ss2 = SaucerSwapV2(w3, network="mainnet")

# HBAR to USDC
hbar_id = "0.0.1456986" # WHBAR
usdc_id = "0.0.456858"

print("Quote 1 HBAR...")
try:
    q1 = ss2.get_quote_single(hbar_id, usdc_id, amount_in=int(1 * 1e8), fee=1500)
    print("Success:", q1['amount_out'])
except Exception as e:
    print("Failed config 1:", e)

print("\nQuote 5 HBAR...")
try:
    q5 = ss2.get_quote_single(hbar_id, usdc_id, amount_in=int(5 * 1e8), fee=1500)
    print("Success:", q5['amount_out'])
except Exception as e:
    print("Failed config 5:", e)
