"""
Pacman Transfers
================

Handles direct crypto transfers (HBAR and HTS Tokens) using the JSON-RPC relay.
This module abstracts the EVM complexity to provide a simple "send" interface.

Usage:
    result = execute_transfer(executor, "HBAR", 100.0, "0.0.12345")
    result = execute_transfer(executor, "USDC", 50.0, "0x...")
"""

import time
from typing import Optional, Dict, Any
from src.logger import logger
from lib.saucerswap import hedera_id_to_evm, ERC20_ABI

def execute_transfer(executor, token_symbol: str, amount: float, recipient: str, memo: str = None) -> dict:
    """
    Execute a transfer of HBAR or Tokens.
    
    Args:
        executor: Initialized PacmanExecutor instance.
        token_symbol: "HBAR" or token symbol (e.g. "USDC").
        amount: Amount in readable units (e.g. 100.0).
        recipient: Hedera ID (0.0.x) or EVM Address (0x...).
        memo: Optional message to include (HBAR only for on-chain, both for local history).
        
    Returns:
        dict with success, tx_hash, error, and receipts.
    """
    try:
        # 1. Resolve Recipient Address
        if recipient.startswith("0.0."):
            to_address = hedera_id_to_evm(recipient)
            # SAFETY CHECK: Whitelist
            if not executor.is_sim:
                import json
                from pathlib import Path
                try:
                    with open("data/settings.json") as f:
                        settings = json.load(f)
                        whitelist = settings.get("transfer_whitelist", [])
                        whitelist_addresses = [entry.get("address") for entry in whitelist]
                        if recipient not in whitelist_addresses:
                            return {"success": False, "error": f"SAFETY: Recipient {recipient} not in whitelist!"}
                except Exception as e:
                    return {"success": False, "error": f"SAFETY: Whitelist check failed: {e}"}

        elif recipient.startswith("0x") and len(recipient) == 42:
            to_address = executor.w3.to_checksum_address(recipient)
            # Cannot easily whitelist EVM addresses without mapping, so BLOCK for now
            if not executor.is_sim:
                 return {"success": False, "error": "SAFETY: Direct EVM transfers blocked. Use Hedera ID."}

        else:
            return {"success": False, "error": f"Invalid recipient format: {recipient}"}
            
        is_native = token_symbol.upper() in ["HBAR", "0.0.0"]
        
        logger.info(f"\n💸 Initiating Transfer: {amount} {token_symbol} -> {recipient}")
        if memo:
            logger.info(f"   Memo: {memo}")
        logger.info(f"   EVM Recipient: {to_address}")
        
        tx_hash = None
        
        # 2. HBAR Native Transfer
        if is_native:
            # Check Balance
            balance_wei = executor.w3.eth.get_balance(executor.eoa)
            amount_wei = int(amount * 10**18) # Hedera EVM uses 18 decimals for HBAR
            
            # Gas Buffer (21000 gas * price)
            gas_price = executor.w3.eth.gas_price
            
            # If memo provided, add data field and increase gas
            data = b""
            gas_limit = 21000
            if memo:
                data = executor.w3.to_hex(text=memo)
                gas_limit = 30000 # Small buffer for data field
            
            gas_cost = gas_limit * gas_price
            
            if balance_wei < (amount_wei + gas_cost):
                return {"success": False, "error": f"Insufficient HBAR. Need {amount} + gas."}
                
            logger.info("   📡 Sending HBAR via JSON-RPC...")
            tx = {
                'to': to_address,
                'value': amount_wei,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': executor.w3.eth.get_transaction_count(executor.eoa),
                'chainId': executor.chain_id,
                'data': data
            }
            
            if executor.is_sim:
                logger.info("   ⚠️  SIMULATION MODE: Skipping broadcast.")
                tx_hash = "SIMULATED_HBAR_TRANSFER"
                # Mock receipt waiting
                time.sleep(1)
                res = {
                    "success": True, 
                    "tx_hash": tx_hash,
                    "block": 0,
                    "gas_used": 21000,
                    "recipient": recipient,
                    "amount": amount,
                    "symbol": token_symbol,
                    "memo": memo
                }
                executor._record_transfer_execution(res)
                return res

            pk = executor.config.private_key.reveal()
            try:
                signed = executor.w3.eth.account.sign_transaction(tx, pk)
                tx_hash = executor.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
            finally:
                del pk # Secure cleanup
            
        # 3. Token Transfer (ERC20/HTS)
        else:
            # Resolve Token ID/Address
            token_id = executor._get_token_id(token_symbol)
            if not token_id:
                return {"success": False, "error": f"Unknown token: {token_symbol}"}
                
            token_address = hedera_id_to_evm(token_id)
            decimals = executor._get_token_decimals(token_symbol)
            amount_raw = int(amount * 10**decimals)
            
            # Check Balance
            token_contract = executor.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            balance_raw = token_contract.functions.balanceOf(executor.eoa).call()
            
            if balance_raw < amount_raw:
                return {"success": False, "error": f"Insufficient {token_symbol}. Have {balance_raw/10**decimals}, Need {amount}"}
            
            logger.info(f"   🛡️  Sending {token_symbol} (HTS/ERC20)...")
            tx = token_contract.functions.transfer(to_address, amount_raw).build_transaction({
                'from': executor.eoa,
                'gas': 100000, # Increased gas for safety
                'gasPrice': executor.w3.eth.gas_price,
                'nonce': executor.w3.eth.get_transaction_count(executor.eoa),
                'chainId': executor.chain_id
            })
            
            if executor.is_sim:
                logger.info("   ⚠️  SIMULATION MODE: Skipping broadcast.")
                tx_hash = f"SIMULATED_{token_symbol}_TRANSFER"
                time.sleep(1)
                res = {
                    "success": True, 
                    "tx_hash": tx_hash,
                    "block": 0,
                    "gas_used": 50000,
                    "recipient": recipient,
                    "amount": amount,
                    "symbol": token_symbol,
                    "memo": memo
                }
                executor._record_transfer_execution(res)
                return res

            pk = executor.config.private_key.reveal()
            try:
                signed = executor.w3.eth.account.sign_transaction(tx, pk)
                tx_hash = executor.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
            finally:
                del pk

        # 4. Wait for Receipt
        logger.info(f"   ⏳ Submitted. Hash: {tx_hash}")
        receipt = executor.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        # Prepare result for recording
        res = {
            "success": receipt.status == 1,
            "tx_hash": tx_hash,
            "block": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "recipient": recipient,
            "amount": amount,
            "symbol": token_symbol,
            "memo": memo
        }
        executor._record_transfer_execution(res)

        if receipt.status == 1:
            logger.info("   ✅ Transfer Successful!")
            return res
        else:
            return {"success": False, "error": "Transaction reverted on-chain", "tx_hash": tx_hash}

    except Exception as e:
        logger.error(f"   ❌ Transfer Failed: {e}")
        return {"success": False, "error": str(e)}
