from pacman_price_manager import price_manager
import json
import os

print(f"HBAR Price: {price_manager.get_hbar_price()}")
print(f"Prices Map Keys: {list(price_manager.prices.keys())[:5]}... (total {len(price_manager.prices)})")

if "0.0.1456986" in price_manager.prices:
    print(f"WHBAR Price: {price_manager.prices['0.0.1456986']}")
else:
    print("WHBAR (0.0.1456986) NOT in prices map")
