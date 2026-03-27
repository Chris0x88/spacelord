"""Tests for USDT0 bridge module."""
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestUSDT0BridgeValidation:
    """Test governance and whitelist validation (no contract calls)."""

    def _make_bridge(self):
        """Create a USDT0Bridge with mocked executor."""
        from lib.bridge_usdt0 import USDT0Bridge

        executor = MagicMock()
        executor.w3 = MagicMock()
        executor.eoa = "0x1234567890abcdef1234567890abcdef12345678"
        executor.config = MagicMock()
        executor.config.private_key = MagicMock()
        executor.config.simulate_mode = False
        executor.chain_id = 295
        executor.network = "mainnet"

        executor.w3.eth.contract.return_value = MagicMock()
        executor.w3.to_checksum_address = lambda x: x

        bridge = USDT0Bridge(executor)
        return bridge

    def test_invalid_chain_rejected(self):
        bridge = self._make_bridge()
        result = bridge.bridge(50.0, "polygon", "0xabc123")
        assert not result["success"]
        assert "not in allowed list" in result["error"].lower() or "not allowed" in result["error"].lower()

    def test_hedera_id_rejected_as_destination(self):
        bridge = self._make_bridge()
        result = bridge.bridge(50.0, "arbitrum", "0.0.12345")
        assert not result["success"]
        assert "hedera id" in result["error"].lower() or "evm address" in result["error"].lower()

    def test_invalid_evm_address_rejected(self):
        bridge = self._make_bridge()
        result = bridge.bridge(50.0, "arbitrum", "not-an-address")
        assert not result["success"]
        assert "invalid" in result["error"].lower()

    def test_amount_below_minimum_rejected(self):
        bridge = self._make_bridge()
        with patch.object(bridge, '_load_governance', return_value={
            "bridging": {"min_bridge_amount_usd": 1.0, "max_bridge_usd": 100.0,
                         "allowed_chains": ["arbitrum"], "counts_toward_daily_limit": True},
            "safety_limits": {"max_daily_usd": 100.0, "min_hbar_reserve": 5.0}
        }):
            result = bridge.bridge(0.5, "arbitrum", "0x1234567890abcdef1234567890abcdef12345678")
            assert not result["success"]
            assert "minimum" in result["error"].lower() or "min" in result["error"].lower()

    def test_amount_above_max_rejected(self):
        bridge = self._make_bridge()
        with patch.object(bridge, '_load_governance', return_value={
            "bridging": {"min_bridge_amount_usd": 1.0, "max_bridge_usd": 100.0,
                         "allowed_chains": ["arbitrum"], "counts_toward_daily_limit": True},
            "safety_limits": {"max_daily_usd": 100.0, "min_hbar_reserve": 5.0}
        }):
            result = bridge.bridge(150.0, "arbitrum", "0x1234567890abcdef1234567890abcdef12345678")
            assert not result["success"]
            assert "exceeds" in result["error"].lower() or "limit" in result["error"].lower()

    def test_unwhitelisted_destination_rejected(self):
        bridge = self._make_bridge()
        with patch.object(bridge, '_load_governance', return_value={
            "bridging": {"min_bridge_amount_usd": 1.0, "max_bridge_usd": 100.0,
                         "allowed_chains": ["arbitrum"], "counts_toward_daily_limit": True},
            "safety_limits": {"max_daily_usd": 100.0, "min_hbar_reserve": 5.0}
        }), patch.object(bridge, '_load_bridge_whitelist', return_value=[]):
            result = bridge.bridge(50.0, "arbitrum", "0x1234567890abcdef1234567890abcdef12345678")
            assert not result["success"]
            assert "whitelist" in result["error"].lower()

    def test_constants(self):
        from lib.bridge_usdt0 import USDT0Bridge
        assert USDT0Bridge.HEDERA_USDT0_OFT == "0xe3119e23fC2371d1E6b01775ba312035425A53d6"
        assert USDT0Bridge.HEDERA_USDT0_TOKEN == "0x00000000000000000000000000000000009Ce723"
        assert USDT0Bridge.HEDERA_USDT0_HEDERA_ID == "0.0.642851"
        assert USDT0Bridge.USDT0_DECIMALS == 6
        assert USDT0Bridge.CHAINS["arbitrum"]["eid"] == 30110
