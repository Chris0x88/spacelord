"""
ERC20 Wrapper for HTS Token Conversion
======================================

This module handles wrapping/unwrapping between ERC20 tokens and HTS tokens
on Hedera using SaucerSwap's ERC20Wrapper contract.

The Problem:
- When swapping USDC -> WBTC through SaucerSwap's high-liquidity pool,
  we receive ERC20 WBTC (0.0.1055483 or similar bridged version)
- HashPack and SaucerSwap UI expect HTS WBTC (0.0.10082597)
- We need to unwrap ERC20 WBTC to HTS WBTC after buy swaps

SaucerSwap ERC20Wrapper Contract:
- Contract ID: 0.0.9675688
- Functions: depositFor (wrap), withdrawTo (unwrap)

Token Mapping:
- ERC20 WBTC: 0.0.1055483 (bridged from Ethereum)
- HTS WBTC:   0.0.10082597 (native HTS token)
"""

import os
import logging
import time
from typing import Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from web3 import Web3

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# CONTRACT ADDRESSES
# =============================================================================

# SaucerSwap ERC20Wrapper contract
ERC20_WRAPPER_ID = "0.0.9675688"

# WBTC Token IDs
ERC20_WBTC_ID = "0.0.1055483"   # ERC20 bridged WBTC
HTS_WBTC_ID = "0.0.10082597"    # HTS native WBTC

# =============================================================================
# ABIs
# =============================================================================

