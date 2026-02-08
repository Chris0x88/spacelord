#!/usr/bin/env python3
"""
Pacman Training Factory v2 - Advanced Intent Grammar
Generates 20,000+ examples including:
1. Reverse Targeting ("get $1 USDC using WBTC")
2. Target Fixed Amount ("swap WBTC for exactly 1.0 USDC")
3. Deep Precision (Satoshis/Gwei)
4. Casual Grammar ("flip my bitcoin into dollars")
"""

import json
import random
from pathlib import Path

PROVEN_LOGIC = {
    "tokens": {
        "USDC": {"id": "0.0.456858", "decimals": 6, "aliases": ["dollars", "usd", "cash", "bucks"]},
        "WBTC": {"id": "0.0.10082597", "decimals": 8, "aliases": ["bitcoin", "btc", "sats"]},
        "WETH": {"id": "0.0.9770617", "decimals": 8, "aliases": ["ethereum", "eth", "ether"]},
        "WHBAR": {"id": "0.0.1456986", "decimals": 8, "aliases": ["wrapped hbar", "whbar"]},
        "HBAR": {"id": "0.0.0", "decimals": 8, "aliases": ["hbar", "hedera", "native"]}
    }
}

# Advanced Templates
TEMPLATES = [
    # Standard Forward
    "{verb} {amount} {from_t} for {to_t}",
    # Reverse Targeting (The "I want X of that" logic)
    "get {amount} {to_t} using {from_t}",
    "swap {from_t} for exactly ${amount} {to_t}",
    "i need {amount} {to_t} from my {from_t}",
    "exchange {from_t} to receive {amount} {to_t}",
    # Casual / Slang
    "flip {amount} {from_t} into {to_t}",
    "move {amount} {from_t} to {to_t}",
    # Deep Precision
    "trade 0.0000{small_amt} {from_t} for {to_t}"
]

def generate_v2_dataset(count=20000):
    dataset = []
    token_keys = list(PROVEN_LOGIC["tokens"].keys())
    
    for i in range(count):
        from_key = random.choice(token_keys)
        to_key = random.choice([t for t in token_keys if t != from_key])
        
        # Randomly choose alias or symbol
        from_t = random.choice([from_key] + PROVEN_LOGIC["tokens"][from_key]["aliases"])
        to_t = random.choice([to_key] + PROVEN_LOGIC["tokens"][to_key]["aliases"])
        
        amount = round(random.uniform(0.01, 1.0), 4)
        small_amt = random.randint(100, 9999)
        template = random.choice(TEMPLATES)
        
        input_text = template.format(
            verb=random.choice(["swap", "trade", "buy", "sell"]),
            amount=amount,
            small_amt=small_amt,
            from_t=from_t,
            to_t=to_t
        )
        
        dataset.append({
            "instruction": input_text,
            "intent": "swap",
            "params": {
                "token_in": from_key,
                "token_out": to_key,
                "amount": amount,
                "is_reverse": ("get" in input_text or "receive" in input_text or "need" in input_text)
            }
        })
    
    # 2. Add Balance Intents
    bal_templates = [
        "how much money do i have",
        "show my balances",
        "what is my portfolio value",
        "wallet status",
        "check my assets",
        "bollinger bands check balance", # Random noise
        "account overview",
        "show me the money"
    ]
    for _ in range(count // 10):
        dataset.append({
            "instruction": random.choice(bal_templates),
            "intent": "balance",
            "params": {}
        })

    # 3. Add History Intents
    history_templates = [
        "show my recent transactions",
        "last 10 txs",
        "history",
        "what did i do recently",
        "show activity",
        "transaction logs",
        "recent operations"
    ]
    for _ in range(count // 10):
        dataset.append({
            "instruction": random.choice(history_templates),
            "intent": "history",
            "params": {}
        })
        
    random.shuffle(dataset)
    return dataset

if __name__ == "__main__":
    print("🏭 Factory v2: Generating 20,000 deep-grammar examples...")
    data = generate_v2_dataset(20000)
    
    output_path = Path("/Users/cdi/Documents/Github/pacman/training_data/brain_v2_set.jsonl")
    with open(output_path, "w") as f:
        for entry in data:
            f.write(json.dumps(entry) + "\n")
            
    print(f"✅ Created Brain v2 dataset at: {output_path}")
