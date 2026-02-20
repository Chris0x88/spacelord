#!/usr/bin/env python3
"""
Pacman Associations - HTS Token Association Management
======================================================

Handles checking and creating token associations on Hedera.
Extracted from PacmanExecutor to keep the executor focused on swap execution.

HEDERA-SPECIFIC NOTE:
    On Hedera, accounts must explicitly "associate" with a token before
    they can hold a balance. balanceOf() returns 0 for BOTH "associated
    with zero balance" and "not associated", so we need Mirror Node
    confirmation for the zero-balance case.
"""

import requests
from src.logger import logger


def check_token_association(client, token_id: str, hedera_account_id: str, eoa: str, network: str) -> bool:
    """
    Check if the account is associated with the token.

    Strategy:
    1. Optimistic Check: If balance > 0, we are definitely associated.
    2. Robust Check: If balance == 0, we MUST check Mirror Node to confirm association.
       (balanceOf returns 0 for unassociated accounts on Hedera EVM).
    """
    if token_id.upper() in ["HBAR", "0.0.0"]:
        return True

    # 1. Optimistic Check (Fast)
    try:
        balance = client.get_token_balance(token_id)
        if balance > 0:
            return True
    except Exception as e:
        logger.warning(f"   ⚠️  Balance check failed during association verify: {e}")
        # Fall through to Mirror Node check

    # 2. Robust Check (Mirror Node)
    return _check_association_via_mirror(token_id, hedera_account_id, eoa, network)


def _check_association_via_mirror(token_id: str, hedera_account_id: str, eoa: str, network: str) -> bool:
    """Verify association using Hedera Mirror Node API."""
    try:
        # Determine Account ID to check
        account_id = hedera_account_id
        if not account_id or account_id == "Unknown":
            account_id = eoa  # Mirror Node supports EVM address lookup

        base_url = "https://mainnet.mirrornode.hedera.com"
        if network == "testnet":
            base_url = "https://testnet.mirrornode.hedera.com"

        url = f"{base_url}/api/v1/accounts/{account_id}/tokens"
        params = {"token.id": token_id, "limit": 1}

        logger.debug(f"   🔍 Checking association via Mirror Node: {url} {params}")
        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if "tokens" in data and len(data["tokens"]) > 0:
                return True  # Found association record
            else:
                return False  # No record found = Not associated
        elif response.status_code == 404:
            # Account not found?
            return False
        else:
            logger.warning(f"   ⚠️  Mirror Node returned {response.status_code}")
            return False  # Assume false to trigger safety association attempt

    except Exception as e:
        logger.error(f"   ❌ Mirror Node check failed: {e}")
        return False  # Fail safe: Assume not associated


def associate_token(client, token_id: str) -> bool:
    """Associate HTS token using Native Precompiles (Python-only)."""
    if token_id.upper() in ["HBAR", "0.0.0"]:
        return True

    logger.info(f"   🛡️  Associating token {token_id} via HTS Precompile...")

    try:
        # Use native python client instead of external node script
        success = client.associate_token_native(token_id)
        if success:
            logger.info(f"   ✅ Association Confirmed.")
            return True
        else:
            logger.error(f"   ❌ Association failed on-chain.")
            return False
    except Exception as e:
        logger.error(f"   ❌ Association error: {e}")
        return False


def get_staking_info(hedera_account_id: str, eoa: str, network: str) -> dict:
    """
    Fetch staking info from Mirror Node.
    Returns: {
        "is_staked": bool,
        "node_id": int or None,
        "period_start": str or None,
        "pending_reward": int (tinybar)
    }
    """
    try:
        account_id = hedera_account_id
        if not account_id or account_id == "Unknown":
            account_id = eoa

        base_url = "https://mainnet-public.mirrornode.hedera.com"
        if network == "testnet":
            base_url = "https://testnet.mirrornode.hedera.com"

        url = f"{base_url}/api/v1/accounts/{account_id}"
        resp = requests.get(url, timeout=5)

        if resp.status_code == 200:
            data = resp.json()
            staked_node_id = data.get("staked_node_id")

            return {
                "is_staked": staked_node_id is not None,
                "node_id": staked_node_id,
                "pending_reward": data.get("pending_reward", 0),
                "decline_reward": data.get("decline_reward", False)
            }
    except Exception as e:
        logger.warning(f"   ⚠️ Failed to fetch staking info: {e}")

    return {"is_staked": False, "node_id": None, "pending_reward": 0}
