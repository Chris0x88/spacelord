#!/usr/bin/env python3
"""
Pacman Chat v4 (AI-Native) - Powered by Pacman Brain v1
Replaces Regex with our fine-tuned tiny transformer.
"""

import sys
import os
import torch
import json
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F

# Paths
PACMAN_DIR = '/Users/cdi/Documents/Github/pacman'
sys.path.insert(0, PACMAN_DIR)

from btc_rebalancer_swap_engine import SaucerSwapV2Engine
from v2_tokens import DEFAULT_FEE
from dotenv import load_dotenv

# Load .env file and ensure PRIVATE_KEY is in environment
load_dotenv()
if os.getenv("PACMAN_PRIVATE_KEY") and not os.getenv("PRIVATE_KEY"):
    os.environ["PRIVATE_KEY"] = os.getenv("PACMAN_PRIVATE_KEY")

# Token Knowledge Base
TOKEN_METADATA = {
    "USDC": {"id": "0.0.456858", "decimals": 6, "aliases": ["dollars", "usd", "cash", "bucks"]},
    "WBTC": {"id": "0.0.10082597", "decimals": 8, "aliases": ["bitcoin", "btc", "sats"]},
    "WETH": {"id": "0.0.9770617", "decimals": 8, "aliases": ["ethereum", "eth", "ether"]},
    "WHBAR": {"id": "0.0.1456986", "decimals": 8, "aliases": ["wrapped hbar", "whbar"]},
    "HBAR": {"id": "0.0.0", "decimals": 8, "aliases": ["hbar", "hedera", "native"]}
}

