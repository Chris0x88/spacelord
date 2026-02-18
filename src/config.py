#!/usr/bin/env python3
"""
Pacman Config - Secure Configuration Management
Handles private keys, RPC endpoints, and safety limits.
"""

import os
import math
import secrets
import itertools
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from src.errors import ConfigurationError

class SecureString:
    """
    A string wrapper that obfuscates the content in memory using XOR with a random key.
    Prevents casual inspection via memory dumps or accidental printing.
    """
    def __init__(self, secret: str):
        if not secret:
            self._data = b''
            self._key = b''
            return

        self._key = secrets.token_bytes(32)
        secret_bytes = secret.encode('utf-8')
        # XOR obfuscation
        self._data = bytes(a ^ b for a, b in zip(secret_bytes, itertools.cycle(self._key)))

    def reveal(self) -> str:
        """Decrypts and returns the original string."""
        if not self._data:
            return ""

        decrypted_bytes = bytes(a ^ b for a, b in zip(self._data, itertools.cycle(self._key)))
        return decrypted_bytes.decode('utf-8')

    def __repr__(self):
        return "<SecureString: ***HIDDEN***>"

    def __str__(self):
        return "<SecureString: ***HIDDEN***>"

    def __bool__(self):
        return bool(self._data)

@dataclass
class PacmanConfig:
    """Secure configuration for Pacman trading."""
    
    # Required
    private_key: Optional[SecureString] = None
    
    # Network
    network: str = "mainnet"
    rpc_url: str = "https://mainnet.hashio.io/api"
    
    # Safety Limits (HARD CODED MAXIMUMS)
    max_swap_amount_usd: float = 1.00  # $1.00 maximum per swap
    max_daily_volume_usd: float = 10.00  # $10.00 daily limit
    max_slippage_percent: float = 1.0  # 1% max slippage
    
    # Execution Settings
    simulate_mode: bool = True  # Start in simulation
    require_confirmation: bool = True  # Always ask before executing
    auto_record: bool = True  # Record all transactions
    verbose_mode: bool = False  # Detailed logging
    
    # Hedera Accounts
    hedera_account_id: Optional[str] = None  # 0.0.xxx format

    @property
    def debug(self) -> bool:
        return self.verbose_mode

    @debug.setter
    def debug(self, value: bool):
        self.verbose_mode = value

    @staticmethod
    def _safe_float(val: Optional[str], default: float) -> float:
        """Safely parse float from string, handling NaN and invalid values."""
        if val is None:
            return default
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return default
            return f
        except (ValueError, TypeError):
            return default
    
    @classmethod
    def from_env(cls) -> "PacmanConfig":
        """Load configuration from environment variables."""
        
        # Load from .env file if present
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if key not in os.environ:
                            os.environ[key] = value
        
        config = cls()
        
        # Required: Private key (Securely Wrapped)
        # PRIORITIZE standard PRIVATE_KEY, fallback to legacy PACMAN_PRIVATE_KEY
        raw_key = os.getenv("PRIVATE_KEY") or os.getenv("PACMAN_PRIVATE_KEY")
        if raw_key:
            config.private_key = SecureString(raw_key)
            del raw_key # Attempt to clear local ref
        
        # Network settings
        config.network = os.getenv("PACMAN_NETWORK", "mainnet")
        if config.network == "testnet":
            config.rpc_url = "https://testnet.hashio.io/api"
        else:
            config.rpc_url = os.getenv("PACMAN_RPC_URL", "https://mainnet.hashio.io/api")
        
        # Safety limits (cannot be overridden above hardcoded max)
        max_swap = cls._safe_float(os.getenv("PACMAN_MAX_SWAP"), 1.00)
        config.max_swap_amount_usd = min(max_swap, 1.00)  # Hard cap at $1
        
        max_daily = cls._safe_float(os.getenv("PACMAN_MAX_DAILY"), 10.00)
        config.max_daily_volume_usd = min(max_daily, 10.00)  # Hard cap at $10
        
        max_slippage = cls._safe_float(os.getenv("PACMAN_MAX_SLIPPAGE"), 1.0)
        config.max_slippage_percent = min(max_slippage, 5.0)  # Hard cap at 5%
        
        # Execution mode
        config.simulate_mode = os.getenv("PACMAN_SIMULATE", "true").lower() == "true"
        config.require_confirmation = os.getenv("PACMAN_CONFIRM", "true").lower() == "true"
        config.verbose_mode = os.getenv("PACMAN_VERBOSE", "false").lower() == "true"
        
        # Hedera account ID (for transaction records)
        config.hedera_account_id = os.getenv("HEDERA_ACCOUNT_ID")
        
        return config
    
    def validate(self) -> None:
        """Validate configuration is safe for trading."""
        
        if not self.simulate_mode:
            if not self.private_key:
                raise ConfigurationError("Private key required for live execution (Set PRIVATE_KEY in .env)")

            # Validate private key format (should be 64 hex chars)
            # Reveal momentarily for validation
            clean_key = self.private_key.reveal().replace("0x", "")
            try:
                if len(clean_key) != 64:
                    raise ConfigurationError(f"Invalid private key format (expected 64 hex chars, got {len(clean_key)})")

                try:
                    int(clean_key, 16)
                except ValueError:
                    raise ConfigurationError("Private key contains non-hex characters")
            finally:
                del clean_key # Ensure cleanup
        
        # Validate limits
        if math.isnan(self.max_swap_amount_usd) or self.max_swap_amount_usd > 1.00 or self.max_swap_amount_usd < 0:
            raise ConfigurationError(f"Invalid max_swap_amount_usd: ${self.max_swap_amount_usd} (Max permitted: $1.00)")
        
        if math.isnan(self.max_daily_volume_usd) or self.max_daily_volume_usd > 10.00 or self.max_daily_volume_usd < 0:
            raise ConfigurationError(f"Invalid max_daily_volume_usd: ${self.max_daily_volume_usd} (Max permitted: $10.00)")

        if math.isnan(self.max_slippage_percent) or self.max_slippage_percent > 5.0 or self.max_slippage_percent < 0:
            raise ConfigurationError(f"Invalid max_slippage_percent: {self.max_slippage_percent}% (Max permitted: 5%)")
    
    def print_status(self):
        """Print current configuration status."""
        print("="*60)
        print("🔧 PACMAN CONFIGURATION")
        print("="*60)
        print(f"Network: {self.network}")
        print(f"RPC: {self.rpc_url}")
        print(f"Account: {self.hedera_account_id or 'Not set'}")
        print(f"Private Key: {'✅ Configured' if self.private_key else '❌ Not set'}")
        print()
        print("🛡️  Safety Limits (HARD CODED):")
        print(f"   Max per swap: ${self.max_swap_amount_usd:.2f}")
        print(f"   Max daily: ${self.max_daily_volume_usd:.2f}")
        print(f"   Max slippage: {self.max_slippage_percent:.1f}%")
        print()
        print("⚙️  Execution Mode:")
        print(f"   Simulation: {'✅ ON' if self.simulate_mode else '❌ OFF'}")
        print(f"   Confirmation required: {'✅ YES' if self.require_confirmation else '❌ NO'}")
        print(f"   Auto-recording: {'✅ ON' if self.auto_record else '❌ OFF'}")
        print("="*60)

