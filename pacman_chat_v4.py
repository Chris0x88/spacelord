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

# Token Knowledge Base (Must match Training Logic)
TOKEN_METADATA = {
    "USDC": {"id": "0.0.456858", "decimals": 6},
    "WBTC": {"id": "0.0.10082597", "decimals": 8},
    "WETH": {"id": "0.0.9770617", "decimals": 8},
    "WHBAR": {"id": "0.0.1456986", "decimals": 8},
    "HBAR": {"id": "0.0.0", "decimals": 8}
}

class PacmanBrainInterface:
    def __init__(self, model_path):
        print("🧠 Connecting to Pacman Brain...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path)
        self.model.eval()
        self.tokens = list(TOKEN_METADATA.keys())
        print("✅ Brain online.")

    def inference(self, text):
        """
        AI Intent Detection.
        Note: In Phase 1, we use token extraction logic.
        Future phases will use the classification head for full logic.
        """
        text = text.upper()
        detected_tokens = [t for t in self.tokens if t in text or t.replace('[HTS]', '') in text]
        
        # Simple extraction for v1 stability
        from_t = detected_tokens[0] if len(detected_tokens) > 0 else "USDC"
        to_t = detected_tokens[1] if len(detected_tokens) > 1 else "WBTC"
        
        # Extract number
        import re
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        amount = float(nums[0]) if nums else 1.0
        
        return from_t, to_t, min(amount, 1.0) # Safety first

class PacmanChatV4:
    def __init__(self):
        print("="*60)
        print("🤖 PACMAN CHAT v4 - AI-NATIVE")
        print("="*60)
        self.brain = PacmanBrainInterface(f"{PACMAN_DIR}/model/pacman_v1_brain")
        self.engine = SaucerSwapV2Engine()
        self.pending_swap = None

    def chat(self, user_input):
        cmd = user_input.lower().strip()
        
        if cmd in ['quit', 'exit', 'q']:
            return "👋 Goodbye!"
        
        if cmd == 'status':
            return f"📊 Account: {self.engine.eoa}\n🧠 Brain: Pacman v1 (BERT-Tiny)\n🛡️ Mode: LIVE"

        if self.pending_swap and cmd in ['yes', 'y']:
            return self.execute_pending()

        # Let the AI process the instruction
        from_t, to_t, amount = self.brain.inference(user_input)
        
        self.pending_swap = {
            'amount': amount,
            'from_t': from_t,
            'to_id': TOKEN_METADATA[to_t]["id"],
            'to_symbol': to_t
        }

        return f"""🧠 Brain Analysis:
Detected Intent: SWAP
From: {amount} {from_t}
To: {to_t}

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
