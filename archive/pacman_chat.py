#!/usr/bin/env python3
"""
Pacman Chat v5 (Consumer-First)
Powered by Pacman Brain v2 and Standardized SwapIntent.
"""

import sys
import os
import time
from pacman_brain_v2 import PacmanBrainV2
from pacman_types import SwapIntent, SwapStrategy
from btc_rebalancer_swap_engine import SaucerSwapV2Engine
from v2_tokens import DEFAULT_FEE

# Ensure we can import modules
sys.path.insert(0, os.getcwd())

class PacmanWizard:
    def __init__(self):
        print("="*60)
        print("🤖 PACMAN TRADER - Consumer First Edition")
        print("   'Swap 100 USDC for HBAR'  or  'Buy 1000 SAUCE'")
        print("="*60)
        
        self.brain = PacmanBrainV2()
        self.engine = SaucerSwapV2Engine() # Initializes Web3 and Engine
        self.current_intent = None

    def start(self):
        while True:
            try:
                if not self.current_intent:
                    user_input = input("\n👤 You: ").strip()
                    if not user_input: continue
                    if user_input.lower() in ['q', 'quit', 'exit']:
                        print("👋 Goodbye!")
                        break

                    # Initial Parse
                    self.current_intent = self.brain.parse_intent(user_input)
                    print(f"🧠 Brain Debug: {self.current_intent}")

                # Check for completeness and ask clarifying questions
                self._refine_intent()

                # Once complete, confirm and execute
                if self.current_intent.is_complete:
                    if self._confirm_and_execute():
                        self.current_intent = None # Reset after success or cancellation
                    else:
                        self.current_intent = None # Reset if user says no

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                self.current_intent = None

    def _refine_intent(self):
        """
        Interactively ask for missing fields.
        """
        intent = self.current_intent
        
        # 1. Missing Token In (The thing we are spending/selling)
        # But wait, if Strategy is RECEIVE_EXACT (Buy X), we might not know what we are paying with.
        # Usually defaults to HBAR or USDC, but better to ask.
        
        if not intent.token_in:
            if intent.strategy == SwapStrategy.SPEND_EXACT:
                ans = input("🤖 Pacman: What token do you want to **sell/spend**? ")
            else:
                ans = input("🤖 Pacman: What token do you want to **pay with**? ")
            
            # Use brain to detect token in answer
            detected = self.brain.detect_tokens(ans)
            if detected:
                intent.token_in = detected[0][0]
            else:
                print("❌ I didn't recognize that token. Try again.")
                return

        # 2. Missing Token Out (The thing we are buying/receiving)
        if not intent.token_out:
            if intent.strategy == SwapStrategy.RECEIVE_EXACT:
                ans = input("🤖 Pacman: What token do you want to **buy/receive**? ")
            else:
                ans = input("🤖 Pacman: What token do you want to **receive**? ")

            detected = self.brain.detect_tokens(ans)
            if detected:
                intent.token_out = detected[0][0]
            else:
                print("❌ I didn't recognize that token. Try again.")
                return

        # 3. Missing Quantity
        if intent.qty <= 0:
            if intent.strategy == SwapStrategy.SPEND_EXACT:
                ans = input(f"🤖 Pacman: How much **{intent.token_in}** do you want to spend? ")
            else:
                ans = input(f"🤖 Pacman: How much **{intent.token_out}** do you want to receive? ")

            # Try parse number (handle commas)
            import re
            clean_ans = ans.replace(",", "")
            nums = re.findall(r"(\d+(\.\d+)?)", clean_ans)
            if nums:
                intent.qty = float(nums[0][0])
            else:
                print("❌ I didn't see a number. Try again.")
                return

    def _confirm_and_execute(self) -> bool:
        """
        Show friendly summary and execute.
        """
        intent = self.current_intent
        
        # Calculate estimate to show user
        print("\n⏳ Fetching live quote...")
        try:
            # Get decimals
            # We need to know decimals for tokens.
            # Using metadata from Brain or fetching from Engine?
            # Engine has `get_quote`.

            # Brain has `known_tokens` dict.
            # We can use that.
            t_in_meta = self.brain.known_tokens.get(intent.token_in)
            t_out_meta = self.brain.known_tokens.get(intent.token_out)

            if not t_in_meta or not t_out_meta:
                print(f"❌ Error: Metadata missing for {intent.token_in} or {intent.token_out}.")
                return False

            dec_in = t_in_meta["decimals"]
            dec_out = t_out_meta["decimals"]

            # Call Engine Quote
            # Engine supports `is_exact_input`
            is_exact_input = (intent.strategy == SwapStrategy.SPEND_EXACT)

            quote_result_raw = self.engine.get_quote(
                token_in_id=t_in_meta["id"],
                token_out_id=t_out_meta["id"],
                amount=intent.qty,
                decimals_in=dec_in,
                decimals_out=dec_out,
                is_exact_input=is_exact_input
            )

            if quote_result_raw is None:
                print("❌ Could not get a quote. Route might not exist.")
                return False

            # Format the output
            if is_exact_input:
                # We spent Qty (Exact), we receive Quote (Approx)
                amount_in = intent.qty
                amount_out = quote_result_raw / (10 ** dec_out)

                print(f"\n📝 **Confirm Order** (Spend Exact):")
                print(f"   📉 You Pay:    {amount_in:.6f} {intent.token_in}")
                print(f"   📈 You Get:   ~{amount_out:.6f} {intent.token_out}")
            else:
                # We receive Qty (Exact), we spend Quote (Approx)
                amount_in = quote_result_raw / (10 ** dec_in)
                amount_out = intent.qty

                print(f"\n📝 **Confirm Order** (Receive Exact):")
                print(f"   📉 You Pay:   ~{amount_in:.6f} {intent.token_in}")
                print(f"   📈 You Get:    {amount_out:.6f} {intent.token_out}")

            confirm = input("\n✅ Execute this swap? (y/n): ").lower()
            if confirm in ['y', 'yes']:
                return self._execute_swap(intent, t_in_meta, t_out_meta)
            else:
                print("🚫 Cancelled.")
                return False

        except Exception as e:
            print(f"❌ Quote Error: {e}")
            return False

    def _execute_swap(self, intent: SwapIntent, t_in, t_out) -> bool:
        print("\n🚀 Executing on SaucerSwap V2...")
        result = self.engine.swap(
            token_in_id=t_in["id"],
            token_out_id=t_out["id"],
            amount=intent.qty,
            decimals_in=t_in["decimals"],
            decimals_out=t_out["decimals"],
            is_exact_input=(intent.strategy == SwapStrategy.SPEND_EXACT)
        )

        if result.success:
            print(f"✅ **Success!**")
            print(f"   TX: https://hashscan.io/mainnet/transaction/{result.tx_hash}")
            print(f"   Swapped {result.amount_in:.6f} {intent.token_in} -> {result.amount_out:.6f} {intent.token_out}")
            return True
        else:
            print(f"❌ Failed: {result.error}")
            return False

if __name__ == "__main__":
    wizard = PacmanWizard()
    wizard.start()