# ---------------------------------------------------------------------------
# Environment Template
# ---------------------------------------------------------------------------

_default_config = PacmanConfig()

ENV_TEMPLATE = f"""# Pacman Configuration
# Copy this to .env and fill in your values

# Required for live trading (Standard Ethereum Format)
PRIVATE_KEY=your_private_key_here_without_0x_prefix

# Optional: Hedera account ID (0.0.xxx format)
HEDERA_ACCOUNT_ID=0.0.123456

# Network (mainnet or testnet)
PACMAN_NETWORK={_default_config.network}

# Safety limits (max ${_default_config.max_swap_amount_usd:.2f} per swap, ${_default_config.max_daily_volume_usd:.2f} daily)
PACMAN_MAX_SWAP={_default_config.max_swap_amount_usd:.2f}
PACMAN_MAX_DAILY={_default_config.max_daily_volume_usd:.2f}
PACMAN_MAX_SLIPPAGE={_default_config.max_slippage_percent:.1f}

# Execution mode
PACMAN_SIMULATE={'true' if _default_config.simulate_mode else 'false'}
PACMAN_CONFIRM={'true' if _default_config.require_confirmation else 'false'}
PACMAN_VERBOSE={'true' if _default_config.verbose_mode else 'false'}
"""

def create_env_template():
    """Create a template .env file and initial .env if needed."""
    template_path = Path(__file__).parent.parent / ".env.template"
    env_path = Path(__file__).parent.parent / ".env"
    
    # 1. Update/Create .env.template
    with open(template_path, 'w') as f:
        f.write(ENV_TEMPLATE)
    print(f"✅ Updated {template_path}")

    # 2. Create .env if it doesn't exist
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(ENV_TEMPLATE)
        print(f"✅ Created {env_path}")
        print("   Added default configuration. Please add your private key to .env")
    else:
        print(f"ℹ️  {env_path} already exists. Skipping creation.")

# CLI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        create_env_template()
    else:
        try:
            config = PacmanConfig.from_env()
            config.print_status()
            config.validate()
            print("\n✅ Configuration is valid and safe for trading")
        except ConfigurationError as e:
            print(f"\n❌ Configuration error: {e}")
