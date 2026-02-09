#!/usr/bin/env python3
"""
Pacman Training Factory - Synthetic Data Generator
Generates 10,000+ training examples mapping natural language to proven 
execution signatures from our 3 successful live test swaps.
"""

import json
import random
from pathlib import Path

# Proven patterns from our 3 live tests
PROVEN_LOGIC = {
    "swap_engine": "btc_rebalancer_swap_engine.SaucerSwapV2Engine",
    "fee_bps": 1500,
    "slippage": 0.01,
    "confirmed_tokens": {
        "USDC": {"id": "0.0.456858", "decimals": 6},
        "WBTC": {"id": "0.0.10082597", "decimals": 8},
        "WETH": {"id": "0.0.9770617", "decimals": 8},
        "WHBAR": {"id": "0.0.1456986", "decimals": 8},
        "HBAR": {"id": "0.0.0", "decimals": 8}
    }
}

VERBS = ["swap", "trade", "exchange", "convert", "buy", "sell", "get", "move"]
TEMPLATES = [
    "{verb} {amount} {from_t} for {to_t}",
    "{verb} {from_t} to {to_t} amount {amount}",
    "can you {verb} {amount} {from_t} into {to_t}",
    "{amount} {from_t} {verb} to {to_t}",
    "i want to {verb} {amount} {from_t} and receive {to_t}",
    "{verb} {amount} {from_t} {to_t}"
]

def generate_dataset(count=10000):
    dataset = []
    tokens = list(PROVEN_LOGIC["confirmed_tokens"].keys())
    
    for i in range(count):
        # Pick random parameters
        verb = random.choice(VERBS)
        from_t = random.choice(tokens)
        to_t = random.choice([t for t in tokens if t != from_t])
        amount = round(random.uniform(0.1, 1.0), 2) # Stick to validated $1 limit
        template = random.choice(TEMPLATES)
        
        # Create input string
        input_text = template.format(verb=verb, amount=amount, from_t=from_t, to_t=to_t)
        
        # Generate the "Execution Signature" (The target for the AI)
        # This maps to the exact code that worked in btc_rebalancer_bridge
        execution_signature = {
            "method": "engine.swap",
            "args": {
                "token_in_id": PROVEN_LOGIC["confirmed_tokens"][from_t]["id"],
                "token_out_id": PROVEN_LOGIC["confirmed_tokens"][to_t]["id"],
                "amount": amount,
                "decimals_in": PROVEN_LOGIC["confirmed_tokens"][from_t]["decimals"],
                "decimals_out": PROVEN_LOGIC["confirmed_tokens"][to_t]["decimals"],
                "fee": PROVEN_LOGIC["fee_bps"],
                "slippage": PROVEN_LOGIC["slippage"]
            }
        }
        
        dataset.append({
            "instruction": input_text,
            "intent": "swap",
            "signature": execution_signature,
            "proven_pattern": True
        })
        
    return dataset

if __name__ == "__main__":
    print("🏭 Generating 10,000 synthetic training examples...")
    data = generate_dataset(10000)
    
    output_path = Path("/Users/cdi/Documents/Github/pacman/training_data/final_training_set.jsonl")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        for entry in data:
            f.write(json.dumps(entry) + "\n")
            
    print(f"✅ Created training set at: {output_path}")
    print("📈 Data coverage: All combinations of USDC, WBTC, WETH, WHBAR, HBAR")
