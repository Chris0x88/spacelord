"""
Space Lord Utilities
================

General purpose utility functions for the Space Lord suite.
"""

import re

def is_valid_account_id(val: str) -> bool:
    """
    Check if a string is a valid Hedera Account ID (shard.realm.num).
    Currently supports the standard 0.0.xxx format.
    """
    if not val:
        return False
    
    # Standard 0.0.xxx format
    pattern = r"^0\.0\.\d+$"
    return bool(re.match(pattern, val))

def is_valid_private_key(val: str) -> bool:
    """
    Check if a string is a valid ECDSA/ED25519 private key (64 hex chars).
    """
    if not val:
        return False
    
    clean_val = val.replace("0x", "").strip()
    if len(clean_val) != 64:
        return False
    
    try:
        int(clean_val, 16)
        return True
    except ValueError:
        return False
