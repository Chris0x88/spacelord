import pytest
from src.utils import is_valid_account_id, is_valid_private_key

def test_is_valid_account_id_valid():
    """Test valid account IDs."""
    assert is_valid_account_id("0.0.123") is True
    assert is_valid_account_id("0.0.0") is True
    assert is_valid_account_id("0.0.999999999999") is True

def test_is_valid_account_id_invalid_format():
    """Test invalid account ID formats."""
    assert is_valid_account_id("0.123") is False
    assert is_valid_account_id("0.0.abc") is False
    assert is_valid_account_id("0.0.123.4") is False
    assert is_valid_account_id("0.0.-1") is False
    assert is_valid_account_id("0.0.") is False
    assert is_valid_account_id("shard.realm.num") is False
    assert is_valid_account_id("0.0.123 ") is False
    assert is_valid_account_id(" 0.0.123") is False

def test_is_valid_account_id_empty_and_none():
    """Test empty string and None for account ID."""
    assert is_valid_account_id("") is False
    assert is_valid_account_id(None) is False

def test_is_valid_private_key_valid():
    """Test valid private keys."""
    valid_key = "a" * 64
    assert is_valid_private_key(valid_key) is True
    assert is_valid_private_key("0x" + valid_key) is True
    assert is_valid_private_key(valid_key.upper()) is True
    assert is_valid_private_key("  " + valid_key + "  ") is True

def test_is_valid_private_key_invalid_length():
    """Test private keys with invalid lengths."""
    assert is_valid_private_key("a" * 63) is False
    assert is_valid_private_key("a" * 65) is False
    assert is_valid_private_key("0x" + "a" * 63) is False

def test_is_valid_private_key_invalid_chars():
    """Test private keys with non-hex characters."""
    assert is_valid_private_key("g" * 64) is False
    assert is_valid_private_key("a" * 63 + "g") is False

def test_is_valid_private_key_empty_and_none():
    """Test empty string and None for private key."""
    assert is_valid_private_key("") is False
    assert is_valid_private_key(None) is False
