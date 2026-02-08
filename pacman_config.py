#!/usr/bin/env python3
"""
Pacman Config - Secure Configuration Management
Handles private keys, RPC endpoints, and safety limits.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

@dataclass
class PacmanConfig:
    """Secure configuration for Pacman trading."""
    
    # Required
    private_key: Optional[str] = None
    
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
    
    # Hedera Accounts
    hedera_account_id: Optional[str] = None  # 0.0.xxx format
    
    @classmethod
    def from_env(cls) -> "PacmanConfig":
        """Load configuration from environment variables."""
        
        # Load from .env file if present
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        config = cls()
        
        # Required: Private key
        config.private_key = os.getenv("PACMAN_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
        if not config.private_key:
            print("⚠️  Warning: No private key found. Set PACMAN_PRIVATE_KEY in .env")
            print("   Running in read-only mode (quotes only)")
        
        # Network settings
        config.network = os.getenv("PACMAN_NETWORK", "mainnet")
        if config.network == "testnet":
            config.rpc_url = "https://testnet.hashio.io/api"
        else:
            config.rpc_url = os.getenv("PACMAN_RPC_URL", "https://mainnet.hashio.io/api")
        
        # Safety limits (cannot be overridden above hardcoded max)
        max_swap = float(os.getenv("PACMAN_MAX_SWAP", "1.00"))
        config.max_swap_amount_usd = min(max_swap, 1.00)  # Hard cap at $1
        
        max_daily = float(os.getenv("PACMAN_MAX_DAILY", "10.00"))
        config.max_daily_volume_usd = min(max_daily, 10.00)  # Hard cap at $10
        
        max_slippage = float(os.getenv("PACMAN_MAX_SLIPPAGE", "1.0"))
        config.max_slippage_percent = min(max_slippage, 5.0)  # Hard cap at 5%
        
        # Execution mode
        config.simulate_mode = os.getenv("PACMAN_SIMULATE", "true").lower() == "true"
        config.require_confirmation = os.getenv("PACMAN_CONFIRM", "true").lower() == "true"
        
        # Hedera account ID (for transaction records)
        config.hedera_account_id = os.getenv("HEDERA_ACCOUNT_ID")
        
        return config
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration is safe for trading."""
        
        if not self.private_key:
            return False, "No private key configured"
        
        # Validate private key format (should be 64 hex chars)
        clean_key = self.private_key.replace("0x", "")
        if len(clean_key) != 64:
            return False, f"Invalid private key format (expected 64 chars, got {len(clean_key)})"
        
        try:
            int(clean_key, 16)
        except ValueError:
            return False, "Private key contains non-hex characters"
        
        # Validate limits
        if self.max_swap_amount_usd > 1.00:
            return False, f"max_swap_amount_usd exceeds $1.00 limit: ${self.max_swap_amount_usd}"
        
        if self.max_daily_volume_usd > 10.00:
            return False, f"max_daily_volume_usd exceeds $10.00 limit: ${self.max_daily_volume_usd}"
        
        return True, "Configuration valid"
    
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

def create_env_template():
    """Create a template .env file."""
    template = """# Pacman Configuration
# Copy this to .env and fill in your values

# Required for live trading
PACMAN_PRIVATE_KEY=your_private_key_here_without_0x_prefix

# Optional: Hedera account ID (0.0.xxx format)
HEDERA_ACCOUNT_ID=0.0.123456

# Network (mainnet or testnet)
PACMAN_NETWORK=mainnet

# Safety limits (max $1.00 per swap, $10.00 daily)
PACMAN_MAX_SWAP=1.00
PACMAN_MAX_DAILY=10.00
PACMAN_MAX_SLIPPAGE=1.0

# Execution mode
PACMAN_SIMULATE=true
PACMAN_CONFIRM=true
"""
    
    env_path = Path(__file__).parent / ".env.template"
    with open(env_path, 'w') as f:
        f.write(template)
    
    print(f"✅ Created {env_path}")
    print("   Copy to .env and add your private key to enable live trading")

# CLI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        create_env_template()
    else:
        config = PacmanConfig.from_env()
        config.print_status()
        
        valid, message = config.validate()
        if valid:
            print("\n✅ Configuration is valid and safe for trading")
        else:
            print(f"\n❌ Configuration error: {message}")
