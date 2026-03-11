import json

with open("data/tokens.json") as f:
    old_tokens = json.load(f)

new_tokens = {}
new_aliases = {}

for sym, data in old_tokens.items():
    tid = data.get("id")
    if not tid:
        continue
    
    # If the token is already added to new_tokens, skip it (it's a duplicate or alias)
    # BUT we want to ensure we capture the *preferred* or *canonical* one.
    
    # Let's clean the data dict first
    is_alias = data.pop("alias_for", None) is not None
    # Remove preferred tag if it exists as we're standardising
    is_preferred = data.pop("preferred", False)
    
    if tid not in new_tokens:
        new_tokens[tid] = data
    else:
        # If the current one is preferred, or if the stored one has "[hts]" and this one doesn't (cleaner name usually preferred)
        # Actually, let's just stick to the first we find unless we see preferred.
        if is_preferred and not old_tokens.get(new_tokens[tid].get("symbol", ""), {}).get("preferred", False):
            # Swap them
            temp_symbol = new_tokens[tid]["symbol"]
            new_tokens[tid] = data
            new_aliases[temp_symbol.lower()] = tid
        else:
            new_aliases[sym.lower()] = tid

    # Also add the symbol itself as an alias for safety
    new_aliases[data["symbol"].lower()] = tid

# Load existing aliases and update them to use IDs instead of symbols
with open("data/aliases.json") as f:
    old_aliases = json.load(f)

# old_aliases map string -> string (symbol like WBTC_HTS)
# we need them to map string -> ID
for k, v in old_aliases.items():
    # Find the ID for the symbol v
    # It might be in old_tokens
    for sym, data in old_tokens.items():
        if sym == v or data.get("symbol") == v:
            new_aliases[k.lower()] = data["id"]
            break

# Dump the new files
with open("data/tokens.json", "w") as f:
    json.dump(new_tokens, f, indent=2)

with open("data/aliases.json", "w") as f:
    json.dump(new_aliases, f, indent=4)

print("Refactored tokens.json and aliases.json")
