#!/usr/bin/env python3
"""
Pacman Chat Interface - Natural Language to Execution
Simple CLI chat that understands trading commands and routes them.
"""

import json
import re
from typing import Optional, Dict
from pathlib import Path

# Import our router
from pacman_variant_router import PacmanVariantRouter, TOKEN_VARIANTS

class PacmanChat:
    """
    Simple chat interface for Pacman trading.
    
    Examples:
    - "swap 500 usdc for wbtc"
    - "buy bitcoin with 1000 usdc"
    - "convert my usdc to wrapped btc"
    - "what's the cheapest way to get wbtc?"
    """
    
    def __init__(self):
        self.router = PacmanVariantRouter()
        self.router.load_pools()
        self.conversation_history = []
        
        # Token aliases for natural language
        self.token_aliases = {
            "usdc": ["USDC", "usdc", "usd coin"],
            "wbtc": ["WBTC", "wbtc", "wrapped btc", "wrapped bitcoin", "bitcoin", "btc"],
            "weth": ["WETH", "weth", "wrapped eth", "wrapped ethereum", "ethereum", "eth"],
            "hbar": ["HBAR", "hbar", "hedera"],
            "sauce": ["SAUCE", "sauce"],
            "usdt": ["USDT", "usdt", "tether"],
            "dai": ["DAI", "dai"],
            "link": ["LINK", "link", "chainlink"],
        }
        
        # Intent patterns
        self.patterns = {
            "swap": r"(?:swap|trade|exchange|convert)\s+(\d+(?:\.\d+)?)\s*(\w+)\s+(?:for|to|into)\s+(\w+)",
            "buy": r"(?:buy|purchase)\s+(\w+)\s+(?:with|using)\s+(\d+(?:\.\d+)?)\s*(\w+)",
            "sell": r"(?:sell)\s+(\d+(?:\.\d+)?)\s*(\w+)\s+(?:for|into)\s+(\w+)",
            "quote": r"(?:what|how much|quote).{0,30}(?:cost|price|get|for)\s+(\d+(?:\.\d+)?)?\s*(\w+)\s+(?:in|to)\s+(\w+)",
            "balance_check": r"(?:what|check|show|how much).{0,20}(?:balance|have|own|hold)",
        }
    
    def parse_intent(self, user_input: str) -> Optional[Dict]:
        """Parse natural language into structured intent."""
        user_input_lower = user_input.lower()
        
        # Try swap pattern
        match = re.search(self.patterns["swap"], user_input_lower)
        if match:
            amount = float(match.group(1))
            from_token_raw = match.group(2)
            to_token_raw = match.group(3)
            
            return {
                "action": "swap",
                "amount": amount,
                "from_token": self.resolve_token(from_token_raw),
                "to_token": self.resolve_token(to_token_raw),
                "user_preference": self.detect_preference(user_input_lower),
                "raw_input": user_input
            }
        
        # Try buy pattern (reversed)
        match = re.search(self.patterns["buy"], user_input_lower)
        if match:
            to_token_raw = match.group(1)
            amount = float(match.group(2))
            from_token_raw = match.group(3)
            
            return {
                "action": "swap",
                "amount": amount,
                "from_token": self.resolve_token(from_token_raw),
                "to_token": self.resolve_token(to_token_raw),
                "user_preference": self.detect_preference(user_input_lower),
                "raw_input": user_input
            }
        
        # Try quote pattern
        match = re.search(self.patterns["quote"], user_input_lower)
        if match:
            amount_str = match.group(1)
            amount = float(amount_str) if amount_str else 100  # Default $100
            from_token_raw = match.group(2)
            to_token_raw = match.group(3)
            
            return {
                "action": "quote",
                "amount": amount,
                "from_token": self.resolve_token(from_token_raw),
                "to_token": self.resolve_token(to_token_raw),
                "user_preference": "cheapest",
                "raw_input": user_input
            }
        
        # Try balance check
        if re.search(self.patterns["balance_check"], user_input_lower):
            return {
                "action": "balance_check",
                "raw_input": user_input
            }
        
        return None
    
    def resolve_token(self, token_str: str) -> Optional[str]:
        """Resolve token string to canonical symbol."""
        token_lower = token_str.lower()
        
        for canonical, aliases in self.token_aliases.items():
            if token_lower in [a.lower() for a in aliases]:
                # Return the appropriate variant
                if canonical == "wbtc":
                    return "WBTC_HTS"  # Default to HTS (visible)
                elif canonical == "weth":
                    return "WETH_HTS"
                elif canonical == "usdc":
                    return "USDC"
                return canonical.upper()
        
        return None
    
    def detect_preference(self, user_input: str) -> str:
        """Detect user preference from input."""
        if "cheap" in user_input or "lowest" in user_input or "best price" in user_input:
            return "cheapest"
        elif "visible" in user_input or "hashpack" in user_input or "see" in user_input:
            return "visible"
        elif "auto" in user_input:
            return "auto"
        return "auto"  # Default
    
    def handle_swap_intent(self, intent: Dict) -> str:
        """Handle a swap intent and return response."""
        amount = intent["amount"]
        from_token = intent["from_token"]
        to_token = intent["to_token"]
        preference = intent["user_preference"]
        
        if not from_token or not to_token:
            return "❌ I couldn't understand which tokens you want to swap. Try: 'swap 500 USDC for WBTC'"
        
        # Get route recommendation
        route = self.router.recommend_route(from_token, to_token, preference, amount)
        
        if not route:
            return f"❌ No route found for {from_token} → {to_token}"
        
        # Format response
        response = [
            f"🎯 **Swap Request: {amount} {from_token} → {to_token}**",
            f"",
            f"📊 **Recommended Route ({preference} preference):**",
            route.explain(),
            f"",
            f"💰 **Total Cost:** {route.total_cost_hbar:.4f} HBAR (~${route.total_cost_hbar * 0.09:.2f})",
            f"⏱️  **Estimated Time:** {route.estimated_time_seconds}s",
            f"👁️  **HashPack Visible:** {'Yes ✅' if route.hashpack_visible else 'No ❌ (unwrap required)'}",
            f"",
        ]
        
        # Add execution prompt
        if route.hashpack_visible:
            response.append("✅ This route outputs HTS tokens visible in HashPack.")
        else:
            response.append("⚠️  This route outputs ERC20 tokens (invisible in HashPack).")
            response.append("    You can unwrap them using: `unwrap all wbtc`")
        
        response.append("")
        response.append("**Execute this swap?** (Reply 'yes' to confirm, 'no' to cancel)")
        
        # Store pending swap for confirmation
        self.pending_swap = {
            "intent": intent,
            "route": route,
            "timestamp": "now"
        }
        
        return "\n".join(response)
    
    def handle_quote_intent(self, intent: Dict) -> str:
        """Handle a quote request."""
        amount = intent["amount"]
        from_token = intent["from_token"]
        to_token = intent["to_token"]
        
        if not from_token or not to_token:
            return "❌ I couldn't understand which tokens to quote. Try: 'what's the price of 500 USDC in WBTC?'"
        
        # Get all routes for comparison
        routes = self.router.get_all_routes(from_token, to_token, amount)
        
        if not routes:
            return f"❌ No routes found for {from_token} → {to_token}"
        
        response = [
            f"📊 **Quote: {amount} {from_token} → {to_token}**",
            f"",
            f"**Available Routes ({len(routes)} found):**",
            f"",
        ]
        
        for i, route in enumerate(routes, 1):
            visibility = "👁️  Visible" if route.hashpack_visible else "👻 Invisible"
            response.append(f"{i}. {route.total_cost_hbar:.4f} HBAR | {visibility} | {route.total_fee_percent:.2f}% fees")
            response.append(f"   {len(route.steps)} steps: {' → '.join([s.from_token for s in route.steps] + [route.steps[-1].to_token])}")
            response.append("")
        
        # Recommendation
        cheapest = routes[0]
        response.append(f"💡 **Recommendation:** Use Route 1 (cheapest)")
        if not cheapest.hashpack_visible:
            response.append(f"   ⚠️  Note: This outputs ERC20 tokens. Add ~0.02 HBAR to unwrap if needed.")
        
        return "\n".join(response)
    
    def handle_balance_check(self, intent: Dict) -> str:
        """Handle balance check request."""
        # In real implementation, this would query actual balances
        return """💰 **Balance Check**

To check your actual balances, I need access to your wallet.

Currently showing example balances:
• USDC: 1,250.00
• WBTC (HTS): 0.0523  ✅ Visible in HashPack
• WBTC (ERC20): 0.0081  👻 Invisible in HashPack
• WHBAR: 845.32

**Tip:** You can unwrap your ERC20 WBTC using `unwrap all wbtc`
"""
    
    def handle_confirmation(self, user_input: str) -> str:
        """Handle yes/no confirmation for pending swap."""
        if not hasattr(self, 'pending_swap') or not self.pending_swap:
            return "❌ No pending swap to confirm."
        
        user_input_lower = user_input.lower().strip()
        
        if user_input_lower in ['yes', 'y', 'confirm', 'execute', 'do it']:
            # In real implementation, this would execute the swap
            route = self.pending_swap["route"]
            intent = self.pending_swap["intent"]
            
            return f"""✅ **Swap Confirmed!**

Executing: {intent['amount']} {intent['from_token']} → {intent['to_token']}
Route: {len(route.steps)} steps, {route.total_cost_hbar:.4f} HBAR total cost

🔄 **Executing...**
[Step 1/{len(route.steps)}] Approving tokens...
[Step 2/{len(route.steps)}] Swapping on SaucerSwap...

⏳ Transaction pending...
"""
        elif user_input_lower in ['no', 'n', 'cancel', 'abort']:
            self.pending_swap = None
            return "❌ Swap cancelled."
        else:
            return "Please reply 'yes' to execute or 'no' to cancel."
    
    def chat(self, user_input: str) -> str:
        """Main chat handler."""
        user_input_lower = user_input.lower().strip()
        
        # Check for explicit confirmation responses
        if hasattr(self, 'pending_swap') and self.pending_swap:
            if user_input_lower in ['yes', 'y', 'confirm', 'execute', 'do it', 'go', 'proceed']:
                return self.handle_confirmation('yes')
            elif user_input_lower in ['no', 'n', 'cancel', 'abort', 'stop', 'quit']:
                return self.handle_confirmation('no')
            # If input is something else, treat it as a new command and clear pending
            else:
                self.pending_swap = None
        
        # Parse new intent
        intent = self.parse_intent(user_input)
        
        if not intent:
            return self.handle_help()
        
        # Cap amount at $1.00 for testing
        if "amount" in intent and intent["amount"] > 1.0:
            intent["amount"] = 1.0
            intent["note"] = "Amount capped at $1.00 for testing"
        
        # Validate supported token pairs (limited set for now)
        supported_pairs = [
            ("USDC", "WBTC_HTS"),
            ("USDC", "WBTC_LZ"),
            ("USDC_HTS", "WBTC_HTS"),
            ("USDC", "WETH_HTS"),
            ("USDC", "WHBAR"),
        ]
        
        if intent["action"] in ["swap", "quote"]:
            from_token = intent.get("from_token")
            to_token = intent.get("to_token")
            
            # Check if pair is in supported list
            pair_valid = (from_token, to_token) in supported_pairs
            
            if not pair_valid:
                return f"""⚠️  **Limited Beta Mode**

This pair ({from_token} → {to_token}) is not yet validated for live testing.

**Currently Supported (Tested & Validated):**
• USDC → WBTC (HTS or LZ)
• USDC → WETH (HTS)
• USDC → WHBAR

Try: "swap 1 USDC for WBTC"

AI training will expand to all tokens once we have execution data from these core pairs."""
        
        # Route to appropriate handler
        if intent["action"] == "swap":
            return self.handle_swap_intent(intent)
        elif intent["action"] == "quote":
            return self.handle_quote_intent(intent)
        elif intent["action"] == "balance_check":
            return self.handle_balance_check(intent)
        
        return self.handle_help()
    
    def handle_help(self) -> str:
        """Return help message."""
        return """🤖 **Pacman Trading Assistant**

I can help you swap tokens on Hedera. Try these commands:

**Swap Commands:**
• "swap 500 USDC for WBTC"
• "buy WBTC with 1000 USDC"
• "convert USDC to wrapped bitcoin"

**Quote Commands:**
• "what's the price of 500 USDC in WBTC?"
• "how much WBTC for 1000 USDC?"

**Balance:**
• "check my balance"
• "what do I have?"

**Preferences:**
Add "cheapest" for lowest cost (may be ERC20)
Add "visible" for HashPack-compatible (HTS)

Example: "swap 500 USDC for WBTC cheapest"
"""

def run_chat_interface():
    """Run interactive chat session."""
    print("="*80)
    print("🤖 PACMAN TRADING CHAT")
    print("   Natural language interface for Hedera swaps")
    print("="*80)
    print()
    print("Type your swap request or 'help' for examples.")
    print("Type 'quit' to exit.")
    print()
    
    chat = PacmanChat()
    
    # Demo commands
    demo_commands = [
        "swap 500 usdc for wbtc",
        "what's the cheapest way to get wbtc?",
        "check my balance",
        "quote 1000 usdc to wbtc",
    ]
    
    print("🎮 **Demo Mode** - Testing these commands:")
    for cmd in demo_commands:
        print(f"\n👤 You: {cmd}")
        print(f"🤖 Pacman:\n{chat.chat(cmd)}")
        print("-"*80)
    
    # Interactive mode
    print("\n💬 **Interactive Mode** - Type your command:")
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if user_input:
                response = chat.chat(user_input)
                print(f"\n🤖 Pacman:\n{response}")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break

if __name__ == "__main__":
    run_chat_interface()
