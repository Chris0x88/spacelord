import requests

def resolve_saucerswap(symbol):
    try:
        r = requests.get("https://api.saucerswap.finance/tokens", timeout=5)
        if r.status_code == 200:
            tokens = r.json()
            for t in tokens:
                if t.get("symbol", "").upper() == symbol.upper():
                    return t.get("id"), t.get("decimals")
    except Exception as e:
        print("Error:", e)
    return None, 8

print("PACK -> ", resolve_saucerswap("PACK"))
print("BONZO -> ", resolve_saucerswap("BONZO"))
