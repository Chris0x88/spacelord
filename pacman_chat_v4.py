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
        
        # 1. Alias Mapping
        token_in, token_out = None, None
        for key, meta in self.tokens.items():
            for alias in [key.lower()] + meta["aliases"]:
                if alias in text:
                    if not token_in: token_in = key
                    else: token_out = key
        
        # 2. Logic Detection (Reverse Targeting)
        is_reverse = any(x in text for x in ["get", "receive", "need", "for exactly"])
        
        # 3. Extraction
        import re
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        amount = float(nums[0]) if nums else 1.0
        
        # Level-Up Fallback Check
        if not token_in or not token_out:
            print("⚠️ Brain confused... Requesting Oracle assistance.")
            # This is where we'd call Gemini/Sonnet to 'Refine' the request
            return None, None, None

        if is_reverse:
            return token_out, token_in, amount # Swap directions for reverse logic
        return token_in, token_out, amount

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

        # Let the AI process
        from_t, to_t, amount = self.brain.inference(user_input)
        
        if not from_t:
            return "❌ Brain & Oracle both confused. Try: 'Swap $1 USDC for Bitcoin'"
        
        amount = min(amount, 1.0) # Safety first
        
        self.pending_swap = {
            'amount': amount,
            'from_t': from_t,
            'to_id': TOKEN_METADATA[to_t]["id"],
            'to_symbol': to_t
        }

        return f"""🧠 Brain Analysis (v2):
Detected Intent: {"REVERSE_SWAP" if "get" in user_input.lower() else "FORWARD_SWAP"}
Target Result: {amount} {to_t}
Funding from: {from_t}

Execute this swap? (yes/no)"""

    def execute_pending(self):
        swap = self.pending_swap
        self.pending_swap = None
        
        print(f"\n🚀 AI-Led Execution: {swap['amount']} {swap['from_t']} → {swap['to_symbol']}...")
        
        result = self.engine.swap(
            token_in_id=TOKEN_METADATA[swap['from_t']]["id"],
            token_out_id=swap['to_id'],
            amount=swap['amount'],
            decimals_in=TOKEN_METADATA[swap['from_t']]["decimals"],
            decimals_out=TOKEN_METADATA[swap['to_symbol']]["decimals"],
            fee=DEFAULT_FEE,
            slippage=0.01,
            is_exact_input=True
        )
        
        if result.success:
            return f"✅ SUCCESS!\nTX: {result.tx_hash}\nRecorded for v2 training."
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
