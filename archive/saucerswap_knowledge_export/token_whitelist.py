"""
Token Whitelist for Hedera Swaps
================================

CURATED LIST OF VERIFIED TOKENS FOR SAFE TRADING

This module contains ONLY verified, official tokens that have been:
1. Verified against official sources (Circle, BitGo, Hashport, LayerZero, etc.)
2. Confirmed to have adequate liquidity on SaucerSwap
3. Cross-referenced with CoinGecko/CoinMarketCap listings

DO NOT ADD TOKENS WITHOUT PROPER VERIFICATION!
Fake/copy tokens and low-liquidity tokens are excluded.

ARCHITECTURE NOTE:
This file is SEPARATE from core swap engines to allow easy updates
without affecting trading logic.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from enum import Enum


class TokenCategory(Enum):
    """Token categories for filtering and display."""
    STABLECOIN = "stablecoin"
    MAJOR_CRYPTO = "major_crypto"      # BTC, ETH, etc.
    DEFI = "defi"                       # LINK, UNI, AAVE, etc.
    HEDERA_NATIVE = "hedera_native"    # SAUCE, HBARX, etc.
    HEDERA_ECOSYSTEM = "hedera_ecosystem"  # Community tokens
    WRAPPED = "wrapped"                 # Wrapped versions


class BridgeSource(Enum):
    """Bridge/source for wrapped tokens."""
    NATIVE = "native"           # Native Hedera token
    HASHPORT = "hashport"       # Hashport bridge
    LAYERZERO = "layerzero"     # LayerZero/Stargate bridge
    AXELAR = "axelar"           # Axelar bridge
    CIRCLE = "circle"           # Circle (USDC)


@dataclass
class WhitelistedToken:
    """
    A verified token approved for trading.
    
    All fields are validated against official sources.
    """
    # Core identifiers
    hedera_id: str              # e.g., "0.0.456858"
    symbol: str                 # e.g., "USDC"
    name: str                   # e.g., "USD Coin"
    decimals: int               # e.g., 6
    
    # Classification
    category: TokenCategory
    bridge_source: BridgeSource
    
    # Trading info
    fee_tier: int = 1500        # Default SaucerSwap V2 fee tier (0.15%)
    
    # External references
    coingecko_id: Optional[str] = None
    coinmarketcap_id: Optional[str] = None
    official_website: Optional[str] = None
    
    # Verification / presentation metadata
    verified: bool = True
    notes: Optional[str] = None
    display_in_app: bool = True
    cross_checked: bool = False
    preferred_pair: Optional[str] = None
    preferred_fee_tier: Optional[int] = None
    hashport_wrapped: bool = False
    description: Optional[str] = None
    
    # Curated swap list - only featured tokens appear in swap UI
    swap_featured: bool = False
    
    @property
    def evm_address(self) -> str:
        """Convert Hedera ID to EVM address format."""
        parts = self.hedera_id.split(".")
        num = int(parts[2])
        return f"0x{num:040x}"


# =============================================================================
# VERIFIED TOKEN WHITELIST
# =============================================================================
# UNIFIED TOKEN ID SYSTEM:
# - WHITELIST: symbol -> WhitelistedToken (legacy, for backward compatibility)
# - WHITELIST_BY_ID: hedera_id -> WhitelistedToken (primary index)
# =============================================================================

WHITELIST: Dict[str, WhitelistedToken] = {}
WHITELIST_BY_ID: Dict[str, WhitelistedToken] = {}  # hedera_id -> token

def _add(token: WhitelistedToken):
    """Add token to whitelist (both symbol and ID indexes)."""
    WHITELIST[token.symbol] = token
    WHITELIST_BY_ID[token.hedera_id] = token


import json
import os
from pathlib import Path

def load_whitelist_from_json():
    """Load token whitelist from JSON registry."""
    # Try multiple possible paths for the JSON file
    paths = [
        Path(__file__).parent / "token_registry.json",
        Path("robot/token_registry.json"),
        Path("token_registry.json")
    ]
    
    registry_path = None
    for p in paths:
        if p.exists():
            registry_path = p
            break
            
    if not registry_path:
        return False
        
    try:
        with open(registry_path, "r") as f:
            tokens_data = json.load(f)
            
        # Clear existing entries before reloading
        WHITELIST.clear()
        WHITELIST_BY_ID.clear()
        
        # Core symbols that should NOT be overridden by discovered tokens with same symbol
        PROTECTED_SYMBOLS = {"USDC", "WBTC", "HBAR", "WHBAR", "WETH"}
        # Canonical IDs for core tokens
        CANONICAL_IDS = {
            "0.0.456858",    # USDC (Circle)
            "0.0.10082597",  # WBTC (LayerZero)
            "0.0.9770617",   # WETH (LayerZero)
            "0.0.1456986",   # WHBAR
            "0.0.0"          # HBAR
        }

        for data in tokens_data:
            symbol = data['symbol'].upper()
            hedera_id = data['hedera_id']
            
            # If it's a protected symbol but NOT the canonical ID, skip or rename
            if symbol in PROTECTED_SYMBOLS and hedera_id not in CANONICAL_IDS:
                # Use the saucer_symbol or append [DISCOVERED]
                symbol = data.get('saucer_symbol', f"{symbol}[hts]").upper()

            # Handle enum conversion
            try:
                category = TokenCategory(data.get('category', 'hedera_ecosystem'))
            except ValueError:
                category = TokenCategory.HEDERA_ECOSYSTEM
                
            try:
                bridge_source = BridgeSource(data.get('bridge_source', 'native'))
            except ValueError:
                bridge_source = BridgeSource.NATIVE
                
            token = WhitelistedToken(
                hedera_id=hedera_id,
                symbol=data.get('symbol', symbol), # Original display symbol
                name=data.get('name', ''),
                decimals=data.get('decimals', 8),
                category=category,
                bridge_source=bridge_source,
                fee_tier=data.get('fee_tier', 1500),
                coingecko_id=data.get('coingecko_id'),
                coinmarketcap_id=data.get('coinmarketcap_id'),
                official_website=data.get('official_website'),
                verified=data.get('verified', True),
                notes=data.get('notes'),
                display_in_app=data.get('display_in_app', True),
                cross_checked=data.get('cross_checked', False),
                preferred_pair=data.get('preferred_pair'),
                preferred_fee_tier=data.get('preferred_fee_tier'),
                hashport_wrapped=data.get('hashport_wrapped', False),
                description=data.get('description'),
                swap_featured=data.get('swap_featured', False)
            )
            # UNIFIED TOKEN ID SYSTEM: Add to both indexes
            WHITELIST[symbol] = token
            WHITELIST_BY_ID[hedera_id] = token  # Primary index by hedera_id
        return True
    except Exception as e:
        print(f"Error loading token registry: {e}")
        return False

# -----------------------------------------------------------------------------
# CRITICAL FALLBACKS - Always ensure core tokens exist
# -----------------------------------------------------------------------------

def _ensure_fallbacks():
    """Ensure core tokens exist in the whitelist as a robust fallback."""
    fallbacks = [
        WhitelistedToken(
            hedera_id="0.0.456858",
            symbol="USDC",
            name="USD Coin",
            decimals=6,
            category=TokenCategory.STABLECOIN,
            bridge_source=BridgeSource.CIRCLE,
            fee_tier=500,
            coingecko_id="usd-coin",
            swap_featured=True,
        ),
        WhitelistedToken(
            hedera_id="0.0.1456986",
            symbol="WHBAR",
            name="Wrapped HBAR",
            decimals=8,
            category=TokenCategory.WRAPPED,
            bridge_source=BridgeSource.NATIVE,
            fee_tier=1500,
            coingecko_id="hedera-hashgraph",
            swap_featured=True,
        ),
        WhitelistedToken(
            hedera_id="0.0.10082597",
            symbol="WBTC",
            name="Wrapped BTC (lz)",
            decimals=8,
            category=TokenCategory.MAJOR_CRYPTO,
            bridge_source=BridgeSource.LAYERZERO,
            fee_tier=1500,
            coingecko_id="wrapped-bitcoin",
            swap_featured=True,
        )
    ]
    for t in fallbacks:
        if t.symbol not in WHITELIST:
            _add(t)

# Initialize whitelist
_ensure_fallbacks()
load_whitelist_from_json()



# =============================================================================
# TOKEN ALIASES
# =============================================================================
# Map common symbol variations to canonical symbols

TOKEN_ALIASES = {
    'HBAR': 'WHBAR',  # Native HBAR trades through WHBAR wrapper
    'BTC': 'WBTC',    # Bitcoin trades as wrapped BTC
    'ETH': 'WETH',    # Ethereum trades as wrapped ETH
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_token(symbol: str) -> Optional[WhitelistedToken]:
    """Get a whitelisted token by symbol (handles aliases)."""
    upper_symbol = symbol.upper()
    # Check for alias
    if upper_symbol in TOKEN_ALIASES:
        upper_symbol = TOKEN_ALIASES[upper_symbol]
    return WHITELIST.get(upper_symbol)


def get_token_by_id(hedera_id: str) -> Optional[WhitelistedToken]:
    """Get a whitelisted token by Hedera ID.
    
    UNIFIED TOKEN ID SYSTEM: O(1) lookup via WHITELIST_BY_ID.
    """
    return WHITELIST_BY_ID.get(hedera_id)


# Alias for clarity
get_token_by_hedera_id = get_token_by_id


def get_all_hedera_ids() -> List[str]:
    """Get all whitelisted token hedera_ids."""
    return list(WHITELIST_BY_ID.keys())


def get_tokens_by_category(category: TokenCategory) -> List[WhitelistedToken]:
    """Get all tokens in a category."""
    return [t for t in WHITELIST.values() if t.category == category]


def get_all_symbols() -> List[str]:
    """Get all whitelisted token symbols."""
    return list(WHITELIST.keys())


def is_whitelisted(symbol_or_id: str) -> bool:
    """Check if a token is whitelisted.
    
    UNIFIED TOKEN ID SYSTEM: Supports both hedera_id and symbol lookups.
    """
    if symbol_or_id.startswith("0.0."):
        return symbol_or_id in WHITELIST_BY_ID  # O(1) lookup
    return symbol_or_id.upper() in WHITELIST


def get_fee_tier(token_in: str, token_out: str) -> int:
    """
    Get the appropriate fee tier for a token pair.
    
    Rules:
    - Stablecoin pairs: 500 (0.05%)
    - Major pairs with stables: 1500 (0.15%)
    - Volatile pairs: 3000 (0.30%)
    - Meme/exotic: 10000 (1.00%)
    """
    t_in = get_token(token_in)
    t_out = get_token(token_out)
    
    if not t_in or not t_out:
        return 1500  # Default
    
    # Both stablecoins
    if t_in.category == TokenCategory.STABLECOIN and t_out.category == TokenCategory.STABLECOIN:
        return 500
    
    # One is WHBAR/HBAR
    if "HBAR" in t_in.symbol or "HBAR" in t_out.symbol:
        return 1500
    
    # Major crypto with stablecoin
    if (t_in.category == TokenCategory.STABLECOIN or t_out.category == TokenCategory.STABLECOIN):
        if t_in.category == TokenCategory.MAJOR_CRYPTO or t_out.category == TokenCategory.MAJOR_CRYPTO:
            return 1500
    
    # Use the higher fee tier of the two tokens
    return max(t_in.fee_tier, t_out.fee_tier)


def get_coingecko_url(symbol: str) -> Optional[str]:
    """Get CoinGecko URL for a token."""
    token = get_token(symbol)
    if token and token.coingecko_id:
        return f"https://www.coingecko.com/en/coins/{token.coingecko_id}"
    return None


def get_coinmarketcap_url(symbol: str) -> Optional[str]:
    """Get CoinMarketCap URL for a token."""
    token = get_token(symbol)
    if token and token.coinmarketcap_id:
        return f"https://coinmarketcap.com/currencies/{token.coinmarketcap_id}/"
    return None


def get_hashscan_url(symbol: str) -> str:
    """Get HashScan URL for a token."""
    token = get_token(symbol)
    if token:
        return f"https://hashscan.io/mainnet/token/{token.hedera_id}"
    return ""


# =============================================================================
# CURATED SWAP LIST
# =============================================================================

def get_featured_tokens() -> List[WhitelistedToken]:
    """Get tokens featured in the swap UI.
    
    Returns a curated list of high-quality tokens for the swap interface.
    These have been selected for:
    - Deep liquidity on SaucerSwap V2
    - Verified token contracts
    - Stable routing paths
    
    Current featured: USDC, WBTC, WHBAR, WETH, SAUCE
    """
    return [t for t in WHITELIST.values() if t.swap_featured]


def get_featured_symbols() -> List[str]:
    """Get symbols of featured tokens for quick filtering."""
    return [t.symbol for t in get_featured_tokens()]


# =============================================================================
# DISPLAY / REPORTING
# =============================================================================

def print_whitelist():
    """Print the full whitelist in a formatted table."""
    print("\n" + "=" * 100)
    print("HEDERA TOKEN WHITELIST - VERIFIED TOKENS FOR TRADING")
    print("=" * 100)
    
    for category in TokenCategory:
        tokens = get_tokens_by_category(category)
        if not tokens:
            continue
            
        print(f"\n### {category.value.upper().replace('_', ' ')} ###")
        print("-" * 100)
        print(f"{'Symbol':<10} {'Hedera ID':<15} {'Decimals':<10} {'Fee':<8} {'Bridge':<12} {'Name'}")
        print("-" * 100)
        
        for t in sorted(tokens, key=lambda x: x.symbol):
            print(f"{t.symbol:<10} {t.hedera_id:<15} {t.decimals:<10} {t.fee_tier:<8} {t.bridge_source.value:<12} {t.name}")
    
    print("\n" + "=" * 100)
    print(f"Total whitelisted tokens: {len(WHITELIST)}")
    print("=" * 100)


if __name__ == "__main__":
    print_whitelist()
