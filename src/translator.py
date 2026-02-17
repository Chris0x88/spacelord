#!/usr/bin/env python3
"""
Pacman Translator - Natural Language to Structured Swap Request
===============================================================

SEPARATE from the agent. This is a dumb, replaceable layer that converts
human text into the structured format PacmanAgent expects.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict

# --- PATH RESOLUTION ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TOKENS_FILE = DATA_DIR / "tokens.json"
ALIASES_FILE = DATA_DIR / "aliases.json"

# Global Alias Map
ALIASES: Dict[str, str] = {}

def load_static_aliases():
    """Load manually curated nicknames from aliases.json."""
    if not ALIASES_FILE.exists():
        return
    try:
        with open(ALIASES_FILE) as f:
            data = json.load(f)
            ALIASES.update({k.lower(): v for k, v in data.items()})
    except Exception as e:
        print(f"Warning: Failed to load static aliases: {e}")

def load_dynamic_aliases():
    """
    Load discovered tokens from tokens.json and add them to ALIASES.
    """
    if not TOKENS_FILE.exists():
        return
        
    try:
        with open(TOKENS_FILE) as f:
            tokens = json.load(f)
            
        for canon, meta in tokens.items():
            token_id = meta.get("id")
            # We NO LONGER skip WHBAR, as it is a valid (though distinct) token.
                
            # 1. Add canonical name itself (e.g. "USDC")
            ALIASES[canon.lower()] = canon
            
            # 2. Add pool symbol (e.g. "usdc[hts]")
            sym = meta.get("symbol", "").lower()
            if sym and sym not in ALIASES:
                ALIASES[sym] = canon
                
            # 3. Add cleaned symbol (e.g. "usdc_hts" or just "usdc")
            # Replace [hts], -, [, ] with empty or underscore
            clean_sym = sym.replace("[hts]", "").replace("-", "_").replace("[", "").replace("]", "")
            if clean_sym and clean_sym not in ALIASES:
                ALIASES[clean_sym] = canon
                
            # 4. Add full descriptive name
            name = meta.get("name", "").lower()
            if name and name not in ALIASES:
                ALIASES[name] = canon
                
            # 5. Add direct ID resolution
            ALIASES[token_id] = canon
            
    except Exception as e:
        print(f"Warning: Failed to load dynamic tokens: {e}")

# Initialization
load_static_aliases()
load_dynamic_aliases()


def resolve_token(text: str) -> Optional[str]:
    """Resolve a token name/alias to canonical form."""
    clean = text.strip().lower()
    if clean in ALIASES:
        return ALIASES[clean]
    # Check if it matches a canonical key directly (case-insensitive)
    for k in ALIASES.values():
        if k.lower() == clean:
            return k
    return None


def translate(text: str) -> Optional[Dict]:
    """
    Parse natural language into a structured request.
    """
    text = text.strip().lower()
    if not text:
        return None

    # Intent Detection
    if any(w in text for w in ["balance", "wallet", "assets", "how much", "portfolio", "holdings"]):
        return {"intent": "balance"}
    if any(w in text for w in ["history", "transactions", "tx", "activity", "recently"]):
        return {"intent": "history"}
    if any(w in text for w in ["list", "tokens", "show tokens", "discovery"]):
        return {"intent": "tokens"}

    # pattern_amount: matches optional currency symbol followed by float
    pattern_amount = r"[\$£]?((?:\d+(?:\.\d*)?|\.\d+))"

    # Pattern 1: "swap AMOUNT TOKEN for TOKEN"
    m = re.match(
        fr"(?:swap|trade|exchange|convert|sell)\s+"
        fr"{pattern_amount}\s+"
        r"(.+?)\s+"
        r"(?:for|to|into)\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        amount = float(m.group(1))
        from_token = resolve_token(m.group(2))
        to_token = resolve_token(m.group(3))
        if from_token and to_token:
            return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_in"}

    # Pattern 2: "swap TOKEN for AMOUNT TOKEN"
    m = re.match(
        fr"(?:swap|trade|exchange|convert)\s+"
        r"(.+?)\s+"
        r"(?:for|to|into|to\s+get)\s+"
        fr"{pattern_amount}\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        from_token = resolve_token(m.group(1).replace("with", "").strip())
        amount = float(m.group(2))
        to_token = resolve_token(m.group(3))
        if from_token and to_token:
            return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_out"}

    # Pattern 3: "buy AMOUNT TOKEN with TOKEN"
    m = re.match(
        fr"(?:buy|purchase|get|receive)\s+"
        fr"(?:exactly\s+)?{pattern_amount}\s+"
        r"(.+?)\s+"
        r"(?:with|using|from|by)\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        amount = float(m.group(1))
        to_token = resolve_token(m.group(2))
        from_token = resolve_token(m.group(3))
        if from_token and to_token:
            return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_out"}

    # Pattern 5: "swap TOKEN for TOKEN" (No amount)
    m = re.match(
        r"(?:swap|trade|exchange|convert)\s+"
        r"(.+?)\s+"
        r"(?:for|to|into)\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        from_token = resolve_token(m.group(1))
        to_token = resolve_token(m.group(2))
        if from_token and to_token:
            return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": 1.0, "mode": "exact_in"}

    return None

if __name__ == "__main__":
    pass
