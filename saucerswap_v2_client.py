"""
Local SaucerSwap V2 client
==========================

This is a vendored copy of the proven SaucerSwap V2 implementation
from the parent repo, trimmed to the pieces we need:

- hedera_id_to_evm
- encode_path
- SaucerSwapV2 with:
  - mainnet contracts 0.0.3949424 (quoter) and 0.0.3949434 (router)
  - get_quote_single / get_quote
  - approve_token / get_token_balance

It makes btc_rebalancer self-contained for deployment.
"""

import time
from typing import List
from web3 import Web3

# Contract IDs (Mainnet/Testnet)
CONTRACTS = {
    "mainnet": {
        "quoter": "0.0.3949424",
        "router": "0.0.3949434",
        "whbar": "0.0.1456986",
    },
    "testnet": {
        "quoter": "0.0.1390002",
        "router": "0.0.1414040",
        "whbar": "0.0.15058",
    },
}

QUOTER_ABI = [
    {
        "inputs": [
            {"internalType": "bytes", "name": "path", "type": "bytes"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
        ],
        "name": "quoteExactInput",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160[]", "name": "sqrtPriceX96AfterList", "type": "uint160[]"},
            {"internalType": "uint32[]", "name": "initializedTicksCrossedList", "type": "uint32[]"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "path", "type": "bytes"},
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
        ],
        "name": "quoteExactOutput",
        "outputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint160[]", "name": "sqrtPriceX96AfterList", "type": "uint160[]"},
            {"internalType": "uint32[]", "name": "initializedTicksCrossedList", "type": "uint32[]"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes", "name": "path", "type": "bytes"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                ],
                "internalType": "struct ISwapRouter.ExactInputParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInput",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes", "name": "path", "type": "bytes"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountInMaximum", "type": "uint256"},
                ],
                "internalType": "struct ISwapRouter.ExactOutputParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactOutput",
        "outputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes[]", "name": "data", "type": "bytes[]"}],
        "name": "multicall",
        "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "amountMinimum", "type": "uint256"}, {"internalType": "address", "name": "recipient", "type": "address"}],
        "name": "unwrapWHBAR",
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
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"}
        ],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def hedera_id_to_evm(hedera_id: str) -> str:
    """Convert Hedera ID (0.0.123) to EVM address (0x000...007B)."""
    if hedera_id.startswith("0x"):
        return Web3.to_checksum_address(hedera_id)
    parts = hedera_id.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid Hedera ID format: {hedera_id}")
    num = int(parts[2])
    return Web3.to_checksum_address(f"0x{num:040x}")


def encode_path(tokens: List[str], fees: List[int]) -> bytes:
    """Encode [token0, token1, ...] and [fee0, fee1, ...] into SaucerSwap path bytes."""
    if len(fees) != len(tokens) - 1:
        raise ValueError(f"Expected {len(tokens) - 1} fees, got {len(fees)}")

    path = b""
    for i, token in enumerate(tokens):
        token_bytes = bytes.fromhex(hedera_id_to_evm(token)[2:])
        path += token_bytes
        if i < len(fees):
            fee_bytes = fees[i].to_bytes(3, "big")
            path += fee_bytes
    return path


