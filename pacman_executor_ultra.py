#!/usr/bin/env python3
"""
Pacman Executor ULTRA - Using btc-rebalancer2's exact patterns
Direct port of the battle-tested swap engine.
"""

import os
import json
import time
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path

from web3 import Web3
from saucerswap_v2_client import SaucerSwapV2, hedera_id_to_evm, encode_path

# Token mappings
TOKEN_IDS = {
    "USDC": "0.0.456858",
    "USDC[hts]": "0.0.1055459",
    "WBTC[hts]": "0.0.1055483",
    "WBTC_HTS": "0.0.10082597",
    "WHBAR": "0.0.1456986",
    "HBAR": "0.0.0",
}

DECIMALS = {
    "USDC": 6,
    "USDC[hts]": 6,
    "WBTC": 8,
    "HBAR": 8,
}

# Extended Router ABI from btc-rebalancer2
ROUTER_ABI_EXTENDED = [
    {
        "inputs": [{"name": "data", "type": "bytes[]"}],
        "name": "multicall",
        "outputs": [{"name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "amountMinimum", "type": "uint256"}, {"name": "recipient", "type": "address"}],
        "name": "unwrapWHBAR",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{
            "components": [
                {"name": "path", "type": "bytes"},
                {"name": "recipient", "type": "address"},
                {"name": "deadline", "type": "uint256"},
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMinimum", "type": "uint256"},
            ],
            "name": "params",
            "type": "tuple",
        }],
        "name": "exactInput",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{
            "components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "recipient", "type": "address"},
                {"name": "deadline", "type": "uint256"},
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMinimum", "type": "uint256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ],
            "name": "params",
            "type": "tuple",
        }],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    }
]

class PacmanExecutorUltra:
    """
    Uses exact patterns from btc-rebalancer2's hbar_swap_engine_v2.
    """
    
    def __init__(self):
        self.private_key = os.getenv("PACMAN_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("Private key required")
        
        self.w3 = Web3(Web3.HTTPProvider("https://mainnet.hashio.io/api"))
        self.client = SaucerSwapV2(self.w3, network="mainnet", private_key=self.private_key)
        self.eoa = self.client.eoa
        self.chain_id = 295
        
        # Extended router
        self.router_extended = self.w3.eth.contract(
            address=self.client.router_address,
            abi=ROUTER_ABI_EXTENDED
        )
        
        print(f"✅ Ultra executor ready: {self.eoa}")
    
    def execute_swap(self, token_in: str, token_out: str, amount: float):
        """
        Execute swap using exact btc-rebalancer2 pattern.
        """
        try:
            print(f"\n🚀 Executing: {amount} {token_in} → {token_out}")
            
            # Resolve IDs
            token_in_id = TOKEN_IDS.get(token_in, token_in)
            token_out_id = TOKEN_IDS.get(token_out, token_out)
            
            # Check if HBAR involved
            is_hbar_in = token_in == "HBAR"
            is_hbar_out = token_out == "HBAR"
            
            # Get addresses
            addr_in = hedera_id_to_evm(TOKEN_IDS["WHBAR"]) if is_hbar_in else hedera_id_to_evm(token_in_id)
            addr_out = hedera_id_to_evm(TOKEN_IDS["WHBAR"]) if is_hbar_out else hedera_id_to_evm(token_out_id)
            
            # Raw amount
            decimals_in = DECIMALS.get(token_in, 8)
            raw_amount = int(amount * (10 ** decimals_in))
            
            # Get quote
            print("   Getting quote...")
            quote = self.client.get_quote_single(addr_in, addr_out, raw_amount, 1500)
            expected_out = quote["amountOut"]
            min_out = int(expected_out * 0.95)  # 5% slippage (more tolerant)
            
            print(f"   Quote: {amount} {token_in} → {expected_out / 10**8:.8f} {token_out}")
            
            # Handle allowance
            if not is_hbar_in:
                print("   Checking allowance...")
                erc20 = self.w3.eth.contract(address=addr_in, abi=[
                    {"inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
                    "name": "allowance", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
                    {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
                    "name": "approve", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"}
                ])
                
                allowance = erc20.functions.allowance(self.eoa, self.client.router_address).call()
                print(f"   Current allowance: {allowance}")
                
                if allowance < raw_amount:
                    print("   Approving...")
                    tx = erc20.functions.approve(self.client.router_address, raw_amount * 10).build_transaction({
                        "from": self.eoa,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "gas": 150000,
                        "gasPrice": self.w3.eth.gas_price
                    })
                    signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
                    tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                    print(f"   Approval sent: {tx_hash.hex()[:40]}...")
                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    print(f"   Approved! Gas: {receipt['gasUsed']}")
                    time.sleep(5)  # Wait for propagation
            
            # Build path
            path_ids = [TOKEN_IDS["WHBAR"] if is_hbar_in else token_in_id,
                       TOKEN_IDS["WHBAR"] if is_hbar_out else token_out_id]
            path_bytes = encode_path(path_ids, [1500])
            
            # Hedera deadline in MILLISECONDS
            deadline = int(time.time() * 1000) + 600000
            
            print(f"   Path: {path_bytes.hex()[:40]}...")
            print(f"   Deadline: {deadline}")
            
            # Build transaction - HTS to HTS (no HBAR)
            if not is_hbar_in and not is_hbar_out:
                print("   Building HTS→HTS swap...")
                
                # Try exactInputSingle instead of exactInput
                params_single = (
                    addr_in,  # tokenIn
                    addr_out,  # tokenOut
                    1500,  # fee
                    self.eoa,  # recipient
                    deadline,  # deadline
                    raw_amount,  # amountIn
                    min_out,  # amountOutMinimum
                    0  # sqrtPriceLimitX96
                )
                
                print(f"   Using exactInputSingle...")
                tx = self.router_extended.functions.exactInputSingle(params_single).build_transaction({
                    "from": self.eoa,
                    "gas": 1000000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.eoa),
                    "chainId": self.chain_id
                })
                
                print(f"   Nonce: {tx['nonce']}")
                
                # Sign and send
                signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                
                print(f"   📤 TX: {tx_hash.hex()[:50]}...")
                print(f"   ⏳ Waiting...")
                
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt["status"] == 1:
                    print(f"\n✅ SUCCESS!")
                    print(f"   TX Hash: {receipt['transactionHash'].hex()}")
                    print(f"   Gas: {receipt['gasUsed']}")
                    return True
                else:
                    print(f"\n❌ Failed: {receipt}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("="*80)
    print("🚀 PACMAN EXECUTOR ULTRA")
    print("   Using exact btc-rebalancer2 patterns")
    print("="*80)
    
    executor = PacmanExecutorUltra()
    
    # Execute $1 USDC -> WBTC
    result = executor.execute_swap("USDC[hts]", "WBTC[hts]", 1.0)
    
    if result:
        print("\n🎉 Swap completed!")
    else:
        print("\n😞 Swap failed")
