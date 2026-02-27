import requests

def resolve_symbol(symbol):
    try:
        r = requests.get(f"https://mainnet-public.mirrornode.hedera.com/api/v1/tokens?symbol={symbol}&limit=10")
        if r.status_code == 200:
            tokens = r.json().get('tokens', [])
            # Find exact match with highest total supply (to weed out fake tokens)
            matches = [t for t in tokens if t.get('symbol', '').upper() == symbol.upper()]
            if matches:
                matches.sort(key=lambda x: int(x.get('total_supply', 0)), reverse=True)
                return matches[0]['token_id'], int(matches[0]['decimals'])
    except Exception as e:
        print("Error:", e)
    return None, 8

def get_decimals(token_id):
    try:
        r = requests.get(f"https://mainnet-public.mirrornode.hedera.com/api/v1/tokens/{token_id}")
        if r.status_code == 200:
            return int(r.json().get('decimals', 8))
    except:
        pass
    return 8

print("PACK -> ", resolve_symbol("PACK"))
print("BONZO -> ", resolve_symbol("BONZO"))
print("0.0.4794920 -> ", get_decimals("0.0.4794920"))
