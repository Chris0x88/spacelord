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


def get_balances(w3, eoa: str, client, token_highlights: list = None) -> Dict[str, float]:
    """
    Fetch all non-zero token balances using Multicall.
    This reduces 30+ RPC calls to 1-2 chunks.
    
    Args:
        token_highlights: Optional list of token symbols to prioritize 
                         or ONLY fetch if sequential fallback occurs.
    """
    from lib.multicall import Multicall
    from lib.saucerswap import hedera_id_to_evm

    balances = {}

    # 1. HBAR Balance (Native)
    hbar_bal = w3.eth.get_balance(eoa)
    hbar_readable = hbar_bal / (10**18)
    if hbar_readable > 0:
        balances["HBAR"] = hbar_readable

    # ... (rest of loading tokens_data)
    try:
        root = Path(__file__).parent.parent
        tokens_path = root / "data" / "tokens.json"
        if not tokens_path.exists():
            tokens_path = Path("data/tokens.json")

        with open(tokens_path) as f:
            tokens_data = json.load(f)
    except Exception as e:
        logger.error(f"Error: Could not load tokens.json for balance check: {e}")
        return balances

    # 3. Prepare Batch Calls
    calls = []
    token_meta_map = {}  # call_index -> (symbol, decimals)

    ERC20_ABI = client.w3.eth.contract(abi=client._erc20_abi).abi
    temp_contract = w3.eth.contract(abi=ERC20_ABI)
    calldata = temp_contract.encode_abi("balanceOf", args=[eoa])

    idx = 0
    for sym, meta in tokens_data.items():
        token_id = meta.get("id")
        if not token_id or token_id in ["0.0.0", "HBAR"]:
            continue

        try:
            target = hedera_id_to_evm(token_id)
            calls.append((target, True, calldata))
            token_meta_map[idx] = (sym, meta.get("decimals", 8))
            idx += 1
        except:
            continue

    # 4. Execute Multicall
    if not calls:
        return balances

    logger.debug(f"   ⚡ Batch fetching {len(calls)} token balances via Multicall...")

    try:
        mc = Multicall(w3)
        results = mc.aggregate(calls)

        for i, (success, return_data) in enumerate(results):
            if success and len(return_data) >= 32:
                val = int.from_bytes(return_data, byteorder='big')
                if val > 0:
                    sym, decimals = token_meta_map[i]
                    balances[sym] = val / (10**decimals)
    except Exception as e:
        logger.warning(f"   ⚠️ Multicall failed ({e}), falling back to sequential...")
        # Fallback to sequential if multicall fails - use highlights to save time
        return _get_balances_sequential(client, tokens_data, token_highlights)

    logger.debug(f"Fetched {len(balances)} non-zero balances.")
    return balances


def _get_balances_sequential(client, tokens_data, token_highlights: list = None) -> Dict[str, float]:
    """
    Fallback method for sequential fetching.
    If highlights are provided, we ONLY check those symbols or prioritize them.
    Given 1500+ tokens, checking all is too slow.
    """
    balances = {}
    
    # Symbols we definitely should check first/only
    targets = token_highlights if token_highlights else ["USDC", "WBTC_HTS", "WETH_HTS", "SAUCE"]
    
    # First pass: Essential highlights
    for sym in targets:
        meta = tokens_data.get(sym)
        if not meta: continue
        token_id = meta.get("id")
        if not token_id: continue
        
        try:
            raw_bal = client.get_token_balance(token_id)
            if raw_bal > 0:
                decimals = meta.get("decimals", 8)
                balances[sym] = raw_bal / (10**decimals)
        except:
            continue
            
    # If no highlights provided, or if user wants full scan (risky)
    # we stop here to prevent 30min hangs unless token_highlights is None
    if token_highlights is not None:
        return balances

    # Full scan fallback (only if no highlights provided)
    # Limiting to first 50 tokens to prevent complete hang
    count = 0
    for sym, meta in tokens_data.items():
        if sym in balances: continue
        if count > 50: break
        
        token_id = meta.get("id")
        if not token_id: continue
        try:
            raw_bal = client.get_token_balance(token_id)
            if raw_bal > 0:
                decimals = meta.get("decimals", 8)
                balances[sym] = raw_bal / (10**decimals)
            count += 1
        except:
            continue
            
    return balances
