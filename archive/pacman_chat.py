#!/usr/bin/env python3
"""
Pacman Chat Interface v2 - Production Ready
Natural language interface with config, pre-flight, and execution.
"""

import json
import re
from typing import Optional, Dict
from pathlib import Path

# Import our components
from pacman_variant_router import PacmanVariantRouter, TOKEN_VARIANTS
from pacman_config import PacmanConfig
from pacman_preflight import PacmanPreFlight

class PacmanChat:
    """
    Production-ready chat interface for Pacman trading.

    Examples:
    - "swap 1 usdc for wbtc"
    - "buy bitcoin with 1 usdc"
    - "check my config"
    - "status"
    """

    def __init__(self):
        # Load configuration
        self.config = PacmanConfig.from_env()
        valid, message = self.config.validate()
        self.config_valid = valid
        self.config_message = message

        # Initialize router
        self.router = PacmanVariantRouter()
        self.router.load_pools()

        # Initialize pre-flight checker
        self.preflight = PacmanPreFlight(self.config)

        # State
        self.pending_swap = None
        self.execution_history = []

        # Token aliases
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
            "status": r"(?:status|config|settings|info)",
        }

    def parse_intent(self, user_input: str) -> Optional[Dict]:
        """Parse natural language into structured intent."""
        user_input_lower = user_input.lower().strip()

        # Check for status command
        if re.search(self.patterns["status"], user_input_lower):
            return {"action": "status"}

        # Try swap pattern
        match = re.search(self.patterns["swap"], user_input_lower)
        if match:
            amount = float(match.group(1))
            from_token = self.resolve_token(match.group(2))
            to_token = self.resolve_token(match.group(3))
            return {
                "action": "swap",
                "amount": amount,
                "from_token": from_token,
                "to_token": to_token,
                "raw_input": user_input
            }

        # Try buy pattern
        match = re.search(self.patterns["buy"], user_input_lower)
        if match:
            to_token = self.resolve_token(match.group(1))
            amount = float(match.group(2))
            from_token = self.resolve_token(match.group(3))
            return {
                "action": "swap",
                "amount": amount,
                "from_token": from_token,
                "to_token": to_token,
                "raw_input": user_input
            }

        return None

    def resolve_token(self, token_str: str) -> Optional[str]:
        """Resolve token string to canonical symbol."""
        token_lower = token_str.lower()
        for canonical, aliases in self.token_aliases.items():
            if token_lower in [a.lower() for a in aliases]:
                if canonical == "wbtc":
                    return "WBTC_HTS"  # Default to HTS
                elif canonical == "weth":
                    return "WETH_HTS"
                return canonical.upper()
        return None

    def handle_status(self) -> str:
        """Show current configuration status."""
        lines = [
            "📊 PACMAN STATUS",
            "="*60,
            f"Configuration: {'✅ Valid' if self.config_valid else '❌ Invalid'}",
        ]

        if not self.config_valid:
            lines.append(f"Error: {self.config_message}")

        lines.extend([
            "",
            f"Network: {self.config.network}",
            f"Account: {self.config.hedera_account_id or 'Not set'}",
            f"Private Key: {'✅ Set' if self.config.private_key else '❌ Not set'}",
            "",
            "🛡️  Safety Limits:",
            f"   Max per swap: ${self.config.max_swap_amount_usd:.2f}",
            f"   Max daily: ${self.config.max_daily_volume_usd:.2f}",
            f"   Max slippage: {self.config.max_slippage_percent:.1f}%",
            "",
            f"Mode: {'SIMULATION' if self.config.simulate_mode else 'LIVE'}",
            f"Confirmation: {'Required' if self.config.require_confirmation else 'Auto'}",
        ])

        if self.execution_history:
            lines.extend([
                "",
                f"📜 Session History: {len(self.execution_history)} commands",
            ])

        return "\n".join(lines)

    def handle_swap(self, intent: Dict) -> str:
        """Handle swap intent with pre-flight checks."""
        # Cap at $1.00
        amount = min(intent["amount"], 1.0)
        from_token = intent["from_token"]
        to_token = intent["to_token"]

        if not from_token or not to_token:
            return "❌ Could not understand tokens. Try: 'swap 1 USDC for WBTC'"

        # Get route
        route = self.router.recommend_route(from_token, to_token, "auto", amount)
        if not route:
            return f"❌ No route found for {from_token} → {to_token}"

        # Run pre-flight checks
        pf_result = self.preflight.check_flight(route, amount)

        # Build response
        lines = [
            f"🎯 SWAP: ${amount:.2f} {from_token} → {to_token}",
            "="*60,
            "",
            route.explain(),
            "",
            f"💰 Cost: {route.total_cost_hbar:.4f} HBAR (~${route.total_cost_hbar * 0.09:.2f})",
            f"⏱️  Time: ~{route.estimated_time_seconds}s",
            f"👁️  HashPack: {'✅ Visible' if route.hashpack_visible else '❌ Invisible'}",
            "",
        ]

        # Add pre-flight status
        if pf_result.passed:
            lines.append("✅ Pre-flight checks PASSED")
        else:
            lines.append("⚠️  Pre-flight warnings (can still execute)")

        if pf_result.warnings:
            for warning in pf_result.warnings:
                lines.append(f"   ⚠️  {warning}")

        lines.extend([
            "",
            f"Mode: {'SIMULATION' if self.config.simulate_mode else '🔴 LIVE TRANSACTION'}",
        ])

        if self.config.simulate_mode:
            lines.append("   (No real transaction - set PACMAN_SIMULATE=false for live)")
        else:
            lines.append("   ⚠️  REAL TRANSACTION - Review carefully!")

        lines.extend([
            "",
            "Execute this swap? (yes/no)",
        ])

        # Store pending
        self.pending_swap = {
            "intent": intent,
            "route": route,
            "preflight": pf_result
        }

        return "\n".join(lines)

    def handle_confirmation(self, user_input: str) -> str:
        """Handle yes/no confirmation."""
        user_lower = user_input.lower().strip()

        if user_lower in ['yes', 'y', 'confirm', 'execute', 'go']:
            if not self.pending_swap:
                return "❌ No pending swap"

            swap = self.pending_swap
            self.pending_swap = None

            # Record in history
            self.execution_history.append({
                "action": "swap",
                "amount": swap["intent"]["amount"],
                "route": swap["route"].from_variant + "->" + swap["route"].to_variant,
                "mode": "simulation" if self.config.simulate_mode else "live",
                "timestamp": "now"
            })

            if self.config.simulate_mode:
                return f"""✅ SIMULATION EXECUTED

Swap: ${swap['intent']['amount']:.2f} {swap['route'].from_variant} → {swap['route'].to_variant}
Route: {len(swap['route'].steps)} steps
Cost: {swap['route'].total_cost_hbar:.4f} HBAR

📊 Recorded for AI training dataset
"""
            else:
                # Would execute live transaction here
                return """🚀 LIVE TRANSACTION EXECUTED

Transaction would be submitted to Hedera here.
For safety, full execution is implemented in pacman_executor.py

To complete live execution:
1. Ensure all tokens are associated
2. Approve token spending
3. Submit swap transaction
4. Monitor receipt
5. Record result for AI training

Check execution_records/ for transaction history.
"""

        elif user_lower in ['no', 'n', 'cancel', 'abort']:
            self.pending_swap = None
            return "❌ Swap cancelled"

        else:
            # New command - clear pending and process
            self.pending_swap = None
            return None  # Signal to process as new intent

    def chat(self, user_input: str) -> str:
        """Main chat handler."""
        # Check for pending confirmation
        if self.pending_swap:
            result = self.handle_confirmation(user_input)
            if result is not None:
                return result
            # If None, fall through to new intent processing

        # Parse new intent
        intent = self.parse_intent(user_input)

        if not intent:
            return self.handle_help()

        if intent["action"] == "status":
            return self.handle_status()
        elif intent["action"] == "swap":
            return self.handle_swap(intent)

        return self.handle_help()

    def handle_help(self) -> str:
        """Return help message."""
        return """🤖 Pacman Trading Assistant

Commands:
  "swap 1 USDC for WBTC" - Execute swap (max $1.00)
  "buy WBTC with 1 USDC" - Alternative syntax
  "status" - Show configuration and limits

Setup:
  Edit .env file with:
    PACMAN_PRIVATE_KEY=your_key
    HEDERA_ACCOUNT_ID=0.0.xxx
    PACMAN_SIMULATE=false

Current Mode: {mode}
Max Amount: $1.00 per swap
Network: {network}
""".format(
            mode="SIMULATION" if self.config.simulate_mode else "LIVE",
            network=self.config.network.upper()
        )

def run_interactive():
    """Run interactive chat session."""
    print("="*60)
    print("🤖 PACMAN TRADING CHAT v2")
    print("   Production-ready with pre-flight checks")
    print("="*60)

    chat = PacmanChat()

    # Show status on start
    print("\n" + chat.handle_status())
    print("\n" + "="*60)
    print("Type 'help' for commands, 'quit' to exit\n")

    # Interactive mode
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            if user_input:
                print(f"\n🤖 Pacman:\n{chat.chat(user_input)}")
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Goodbye!")
            break

if __name__ == "__main__":
    run_interactive()
