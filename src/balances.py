#!/usr/bin/env python3
"""
Pacman Balances - Token Balance Queries
=======================================

Fetches wallet balances using Multicall batching or sequential fallback.
Extracted from PacmanExecutor to keep the executor focused on swap execution.
"""

import json
from typing import Dict
from pathlib import Path
from src.logger import logger


def get_balances(w3, eoa: str, client) -> Dict[str, float]:
    """
    Fetch all non-zero token balances from Hedera Mirror Node.
    This automatically discovers tokens NOT in the local tokens.json registry.
    """
    import requests
    balances = {}

    # 1. HBAR Balance (Native) - Always check local RPC for real-time accuracy
    try:
        hbar_bal = w3.eth.get_balance(eoa)
        hbar_readable = hbar_bal / (10**18)
        if hbar_readable > 0:
            balances["HBAR"] = hbar_readable
    except Exception as e:
        logger.warning(f"Failed to fetch HBAR balance from RPC: {e}")

    # 2. Token Balances from Mirror Node
    # This is the 'Headless Discovery' fix: find everything the user actually owns.
    try:
        url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/accounts/{eoa}/tokens"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # Fetch symbols from tokens.json to use nice names where possible
            try:
                with open("data/tokens.json") as f:
                    t_registry = json.load(f)
                id_to_sym = {meta['id']: sym for sym, meta in t_registry.items()}
            except:
                id_to_sym = {}

            for t_record in data.get('tokens', []):
                tid = t_record.get('token_id')
                bal = int(t_record.get('balance', 0))
                if bal <= 0: continue

                # Try to get decimals from Mirror Node token details API
                # or fallback to common symbols if possible
                decimals = 8 # Safety fallback
                try:
                    t_url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/tokens/{tid}"
                    t_resp = requests.get(t_url, timeout=5)
                    if t_resp.status_code == 200:
                        decimals = int(t_resp.json().get('decimals', 8))
                except: pass

                sym = id_to_sym.get(tid)
                if not sym:
                    # Resolve symbol from mirror node if not in registry
                    try: sym = t_resp.json().get('symbol', tid)
                    except: sym = tid

                balances[sym] = bal / (10**decimals)
                
    except Exception as e:
        logger.error(f"Mirror Node balance discovery failed: {e}")
        # Final fallback to existing sequential logic if mirror node is down
        with open("data/tokens.json") as f:
            tokens_data = json.load(f)
        return _get_balances_sequential(client, tokens_data)

    return balances


def _get_balances_sequential(client, tokens_data) -> Dict[str, float]:
    """Fallback method for sequential fetching."""
    balances = {}
    for sym, meta in tokens_data.items():
        token_id = meta.get("id")
        if not token_id:
            continue
        try:
            raw_bal = client.get_token_balance(token_id)
            if raw_bal > 0:
                decimals = meta.get("decimals", 8)
                balances[sym] = raw_bal / (10**decimals)
        except:
            continue
    return balances
