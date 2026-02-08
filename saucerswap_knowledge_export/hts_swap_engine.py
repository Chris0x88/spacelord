"""
Swap Execution Engine
=====================

This module handles all interactions with SaucerSwap V2 on Hedera.
It provides a clean interface for:
- Getting swap quotes
- Executing swaps
- Managing token approvals
- Querying balances

ARCHITECTURE NOTES:
- Uses Web3.py for Ethereum-compatible interactions
- Supports both single-hop and multi-hop swaps
- Includes automatic RPC fallback for reliability
- All swap functions are stateless and can be retried

KEY CONCEPTS:
- Path Encoding: Tokens and fees are packed into a bytes path
- WHBAR: Used internally for routing, never held by user
- Approvals: HTS tokens require high gas (1M) for approvals
- Quotes: Always get a quote before executing to know expected output

IMPORTANT: After BUY_BTC swaps, ERC20 WBTC is automatically unwrapped to HTS WBTC (0.0.10082597)
via the SaucerSwap ERC20Wrapper contract (0.0.9675688). This ensures compatibility with HashPack.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from web3 import Web3
from web3.exceptions import ContractLogicError, BadFunctionCallOutput

from config import Config, get_config
from tokens import Token, SwapPair, TOKENS, get_swap_pair
from saucerswap_adapter import get_adapter
from erc20_to_hts_wrapper import unwrap_all_erc20_wbtc, check_wbtc_balances

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# CONTRACT ADDRESSES (Hedera Mainnet)
# =============================================================================

# SaucerSwap V2 Quoter - Used to get swap quotes without executing
# IMPORTANT: This must be 0.0.3949424 for V2 liquidity pools.
# Hedera ID 0.0.3949424 -> EVM 0x00000000000000000000000000000000003c4370
QUOTER_ADDRESS = "0x00000000000000000000000000000000003c4370"  # 0.0.3949424

# SaucerSwap V2 Router - Used to execute swaps
ROUTER_ADDRESS = "0x00000000000000000000000000000000003c437A"  # 0.0.3949434


# =============================================================================
# CONTRACT ABIs (Minimal - only functions we need)
# =============================================================================

QUOTER_ABI = [
    {
        "inputs": [
            {"name": "path", "type": "bytes"},
            {"name": "amountIn", "type": "uint256"}
        ],
        "name": "quoteExactInput",
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceX96AfterList", "type": "uint160[]"},
            {"name": "initializedTicksCrossedList", "type": "uint32[]"},
            {"name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "path", "type": "bytes"},
                    {"name": "recipient", "type": "address"},
                    {"name": "deadline", "type": "uint256"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMinimum", "type": "uint256"}
                ],
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "exactInput",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "data", "type": "bytes[]"}],
        "name": "multicall",
        "outputs": [{"name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "amountMinimum", "type": "uint256"},
            {"name": "recipient", "type": "address"}
        ],
        "name": "unwrapWETH9",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "refundETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


# =============================================================================
# PATH ENCODING
# =============================================================================

def encode_path(tokens: List[Token], fees: List[int]) -> bytes:
    """
    Encode a swap path for SaucerSwap V2.
    
    The path format is: token0 + fee0 + token1 + fee1 + token2 + ...
    Each token is 20 bytes (address) and each fee is 3 bytes.
    
    Args:
        tokens: List of Token objects in swap order
        fees: List of fee tiers (length = len(tokens) - 1)
        
    Returns:
        Encoded path as bytes
        
    Example:
        # USDC -> HBAR -> WBTC with 0.15% fee on each hop
        path = encode_path(
            [TOKENS["USDC"], TOKENS["WHBAR"], TOKENS["WBTC"]],
            [1500, 1500]
        )
    """
    if len(fees) != len(tokens) - 1:
        raise ValueError(f"Expected {len(tokens)-1} fees, got {len(fees)}")
    
    # Start with first token address (20 bytes, no checksum)
    path = bytes.fromhex(tokens[0].evm_address[2:].lower())
    
    # Add each fee + token pair
    for fee, token in zip(fees, tokens[1:]):
        # Fee is 3 bytes, big-endian
        path += fee.to_bytes(3, "big")
        # Token address is 20 bytes
        path += bytes.fromhex(token.evm_address[2:].lower())
    
    return path


# =============================================================================
# SWAP ENGINE CLASS
# =============================================================================

@dataclass
class QuoteResult:
    """
    Result of a swap quote.
    
    Attributes:
        amount_in: Input amount in raw token units
        amount_out: Expected output in raw token units
        price_impact: Estimated price impact (not always available)
        path: The swap path used
    """
    amount_in: int
    amount_out: int
    price_impact: float = 0.0
    path: bytes = b""


@dataclass
class SwapResult:
    """
    Result of an executed swap.
    
    Attributes:
        success: Whether the swap succeeded
        tx_hash: Transaction hash
        amount_in: Actual input amount
        amount_out: Actual output amount (if success)
        gas_used: Gas consumed
        error: Error message (if failed)
    """
    success: bool
    tx_hash: str
    amount_in: int = 0
    amount_out: int = 0
    gas_used: int = 0
    error: str = ""


class SwapEngine:
    """
    Core swap execution engine for SaucerSwap V2.
    
    This class handles all swap-related operations:
    - Getting quotes for swaps
    - Executing swaps with slippage protection
    - Managing token approvals
    - Querying token balances
    
    Usage:
        engine = SwapEngine(config)
        
        # Get a quote
        quote = engine.get_quote(swap_pair, amount)
        
        # Execute the swap
        result = engine.execute_swap(swap_pair, amount, min_out)
    
    IMPORTANT NOTES:
    - Always get a quote before executing to know expected output
    - Approvals are required before first swap of each token
    - HTS tokens on Hedera require high gas (1M) for approvals
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the swap engine.
        
        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or get_config()
        
        # Initialize Web3 with primary RPC
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc.primary_url))
        self._fallback_w3 = None  # Lazy-loaded
        self._using_fallback = False
        
        # Verify connection
        if not self.w3.is_connected():
            logger.warning("Primary RPC not connected, trying fallback...")
            self._switch_to_fallback()
        
        # Load account from private key
        self.account = self.w3.eth.account.from_key(self.config.private_key)
        self.eoa = self.account.address
        
        # Initialize contracts
        self.quoter = self.w3.eth.contract(
            address=Web3.to_checksum_address(QUOTER_ADDRESS),
            abi=QUOTER_ABI
        )
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(ROUTER_ADDRESS),
            abi=ROUTER_ABI
        )
        
        logger.info(f"SwapEngine initialized")
        logger.info(f"  Account: {self.eoa}")
        logger.info(f"  RPC: {self.config.rpc.primary_url}")
    
    def _switch_to_fallback(self):
        """Switch to fallback RPC if primary fails."""
        if self._fallback_w3 is None:
            self._fallback_w3 = Web3(Web3.HTTPProvider(
                self.config.rpc.fallback_url
            ))
        
        if self._fallback_w3.is_connected():
            self.w3 = self._fallback_w3
            self._using_fallback = True
            logger.info(f"Switched to fallback RPC: {self.config.rpc.fallback_url}")
        else:
            raise ConnectionError("Both primary and fallback RPC failed")
    
    # =========================================================================
    # BALANCE QUERIES
    # =========================================================================
    
    def get_balance(self, token: Token) -> int:
        """
        Get token balance for the bot's account.
        
        Args:
            token: Token to check balance for
            
        Returns:
            Balance in raw token units
        """
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token.evm_address),
            abi=ERC20_ABI
        )
        return contract.functions.balanceOf(self.eoa).call()
    
    def get_balance_human(self, token: Token) -> float:
        """
        Get token balance in human-readable format.
        
        Args:
            token: Token to check balance for
            
        Returns:
            Balance as float (e.g., 10.5 USDC)
        """
        raw = self.get_balance(token)
        return token.to_human(raw)
    
    def get_hbar_balance(self) -> float:
        """Get native HBAR balance in human-readable format."""
        wei = self.w3.eth.get_balance(self.eoa)
        return wei / 10**18  # HBAR has 18 decimals in EVM context
    
    # =========================================================================
    # APPROVALS
    # =========================================================================
    
    def get_allowance(self, token: Token) -> int:
        """
        Get current allowance for the router to spend token.
        
        Args:
            token: Token to check allowance for
            
        Returns:
            Allowance in raw token units
        """
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token.evm_address),
            abi=ERC20_ABI
        )
        return contract.functions.allowance(
            self.eoa,
            Web3.to_checksum_address(ROUTER_ADDRESS)
        ).call()
    
    def approve(self, token: Token, amount: Optional[int] = None) -> str:
        """
        Approve the router to spend tokens.
        
        IMPORTANT: HTS tokens on Hedera require high gas (1M) for approvals.
        This is handled automatically.
        
        Args:
            token: Token to approve
            amount: Amount to approve (None = max uint256)
            
        Returns:
            Transaction hash
        """
        if amount is None:
            amount = 2**256 - 1  # Max approval
        
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token.evm_address),
            abi=ERC20_ABI
        )
        
        # Build transaction with high gas for HTS tokens
        tx = contract.functions.approve(
            Web3.to_checksum_address(ROUTER_ADDRESS),
            amount
        ).build_transaction({
            "from": self.eoa,
            "gas": 1000000,  # High gas required for HTS tokens
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.config.chain_id
        })
        
        # Sign and send
        signed = self.w3.eth.account.sign_transaction(tx, self.config.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        logger.info(f"Approval tx sent: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt["status"] != 1:
            raise RuntimeError(f"Approval failed: {tx_hash.hex()}")
        
        logger.info(f"Approval confirmed, gas used: {receipt['gasUsed']}")
        return tx_hash.hex()
    
    def ensure_approval(self, token: Token, amount: int) -> bool:
        """
        Ensure token is approved for at least the specified amount.
        
        Args:
            token: Token to check/approve
            amount: Minimum required allowance
            
        Returns:
            True if approval was needed and executed
        """
        current = self.get_allowance(token)
        if current >= amount:
            logger.debug(f"{token.symbol} already approved: {token.to_human(current)}")
            return False
        
        logger.info(f"Approving {token.symbol}...")
        self.approve(token, amount)
        return True
    
    # =========================================================================
    # QUOTES
    # =========================================================================

    def _call_quoter(self, path: bytes, amount_in: int) -> int:
        """Internal helper to call quoter with primary then fallback RPC.
        
        This first tries the current provider (Railway). If the call reverts
        or returns empty (BadFunctionCallOutput), it will retry once on the
        fallback RPC (Hashio mainnet) using the same quoter contract.
        """
        # First attempt on current provider
        try:
            result = self.quoter.functions.quoteExactInput(path, amount_in).call()
            return result[0]
        except (ContractLogicError, BadFunctionCallOutput, ValueError) as e:
            logger.error(f"Primary quoter call failed: {e}")
            # If we're already on fallback, just re-raise
            if self._using_fallback:
                raise
            # Switch provider and re-initialize contracts
            self._switch_to_fallback()
            self.quoter = self.w3.eth.contract(
                address=Web3.to_checksum_address(QUOTER_ADDRESS),
                abi=QUOTER_ABI
            )
            self.router = self.w3.eth.contract(
                address=Web3.to_checksum_address(ROUTER_ADDRESS),
                abi=ROUTER_ABI
            )
            # Retry once on fallback
            result = self.quoter.functions.quoteExactInput(path, amount_in).call()
            return result[0]

    def get_quote(self, swap_pair: SwapPair, amount_in: int) -> QuoteResult:
        """
        Get a quote for a swap without executing.
        
        Args:
            swap_pair: The swap pair configuration
            amount_in: Input amount in raw token units
            
        Returns:
            QuoteResult with expected output
            
        Raises:
            ContractLogicError: If quote fails (e.g., no liquidity)
        """
        # Special-case BTC pairs to use the proven SaucerSwapV2 adapter
        if (
            swap_pair.token_in.hedera_id == TOKENS["USDC"].hedera_id and swap_pair.token_out.hedera_id == TOKENS["WBTC"].hedera_id
        ) or (
            swap_pair.token_in.hedera_id == TOKENS["WBTC"].hedera_id and swap_pair.token_out.hedera_id == TOKENS["USDC"].hedera_id
        ):
            adapter = get_adapter()
            if swap_pair.token_in.hedera_id == TOKENS["USDC"].hedera_id:
                q = adapter.quote_usdc_to_wbtc(amount_in)
            else:
                q = adapter.quote_wbtc_to_usdc(amount_in)
            return QuoteResult(
                amount_in=amount_in,
                amount_out=q.amount_out,
                path=b""  # path is handled internally by SaucerSwapV2
            )

        # Default path: use generic quoter with encoded path
        path_tokens = swap_pair.get_path()
        fees = swap_pair.get_fees()
        path = encode_path(path_tokens, fees)
        
        try:
            amount_out = self._call_quoter(path, amount_in)
            return QuoteResult(
                amount_in=amount_in,
                amount_out=amount_out,
                path=path
            )
        except (ContractLogicError, BadFunctionCallOutput, ValueError) as e:
            logger.error(f"Quote failed for {swap_pair.name}: {e}")
            raise
    
    def get_quote_human(
        self, 
        swap_pair: SwapPair, 
        amount_in: float
    ) -> Tuple[float, float]:
        """
        Get a quote using human-readable amounts.
        
        Args:
            swap_pair: The swap pair configuration
            amount_in: Input amount (e.g., 10.0 for 10 USDC)
            
        Returns:
            Tuple of (amount_in, expected_amount_out) in human format
        """
        raw_in = swap_pair.token_in.to_raw(amount_in)
        quote = self.get_quote(swap_pair, raw_in)
        human_out = swap_pair.token_out.to_human(quote.amount_out)
        return (amount_in, human_out)
    
    # =========================================================================
    # SWAP EXECUTION
    # =========================================================================
    
    def execute_swap(
        self,
        swap_pair: SwapPair,
        amount_in: int,
        min_amount_out: int,
        deadline_seconds: int = 120
    ) -> SwapResult:
        """
        Execute a swap on SaucerSwap V2.
        
        Args:
            swap_pair: The swap pair configuration
            amount_in: Input amount in raw token units
            min_amount_out: Minimum acceptable output (slippage protection)
            deadline_seconds: Transaction deadline in seconds from now
            
        Returns:
            SwapResult with transaction details
        """
        # Build path
        path_tokens = swap_pair.get_path()
        fees = swap_pair.get_fees()
        path = encode_path(path_tokens, fees)
        
        # Calculate deadline (Hedera requires milliseconds, not seconds)
        deadline = int(time.time() * 1000) + (deadline_seconds * 1000)
        
        # Build exactInput params
        params = (
            path,
            self.eoa,
            deadline,
            amount_in,
            min_amount_out
        )
        
        try:
            # Build transaction
            tx = self.router.functions.exactInput(params).build_transaction({
                "from": self.eoa,
                "value": 0,  # No native HBAR for token-to-token swaps
                "gas": 500000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.config.chain_id
            })
            
            # Sign and send
            signed = self.w3.eth.account.sign_transaction(
                tx, self.config.private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            logger.info(f"Swap tx sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt["status"] == 1:
                logger.info(f"Swap succeeded, gas used: {receipt['gasUsed']}")
                return SwapResult(
                    success=True,
                    tx_hash=tx_hash.hex(),
                    amount_in=amount_in,
                    gas_used=receipt["gasUsed"]
                )
            else:
                logger.error(f"Swap failed: {tx_hash.hex()}")
                return SwapResult(
                    success=False,
                    tx_hash=tx_hash.hex(),
                    error="Transaction reverted"
                )
                
        except Exception as e:
            logger.error(f"Swap execution error: {e}")
            return SwapResult(
                success=False,
                tx_hash="",
                error=str(e)
            )
    
    def execute_swap_with_slippage(
        self,
        swap_pair: SwapPair,
        amount_in: int,
        slippage_percent: Optional[float] = None
    ) -> SwapResult:
        """
        Execute a swap with automatic slippage calculation.
        
        This is the recommended method for executing swaps.
        It gets a quote first, then executes with slippage protection.
        
        Args:
            swap_pair: The swap pair configuration
            amount_in: Input amount in raw token units
            slippage_percent: Slippage tolerance (default from config)
            
        Returns:
            SwapResult with transaction details
        """
        slippage = slippage_percent or self.config.trading.slippage_percent
        
        # Get quote first
        quote = self.get_quote(swap_pair, amount_in)
        
        # Calculate minimum output with slippage
        min_out = int(quote.amount_out * (100 - slippage) / 100)
        
        logger.info(
            f"Executing {swap_pair.name}: "
            f"{swap_pair.token_in.to_human(amount_in):.6f} {swap_pair.token_in.symbol} -> "
            f"~{swap_pair.token_out.to_human(quote.amount_out):.8f} {swap_pair.token_out.symbol} "
            f"(min: {swap_pair.token_out.to_human(min_out):.8f})"
        )
        
        # Ensure approval
        self.ensure_approval(swap_pair.token_in, amount_in)
        
        # Execute
        result = self.execute_swap(swap_pair, amount_in, min_out)
        
        # After BUY_BTC swaps, unwrap any ERC20 WBTC to HTS WBTC
        # This ensures all WBTC is in the HTS format compatible with HashPack/SaucerSwap
        if result.success and swap_pair.token_out.symbol == "WBTC":
            logger.info("Checking for ERC20 WBTC to unwrap...")
            try:
                balances = check_wbtc_balances()
                erc20_balance = balances["erc20_wbtc"]["balance_raw"]
                if erc20_balance > 0:
                    logger.info(f"Found {erc20_balance / 10**8:.8f} ERC20 WBTC, unwrapping to HTS...")
                    unwrap_result = unwrap_all_erc20_wbtc()
                    if unwrap_result.success:
                        logger.info(f"Unwrap successful: {unwrap_result.tx_hash}")
                    else:
                        logger.warning(f"Unwrap failed: {unwrap_result.error}")
                else:
                    logger.info("No ERC20 WBTC to unwrap")
            except Exception as e:
                logger.warning(f"ERC20 unwrap check failed (non-fatal): {e}")
        
        return result


# =============================================================================
# HBAR GAS TOP-UP
# =============================================================================

def topup_hbar_from_usdc(
    usdc_amount: float,
    slippage_percent: float = 2.0,
    config: Optional[Config] = None
) -> dict:
    """
    Swap USDC to native HBAR for gas top-up.
    
    Uses SaucerSwap V2 with proven multicall(exactInput + unwrapWHBAR) pattern.
    
    IMPORTANT NOTES (from CL12 research):
    - Deadline must be in MILLISECONDS (not seconds)
    - Uses multicall with exactInput + unwrapWHBAR for native HBAR output
    - HTS token approvals require Hedera SDK (not EVM approve)
    
    Args:
        usdc_amount: Amount of USDC to swap (e.g., 3.0 for $3)
        slippage_percent: Maximum slippage (default 2%)
        config: Optional config, loads from env if None
        
    Returns:
        Dict with success, tx_hash, usdc_spent, hbar_received, error
    """
    from hbar_swap_engine_v2 import SaucerSwapV2Engine
    
    logger.info(f"{'='*60}")
    logger.info(f"⛽ HBAR TOP-UP: Swapping {usdc_amount:.2f} USDC → HBAR (V2)")
    logger.info(f"{'='*60}")
    
    try:
        engine = SaucerSwapV2Engine()
        
        # Use V2's proven USDC → HBAR swap with multicall
        # token_in_id, token_out_id, amount, decimals_in, decimals_out, slippage
        result = engine.swap(
            token_in_id="0.0.456858",  # USDC
            token_out_id="HBAR",       # Native HBAR (engine handles wrap/unwrap)
            amount=usdc_amount,
            decimals_in=6,
            decimals_out=8,
            slippage=slippage_percent / 100  # Convert percent to decimal
        )
        
        if result.success:
            logger.info(f"✅ Top-up successful!")
            logger.info(f"   TX: {result.tx_hash}")
            logger.info(f"   Spent: {usdc_amount:.2f} USDC")
            logger.info(f"   Received: ~{result.amount_out:.4f} HBAR")
            logger.info(f"   Gas used: {result.gas_used}")
            
            return {
                "success": True,
                "tx_hash": result.tx_hash,
                "usdc_spent": usdc_amount,
                "hbar_received": result.amount_out,
                "gas_used": result.gas_used,
                "error": None
            }
        else:
            logger.error(f"❌ Top-up failed: {result.error}")
            return {
                "success": False,
                "tx_hash": result.tx_hash if hasattr(result, 'tx_hash') else None,
                "usdc_spent": 0,
                "hbar_received": 0,
                "gas_used": 0,
                "error": result.error
            }
            
    except Exception as e:
        logger.error(f"❌ Top-up exception: {e}")
        return {
            "success": False,
            "tx_hash": None,
            "usdc_spent": 0,
            "hbar_received": 0,
            "gas_used": 0,
            "error": str(e)
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_engine(config: Optional[Config] = None) -> SwapEngine:
    """
    Factory function to create a SwapEngine.
    
    Args:
        config: Optional configuration. If None, loads from environment.
        
    Returns:
        Initialized SwapEngine
    """
    return SwapEngine(config)


# =============================================================================
# QUICK REFERENCE
# =============================================================================
#
# Common operations:
#
#   # Create engine
#   engine = SwapEngine()
#
#   # Check balances
#   usdc = engine.get_balance_human(TOKENS["USDC"])
#   wbtc = engine.get_balance_human(TOKENS["WBTC"])
#
#   # Get quote for buying BTC
#   quote = engine.get_quote(get_swap_pair("BUY_BTC"), usdc_amount_raw)
#
#   # Execute swap with slippage protection
#   result = engine.execute_swap_with_slippage(
#       get_swap_pair("BUY_BTC"),
#       usdc_amount_raw
#   )
#
# =============================================================================
