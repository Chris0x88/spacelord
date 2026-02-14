
from pacman_agent import PacmanAgent
import logging

# Disable excessive logging
logging.getLogger('pacman_agent').setLevel(logging.WARNING)

agent = PacmanAgent()

print("\n--- TEST 1: EXACT_OUT (Target: 0.80 USDC) ---")
print(agent.explain("SAUCE", "USDC", 0.80, mode="exact_out"))

print("\n--- TEST 2: EXACT_IN (Input: 100 SAUCE) ---")
print(agent.explain("SAUCE", "USDC", 100, mode="exact_in"))
