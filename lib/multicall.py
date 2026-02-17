"""
Pacman Multicall
================
Minimal implementation of Multicall3 for Hedera.
Allows batching multiple read-only calls into a single RPC request.
"""
from typing import List, Tuple, Any

# Multicall3 Address on Hedera Mainnet/Testnet (Same address)
MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"

MULTICALL_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "target", "type": "address"},
                    {"internalType": "bool", "name": "allowFailure", "type": "bool"},
                    {"internalType": "bytes", "name": "callData", "type": "bytes"}
                ],
                "internalType": "struct Multicall3.Call3[]",
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"internalType": "bool", "name": "success", "type": "bool"},
                    {"internalType": "bytes", "name": "returnData", "type": "bytes"}
                ],
                "internalType": "struct Multicall3.Result[]",
                "name": "returnData",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class Multicall:
    def __init__(self, w3):
        self.w3 = w3
        self.contract = w3.eth.contract(address=MULTICALL3_ADDRESS, abi=MULTICALL_ABI)

    def aggregate(self, calls: List[Tuple[str, bool, bytes]]) -> List[Tuple[bool, bytes]]:
        """
        Execute multiple calls in a single transaction.
        
        Args:
            calls: List of (target, allowFailure, callData) tuples
            
        Returns:
            List of (success, returnData) tuples
        """
        # Ensure address checksums
        sanitized_calls = []
        for target, allow_fail, data in calls:
            sanitized_calls.append((
                self.w3.to_checksum_address(target),
                allow_fail,
                data
            ))
            
        return self.contract.functions.aggregate3(sanitized_calls).call()
