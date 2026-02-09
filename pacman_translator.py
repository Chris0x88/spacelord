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

TOKENS_FILE = Path(__file__).parent / "tokens.json"

# Base legacy aliases to maintain compatibility and common naming
ALIASES = {
    "bitcoin": "WBTC_HTS",
    "btc": "WBTC_HTS",
    "wbtc": "WBTC_HTS",
    "eth": "WETH_HTS",
    "ether": "WETH_HTS",
    "ethereum": "WETH_HTS",
    "usd": "USDC",
    "dollar": "USDC",
    "dollars": "USDC",
    "bucks": "USDC",
    "stables": "USDC",
    "saucerswap": "SAUCE",
    "sauce": "SAUCE",
    "tune": "JAM",
    "tune.fm": "JAM",
    "diamond": "CARAT",
    "avalanche": "WAVAX_HTS",
    "avax": "WAVAX_HTS",
    "chainlink": "LINK_HTS",
    "link": "LINK_HTS",
    "headstarter": "HST",
    "calaxy": "CLXY",
    "bonzo": "BONZO",
    "pack": "PACK",
    "sats": "WBTC_HTS",
    "hbar": "HBAR",
    "hbarx": "HBARX",
    "xsauce": "XSAUCE",
    "wbtc_hts": "WBTC_HTS",
    "wbtc_erc20": "WBTC_ERC20",
    "weth_hts": "WETH_HTS",
    "weth_erc20": "WETH_ERC20",
    "hts_wbtc": "WBTC_HTS",
    "erc20_wbtc": "WBTC_ERC20",
    "hts_weth": "WETH_HTS",
    "erc20_weth": "WETH_ERC20",
}

def load_dynamic_aliases():
    """Load discovered tokens and add them to ALIASES."""
    if not TOKENS_FILE.exists():
        return
        
    try:
        with open(TOKENS_FILE) as f:
            tokens = json.load(f)
            
        for canon, meta in tokens.items():
            token_id = meta.get("id")
            if token_id == "0.0.1456986": # Skip WHBAR
                continue
                
            # 1. Add canonical name itself (lowercase)
            ALIASES[canon.lower()] = canon
            
            # 2. Add pool symbol (lowercase)
            sym = meta["symbol"].lower()
            if sym not in ALIASES:
                ALIASES[sym] = canon
            # Also stripped version (no [hts])
            clean_sym = sym.replace("[hts]", "").replace("-", "_")
            if clean_sym not in ALIASES:
                ALIASES[clean_sym] = canon
                
            # 3. Add full name (lowercase)
            name = meta["name"].lower()
            if name not in ALIASES:
                ALIASES[name] = canon
                
            # 4. Add token ID
            ALIASES[meta["id"]] = canon
    except Exception as e:
        print(f"Warning: Failed to load dynamic tokens: {e}")

# Load 'em up
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
