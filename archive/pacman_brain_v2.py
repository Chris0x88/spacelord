import re
import json
import os
from typing import Dict, List, Tuple, Optional
from pacman_types import SwapIntent, SwapStrategy

# Aliases for smoother UX
TOKEN_ALIASES = {
    "bitcoin": "WBTC",
    "btc": "WBTC",
    "wbtc": "WBTC",
    "ethereum": "WETH",
    "eth": "WETH",
    "ether": "WETH",
    "weth": "WETH",
    "usdc": "USDC",
    "usd": "USDC",
    "dollar": "USDC",
    "dollars": "USDC",
    "cash": "USDC",
    "bucks": "USDC",
    "hbar": "HBAR",
    "hedera": "HBAR",
    "whbar": "WHBAR",
    "wrapped hbar": "WHBAR",
    "sauce": "SAUCE",
    "xsauce": "XSAUCE",
    "bonzo": "BONZO",
    "clxy": "CLXY",
    "pack": "PACK",
    "usdt": "USDT_HTS",
    "tether": "USDT_HTS",
    "dai": "DAI_HTS",
    "link": "LINK_HTS",
    "avax": "WAVAX_HTS",
    "qnt": "QNT_HTS",
}

class PacmanBrainV2:
    def __init__(self, tokens_file: str = "tokens.json"):
        # Resolve path relative to this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.tokens_file = os.path.join(base_dir, tokens_file)

        self.known_tokens = self._load_tokens()
        # Add HBAR manually as it might not be in the JSON if it's HTS-only list
        if "HBAR" not in self.known_tokens:
            self.known_tokens["HBAR"] = {"id": "0.0.0", "decimals": 8, "symbol": "HBAR"}

        # Build reverse lookup for detection
        self.token_matcher = self._build_matcher()

    def _load_tokens(self) -> Dict[str, Dict]:
        try:
            with open(self.tokens_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback to empty if file not found (will rely on manual adds or aliases)
            return {}

    def _build_matcher(self) -> List[Tuple[str, str]]:
        """Build a list of (alias, symbol) tuples."""
        matcher = []
        # Add from JSON
        for symbol in self.known_tokens.keys():
            matcher.append((symbol.lower(), symbol))

        # Add explicit aliases
        for alias, symbol in TOKEN_ALIASES.items():
            if symbol in self.known_tokens or symbol in ["HBAR", "WHBAR", "WBTC", "WETH"]:
                 matcher.append((alias.lower(), symbol))

        return matcher

    def detect_tokens(self, text: str) -> List[Tuple[str, int]]:
        """
        Find all tokens in the text.
        Returns list of (Symbol, StartIndex) sorted by appearance.
        Handles overlaps by prioritizing longer matches (e.g. "Wrapped HBAR" > "HBAR").
        """
        lower_text = text.lower()
        all_matches = []

        # 1. Find all possible matches
        for alias, symbol in self.token_matcher:
            # Use regex for word boundary to avoid partial matches like "USDC" in "USDC_HTS" if alias was just "usd"
            # Escaping alias is important
            pattern = re.compile(r'\b' + re.escape(alias) + r'\b')
            for m in pattern.finditer(lower_text):
                all_matches.append({
                    "symbol": symbol,
                    "start": m.start(),
                    "end": m.end(),
                    "length": m.end() - m.start()
                })

        # 2. Sort by Length DESC (Greedy)
        all_matches.sort(key=lambda x: x["length"], reverse=True)

        # 3. Filter overlaps
        final_matches = []
        taken_ranges = [] # (start, end)

        for m in all_matches:
            is_overlap = False
            for start, end in taken_ranges:
                # Check intersection
                if max(m["start"], start) < min(m["end"], end):
                    is_overlap = True
                    break

            if not is_overlap:
                final_matches.append(m)
                taken_ranges.append((m["start"], m["end"]))

        # 4. Sort by Start Index to preserve sentence order
        final_matches.sort(key=lambda x: x["start"])

        return [(m["symbol"], m["start"]) for m in final_matches]

    def parse_intent(self, text: str) -> SwapIntent:
        """
        Parse natural language into a SwapIntent.
        """
        intent = SwapIntent()
        lower_text = text.lower()

        # 1. Detect Strategy (Buy vs Sell)
        is_buy_verb = any(w in lower_text for w in ["buy", "get", "receive", "want", "need"])
        is_sell_verb = any(w in lower_text for w in ["sell", "spend", "pay", "swap", "trade"])

        # Default to SPEND if unsure, or if it's "Swap"
        if is_buy_verb and not is_sell_verb:
            intent.strategy = SwapStrategy.RECEIVE_EXACT
        elif is_sell_verb:
            intent.strategy = SwapStrategy.SPEND_EXACT
        else:
            intent.strategy = SwapStrategy.SPEND_EXACT

        # 2. Extract Amount
        # Look for number.
        qty_matches = list(re.finditer(r"(\d+(\.\d+)?)", text))
        qty_val = 0.0
        qty_index = -1

        if qty_matches:
            try:
                m = qty_matches[0]
                qty_val = float(m.group(1))
                qty_index = m.start()
            except:
                pass

        intent.qty = qty_val

        # 3. Detect Tokens
        tokens_found = self.detect_tokens(text) # [(Symbol, Index)]

        if not tokens_found:
            return intent

        # 4. Map Tokens to In/Out based on Strategy and grammar
        t1 = tokens_found[0][0]
        t2 = tokens_found[1][0] if len(tokens_found) > 1 else None

        # Detect prepositions relative to tokens
        # We need to check if "with" or "using" is BEFORE a token

        def is_preposition_before(token_idx, preps):
            # Look at substring before token
            # We need a safe window, say 10 chars
            start = max(0, token_idx - 10)
            window = lower_text[start:token_idx]
            return any(p in window for p in preps)

        has_with_before_t1 = is_preposition_before(tokens_found[0][1], [" with ", " using "])
        has_with_before_t2 = False
        if t2:
             has_with_before_t2 = is_preposition_before(tokens_found[1][1], [" with ", " using "])

        if has_with_before_t1:
            # "Buy X with Y" -> X is Out, Y is In.
            # But here t1 is after "with". So t1 is Y (In).
            intent.token_in = t1
            intent.token_out = t2 # might be None or already set
        elif has_with_before_t2:
            # "Buy X with Y" -> t2 is after "with" -> t2 is In.
            intent.token_in = t2
            intent.token_out = t1
        elif " for " in lower_text or " to " in lower_text or " into " in lower_text:
             # "Swap X for Y" -> In: X, Out: Y
             if intent.strategy == SwapStrategy.RECEIVE_EXACT: # Buy/Get
                 # "Buy X for Y" -> Out: X, In: Y?
                 intent.token_out = t1
                 intent.token_in = t2
             else:
                 intent.token_in = t1
                 intent.token_out = t2
        else:
            # Default order
            if intent.strategy == SwapStrategy.RECEIVE_EXACT:
                intent.token_out = t1
                intent.token_in = t2
            else:
                intent.token_in = t1
                intent.token_out = t2

        # 5. Associate Qty with Token (Override Strategy)
        if qty_val > 0:
            # Find closest token
            t1_idx = tokens_found[0][1]
            t2_idx = tokens_found[1][1] if len(tokens_found) > 1 else 9999

            dist_t1 = abs(qty_index - t1_idx)
            dist_t2 = abs(qty_index - t2_idx)

            associated_token = t1 if dist_t1 < dist_t2 else tokens_found[1][0]

            if associated_token == intent.token_out and intent.token_out is not None:
                intent.strategy = SwapStrategy.RECEIVE_EXACT
            elif associated_token == intent.token_in and intent.token_in is not None:
                intent.strategy = SwapStrategy.SPEND_EXACT

        return intent

if __name__ == "__main__":
    # Quick Test
    brain = PacmanBrainV2()

    test_phrases = [
        "Swap 100 USDC for HBAR",
        "Buy 1000 WBTC with USDC",
        "Sell 50 HBAR for SAUCE",
        "I want to get 500 SAUCE using HBAR",
        "Swap HBAR for 100 USDC",
        "Trade 100 USDC to WBTC"
    ]

    for p in test_phrases:
        print(f"Phrase: '{p}'")
        print(f"  {brain.parse_intent(p)}")
        print("-" * 20)
