#!/usr/bin/env python3
"""
Pacman Translator - Natural Language to Structured Swap Request
===============================================================

SEPARATE from the agent. This is a dumb, replaceable layer that converts
human text into the structured format PacmanAgent expects.

Swap this file for an LLM-powered version, a voice parser, a Telegram bot
parser - the agent doesn't care. It just needs:
    {from_token, to_token, amount, mode}

Usage:
    from pacman_translator import translate

    request = translate("swap 1 USDC for bitcoin")
    # -> {"from_token": "USDC", "to_token": "WBTC_HTS", "amount": 1.0, "mode": "exact_in"}

    request = translate("buy 0.001 BTC with USDC")
    # -> {"from_token": "USDC", "to_token": "WBTC_HTS", "amount": 0.001, "mode": "exact_out"}
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict

# --- PATH RESOLUTION ---
# WHY: We use absolute paths to ensure the translator can find data regardless
# of where the user runs the 'pacman' command from.
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
    
    WHY: This ensures that even if a token isn't in aliases.json, 
    the user can still use its Symbol or Name as a valid alias.
    """
    if not TOKENS_FILE.exists():
        return
        
    try:
        with open(TOKENS_FILE) as f:
            tokens = json.load(f)
            
        for canon, meta in tokens.items():
            token_id = meta.get("id")
            # Skip internal WHBAR (0.0.1456986) to keep aliases focused on logic
            if token_id == "0.0.1456986": 
                continue
                
            # 1. Add canonical name itself (e.g. "USDC")
            ALIASES[canon.lower()] = canon
            
            # 2. Add pool symbol (e.g. "usdc[hts]")
            sym = meta.get("symbol", "").lower()
            if sym and sym not in ALIASES:
                ALIASES[sym] = canon
                
            # 3. Add cleaned symbol (e.g. "usdc_hts" or just "usdc")
            clean_sym = sym.replace("[hts]", "").replace("-", "_")
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
    # Direct match
    if clean in ALIASES:
        return ALIASES[clean]
    # Try uppercase direct (already canonical)
    upper = text.strip().upper()
    if upper in {v for v in ALIASES.values()}:
        return upper
    return None


def translate(text: str) -> Optional[Dict]:
    """
    Parse natural language into a structured request.
    
    Supported Swaps:
        "swap 1 USDC for WBTC"       -> exact_in
        "swap USDC for 0.001 WBTC"   -> exact_out
        "buy 0.001 BTC with USDC"    -> exact_out
        "sell 10 HBAR for USDC"      -> exact_in
        "convert 5 SAUCE to HBAR"    -> exact_in
        
    Supported Intents:
        "what is my balance?"        -> intent: balance
        "show my history"            -> intent: history
        "list tokens"                -> intent: tokens

    Returns:
        {"intent": str, "from_token": str, "to_token": str, "amount": float, "mode": str}
        or {"intent": "balance" / "history" / "tokens"}
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

    # Patterns for extraction
    # pattern_amount: matches optional currency symbol followed by float (supports .5 and 0.5)
    pattern_amount = r"[\$£]?((?:\d+(?:\.\d*)?|\.\d+))"

    # Pattern 1: "swap/trade/exchange/convert AMOUNT TOKEN for/to/into TOKEN" (Exact In)
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
            intent_val = "convert" if "convert" in text else "swap"
            return {
                "intent": intent_val,
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "mode": "exact_in",
            }

    # Pattern 2: "swap TOKEN for AMOUNT TOKEN" (Exact Out)
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
            return {
                "intent": "swap",
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "mode": "exact_out",
            }

    # Pattern 3: "buy AMOUNT TOKEN with TOKEN" (Exact Out)
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
            return {
                "intent": "swap",
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "mode": "exact_out",
            }

    # Pattern 4: "buy TOKEN with AMOUNT TOKEN" (Exact In)
    m = re.match(
        fr"(?:buy|purchase|get)\s+"
        r"(.+?)\s+"
        r"(?:with|using|from)\s+"
        fr"{pattern_amount}\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        to_token = resolve_token(m.group(1))
        amount = float(m.group(2))
        from_token = resolve_token(m.group(3))
        if from_token and to_token:
            # If the user used 'convert', we use a special intent
            intent_val = "convert" if "convert" in text else "swap"
            return {
                "intent": intent_val,
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "mode": "exact_in",
            }

    return None


# ---------------------------------------------------------------------------
# CLI / interactive
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        "swap 1 USDC for WBTC",
        "swap 10 hbar to bitcoin",
        "buy 0.001 BTC with USDC",
        "buy bitcoin with 5 dollars",
        "convert 100 SAUCE to HBAR",
        "sell 50 HBAR for USDC",
        "swap USDC for 0.001 bitcoin",
        "trade 1 USDC for ethereum",
    ]

    print("Pacman Translator - Test Suite")
    print("=" * 60)
    for text in test_cases:
        result = translate(text)
        if result:
            print(f'  "{text}"')
            print(f"    -> {result['from_token']} -> {result['to_token']}, "
                  f"{result['amount']} ({result['mode']})")
        else:
            print(f'  "{text}" -> FAILED TO PARSE')
        print()
