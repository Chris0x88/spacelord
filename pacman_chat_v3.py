#!/usr/bin/env python3
"""
Pacman Chat v3 - Using WORKING btc_rebalancer2 code
Live trading with battle-tested execution.
"""

import sys
import os
sys.path.insert(0, '/Users/cdi/Documents/Github/pacman')

from btc_rebalancer_swap_engine import SaucerSwapV2Engine, SwapResult
from v2_tokens import DEFAULT_FEE

USDC_ID = "0.0.456858"
WBTC_ID = "0.0.10082597"
WETH_ID = "0.0.9770617"
WHBAR_ID = "0.0.1456986"

class PacmanChatV3:
    """Chat interface using the WORKING btc_rebalancer2 engine."""
    
    def __init__(self):
        print("🔌 Initializing Pacman Chat v3...")
        self.engine = SaucerSwapV2Engine()
        self.pending_swap = None
        print(f"✅ Ready! Account: {self.engine.eoa}")
    
    def chat(self, user_input):
        """Process user input."""
        cmd = user_input.lower().strip()
        
        if cmd in ['quit', 'exit', 'q']:
            return "👋 Goodbye!"
        
        if cmd == 'help':
            return """Commands:
  "swap 1 usdc wbtc" - Swap $1 USDC to WBTC
  "status" - Check account status
  "quit" - Exit
  
  Max: $1.00 per swap (hardcoded)"""
        
        if cmd == 'status':
            return f"""📊 Status:
  Account: {self.engine.eoa}
  Engine: SaucerSwapV2Engine (btc_rebalancer2)
  Max Swap: $1.00
  Network: Mainnet"""
        
        if 'swap' in cmd:
            return self.handle_swap(cmd)
        
        if self.pending_swap and cmd in ['yes', 'y']:
            return self.execute_pending()
        
        if self.pending_swap and cmd in ['no', 'n']:
            self.pending_swap = None
            return "❌ Cancelled"
        
        return "Type 'help' for commands"
    
    def handle_swap(self, cmd):
        """Handle swap command."""
        # Parse amount (default $1)
        amount = 1.0
        
        # Determine token pair
        if 'wbtc' in cmd or 'btc' in cmd:
            to_id, to_symbol = WBTC_ID, "WBTC"
        elif 'weth' in cmd or 'eth' in cmd:
            to_id, to_symbol = WETH_ID, "WETH"
        elif 'hbar' in cmd:
            to_id, to_symbol = WHBAR_ID, "HBAR"
        else:
            to_id, to_symbol = WBTC_ID, "WBTC"
        
        # Show preview
        result = f"""🎯 SWAP PREVIEW

From: ${amount} USDC
To: {to_symbol}

Execute this swap? (yes/no)"""
        
        self.pending_swap = {
            'amount': amount,
            'to_id': to_id,
            'to_symbol': to_symbol
        }
        
        return result
    
    def execute_pending(self):
        """Execute the pending swap using WORKING code."""
        if not self.pending_swap:
            return "No pending swap"
        
        swap = self.pending_swap
        self.pending_swap = None
        
        print(f"\n🚀 Executing ${swap['amount']} USDC → {swap['to_symbol']}...")
        print("   Using btc_rebalancer2's SaucerSwapV2Engine...")
        
        # Execute using EXACT working code
        result = self.engine.swap(
            token_in_id=USDC_ID,
            token_out_id=swap['to_id'],
            amount=swap['amount'],
            decimals_in=6,
            decimals_out=8,
            fee=DEFAULT_FEE,
            slippage=0.01,
            is_exact_input=True
        )
        
        if result.success:
            return f"""✅ SWAP EXECUTED!

TX Hash: {result.tx_hash}
Amount In: {result.amount_in} USDC
Amount Out: {result.amount_out} {swap['to_symbol']}
Gas: {result.gas_used}

Recorded for AI training!"""
        else:
            return f"""❌ SWAP FAILED

Error: {result.error}

Check HashScan for details."""

def main():
    print("="*60)
    print("🤖 PACMAN CHAT v3 - LIVE TRADING")
    print("   Using battle-tested btc_rebalancer2 code")
    print("="*60)
    
    chat = PacmanChatV3()
    
    print("\nType 'help' for commands\n")
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
            if user_input:
                response = chat.chat(user_input)
                print(f"\n🤖 Pacman:\n{response}\n")
                if response == "👋 Goodbye!":
                    break
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

if __name__ == "__main__":
    main()
