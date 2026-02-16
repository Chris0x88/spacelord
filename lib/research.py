#!/usr/bin/env python3
import json
import sys
import os

def search_tokens(query, data_file="pacman_data_raw.json"):
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found.")
        return

    try:
        with open(data_file, 'r') as f:
            pools = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    query = query.lower()
    matches = {}

    for pool in pools:
        for key in ['tokenA', 'tokenB']:
            token = pool.get(key)
            if not token: continue
            
            # Search fields
            symbol = token.get('symbol', '').lower()
            name = token.get('name', '').lower()
            tid = token.get('id', '').lower()
            
            if query in symbol or query in name or query in tid:
                # Store unique by ID
                matches[token['id']] = {
                    "id": token['id'],
                    "symbol": token['symbol'],
                    "name": token['name']
                }

    if not matches:
        print(f"No tokens found matching '{query}'.")
    else:
        # Output as JSON list for the AI to parse easily
        results = list(matches.values())
        print(json.dumps(results))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 pacman_research.py <query>")
    else:
        search_tokens(sys.argv[1])
