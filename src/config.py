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
    
    # Safety Limits — loaded from data/governance.json at runtime (edit there to change)
    max_swap_amount_usd: float = 100.00
    max_daily_volume_usd: float = 100.00
    max_slippage_percent: float = 2.0  # 2% default slippage
    lp_padding_percent: float = 2.0  # +2% buffer for EVM math rounding on LP deposits
    
    # Execution Settings
    simulate_mode: bool = False  # Live execution (we NEVER simulate)
    require_confirmation: bool = True  # Always ask before executing
    auto_record: bool = True  # Record all transactions
    verbose_mode: bool = False  # Detailed logging
    
    # Hedera Accounts
    hedera_account_id: Optional[str] = None  # 0.0.xxx format
    robot_account_id: Optional[str] = None   # Dedicated robot account ID
    robot_private_key: Optional[SecureString] = None  # Dedicated robot private key (if independent)

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
        raw_key = os.getenv("PRIVATE_KEY")
        if raw_key:
            config.private_key = SecureString(raw_key)
            del raw_key # Attempt to clear local ref
        
        # Network settings
        config.network = os.getenv("PACMAN_NETWORK", "mainnet")
        if config.network == "testnet":
            config.rpc_url = "https://testnet.hashio.io/api"
        else:
            config.rpc_url = os.getenv("PACMAN_RPC_URL", "https://mainnet.hashio.io/api")
        
        # Safety limits — data/governance.json is the ONLY place to change these.
        # Edit that file, not this code and not .env.
        try:
            gov_path = Path(__file__).parent.parent / "data" / "governance.json"
            if gov_path.exists():
                import json as _gjson
                with open(gov_path) as gf:
                    gov = _gjson.load(gf)
                limits = gov.get("safety_limits", {})
                config.max_swap_amount_usd = cls._safe_float(str(limits.get("max_swap_usd", 100.00)), 100.00)
                config.max_daily_volume_usd = cls._safe_float(str(limits.get("max_daily_usd", 100.00)), 100.00)
        except Exception:
            pass  # Keeps dataclass defaults (100.00) if governance.json is unreadable
        
        # Slippage priority: ENV var > settings.json > default (2.0%)
        max_slippage = 2.0  # Default fallback
        env_slippage = os.getenv("PACMAN_MAX_SLIPPAGE")
        if env_slippage:
            max_slippage = cls._safe_float(env_slippage, 2.0)
        else:
            try:
                settings_path = Path(__file__).parent.parent / "data" / "settings.json"
                if settings_path.exists():
                    import json
                    with open(settings_path) as sf:
                        settings = json.load(sf)
                    saved = settings.get("swap_settings", {}).get("slippage_percent")
                    if saved is not None:
                        max_slippage = cls._safe_float(str(saved), 2.0)
                        
                    saved_pad = settings.get("swap_settings", {}).get("lp_padding_percent")
                    if saved_pad is not None:
                        config.lp_padding_percent = min(cls._safe_float(str(saved_pad), 2.0), 10.0) # hard cap at 10%
            except Exception:
                pass
        config.max_slippage_percent = min(max_slippage, 5.0)  # Hard cap at 5%
        
        # Execution mode
        config.simulate_mode = os.getenv("PACMAN_SIMULATE", "false").lower() == "true"
        config.require_confirmation = os.getenv("PACMAN_CONFIRM", "true").lower() == "true"
        config.verbose_mode = os.getenv("PACMAN_VERBOSE", "false").lower() == "true"
        
        # Hedera account ID (for transaction records)
        config.hedera_account_id = os.getenv("HEDERA_ACCOUNT_ID")
        config.robot_account_id = os.getenv("ROBOT_ACCOUNT_ID")

        # Robot private key (for independent robot accounts with their own key)
        robot_key = os.getenv("ROBOT_PRIVATE_KEY")
        if robot_key:
            config.robot_private_key = SecureString(robot_key)
            del robot_key
        
        # Hands-free: Load robot_account_id from data if not in env
        if not config.robot_account_id:
            try:
                import json
                # 1. Try derived account from accounts.json (Primary intuitive source)
                acc_path = Path(__file__).parent.parent / "data" / "accounts.json"
                if acc_path.exists():
                    with open(acc_path) as f:
                        acc_data = json.load(f)
                        # Priority 1: Match "Bitcoin Rebalancer Daemon" nickname
                        for acc in acc_data:
                            if acc.get("nickname") == "Bitcoin Rebalancer Daemon":
                                config.robot_account_id = acc.get("id")
                                break
                        
                        # Priority 2: Fallback to first derived account if no specific nickname found
                        if not config.robot_account_id:
                            for acc in acc_data:
                                if acc.get("type") == "derived":
                                    config.robot_account_id = acc.get("id")
                                    break
                
                # 2. Fallback to robot_state.json if still not found
                if not config.robot_account_id:
                    state_path = Path(__file__).parent.parent / "data" / "robot_state.json"
                    if state_path.exists():
                        with open(state_path) as f:
                            state_data = json.load(f)
                            config.robot_account_id = state_data.get("robot_account_id")
            except Exception:
                pass
        
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
        if math.isnan(self.max_swap_amount_usd) or self.max_swap_amount_usd < 0:
            raise ConfigurationError(f"Invalid max_swap_amount_usd: ${self.max_swap_amount_usd} (must be a positive number — edit data/governance.json)")

        if math.isnan(self.max_daily_volume_usd) or self.max_daily_volume_usd < 0:
            raise ConfigurationError(f"Invalid max_daily_volume_usd: ${self.max_daily_volume_usd} (must be a positive number — edit data/governance.json)")

        if math.isnan(self.max_slippage_percent) or self.max_slippage_percent > 5.0 or self.max_slippage_percent < 0:
            raise ConfigurationError(f"Invalid max_slippage_percent: {self.max_slippage_percent}% (Max permitted: 5%)")
    
    @staticmethod
    def set_env_value(key: str, value: str):
        """Programmatically update a value in the .env file securely."""
        from pathlib import Path
        import os
        
        env_path = Path(__file__).parent.parent / ".env"
        
        # Also update current session immediately
        os.environ[key] = value

        # Use python-dotenv if available for standard parsing
        try:
            from dotenv import set_key
            set_key(str(env_path), key, value)
            return
        except ImportError:
            pass

        # Fallback: Manual update without risky archival/backup behavior
        if not env_path.exists():
            env_path.write_text(f"{key}={value}\n")
            return

        lines = env_path.read_text().splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"{key}={value}")
            
        env_path.write_text("\n".join(new_lines) + "\n")

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
        print(f"   Max per swap: ${self.max_swap_amount_usd:.2f} (edit data/governance.json)")
        print(f"   Max daily: ${self.max_daily_volume_usd:.2f} (edit data/governance.json)")
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

# Safety limits — edit data/governance.json (NOT here)
# Slippage only (swap/daily limits live in data/governance.json)
PACMAN_MAX_SLIPPAGE={_default_config.max_slippage_percent:.1f}  # Or set in data/settings.json

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
