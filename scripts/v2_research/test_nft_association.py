import sys, os
sys.path.insert(0, '.')
from src.config import PacmanConfig
from lib.saucerswap import SaucerSwapV2
from web3 import Web3

config = PacmanConfig.from_env()
w3 = Web3(Web3.HTTPProvider("https://mainnet.hashio.io/api"))
client = SaucerSwapV2(w3, config.network, config.private_key.reveal())
client.associate_token_native("0.0.4054027")
print("Done")
