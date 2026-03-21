#!/usr/bin/env python3
"""
Pacman Translator - Natural Language to Intent
==============================================

Parses user commands into structured requests.
Supports swaps, price checks, balance checks, and history.
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
VARIANTS_FILE = DATA_DIR / "variants.json"

# Global Data
ALIASES: Dict[str, str] = {}

def load_static_aliases():
    """Load manually curated nicknames from aliases.json + built-in canonical defaults."""
    global ALIASES
    
    # Built-in canonical aliases — these MUST always resolve to absolute IDs
    CANONICAL = {
        "BITCOIN": "0.0.10082597", "BTC": "0.0.10082597",
        "ETHEREUM": "0.0.9770617", "ETH": "0.0.9770617",
        "DOLLAR": "0.0.456858", "USD": "0.0.456858", "STABLECOIN": "0.0.456858",
        "HEDERA": "0.0.0", "HBAR": "0.0.0",
    }
    ALIASES.update(CANONICAL)
    
    try:
        if ALIASES_FILE.exists():
            with open(ALIASES_FILE) as f:
                data = json.load(f)
                # User aliases override built-in (normalize to UPPERCASE)
                ALIASES.update({k.upper(): v for k, v in data.items()})
    except Exception:
        pass

def resolve_token(name: str) -> Optional[str]:
    """Resolve a nickname or symbol to its internal token ID (e.g. 0.0.10082597)."""
    if not name: return None
    
    # Normalize input: UPPERCASE
    clean = name.strip().upper()
    
    # 1. Direct Alias Match (checks aliases.json mappings which are now all IDs)
    if clean in ALIASES:
        return ALIASES[clean]
    
    # 2. Key Match in Tokens.json (e.g. if User actually passed 0.0.456858)
    try:
        with open(TOKENS_FILE) as f:
            t_data = json.load(f)
            if clean in t_data:
                return clean
            
            # 3. Symbol Match in Tokens.json
            for token_id, meta in t_data.items():
                sym = meta.get("symbol", "").upper()
                if sym == clean or sym.replace("[HTS]", "") == clean:
                    return token_id
    except Exception:
        pass
        
    return clean # Fallback to original normalized string

def strip_cli_flags(text: str) -> tuple:
    """Strip CLI flags (--flag or -f) from text, return (cleaned_text, flags_dict).

    Must be called BEFORE regex matching to prevent flags being captured
    into token names (e.g. 'usdc --yes --json' → to_token='usdc --yes --json').
    """
    words = text.split()
    clean_words = []
    flags = {}
    i = 0
    while i < len(words):
        word = words[i]
        if word.startswith("--"):
            flags[word.lstrip("-")] = True
        elif word.startswith("-") and len(word) == 2 and word[1].isalpha():
            flags[word.lstrip("-")] = True
        else:
            clean_words.append(word)
        i += 1
    return " ".join(clean_words), flags


def translate_command(text: str) -> Optional[dict]:
    """Main entry point for command interpretation."""
    if not text: return None

    # Strip ALL CLI flags before NLP parsing to prevent them from being
    # captured into token names by greedy regex patterns.
    # BUG-014: --yes/--json after destination token caused IndexError
    text_clean, flags = strip_cli_flags(text)
    t = text_clean.lower().strip()
    
    # Static Intents
    if t in ["balance", "wallet", "bal", "show balance"]:
        return {"intent": "balance"}
    if t in ["tokens", "list tokens", "supported tokens"]:
        return {"intent": "tokens"}
    if t in ["history", "show history", "records"]:
        return {"intent": "history"}
        
    # Pattern 1: Price Check ("price WBTC", "what is the price of HBAR")
    m = re.match(r"(?:price(?:\s+of)?|what(?:\s+is)?\s+the\s+price(?:\s+of)?)\s+(.+)", t)
    if m:
        token = resolve_token(m.group(1))
        return {"intent": "price", "token": token}

    # Pattern 1b: "swap all/max TOKEN to TOKEN" (Exact In, amount=-1 signals "use full balance")
    # e.g. "swap all USDC for HBAR", "sell max hbar for usdc"
    m = re.match(r"(?:swap|trade|exchange|convert|sell)\s+(?:all|max)\s+(.+?)\s+(?:for|to|into)\s+(.+)", t)
    if m:
        from_token = resolve_token(m.group(1))
        to_token = resolve_token(m.group(2))
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": -1, "mode": "exact_in", "flags": flags}

    # Pattern 2: "swap AMOUNT TOKEN to TOKEN" (Exact In)
    # e.g. "swap 100 hbar for usdc"
    m = re.match(r"(?:swap|trade|exchange|convert)\s+([\d\.]+)\s+(.+?)\s+(?:for|to|into)\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        from_token = resolve_token(m.group(2))
        to_token = resolve_token(m.group(3))
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_in", "flags": flags}

    # Pattern 3: "swap TOKEN to AMOUNT TOKEN" (Exact Out)
    # e.g. "swap hbar to 10 usdc"
    m = re.match(r"(?:swap|trade|exchange|convert)\s+(.+?)\s+(?:for|to|into)\s+([\d\.]+)\s+(.+)", t)
    if m:
        from_token = resolve_token(m.group(1))
        amount = float(m.group(2))
        to_token = resolve_token(m.group(3))
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_out", "flags": flags}

    # Pattern 4a: "buy AMOUNT TOKEN with TOKEN" (Exact Out)
    # e.g. "buy 1 wbtc with usdc"
    m = re.match(r"(?:buy|get|receive)\s+([\d\.]+)\s+(.+?)\s+with\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        to_token = resolve_token(m.group(2))
        from_token = resolve_token(m.group(3))
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_out", "flags": flags}

    # Pattern 4b: "buy AMOUNT TOKEN" (no source — default from USDC)
    # e.g. "buy 5 HBAR", "buy 0.001 BTC"
    m = re.match(r"(?:buy|get)\s+([\d\.]+)\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        to_token = resolve_token(m.group(2))
        from_token = resolve_token("USDC")
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_out", "flags": flags}

    # Pattern 4c: "sell AMOUNT TOKEN for TOKEN" (Exact In)
    # e.g. "sell 10 USDC for HBAR"
    m = re.match(r"sell\s+([\d\.]+)\s+(.+?)\s+(?:for|to|into)\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        from_token = resolve_token(m.group(2))
        to_token = resolve_token(m.group(3))
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_in", "flags": flags}

    # Pattern 4d: "sell AMOUNT TOKEN" (no destination — default to USDC)
    # e.g. "sell 10 HBAR", "sell 0.001 BTC"
    m = re.match(r"sell\s+([\d\.]+)\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        from_token = resolve_token(m.group(2))
        to_token = resolve_token("USDC")
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_in", "flags": flags}

    # Pattern 5: "swap TOKEN to TOKEN" (No amount -> Default 1.0)
    # e.g. "swap hbar for usdc"
    m = re.match(r"(?:swap|trade|exchange|convert)\s+(.+?)\s+(?:for|to|into)\s+(.+)", t)
    if m:
        from_token = resolve_token(m.group(1))
        to_token = resolve_token(m.group(2))
        # Ensure we didn't just match a previous pattern's fragment
        if from_token and to_token:
            return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": 1.0, "mode": "exact_in", "flags": flags}

    # Pattern 6: "send AMOUNT TOKEN to RECIPIENT"
    m = re.match(r"(?:send|transfer|give)\s+([\d\.]+)\s+(.+?)\s+to\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        token = resolve_token(m.group(2))
        recipient = m.group(3).strip()
        return {"intent": "send", "token": token, "amount": amount, "recipient": recipient}

    return None

translate = translate_command

# Load aliases on import
load_static_aliases()
