#!/usr/bin/env python3
"""
Pacman Filter - Token Filtering and Sorting
=============================================

Provides UI-focused filtering and sorting for token data.
Loads data from tokens.json, aliases.json, and settings.json.
Supports user-defined priority sorting and blacklisting.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

class UIFilter:
    """UI Filter class for token data."""
    
    def __init__(self):
        self._tokens = None
        self._aliases = None
        self._settings = None
        
        # Project Root
        self.root = Path(__file__).parent.parent
        
    def _load_json(self, filename: str) -> Any:
        paths = [
            self.root / "data" / filename,
            self.root / filename,
            Path(f"data/{filename}"),
            Path(filename)
        ]
        
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r") as f:
                        return json.load(f)
                except Exception:
                    continue
        return None

    def _load_tokens(self) -> Dict[str, Any]:
        if self._tokens is None:
            self._tokens = self._load_json("tokens.json") or {}
        return self._tokens

    def _load_aliases(self) -> Dict[str, str]:
        if self._aliases is None:
            self._aliases = self._load_json("aliases.json") or {}
        return self._aliases
        
    def _load_settings(self) -> Dict[str, Any]:
        if self._settings is None:
            self._settings = self._load_json("settings.json") or {}
        return self._settings
    
    def get_token_metadata(self) -> Dict[str, Any]:
        """Get token metadata for UI display."""
        return self._load_tokens()
    
    def is_blacklisted(self, token_id: str) -> bool:
        """Check if a token is blacklisted from UI display."""
        settings = self._load_settings()
        blacklist = settings.get("display_rules", {}).get("blacklist_ids", [])
        return token_id in blacklist
    
    def sort_wallet_balances(self, items: List[Any]) -> List[Any]:
        """
        Sort wallet balances by:
        1. Settings priority (wallet_balance_order)
        2. USD value (descending)
        """
        settings = self._load_settings()
        order = settings.get("display_rules", {}).get("wallet_balance_order", [])
        # Create a mapping for fast lookup
        order_map = {sym.upper(): i for i, sym in enumerate(order)}
        
        def sort_key(item):
            # item = (symbol, meta, readable, usd_val)
            sym = item[0].upper()
            meta_sym = item[1].get("symbol", "").upper()
            usd_val = item[3]
            
            # 1. Order by defined preference
            priority = order_map.get(sym, order_map.get(meta_sym, 999))
            
            # 2. Tie-break with USD value (descending -> negative)
            return (priority, -usd_val)
            
        return sorted(items, key=sort_key)
    
    def get_sorted_tokens(self) -> List[tuple]:
        """
        Get list of tokens sorted by:
        1. Priority symbols
        2. Alphabetical symbol
        """
        tokens = self._load_tokens()
        settings = self._load_settings()
        priority = settings.get("display_rules", {}).get("priority_symbols", [])
        priority_map = {sym.upper(): i for i, sym in enumerate(priority)}
        
        items = list(tokens.items())
        
        def sort_key(pair):
            token_id, meta = pair
            sym = meta.get("symbol", "UNKNOWN").upper()
            p_val = priority_map.get(sym, 999)
            return (p_val, sym)
            
        return sorted(items, key=sort_key)
    
    def get_display_aliases(self, query_id: str) -> Optional[str]:
        """Get display alias for a token ID."""
        aliases = self._load_json("aliases.json") or {}
        tokens = self._load_tokens()
        
        found = []
        
        # 1. Automatic Alias: Use Symbol (lowercase, stripped of [hts] etc)
        meta = tokens.get(query_id)
        if meta:
            sym = meta.get("symbol", "").lower()
            if sym:
                clean_sym = sym.split("[")[0].strip()
                found.append(clean_sym)
                if clean_sym != sym:
                    found.append(sym)

        # 2. Manual Aliases from aliases.json (keys are lowercase variants)
        for alias_name, target_id in aliases.items():
            if target_id == query_id:
                if alias_name not in found:
                    found.append(alias_name)
                    
        # Sort for consistency (shorter aliases first)
        found.sort(key=len)
        # Deduplicate while preserving order
        unique_found = []
        for x in found:
            if x not in unique_found: unique_found.append(x)
        return ", ".join(unique_found) if unique_found else None

# Singleton instance for compatibility
ui_filter = UIFilter()
