import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from pacman_config import PacmanConfig
from pacman_errors import ConfigurationError

class TestPacmanConfig:

    @patch("pathlib.Path.exists")
    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_defaults(self, mock_exists):
        """Test loading default values when no env vars are set."""
        mock_exists.return_value = False

        config = PacmanConfig.from_env()

        assert config.network == "mainnet"
        assert config.rpc_url == "https://mainnet.hashio.io/api"
        assert config.max_swap_amount_usd == 1.00
        assert config.max_daily_volume_usd == 10.00
        assert config.max_slippage_percent == 1.0
        assert config.simulate_mode is True
        assert config.require_confirmation is True
        assert config.verbose_mode is False
        assert config.private_key is None
        assert config.hedera_account_id is None

    @patch("pathlib.Path.exists")
    @patch.dict(os.environ, {
        "PACMAN_PRIVATE_KEY": "abc",
        "PACMAN_NETWORK": "testnet",
        "PACMAN_MAX_SWAP": "0.5",
        "PACMAN_MAX_DAILY": "5.0",
        "PACMAN_MAX_SLIPPAGE": "2.0",
        "PACMAN_SIMULATE": "false",
        "PACMAN_CONFIRM": "false",
        "PACMAN_VERBOSE": "true",
        "HEDERA_ACCOUNT_ID": "0.0.123"
    }, clear=True)
    def test_from_env_overrides(self, mock_exists):
        """Test loading values from environment variables."""
        mock_exists.return_value = False

        config = PacmanConfig.from_env()

        assert config.private_key == "abc"
        assert config.network == "testnet"
        assert config.rpc_url == "https://testnet.hashio.io/api"
        assert config.max_swap_amount_usd == 0.5
        assert config.max_daily_volume_usd == 5.0
        assert config.max_slippage_percent == 2.0
        assert config.simulate_mode is False
        assert config.require_confirmation is False
        assert config.verbose_mode is True
        assert config.hedera_account_id == "0.0.123"

    @patch("pathlib.Path.exists")
    @patch.dict(os.environ, {
        "PACMAN_MAX_SWAP": "2.0",
        "PACMAN_MAX_DAILY": "20.0",
        "PACMAN_MAX_SLIPPAGE": "10.0"
    }, clear=True)
    def test_from_env_safety_caps(self, mock_exists):
        """Test that hardcoded safety caps are enforced in from_env."""
        mock_exists.return_value = False

        config = PacmanConfig.from_env()

        assert config.max_swap_amount_usd == 1.00
        assert config.max_daily_volume_usd == 10.00
        assert config.max_slippage_percent == 5.0

    def test_safe_float(self):
        """Test the _safe_float static method."""
        # Valid floats
        assert PacmanConfig._safe_float("1.23", 0.0) == 1.23
        assert PacmanConfig._safe_float("0", 1.0) == 0.0

        # Invalid inputs
        assert PacmanConfig._safe_float(None, 5.0) == 5.0
        assert PacmanConfig._safe_float("not a float", 5.0) == 5.0
        assert PacmanConfig._safe_float("nan", 5.0) == 5.0
        assert PacmanConfig._safe_float("inf", 5.0) == 5.0
        assert PacmanConfig._safe_float("-inf", 5.0) == 5.0

    def test_validate_success(self):
        """Test validate method with a valid configuration."""
        config = PacmanConfig(
            private_key="a" * 64,
            simulate_mode=False,
            max_swap_amount_usd=0.5,
            max_daily_volume_usd=5.0,
            max_slippage_percent=2.0
        )
        # Should not raise
        config.validate()

    def test_validate_simulate_mode_no_key(self):
        """Test validate method in simulation mode with no key (should pass)."""
        config = PacmanConfig(private_key=None, simulate_mode=True)
        # Should not raise
        config.validate()

    def test_validate_live_mode_no_key(self):
        """Test validate method in live mode with no key."""
        config = PacmanConfig(private_key=None, simulate_mode=False)
        with pytest.raises(ConfigurationError, match="Private key required"):
            config.validate()

    def test_validate_invalid_key_length(self):
        """Test validate method with invalid private key length."""
        config = PacmanConfig(private_key="abc", simulate_mode=False)
        with pytest.raises(ConfigurationError, match="Invalid private key format"):
            config.validate()

        config.private_key = "a" * 63
        with pytest.raises(ConfigurationError, match="Invalid private key format"):
            config.validate()

    def test_validate_invalid_key_chars(self):
        """Test validate method with non-hex characters in private key."""
        config = PacmanConfig(private_key="z" * 64, simulate_mode=False)
        with pytest.raises(ConfigurationError, match="non-hex characters"):
            config.validate()

    def test_validate_invalid_limits(self):
        """Test validate method with out-of-bounds limits."""
        # Max swap too high
        config = PacmanConfig(max_swap_amount_usd=1.01)
        with pytest.raises(ConfigurationError, match="Invalid max_swap_amount_usd"):
            config.validate()

        # Max swap negative
        config.max_swap_amount_usd = -0.1
        with pytest.raises(ConfigurationError, match="Invalid max_swap_amount_usd"):
            config.validate()

        # Max daily too high
        config = PacmanConfig(max_daily_volume_usd=10.01)
        with pytest.raises(ConfigurationError, match="Invalid max_daily_volume_usd"):
            config.validate()

        # Max slippage too high
        config = PacmanConfig(max_slippage_percent=5.1)
        with pytest.raises(ConfigurationError, match="Invalid max_slippage_percent"):
            config.validate()

        # NaN limits
        config = PacmanConfig(max_swap_amount_usd=float('nan'))
        with pytest.raises(ConfigurationError, match="Invalid max_swap_amount_usd"):
            config.validate()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="TEST_KEY=test_value\n#Comment\nINVALID LINE\n")
    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_dot_env_loading(self, mock_file, mock_exists):
        """Test loading from .env file."""
        mock_exists.return_value = True

        # from_env manually parses .env
        config = PacmanConfig.from_env()

        assert os.environ.get("TEST_KEY") == "test_value"
        # Verify it doesn't override existing env vars
        with patch.dict(os.environ, {"EXISTING": "old"}):
            with patch("builtins.open", mock_open(read_data="EXISTING=new")):
                PacmanConfig.from_env()
                assert os.environ["EXISTING"] == "old"
