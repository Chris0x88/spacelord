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

import re
from typing import Optional, Dict

# Token aliases: maps casual names -> canonical agent token name
# Update this when you add new tokens to the route table
ALIASES = {
    # Stablecoins
    "usdc": "USDC",
    "usd": "USDC",
    "dollars": "USDC",
    "dollar": "USDC",
    "usd coin": "USDC",
    "usdc hts": "USDC_HTS",
    "usdt": "USDT_HTS",
    "tether": "USDT_HTS",
    "dai": "DAI_HTS",
    # HBAR ecosystem (WHBAR is routing-only, NOT tradeable)
    "hbarx": "HBARX",
    # Bitcoin
    "btc": "WBTC_HTS",
    "bitcoin": "WBTC_HTS",
    "wbtc": "WBTC_HTS",
    "wrapped bitcoin": "WBTC_HTS",
    "wbtc hts": "WBTC_HTS",
    "wbtc_hts": "WBTC_HTS",
    "hts-wbtc": "WBTC_HTS",
    "hts wbtc": "WBTC_HTS",
    "wbtc lz": "WBTC_LZ",
    "wbtc_lz": "WBTC_LZ",
    # Ethereum
    "eth": "WETH_HTS",
    "ether": "WETH_HTS",
    "ethereum": "WETH_HTS",
    "weth": "WETH_HTS",
    "wrapped ether": "WETH_HTS",
    "weth hts": "WETH_HTS",
    "weth_hts": "WETH_HTS",
    "weth lz": "WETH_LZ",
    "weth_lz": "WETH_LZ",
    # DeFi
    "sauce": "SAUCE",
    "saucerswap": "SAUCE",
    "xsauce": "XSAUCE",
    "karate": "KARATE",
    "dovu": "DOVU",
    "pack": "PACK",
    "grelf": "GRELF",
    "link": "LINK_HTS",
    "chainlink": "LINK_HTS",
    "avax": "WAVAX_HTS",
    "avalanche": "WAVAX_HTS",
    "qnt": "QNT_HTS",
    "quant": "QNT_HTS",
    "hchf": "HCHF",
    "bonzo": "BONZO",
    "hst": "HST",
    "headstarter": "HST",
    "clxy": "CLXY",
    "calaxy": "CLXY",
    "bnb": "WBNB_HTS",
    "davinci": "DAVINCI",
    "carat": "CARAT",
    "diamond": "CARAT",
    # Meme / community tokens
    "gib": "GIB",
    "jam": "JAM",
    "tune": "JAM",
    "tune.fm": "JAM",
    "steam": "STEAM",
}


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
    Parse natural language into a structured swap request.

    Supported patterns:
        "swap 1 USDC for WBTC"       -> exact_in
        "swap USDC for 0.001 WBTC"   -> exact_out
        "buy 0.001 BTC with USDC"    -> exact_out
        "sell 10 HBAR for USDC"      -> exact_in
        "convert 5 SAUCE to HBAR"    -> exact_in

    Returns:
        {"from_token": str, "to_token": str, "amount": float, "mode": str}
        or None if unparseable
    """
    text = text.strip()
    if not text:
        return None

    # Pattern 1: "swap/trade/exchange/convert AMOUNT TOKEN for/to/into TOKEN"
    m = re.match(
        r"(?:swap|trade|exchange|convert|sell)\s+"
        r"(\d+(?:\.\d+)?)\s+"
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
            return {
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "mode": "exact_in",
            }

    # Pattern 2: "swap TOKEN for AMOUNT TOKEN" (exact output)
    m = re.match(
        r"(?:swap|trade|exchange|convert)\s+"
        r"(.+?)\s+"
        r"(?:for|to|into)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        from_token = resolve_token(m.group(1))
        amount = float(m.group(2))
        to_token = resolve_token(m.group(3))
        if from_token and to_token:
            return {
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "mode": "exact_out",
            }

    # Pattern 3: "buy AMOUNT TOKEN with TOKEN" (exact output)
    m = re.match(
        r"(?:buy|purchase|get)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(.+?)\s+"
        r"(?:with|using|from)\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        amount = float(m.group(1))
        to_token = resolve_token(m.group(2))
        from_token = resolve_token(m.group(3))
        if from_token and to_token:
            return {
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "mode": "exact_out",
            }

    # Pattern 4: "buy TOKEN with AMOUNT TOKEN" (exact input)
    m = re.match(
        r"(?:buy|purchase|get)\s+"
        r"(.+?)\s+"
        r"(?:with|using|from)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(.+)",
        text, re.IGNORECASE
    )
    if m:
        to_token = resolve_token(m.group(1))
        amount = float(m.group(2))
        from_token = resolve_token(m.group(3))
        if from_token and to_token:
            return {
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