# ERC20Wrapper ABI (OpenZeppelin pattern)
ERC20_WRAPPER_ABI = [
    {
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "depositFor",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "withdrawTo",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "underlying",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Standard ERC20 ABI for balance and approval checks
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
# HELPER FUNCTIONS
# =============================================================================

def hedera_id_to_evm(hedera_id: str) -> str:
    """Convert Hedera ID (0.0.123) to EVM address."""
    if hedera_id.startswith("0x"):
        return Web3.to_checksum_address(hedera_id)
    parts = hedera_id.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid Hedera ID: {hedera_id}")
    num = int(parts[2])
    return Web3.to_checksum_address(f"0x{num:040x}")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class UnwrapResult:
    """Result of an unwrap operation."""
    success: bool
    tx_hash: str = ""
    amount_unwrapped: int = 0
    error: str = ""


# =============================================================================
# ERC20 WRAPPER CLASS
# =============================================================================

class ERC20WrapperClient:
    """
    Client for interacting with SaucerSwap's ERC20Wrapper contract.
    
    This handles conversion between ERC20 tokens (bridged) and HTS tokens (native).
    
    Usage:
        client = ERC20WrapperClient()
        
        # Check ERC20 WBTC balance
        balance = client.get_erc20_wbtc_balance()
        
        # Unwrap ERC20 WBTC to HTS WBTC
        result = client.unwrap_wbtc(amount)
    """
    
    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None):
        """Initialize the wrapper client."""
        load_dotenv()
        
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "https://mainnet.hashio.io/api")
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        
        if not self.private_key:
            raise ValueError("PRIVATE_KEY is required")
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {self.rpc_url}")
        
        self.account = self.w3.eth.account.from_key(self.private_key)
        self.eoa = self.account.address
        self.chain_id = 295  # Hedera mainnet
        
        # Contract addresses
        self.wrapper_address = hedera_id_to_evm(ERC20_WRAPPER_ID)
        self.erc20_wbtc_address = hedera_id_to_evm(ERC20_WBTC_ID)
        self.hts_wbtc_address = hedera_id_to_evm(HTS_WBTC_ID)
        
        # Initialize contracts
        self.wrapper = self.w3.eth.contract(
            address=self.wrapper_address,
            abi=ERC20_WRAPPER_ABI
        )
        self.erc20_wbtc = self.w3.eth.contract(
            address=self.erc20_wbtc_address,
            abi=ERC20_ABI
        )
        self.hts_wbtc = self.w3.eth.contract(
            address=self.hts_wbtc_address,
            abi=ERC20_ABI
        )
        
        logger.info(f"ERC20WrapperClient initialized")
        logger.info(f"  Account: {self.eoa}")
        logger.info(f"  Wrapper: {ERC20_WRAPPER_ID}")
    
    def get_erc20_wbtc_balance(self) -> int:
        """Get ERC20 WBTC balance (raw units, 8 decimals)."""
        return self.erc20_wbtc.functions.balanceOf(self.eoa).call()
    
    def get_hts_wbtc_balance(self) -> int:
        """Get HTS WBTC balance (raw units, 8 decimals)."""
        return self.hts_wbtc.functions.balanceOf(self.eoa).call()
    
    def get_erc20_wbtc_balance_human(self) -> float:
        """Get ERC20 WBTC balance in human-readable format."""
        return self.get_erc20_wbtc_balance() / 10**8
    
    def get_hts_wbtc_balance_human(self) -> float:
        """Get HTS WBTC balance in human-readable format."""
        return self.get_hts_wbtc_balance() / 10**8
    
    def ensure_approval(self, amount: int) -> bool:
        """
        Ensure ERC20 WBTC is approved for the wrapper contract.
        
        Returns True if approval was needed and executed.
        """
        allowance = self.erc20_wbtc.functions.allowance(
            self.eoa, self.wrapper_address
        ).call()
        
        if allowance >= amount:
            logger.debug(f"ERC20 WBTC already approved: {allowance}")
            return False
        
        logger.info(f"Approving ERC20 WBTC for wrapper...")
        
        tx = self.erc20_wbtc.functions.approve(
            self.wrapper_address,
            2**256 - 1  # Max approval
        ).build_transaction({
            "from": self.eoa,
            "gas": 1000000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        logger.info(f"Approval TX sent: {tx_hash.hex()}")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt["status"] != 1:
            raise RuntimeError(f"Approval failed: {tx_hash.hex()}")
        
        logger.info(f"Approval confirmed, gas used: {receipt['gasUsed']}")
        time.sleep(3)  # Wait for propagation
        return True
    
    def unwrap_wbtc(self, amount: Optional[int] = None) -> UnwrapResult:
        """
        Unwrap ERC20 WBTC to HTS WBTC.
        
        This converts bridged ERC20 WBTC to native HTS WBTC that is
        compatible with HashPack and SaucerSwap UI.
        
        Args:
            amount: Amount to unwrap in raw units (8 decimals).
                   If None, unwraps entire ERC20 WBTC balance.
        
        Returns:
            UnwrapResult with transaction details
        """
        try:
            # Get current ERC20 WBTC balance
            erc20_balance = self.get_erc20_wbtc_balance()
            
            if erc20_balance == 0:
                logger.info("No ERC20 WBTC to unwrap")
                return UnwrapResult(success=True, amount_unwrapped=0)
            
            # Use full balance if amount not specified
            unwrap_amount = amount if amount is not None else erc20_balance
            
            if unwrap_amount > erc20_balance:
                return UnwrapResult(
                    success=False,
                    error=f"Insufficient ERC20 WBTC: have {erc20_balance}, need {unwrap_amount}"
                )
            
            logger.info(f"Unwrapping {unwrap_amount / 10**8:.8f} ERC20 WBTC to HTS WBTC")
            
            # Ensure approval
            self.ensure_approval(unwrap_amount)
            
            # Build unwrap transaction
            # withdrawTo(address account, uint256 value) - sends HTS tokens to account
            tx = self.wrapper.functions.withdrawTo(
                self.eoa,
                unwrap_amount
            ).build_transaction({
                "from": self.eoa,
                "gas": 1000000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.chain_id
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            logger.info(f"Unwrap TX sent: {tx_hash.hex()}")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt["status"] == 1:
                logger.info(f"Unwrap successful! Gas used: {receipt['gasUsed']}")
                return UnwrapResult(
                    success=True,
                    tx_hash=tx_hash.hex(),
                    amount_unwrapped=unwrap_amount
                )
            else:
                logger.error(f"Unwrap failed: {tx_hash.hex()}")
                return UnwrapResult(
                    success=False,
                    tx_hash=tx_hash.hex(),
                    error="Transaction reverted"
                )
                
        except Exception as e:
            logger.error(f"Unwrap error: {e}")
            return UnwrapResult(success=False, error=str(e))
    
    def wrap_wbtc(self, amount: Optional[int] = None) -> UnwrapResult:
        """
        Wrap HTS WBTC to ERC20 WBTC.
        
        This is the reverse operation - converts native HTS WBTC to
        bridged ERC20 WBTC. Rarely needed but included for completeness.
        
        Args:
            amount: Amount to wrap in raw units (8 decimals).
                   If None, wraps entire HTS WBTC balance.
        
        Returns:
            UnwrapResult with transaction details
        """
        try:
            # Get current HTS WBTC balance
            hts_balance = self.get_hts_wbtc_balance()
            
            if hts_balance == 0:
                logger.info("No HTS WBTC to wrap")
                return UnwrapResult(success=True, amount_unwrapped=0)
            
            wrap_amount = amount if amount is not None else hts_balance
            
            if wrap_amount > hts_balance:
                return UnwrapResult(
                    success=False,
                    error=f"Insufficient HTS WBTC: have {hts_balance}, need {wrap_amount}"
                )
            
            logger.info(f"Wrapping {wrap_amount / 10**8:.8f} HTS WBTC to ERC20 WBTC")
            
            # Ensure HTS WBTC is approved for wrapper
            hts_allowance = self.hts_wbtc.functions.allowance(
                self.eoa, self.wrapper_address
            ).call()
            
            if hts_allowance < wrap_amount:
                logger.info("Approving HTS WBTC for wrapper...")
                approve_tx = self.hts_wbtc.functions.approve(
                    self.wrapper_address,
                    2**256 - 1
                ).build_transaction({
                    "from": self.eoa,
                    "gas": 1000000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.eoa),
                    "chainId": self.chain_id
                })
                signed = self.w3.eth.account.sign_transaction(approve_tx, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                time.sleep(3)
            
            # Build wrap transaction
            # depositFor(address account, uint256 value) - deposits HTS, mints ERC20
            tx = self.wrapper.functions.depositFor(
                self.eoa,
                wrap_amount
            ).build_transaction({
                "from": self.eoa,
                "gas": 1000000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.chain_id
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            logger.info(f"Wrap TX sent: {tx_hash.hex()}")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt["status"] == 1:
                logger.info(f"Wrap successful! Gas used: {receipt['gasUsed']}")
                return UnwrapResult(
                    success=True,
                    tx_hash=tx_hash.hex(),
                    amount_unwrapped=wrap_amount
                )
            else:
                return UnwrapResult(
                    success=False,
                    tx_hash=tx_hash.hex(),
                    error="Transaction reverted"
                )
                
        except Exception as e:
            logger.error(f"Wrap error: {e}")
            return UnwrapResult(success=False, error=str(e))


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_wrapper_client: Optional[ERC20WrapperClient] = None

def get_wrapper_client() -> ERC20WrapperClient:
    """Get or create the singleton wrapper client."""
    global _wrapper_client
    if _wrapper_client is None:
        _wrapper_client = ERC20WrapperClient()
    return _wrapper_client


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def unwrap_all_erc20_wbtc() -> UnwrapResult:
    """
    Convenience function to unwrap all ERC20 WBTC to HTS WBTC.
    
    Call this after a BUY_BTC swap to ensure all WBTC is in HTS format.
    """
    client = get_wrapper_client()
    return client.unwrap_wbtc()


def check_wbtc_balances() -> dict:
    """
    Check both ERC20 and HTS WBTC balances.
    
    Returns dict with both balances for diagnostics.
    """
    client = get_wrapper_client()
    return {
        "erc20_wbtc": {
            "token_id": ERC20_WBTC_ID,
            "balance_raw": client.get_erc20_wbtc_balance(),
            "balance_human": client.get_erc20_wbtc_balance_human(),
        },
        "hts_wbtc": {
            "token_id": HTS_WBTC_ID,
            "balance_raw": client.get_hts_wbtc_balance(),
            "balance_human": client.get_hts_wbtc_balance_human(),
        }
    }


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="ERC20 WBTC Wrapper Tool")
    parser.add_argument("--check", action="store_true", help="Check WBTC balances")
    parser.add_argument("--unwrap", action="store_true", help="Unwrap all ERC20 WBTC to HTS")
    parser.add_argument("--wrap", action="store_true", help="Wrap all HTS WBTC to ERC20")
    
    args = parser.parse_args()
    
    if args.check:
        balances = check_wbtc_balances()
        print("\n=== WBTC Balances ===")
        print(f"ERC20 WBTC ({ERC20_WBTC_ID}): {balances['erc20_wbtc']['balance_human']:.8f}")
        print(f"HTS WBTC ({HTS_WBTC_ID}):   {balances['hts_wbtc']['balance_human']:.8f}")
    
    elif args.unwrap:
        print("\n=== Unwrapping ERC20 WBTC to HTS WBTC ===")
        result = unwrap_all_erc20_wbtc()
        if result.success:
            print(f"Success! TX: {result.tx_hash}")
            print(f"Amount: {result.amount_unwrapped / 10**8:.8f} WBTC")
        else:
            print(f"Failed: {result.error}")
    
    elif args.wrap:
        print("\n=== Wrapping HTS WBTC to ERC20 WBTC ===")
        client = get_wrapper_client()
        result = client.wrap_wbtc()
        if result.success:
            print(f"Success! TX: {result.tx_hash}")
        else:
            print(f"Failed: {result.error}")
    
    else:
        # Default: show balances
        balances = check_wbtc_balances()
        print("\n=== WBTC Balances ===")
        print(f"ERC20 WBTC ({ERC20_WBTC_ID}): {balances['erc20_wbtc']['balance_human']:.8f}")
        print(f"HTS WBTC ({HTS_WBTC_ID}):   {balances['hts_wbtc']['balance_human']:.8f}")
