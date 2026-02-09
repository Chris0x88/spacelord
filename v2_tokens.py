"""
Configuration for SaucerSwap V2 Tokens and Pools
===============================================

Users can add their own token IDs here.
"""

# Common Token IDs (Hedera format)
USDC_ID = "0.0.456858"
WBTC_ID = "0.0.10082597"
WETH_ID = "0.0.541564"

# Fee Tiers (in hundredths of a basis point, e.g. 1500 = 0.15%)
FEE_LOW = 100    # 0.01%
FEE_MEDIUM = 500 # 0.05%
FEE_STABLE = 1500 # 0.15% (Common for USDC/HBAR)
FEE_HIGH = 10000 # 1.00%

# Default configuration
DEFAULT_FEE = FEE_STABLE
