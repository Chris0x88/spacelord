"""
Configuration Management
========================

This module handles all configuration for the BTC Rebalancer bot.
It loads settings from environment variables with sensible defaults.

IMPORTANT: Never commit .env files or expose private keys!

Environment Variables:
    PRIVATE_KEY: Your Hedera account private key (required)
    RPC_URL: Primary RPC endpoint (your Railway RPC recommended)
    MAINNET_RPC_URL: Fallback RPC endpoint (public Hashio)
    
Configuration can be overridden at runtime by passing a config dict
to the bot initialization.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present (for local development)
# Priority: robot/.env > .env (root)
if Path("robot/.env").exists():
    load_dotenv(Path("robot/.env"))
if Path(".env").exists():
    load_dotenv(Path(".env"))


@dataclass
class RPCConfig:
    """
    RPC Connection Configuration
    
    The bot uses a primary RPC with automatic fallback to backup RPC.
    
    Priority order for local development:
    1. Local RPC relay (http://localhost:7546) if running
    2. Public Hashio (reliable, slightly rate-limited)
    3. Railway RPC (may have timeout issues with mirror node)
    
    Attributes:
        primary_url: Main RPC endpoint (Hashio is reliable default)
        fallback_url: Backup RPC endpoint
        timeout_seconds: How long to wait for RPC responses
        max_retries: Number of retry attempts before failing
    """
    # Default to Hashio (reliable and always available)
    # For local dev, set RPC_URL=http://localhost:7546 if running local relay
    primary_url: str = field(default_factory=lambda: os.getenv(
        "RPC_URL", 
        "https://mainnet.hashio.io/api"
    ))
    # Fallback to Railway RPC 
    fallback_url: str = field(default_factory=lambda: os.getenv(
        "MAINNET_RPC_URL", 
        "https://hiero-json-rpc-relay-production.up.railway.app"
    ))
    timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class TradingConfig:
    """
    Trading Parameters
    
    These settings control how the bot executes trades.
    Adjust based on your risk tolerance and portfolio size.
    
    Attributes:
        slippage_percent: Maximum acceptable slippage (0.5 = 0.5%)
                         Higher = more likely to execute, but worse price
        min_trade_usdc: Minimum trade size in USDC terms
                       Prevents dust trades that cost more in fees
        fee_tier: SaucerSwap V2 pool fee tier (1500 = 0.15%)
        hbar_reserve_min: Minimum HBAR to keep for gas (prevents wallet lockup)
        hbar_per_trade: Estimated HBAR cost per trade (swap + potential approve)
    """
    slippage_percent: float = field(default_factory=lambda: float(
        os.getenv("SLIPPAGE_PERCENT", "0.5")
    ))
    min_trade_usdc: float = field(default_factory=lambda: float(
        os.getenv("MIN_TRADE_USDC", "1.0")
    ))
    fee_tier: int = 1500  # 0.15% - standard SaucerSwap V2 fee
    
    # HBAR Reserve System - prevents wallet from running out of gas
    hbar_reserve_min: float = field(default_factory=lambda: float(
        os.getenv("HBAR_RESERVE_MIN", "5.0")  # Keep at least 5 HBAR
    ))
    hbar_per_trade: float = field(default_factory=lambda: float(
        os.getenv("HBAR_PER_TRADE", "0.3")  # ~0.3 HBAR per trade (swap + approve)
    ))


@dataclass
class RebalanceConfig:
    """
    Rebalancing Strategy Configuration
    
    Controls when and how the bot rebalances the portfolio.
    
    Attributes:
        interval_seconds: How often to check if rebalancing is needed
                         3600 = hourly, 86400 = daily
        threshold_percent: Minimum deviation from target before rebalancing
                          Prevents excessive trading on small movements
        extreme_threshold_percent: Threshold for immediate rebalance
                                  Triggers on large price spikes
    """
    interval_seconds: int = field(default_factory=lambda: int(
        os.getenv("REBALANCE_INTERVAL_SECONDS", "3600")
    ))
    # V3 UPDATE: Default changed from 1.0 to 15.0 based on backtest research
    # 15% threshold achieves 1.51x vs HODL (up from 1.09x) with 40% fewer trades
    threshold_percent: float = field(default_factory=lambda: float(
        os.getenv("REBALANCE_THRESHOLD_PERCENT", "15.0")
    ))
    extreme_threshold_percent: float = field(default_factory=lambda: float(
        os.getenv("EXTREME_THRESHOLD_PERCENT", "5.0")
    ))


@dataclass
class HyperliquidConfig:
    """
    Hyperliquid Perps Configuration
    """
    private_key: Optional[str] = field(default_factory=lambda: os.getenv("HYPERLIQUID_PRIVATE_KEY"))
    mainnet: bool = field(default_factory=lambda: os.getenv("HYPERLIQUID_MAINNET", "false").lower() == "true")
    # Default to 1x leverage for safety
    leverage: int = 1


@dataclass
class Config:
    """
    Master Configuration Container
    
    Aggregates all configuration sections. Create an instance to access
    all bot settings.
    
    Usage:
        config = Config()
        print(config.trading.slippage_percent)
        print(config.rpc.primary_url)
    
    Override at runtime:
        config = Config()
        config.trading.min_trade_usdc = 5.0
    """
    rpc: RPCConfig = field(default_factory=RPCConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    rebalance: RebalanceConfig = field(default_factory=RebalanceConfig)
    hyperliquid: HyperliquidConfig = field(default_factory=HyperliquidConfig)
    
    # Hedera chain ID (295 = mainnet, 296 = testnet)
    chain_id: int = 295
    
    # Private keys (loaded from environment)
    private_key: Optional[str] = field(default_factory=lambda: 
        os.getenv("PRIVATE_KEY")
    )
    
    # Arbitrum configuration
    arbitrum_private_key: Optional[str] = field(default_factory=lambda: 
        os.getenv("ARBITRUM_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
    )
    arbitrum_rpc_url: str = field(default_factory=lambda: 
        os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc")
    )
    
    def validate(self) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            True if valid, raises ValueError if not
        """
        if not self.private_key:
            raise ValueError(
                "PRIVATE_KEY environment variable is required. "
                "Set it in your .env file or Railway dashboard."
            )
        
        if not self.rpc.primary_url:
            raise ValueError(
                "RPC_URL environment variable is required. "
                "Use your Railway RPC or https://mainnet.hashio.io/api"
            )
        
        return True


def get_config() -> Config:
    """
    Factory function to create and validate configuration.
    
    Returns:
        Validated Config instance
        
    Raises:
        ValueError: If required configuration is missing
    """
    config = Config()
    config.validate()
    return config


# =============================================================================
# QUICK REFERENCE: Environment Variables
# =============================================================================
#
# Required:
#   PRIVATE_KEY          Your Hedera private key (hex string)
#
# RPC Settings:
#   RPC_URL              Primary RPC (default: hashio)
#   MAINNET_RPC_URL      Fallback RPC (default: hashio)
#
# Trading Settings:
#   SLIPPAGE_PERCENT     Max slippage (default: 0.5)
#   MIN_TRADE_USDC       Min trade size (default: 1.0)
#
# Rebalancing Settings:
#   REBALANCE_INTERVAL_SECONDS    Check interval (default: 3600)
#   REBALANCE_THRESHOLD_PERCENT   Min deviation (default: 1.0)
#   EXTREME_THRESHOLD_PERCENT     Spike threshold (default: 5.0)
#
# =============================================================================