class SaucerSwapV2:
    """Minimal SaucerSwap V2 client for quoting and token swaps."""

    def __init__(self, w3: Web3, network: str = "mainnet", private_key: str | None = None):
        self.w3 = w3
        self.network = network
        self.private_key = private_key

        if private_key:
            self.account = w3.eth.account.from_key(private_key)
            self.eoa = self.account.address
        else:
            self.account = None
            self.eoa = None

        contracts = CONTRACTS[network]
        self.quoter_address = hedera_id_to_evm(contracts["quoter"])
        self.router_address = hedera_id_to_evm(contracts["router"])
        self._whbar_for_path = hedera_id_to_evm(contracts["whbar"])  # kept for completeness

        self.quoter = w3.eth.contract(address=self.quoter_address, abi=QUOTER_ABI)
        self.router = w3.eth.contract(address=self.router_address, abi=ROUTER_ABI)

        self.chain_id = 295 if network == "mainnet" else 296

    def get_quote_single(self, token_in: str, token_out: str, amount_in: int, fee: int = 1500) -> dict:
        """Get a quote for a single-hop swap using quoteExactInput(path)."""
        path = encode_path([token_in, token_out], [fee])
        try:
            result = self.quoter.functions.quoteExactInput(path, amount_in).call()
            return {
                "amountOut": result[0],
                "amount_out": result[0],  # snake_case alias for API compatibility
                "sqrtPriceX96AfterList": result[1],
                "initializedTicksCrossedList": result[2],
                "gasEstimate": result[3],
            }
        except Exception as e:
            raise RuntimeError(f"Quote failed: {e}")

    def get_quote_exact_output(self, token_in: str, token_out: str, amount_out: int, fee: int = 1500) -> dict:
        """
        Get a quote for a single-hop EXACT OUTPUT swap.
        Path for exactOutput is encoded in REVERSE: [tokenOut, tokenIn] with [fee].
        Returns amountIn needed.
        """
        # Note: exactOutput path is reversed
        path = encode_path([token_out, token_in], [fee])
        try:
            result = self.quoter.functions.quoteExactOutput(path, amount_out).call()
            return {
                "amountIn": result[0],
                "amount_in": result[0],  # snake_case alias
                "sqrtPriceX96AfterList": result[1],
                "initializedTicksCrossedList": result[2],
                "gasEstimate": result[3],
            }
        except Exception as e:
            raise RuntimeError(f"Quote Exact Output failed: {e}")

    def swap_exact_output(self, token_in: str, token_out: str, amount_out: int, max_amount_in: int, fee: int = 1500, recipient: str = None, value: int = 0) -> str:
        """
        Execute a swap for an exact output amount.
        """
        if not self.private_key:
            raise ValueError("Private key required")
            
        recipient = recipient or self.eoa
        deadline = int(time.time() * 1000) + 600000 # 10 mins (Hedera needs milliseconds)
        
        # Path for exactOutput is reversed: [tokenOut, tokenIn]
        path = encode_path([token_out, token_in], [fee])
        
        params = (
            path,
            recipient,
            deadline,
            amount_out,
            max_amount_in
        )
        
        # Scale HBAR value to 18 decimals for relay compatibility
        scaled_value = value * 10**10 if value > 0 else 0
        
        # Estimate gas? Or just set high.
        tx = self.router.functions.exactOutput(params).build_transaction({
            "from": self.eoa,
            "gas": 1_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
            "value": scaled_value,
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def swap_exact_input(self, token_in: str, token_out: str, amount_in: int, min_amount_out: int, fee: int = 1500, recipient: str = None, value: int = 0) -> str:
        """
        Execute a swap for an exact input amount.
        """
        if not self.private_key:
            raise ValueError("Private key required")
            
        recipient = recipient or self.eoa
        deadline = int(time.time() * 1000) + 600000 # 10 mins (Hedera needs milliseconds)
        
        path = encode_path([token_in, token_out], [fee])
        
        params = (
            path,
            recipient,
            deadline,
            amount_in,
            min_amount_out
        )
        
        # Scale HBAR value to 18 decimals for relay compatibility
        scaled_value = value * 10**10 if value > 0 else 0
        
        tx = self.router.functions.exactInput(params).build_transaction({
            "from": self.eoa,
            "gas": 1_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
            "value": scaled_value,
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def swap_exact_input_multicall(self, token_in: str, token_out: str, amount_in: int, min_amount_out: int, 
                                 input_is_native: bool = False, output_is_native: bool = False, 
                                 fee: int = 1500, recipient: str = None) -> str:
        """
        Execute a swap using multicall for Native HBAR handling.
        """
        if not self.private_key:
            raise ValueError("Private key required")
            
        recipient = self.eoa if not recipient else recipient
        deadline = int(time.time() * 1000) + 600000 # 10 mins (Hedera needs milliseconds)
        
        # Path Encoding
        # If input is native, token_in provided should be WHBAR ID for path
        # If output is native, token_out provided should be WHBAR ID for path
        path = encode_path([token_in, token_out], [fee])
        
        encoded_calls = []
        value_to_send = 0
        
        if input_is_native:
            # HBAR -> Token
            # 1. exactInput (recipient=self.eoa)
            # 2. refundETH
            
            # Params for exactInput
            params = (path, self.eoa, deadline, amount_in, min_amount_out)
            
            # Encode exactInput
            swap_calldata = self.router.encode_abi("exactInput", [params])
            encoded_calls.append(swap_calldata)
            
            # Encode refundETH
            print(f"   🔄 Executing Multicall (ExactInput + RefundETH)...")
            refund_calldata = self.router.encode_abi("refundETH")
            encoded_calls.append(refund_calldata)
            
            value_to_send = amount_in
            
        elif output_is_native:
            # Token -> HBAR
            # 1. exactInput (recipient=ROUTER)
            # 2. unwrapWHBAR(minAmount, recipient)
            
            # Params for exactInput: recipient MUST be ROUTER
            params = (path, self.router_address, deadline, amount_in, min_amount_out)
            
            swap_calldata = self.router.encode_abi("exactInput", [params])
            encoded_calls.append(swap_calldata)
            
            # Encode unwrapWHBAR
            # amountMinimum=0 (slippage already handled by exactInput), recipient=self.eoa
            print(f"   🔄 Executing Multicall (ExactInput + unwrapWHBAR)...")
            print(f"      - Path: {path.hex()}")
            print(f"      - Recipient (Swap): {self.router_address}")
            print(f"      - Recipient (Unwrap): {self.eoa}")
            unwrap_calldata = self.router.encode_abi("unwrapWHBAR", [0, self.eoa])
            encoded_calls.append(unwrap_calldata)
            
            value_to_send = 0 # ERC20 used
            
        else:
            raise ValueError("Use standard swap_exact_input for non-native swaps")
            
        # Scale HBAR value to 18 decimals for relay compatibility
        scaled_value = value_to_send * 10**10 if value_to_send > 0 else 0
        if scaled_value > 0:
            print(f"   🔧 Scaled HBAR Value: {scaled_value} (pseudo-Wei)")
        
        # Build Multicall Transaction
        tx = self.router.functions.multicall(encoded_calls).build_transaction({
            "from": self.eoa,
            "gas": 2_500_000, # Increased gas for multicall (V2 complex paths)
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
            "value": scaled_value
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def get_quote_multi_hop(self, token_path: List[str], fee_tiers: List[int], amount_in: int) -> dict:
        """
        Get a quote for a multi-hop swap using quoteExactInput(path).

        Args:
            token_path: List of token addresses [tokenA, tokenB, tokenC, ...]
            fee_tiers: List of fee tiers for each hop [fee1, fee2, ...]
            amount_in: Input amount in raw units

        Returns:
            dict with quote data (amountOut, gas, etc.)

        Example:
            # WBTC → USDC → WETH (2-hop)
            token_path = [wbtc_address, usdc_address, weth_address]
            fee_tiers = [1500, 1500]  # 0.15% for each hop
        """
        if len(fee_tiers) != len(token_path) - 1:
            raise ValueError(f"Expected {len(token_path) - 1} fee tiers, got {len(fee_tiers)}")

        path = encode_path(token_path, fee_tiers)
        try:
            result = self.quoter.functions.quoteExactInput(path, amount_in).call()
            return {
                "amount_out": result[0],
                "sqrtPriceX96AfterList": result[1],
                "initializedTicksCrossedList": result[2],
                "gasEstimate": result[3],
                "path": token_path,
                "fee_tiers": fee_tiers,
                "num_hops": len(fee_tiers)
            }
        except Exception as e:
            raise RuntimeError(f"Multi-hop quote failed: {e}")

    def approve_token(self, token_id: str, amount: int | None = None, spender: str | None = None) -> str:
        """
        Approve router or custom spender to spend token_id for amount (or max uint256).
        Uses Hedera SDK via JS script for HTS tokens to avoid EVM revert.
        """
        if not self.private_key:
            raise ValueError("Private key required")

        if amount is None:
            amount = 2**256 - 1
            
        # Default spender is the router
        spender_val = spender or CONTRACTS[self.network]["router"]

        # Use Hedera SDK for HTS tokens (starting with 0.0.)
        if token_id.startswith("0.0."):
            import subprocess
            import os
            
            print(f"   🔓 Approving HTS token {token_id} for {spender_val} via Hedera SDK...")
            
            # Use current process environment plus any needed IDs
            env = os.environ.copy()
            
            script_path = "approve_hts_token.js"
            try:
                # amount for JS script. If max, use a large enough number but not 2^256 as JS might struggle.
                amount_str = str(min(amount, 10**18)) 
                
                result = subprocess.run(
                    ["node", script_path, token_id, spender_val, amount_str],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"   ✅ HTS Approval SUCCESS: {result.stdout.strip()}")
                return "HTS_SDK_APPROVAL_SUCCESS"
            except Exception as e:
                print(f"   ❌ HTS Approval FAILED: {e}")
                if hasattr(e, 'stderr'): print(e.stderr)
                # Fallback to EVM if JS fails? No, better to fail loud.
                raise RuntimeError(f"HTS Approval failed: {e}")

        # Fallback to EVM for others (though most tokens in this app are HTS)
        token_address = hedera_id_to_evm(token_id)
        token = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        # If spender is a Hedera ID, convert to EVM
        if spender_val.startswith("0.0."):
            spender_evm = hedera_id_to_evm(spender_val)
        else:
            spender_evm = spender_val

        tx = token.functions.approve(spender_evm, amount).build_transaction({
            "from": self.eoa,
            "gas": 1_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def get_token_balance(self, token_id: str, account: str | None = None) -> int:
        """Get token balance for account (defaults to EOA)."""
        token_address = hedera_id_to_evm(token_id)
        acct = account or self.eoa
        if acct and not acct.startswith("0x"):
            acct = hedera_id_to_evm(acct)
        token = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        return token.functions.balanceOf(acct).call()

    def get_allowance(self, token_id: str, owner: str, spender: str) -> int:
        """Get allowance."""
        token_address = hedera_id_to_evm(token_id)
        token = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        return token.functions.allowance(owner, spender).call()


# =============================================================================
# POOL LIQUIDITY QUERIES (for Phase 1A enhancements)
# =============================================================================

# SaucerSwap V2 Factory ABI - for pool address discovery
FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V3 Pool ABI - SaucerSwap V2 uses Uniswap V3 pool contracts
POOL_ABI = [
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [{"internalType": "uint24", "name": "", "type": "uint24"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Factory address (mainnet)
FACTORY_ADDRESS_MAINNET = "0.0.3946833"


def get_pool_address(w3: Web3, token0_id: str, token1_id: str, fee_tier: int, network: str = "mainnet") -> str:
    """
    Get pool address from SaucerSwap V2 factory contract.

    Args:
        w3: Web3 instance
        token0_id: Hedera ID or EVM address of first token
        token1_id: Hedera ID or EVM address of second token
        fee_tier: Fee tier in basis points (500, 1500, 3000, 10000)
        network: Network ("mainnet" or "testnet")

    Returns:
        Pool address (EVM format) or raises error if pool doesn't exist
    """
    factory_id = FACTORY_ADDRESS_MAINNET if network == "mainnet" else "0.0.1390001"  # testnet factory
    factory_address = hedera_id_to_evm(factory_id)

    # Convert tokens to EVM addresses
    if token0_id.startswith("0.0."):
        token0 = hedera_id_to_evm(token0_id)
    else:
        token0 = Web3.to_checksum_address(token0_id)

    if token1_id.startswith("0.0."):
        token1 = hedera_id_to_evm(token1_id)
    else:
        token1 = Web3.to_checksum_address(token1_id)

    factory = w3.eth.contract(address=factory_address, abi=FACTORY_ABI)

    try:
        pool_address = factory.functions.getPool(token0, token1, fee_tier).call()

        # Check if pool exists (address is not zero)
        if pool_address == "0x0000000000000000000000000000000000000000":
            raise ValueError(f"Pool does not exist for {token0_id}/{token1_id} at fee tier {fee_tier}")

        return pool_address
    except Exception as e:
        raise RuntimeError(f"Failed to get pool address: {e}")


def get_pool_liquidity_data(w3: Web3, pool_address: str) -> dict:
    """
    Query pool contract directly for liquidity and price data.

    Args:
        w3: Web3 instance
        pool_address: Pool contract address (EVM format)

    Returns:
        dict with:
            - liquidity: uint128 liquidity value
            - sqrt_price_x96: Current sqrt price (Q64.96 format)
            - tick: Current tick
            - token0: Address of token0
            - token1: Address of token1
            - fee: Pool fee tier
    """
    pool = w3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=POOL_ABI)

    try:
        liquidity = pool.functions.liquidity().call()
        slot0 = pool.functions.slot0().call()
        token0 = pool.functions.token0().call()
        token1 = pool.functions.token1().call()
        fee = pool.functions.fee().call()

        return {
            "liquidity": liquidity,
            "sqrt_price_x96": slot0[0],
            "tick": slot0[1],
            "token0": token0,
            "token1": token1,
            "fee": fee
        }
    except Exception as e:
        raise RuntimeError(f"Failed to query pool liquidity: {e}")