class PacmanBrainInterface:
    def __init__(self, model_path):
        print("🧠 Connecting to Pacman Brain v2...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path)
        self.model.eval()
        self.tokens = TOKEN_METADATA
        print("✅ Brain online.")

    def inference(self, text):
        text = text.lower()
        
        # 1. Strict Keyword Directional Logic
        # "Swap [A] for [B]" -> FROM A, TO B
        # "Buy [B] with [A]" -> FROM A, TO B
        # "Get [B] using [A]" -> FROM A, TO B
        
        token_in, token_out = None, None
        amount = 1.0
        is_exact_input = True  # Default: amount is INPUT
        
        # Find all mentioned tokens in order
        found = []
        for key, meta in self.tokens.items():
            for alias in [key.lower()] + meta["aliases"]:
                if alias in text:
                    # Capture the position to maintain grammar order
                    found.append((text.find(alias), key))
        
        found.sort() # Ensure they are in order of the sentence
        
        # 2. Logic Gates with EXACT INPUT vs EXACT OUTPUT detection
        import re
        
        import re
        
        # Normalize text for keyword matching
        clean_text = " " + text + " "
        
        # 2. Logic Gates with EXACT INPUT vs EXACT OUTPUT detection
        
        # Template: "Swap X for [exactly] Y"
        if " for " in clean_text:
            parts = text.split(" for ")
            before_for = parts[0]
            after_for = parts[1] if len(parts) > 1 else ""
            token_in = self._extract_token(before_for)
            token_out = self._extract_token(after_for)
            
            # Check if amount is in AFTER part ("swap wbtc for $1 usdc") or if "exactly" is used
            nums_after = re.findall(r"[-+]?\d*\.\d+|\d+", after_get if " get " in clean_text or clean_text.startswith(" get ") else after_for)
            # Re-evaluating for the "for" case specifically
            nums_after = re.findall(r"[-+]?\d*\.\d+|\d+", after_for)
            
            if (nums_after and token_out) or "exactly" in text or "receive" in text:
                is_exact_input = False  # Amount refers to OUTPUT token
                amount = float(nums_after[0]) if nums_after else 1.0
            else:
                is_exact_input = True   # Amount refers to INPUT token
                nums_before = re.findall(r"[-+]?\d*\.\d+|\d+", before_for)
                amount = float(nums_before[0]) if nums_before else 1.0
                
        # Template: "Get [exactly] Y using X" or "Get [exactly] Y with X"
        elif " get " in clean_text or clean_text.startswith(" get "):
            is_exact_input = False # "Get Y" implies Y is the target amount
            
            # Find tokens
            token_out = self._extract_token(text) # Assume first token mentioned after get is output
            # Need to find the "using/with" part for token_in
            if " using " in clean_text:
                token_in = self._extract_token(text.split(" using ")[1])
            elif " with " in clean_text:
                token_in = self._extract_token(text.split(" with ")[1])
            else:
                # Fallback: if two tokens found, first is out, second is in (for "get" case)
                if len(found) >= 2:
                    token_out = found[0][1]
                    token_in = found[1][1]
            
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
            amount = float(nums[0]) if nums else 1.0
            
        elif " with " in clean_text or " using " in clean_text:
            # "Buy Y with X" or "Trade Y using X"
            sep = " with " if " with " in clean_text else " using "
            parts = text.split(sep)
            before_sep = parts[0]
            after_sep = parts[1] if len(parts) > 1 else ""
            
            # If "buy" or "get" is in start, before is OUT, after is IN
            if any(w in before_sep.lower() for w in ["buy", "get", "need", "receive"]):
                token_out = self._extract_token(before_sep, prefer_non_usdc=True)
                token_in = self._extract_token(after_sep)
                is_exact_input = False if any(re.findall(r"[-+]?\d*\.\d+|\d+", before_sep)) else True
            else:
                token_in = self._extract_token(after_sep)
                token_out = self._extract_token(before_sep)
                is_exact_input = True
            
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
            amount = float(nums[0]) if nums else 1.0

        # Template: "into" (flip X into Y)
        elif " into " in clean_text:
            parts = text.split(" into ")
            token_in = self._extract_token(parts[0])
            token_out = self._extract_token(parts[1])
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
            amount = float(nums[0]) if nums else 1.0
            is_exact_input = True
        
        if not token_in and len(found) >= 2:
            token_in = found[0][1]
            token_out = found[1][1]
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
            amount = float(nums[0]) if nums else 1.0

        # 3. AI Intent Detection (Simulated embedding similarity)
        # In production, this would be: self.model(encoding)["intent_logits"]
        intent = "swap"
        if any(w in text for w in ["balance", "wallet", "bal", "assets", "how much", "portfolio", "money", " holdings"]):
            intent = "balance"
        elif any(w in text for w in ["history", "transactions", "tx", "last 10", "activity", "recently", " txs"]):
            intent = "history"
            
        return intent, token_in, token_out, amount, is_exact_input

    def _extract_token(self, fragment, prefer_non_usdc=False):
        if not fragment: return None
        
        # Sort all aliases by length descending to match "wrapped hbar" before "hbar"
        all_aliases = []
        for key, meta in self.tokens.items():
            for alias in [key.lower()] + meta["aliases"]:
                all_aliases.append((alias, key))
        all_aliases.sort(key=lambda x: len(x[0]), reverse=True)
        
        found_tokens = []
        for alias, key in all_aliases:
            if f" {alias} " in f" {fragment.lower()} " or alias == fragment.lower().strip():
                if key not in [t[1] for t in found_tokens]:
                    found_tokens.append((alias, key))
                
        if not found_tokens:
            # Fallback to simple substring
            for alias, key in all_aliases:
                if alias in fragment.lower():
                    if key not in [t[1] for t in found_tokens]:
                        found_tokens.append((alias, key))

        if not found_tokens: return None
        
        if prefer_non_usdc and len(found_tokens) > 1:
            # If we see "dollars" and "bitcoin", and we want the actual token, pick bitcoin
            for alias, key in found_tokens:
                if key != "USDC":
                    return key
        
        return found_tokens[0][1]

class PacmanChatV4:
    def __init__(self):
        print("="*60)
        print("🤖 PACMAN CHAT v4 - AI-NATIVE (Brain v2)")
        print("="*60)
        self.brain = PacmanBrainInterface(f"{PACMAN_DIR}/model/pacman_v1_brain")
        self.engine = SaucerSwapV2Engine()
        self.pending_swap = None

    def chat(self, user_input):
        cmd = user_input.lower().strip()
        
        if cmd in ['quit', 'exit', 'q']:
            return "👋 Goodbye!"
        
        if self.pending_swap and cmd in ['yes', 'y']:
            return self.execute_pending()

        # Let the AI Brain lead the execution
        intent, from_t, to_t, amount, is_exact_input = self.brain.inference(user_input)
        
        # 1. AI-Led Balance/Wallet Intent
        if intent == "balance":
            balances = self.engine.get_all_balances(TOKEN_METADATA)
            if not balances:
                return "Your wallet appears to be empty (or all known balances are zero)."
            
            output = "💰 **Current Balances (with USDC valuation):**\n"
            total_usd = 0
            for sym, data in balances.items():
                bal = data["balance"]
                usd = data["usd_value"]
                output += f"- {sym}: {bal:.6f} (${usd:.2f})\n"
                total_usd += usd
            
            output += f"\n**Total Portfolio Value: ${total_usd:.2f}**"
            return output

        # 2. AI-Led Transaction History Intent
        if intent == "history":
            txs = self.engine.get_recent_transactions(limit=10)
            if not txs:
                if not self.engine.account_id:
                    return "❌ Cannot fetch history: `HEDERA_ACCOUNT_ID` is not set in `.env`."
                return "No recent transactions found for this account."
            
            output = "📜 **Last 10 Transactions:**\n"
            for tx in txs:
                memo = f" | {tx['memo']}" if tx['memo'] else ""
                fee_str = f" [Fee: {tx['fee_hbar']:.4f} HBAR (${tx['fee_usdc']:.4f})]"
                output += f"- `{tx['timestamp']}`: {tx['name']} -> {tx['result']}{memo}{fee_str}\n"
            return output

        # 3. Swap Intent
        if not from_t or not to_t:
            return "❌ Brain & Oracle both confused. Try: 'Swap $1 USDC for Bitcoin' or 'What is my balance?'"
        
        amount = min(amount, 100.0) # Safety first (increased for HBAR/USDC)
        
        self.pending_swap = {
            'amount': amount,
            'from_t': from_t,
            'to_id': TOKEN_METADATA[to_t]["id"],
            'to_symbol': to_t,
            'is_exact_input': is_exact_input
        }

        mode_str = "EXACT_OUTPUT (you receive)" if not is_exact_input else "EXACT_INPUT (you send)"
        return f"""🧠 Brain Analysis (v2):
Detected Intent: {mode_str}
Target: {amount} {to_t if not is_exact_input else from_t}
{'Receive' if not is_exact_input else 'Send'}: {amount} {to_t if not is_exact_input else from_t}
{'Pay with' if not is_exact_input else 'To receive'}: {from_t if not is_exact_input else to_t}

Execute this swap? (yes/no)"""

    def execute_pending(self):
        swap = self.pending_swap
        self.pending_swap = None
        
        is_exact_input = swap.get('is_exact_input', True)
        mode = "EXACT_INPUT" if is_exact_input else "EXACT_OUTPUT"
        print(f"\n🚀 AI-Led Execution [{mode}]: {swap['amount']} {swap['from_t'] if is_exact_input else swap['to_symbol']} → {swap['to_symbol'] if is_exact_input else swap['from_t']}...")
        
        result = self.engine.swap(
            token_in_id=TOKEN_METADATA[swap['from_t']]["id"],
            token_out_id=swap['to_id'],
            amount=swap['amount'],
            decimals_in=TOKEN_METADATA[swap['from_t']]["decimals"],
            decimals_out=TOKEN_METADATA[swap['to_symbol']]["decimals"],
            fee=DEFAULT_FEE,
            slippage=0.01,
            is_exact_input=is_exact_input
        )
        
        if result.success:
            # Get USDC valuation for the result
            price_out = self.engine.get_usdc_price(swap['to_symbol'], TOKEN_METADATA[swap['to_symbol']]["decimals"])
            usd_value = result.amount_out * price_out
            
            return f"""✅ **Swap Success!**
Transaction Hash: `{result.tx_hash}`
Result: {result.amount_in:.6f} {swap['from_t']} → **{result.amount_out:.6f} {swap['to_symbol']}** (${usd_value:.2f})
Gas Used: {result.gas_used}
Recorded for v2 training.
"""
        return f"❌ FAILED: {result.error}"

if __name__ == "__main__":
    chat_app = PacmanChatV4()
    while True:
        try:
            inp = input("👤 You: ")
            if inp:
                print(f"🤖 Pacman: {chat_app.chat(inp)}")
        except (KeyboardInterrupt, EOFError):
            break
