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
        balances["0.0.0"] = hbar_readable
    else:
        # Unfunded account — no HBAR means no associated tokens on Hedera.
        # Skip multicall entirely and go straight to Mirror Node to confirm.
        try:
            root = Path(__file__).parent.parent
            tokens_path = root / "data" / "tokens.json"
            if not tokens_path.exists():
                tokens_path = Path("data/tokens.json")
            with open(tokens_path) as f:
                tokens_data = json.load(f)
        except Exception:
            return balances
        return _get_balances_mirror(eoa, tokens_data, token_highlights, client.network)

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
    for token_id, meta in tokens_data.items():
        if not token_id or token_id in ["0.0.0", "HBAR"]:
            continue

        try:
            target = hedera_id_to_evm(token_id)
            calls.append((target, True, calldata))
            token_meta_map[idx] = (token_id, meta.get("decimals", 8))
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
                    token_id, decimals = token_meta_map[i]
                    balances[token_id] = val / (10**decimals)
    except Exception as e:
        # Hedera HTS balanceOf via multicall3 can return b'' for unassociated accounts — expected.
        logger.debug(f"   Multicall unavailable ({e}), using Mirror Node...")
        return _get_balances_mirror(eoa, tokens_data, token_highlights, client.network)

    # For sub-accounts on Hedera, Mirror Node is the only reliable source for HTS balances
    # when multiple IDs share an ECDSA alias. We double-check if we found low token count.
    if len(balances) <= 1:
        logger.debug("   ⚠️ Low token count via RPC, checking with Mirror Node...")
        mirror_bal = _get_balances_mirror(eoa, tokens_data, token_highlights, client.network)
        balances.update(mirror_bal)

    logger.debug(f"Fetched {len(balances)} non-zero balances.")
    return balances


def _get_balances_mirror(eoa: str, tokens_data: dict, token_highlights: list = None, network: str = "mainnet") -> Dict[str, float]:
    """
    Fallback: Fetch HTS balances directly from Mirror Node API.
    Required for sub-accounts where EVM long-zero or alias queries fail.
    """
    import requests
    balances = {}
    
    # Resolve Hedera ID if eoa is long-zero or alias
    account_id = eoa
    if eoa.startswith("0x0000000000000000000000000000000000"):
        # Convert hex suffix to decimal ID
        num = int(eoa[34:], 16)
        account_id = f"0.0.{num}"
    
    base_url = "https://mainnet-public.mirrornode.hedera.com" if network == "mainnet" else "https://testnet.mirrornode.hedera.com"
    url = f"{base_url}/api/v1/accounts/{account_id}"
    
    try:
        logger.debug(f"   📡 Mirror Node balance check for {account_id}...")
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            balance_data = data.get("balance", {})
            for t_entry in balance_data.get("tokens", []):
                tid = t_entry.get("token_id")
                raw_bal = t_entry.get("balance", 0)
                if raw_bal > 0:
                    # Find decimals from our tokens_data
                    meta = tokens_data.get(tid)
                    if not meta:
                        # Find by scanning values if tid is not a key
                        for m in tokens_data.values():
                            if m.get("id") == tid:
                                meta = m
                                break
                    
                    decimals = meta.get("decimals", 8) if meta else 8
                    balances[tid] = raw_bal / (10**decimals)
                    
            logger.debug(f"   ✅ Mirror Node returned {len(balances)} tokens.")
        else:
            logger.warning(f"   ⚠️ Mirror Node returned {resp.status_code}")
    except Exception as e:
        logger.error(f"   ❌ Mirror Node fallback failed: {e}")
        
    return balances


def _get_balances_sequential(client, tokens_data, token_highlights: list = None) -> Dict[str, float]:
    """
    Fallback method for sequential fetching.
    Still kept for architectural completeness, but Mirror Node is preferred now.
    """
    balances = {}
    targets = token_highlights if token_highlights else ["0.0.456858", "0.0.10082597", "0.0.9470869"]
    for token_id in targets:
        meta = tokens_data.get(token_id)
        if not meta: continue
        try:
            raw_bal = client.get_token_balance(token_id)
            if raw_bal > 0:
                decimals = meta.get("decimals", 8)
                balances[token_id] = raw_bal / (10**decimals)
        except: continue
    return balances

