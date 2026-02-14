"""
SaucerSwap V2 Adapter
======================

Thin wrapper around the proven SaucerSwapV2 implementation from the
parent `python/` directory. This ensures the rebalancer bot uses the
exact same quoting path that we have already battle-tested:

- Quoter contract: 0.0.3949424
- Router contract: 0.0.3949434
- Direct USDC/HTS-WBTC pool: 0.0.10092996 (fee 1500)

This module exposes simple helpers for USDC ↔ HTS-WBTC quotes.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from web3 import Web3

from saucerswap_v2_client import SaucerSwapV2, hedera_id_to_evm


USDC_ID = "0.0.456858"      # Native USDC
HTS_WBTC_ID = "0.0.10082597"  # HTS-WBTC in high-liquidity pool
FEE_TIER = 1500              # 0.15%


@dataclass
class DirectQuote:
    amount_in: int
    amount_out: int


class SaucerSwapAdapter:
    """Adapter around local SaucerSwapV2 client for direct USDC/HTS-WBTC quotes."""

    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None):
        # Load env from local btc_rebalancer/.env only
        here = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(here, ".env"))

        rpc = rpc_url or os.getenv("RPC_URL") or "https://mainnet.hashio.io/api"
        pk = private_key or os.getenv("PRIVATE_KEY")
        if not pk:
            raise RuntimeError("PRIVATE_KEY not set for SaucerSwapAdapter")

        self.w3 = Web3(Web3.HTTPProvider(rpc))
        self.ss = SaucerSwapV2(self.w3, network="mainnet", private_key=pk)

        self.usdc = hedera_id_to_evm(USDC_ID)
        self.wbtc = hedera_id_to_evm(HTS_WBTC_ID)
        self.fee = FEE_TIER

    def quote_usdc_to_wbtc(self, amount_in: int) -> DirectQuote:
        """Quote USDC -> HTS-WBTC using direct pool (single hop)."""
        q = self.ss.get_quote_single(self.usdc, self.wbtc, amount_in, self.fee)
        return DirectQuote(amount_in=amount_in, amount_out=q["amountOut"])

    def quote_wbtc_to_usdc(self, amount_in: int) -> DirectQuote:
        """Quote HTS-WBTC -> USDC using direct pool (single hop)."""
        q = self.ss.get_quote_single(self.wbtc, self.usdc, amount_in, self.fee)
        return DirectQuote(amount_in=amount_in, amount_out=q["amountOut"])


_adapter_singleton: Optional[SaucerSwapAdapter] = None


def get_adapter() -> SaucerSwapAdapter:
    global _adapter_singleton
    if _adapter_singleton is None:
        _adapter_singleton = SaucerSwapAdapter()
    return _adapter_singleton
