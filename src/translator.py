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
VARIANTS_FILE = DATA_DIR / "variants.json"

# Global Data
ALIASES: Dict[str, str] = {}

def load_static_aliases():
    """Load manually curated nicknames from aliases.json."""
    global ALIASES
    try:
        if ALIASES_FILE.exists():
            with open(ALIASES_FILE) as f:
                ALIASES.update(json.load(f))
    except Exception:
        pass

def resolve_token(name: str) -> Optional[str]:
    """Resolve a nickname or symbol to its internal token key (e.g. WBTC_HTS)."""
    if not name: return None
    
    clean = name.strip().upper()
    
    # 1. Direct Alias Match
    if clean in ALIASES:
        return ALIASES[clean]
    
    # 2. Key Match in Tokens.json
    try:
        with open(TOKENS_FILE) as f:
            t_data = json.load(f)
            if clean in t_data:
                return clean
            
            # 3. Symbol Match in Tokens.json
            for key, meta in t_data.items():
                if meta.get("symbol", "").upper() == clean:
                    return key
    except Exception:
        pass
        
    return clean # Fallback to original cleaned string

def translate_command(text: str) -> Optional[dict]:
    """Main entry point for command interpretation."""
    if not text: return None
    t = text.lower().strip()
    
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

    # Pattern 2: "swap AMOUNT TOKEN for TOKEN"
    m = re.match(r"(?:swap|trade|exchange|convert)\s+([\d\.]+)\s+(.+?)\s+(?:for|to|into)\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        from_token = resolve_token(m.group(2))
        to_token = resolve_token(m.group(3))
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_in"}

    # Pattern 3: "swap TOKEN for TOKEN" (No amount -> Default 1.0)
    m = re.match(r"(?:swap|trade|exchange|convert)\s+(.+?)\s+(?:for|to|into)\s+(.+)", t)
    if m:
        # Check if the first group starts with a number to avoid double matching
        if not re.match(r"^[\d\.]+\s+", m.group(1)):
            from_token = resolve_token(m.group(1))
            to_token = resolve_token(m.group(2))
            return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": 1.0, "mode": "exact_in"}

    # Pattern 4: "send AMOUNT TOKEN to RECIPIENT"
    m = re.match(r"(?:send|transfer|give)\s+([\d\.]+)\s+(.+?)\s+to\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        token = resolve_token(m.group(2))
        recipient = m.group(3).strip()
        return {"intent": "send", "token": token, "amount": amount, "recipient": recipient}

    # Pattern 5: "buy AMOUNT TOKEN with TOKEN" (Exact Out)
    m = re.match(r"(?:buy|get|receive)\s+([\d\.]+)\s+(.+?)\s+with\s+(.+)", t)
    if m:
        amount = float(m.group(1))
        to_token = resolve_token(m.group(2))
        from_token = resolve_token(m.group(3))
        return {"intent": "swap", "from_token": from_token, "to_token": to_token, "amount": amount, "mode": "exact_out"}

    return None

def load_dynamic_aliases():
    """Stub for dynamic alias loading."""
    pass

translate = translate_command

# Load aliases on import
load_static_aliases()
