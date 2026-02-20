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
    Fetch all non-zero token balances using Multicall.
    This reduces 30+ RPC calls to 1-2 chunks.
    """
    from lib.multicall import Multicall
    from lib.saucerswap import hedera_id_to_evm

    balances = {}

    # 1. HBAR Balance (Native)
    hbar_bal = w3.eth.get_balance(eoa)
    hbar_readable = hbar_bal / (10**18)
    if hbar_readable > 0:
        balances["HBAR"] = hbar_readable

    # 2. Load Token List
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

    # Load ABI for balanceOf
    ERC20_ABI = client.w3.eth.contract(abi=client._erc20_abi).abi

    # Helper to encode calldata
    temp_contract = w3.eth.contract(abi=ERC20_ABI)
    calldata = temp_contract.encode_abi("balanceOf", args=[eoa])

    idx = 0
    for sym, meta in tokens_data.items():
        token_id = meta.get("id")
        if not token_id:
            continue

        # Skip if native HBAR (already got it)
        if token_id in ["0.0.0", "HBAR"]:
            continue

        try:
            target = hedera_id_to_evm(token_id)
            # (target, allowFailure, callData)
            calls.append((target, True, calldata))
            token_meta_map[idx] = (sym, meta.get("decimals", 8))
            idx += 1
        except:
            continue

    # 4. Execute Multicall (Chunked if needed, but 50 fits easily)
    if not calls:
        return balances

    logger.debug(f"   ⚡ Batch fetching {len(calls)} token balances via Multicall...")

    try:
        mc = Multicall(w3)
        results = mc.aggregate(calls)

        # 5. Decode Results
        for i, (success, return_data) in enumerate(results):
            if success and len(return_data) >= 32:
                # Decode uint256
                val = int.from_bytes(return_data, byteorder='big')
                if val > 0:
                    sym, decimals = token_meta_map[i]
                    balances[sym] = val / (10**decimals)
    except Exception as e:
        logger.warning(f"   ⚠️ Multicall failed ({e}), falling back to sequential...")
        # Fallback to sequential if multicall fails
        return _get_balances_sequential(client, tokens_data)

    logger.debug(f"Fetched {len(balances)} non-zero balances.")
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
