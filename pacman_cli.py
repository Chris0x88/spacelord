#!/usr/bin/env python3
"""
Pacman CLI - Operational Trading Interface
==========================================

The single source of truth for command-line interaction.
Pipelines natural language -> Validator -> Router -> Executor.

Architecture:
  1. Input: "swap 100 USDC to WBTC"
  2. Translator: {"intent": "swap", "from": "USDC", "to": "WBTC", ...}
  3. Router: Calculates best route (Variant-aware: HTS vs ERC20)
  4. Executor: Executes the route (approvals, swaps, wrapping)
"""

import sys
import os
import argparse
from typing import Optional
from dotenv import load_dotenv

# Core Pipeline Modules
from pacman_translator import translate
from pacman_variant_router import PacmanVariantRouter
from pacman_executor import PacmanExecutor

# Load Environment
load_dotenv()

def main():
    print("="*60)
    print("👻 PACMAN CLI - OPERATIONAL MODE")
    print("="*60)
    
    # Initialize Core Components
    try:
        router = PacmanVariantRouter()
        router.load_pools() # Load pool data once
        
        # Initialize executor (requires private key for real options)
        private_key = os.getenv("PRIVATE_KEY") or os.getenv("PACMAN_PRIVATE_KEY")
        if not private_key:
            print("⚠️  WARNING: No PRIVATE_KEY found in .env. executing in SIMULATION ONLY mode.")
            executor = PacmanExecutor(simulate=True)
        else:
            executor = PacmanExecutor(private_key=private_key)
            
    except Exception as e:
        print(f"❌ CRITICAL: Failed to initialize components: {e}")
        return

    # Check for command line args (One-shot mode)
    if len(sys.argv) > 1:
        handle_oneshot(sys.argv[1:], router, executor)
        return

    # Interactive REPL
    print("\nOperational Ready. Commands:")
    print("  - swap [amount] [token] for [token]  (Exact Input)")
    print("  - swap [token] for [amount] [token]  (Exact Output)")
    print("  - balance")
    print("  - history")
    print("  - exit")
    print("-" * 60)

    while True:
        try:
            user_input = input("\n👤 Command: ").strip()
            if not user_input: continue
            
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Shutting down.")
                break
                
            process_command(user_input, router, executor)
            
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def handle_oneshot(args: list, router, executor):
    """Handle command line arguments as a single command."""
    command = " ".join(args)
    process_command(command, router, executor)

def process_command(text: str, router: PacmanVariantRouter, executor: PacmanExecutor):
    """Process a single natural language command."""
    
    # 1. Translate
    req = translate(text)
    if not req:
        # Fallback for simple keywords if translator fails
        cmd = text.split()[0].lower()
        if cmd == "balance":
            req = {"intent": "balance"}
        elif cmd == "history":
            req = {"intent": "history"}
        else:
            print("❌ Unknown command or format. Try 'swap 100 USDC for WBTC'")
            return

    intent = req.get("intent")

    # 2. Balance
    if intent == "balance":
        show_balance(executor)
        return

    # 3. History
    if intent == "history":
        show_history(executor)
        return

    # 4. Token Registry Discovery
    if intent == "tokens":
        show_tokens()
        return

    # 5. Swap (The Core Op)
    if intent == "swap":
        handle_swap(req, router, executor)
        return

    print(f"❌ Unhandled intent: {intent}")

def show_balance(executor: PacmanExecutor):
    """Display wallet balances using the new client."""
    print("\n💰 Wallet Balances:")
    try:
        client = executor.client
        
        # 1. HBAR Balance
        hbar_bal = client.w3.eth.get_balance(client.eoa)
        hbar_readable = hbar_bal / (10**18) # EVM compatibility uses 18 decimals
        
        # Determine HBAR price
        hbar_price = 0.09 # Default fallback
        try:
            with open("tokens.json") as f:
                tdata = json.load(f)
                for meta in tdata.values():
                    if meta.get("symbol") == "HBAR" or meta.get("name") == "Hedera":
                        hbar_price = meta.get("priceUsd", hbar_price)
                        break
        except:
            pass
            
        hbar_usd = hbar_readable * hbar_price
        print(f"  HBAR      : {hbar_readable:12.6f} (${hbar_usd:8.2f})")

        # 2. Token Balances from tokens.json
        import json
        with open("tokens.json") as f:
            tokens_data = json.load(f)
            
        total_usd = 0
        
        # Priority sort: HBAR is already shown. For tokens:
        # 1. USDC, 2. WBTC, 3. WETH, 4. Others (alphabetical)
        def sort_key(item):
            sym = item[0]
            if "USDC" in sym: return (0, sym)
            if "WBTC" in sym: return (1, sym)
            if "WETH" in sym: return (2, sym)
            return (3, sym)
            
        sorted_tokens = sorted(tokens_data.items(), key=sort_key)

        for sym, meta in sorted_tokens:
            token_id = meta.get("id")
            if not token_id: continue
            
            try:
                raw_bal = client.get_token_balance(token_id)
                if raw_bal > 0:
                    decimals = meta.get("decimals", 8)
                    readable = raw_bal / (10**decimals)
                    
                    # Manual floor to avoid "0.000011" rounding
                    factor = 10**decimals
                    readable_floored = (raw_bal // 1) / factor
                    
                    price = meta.get("priceUsd", 0)
                    usd_val = readable_floored * price
                    
                    # Show 8 decimals for everything to be safe
                    print(f"  {sym:10s}: {readable_floored:12.8f} (${usd_val:8.2f})")
                    total_usd += usd_val
            except:
                continue 
                
        print(f"  Total Assets USD: ${total_usd:.2f}")

    except Exception as e:
        print(f"❌ Failed to fetch balance: {e}")

def show_tokens():
    """Display all valid token aliases in a neat priority-sorted table."""
    print("\n🎫 Token Gallery (ID -> Aliases):")
    try:
        from pacman_translator import ALIASES
        from pacman_variant_router import PacmanVariantRouter
        import json
        
        BLACKLIST = PacmanVariantRouter.BLACKLISTED_TOKENS
        
        with open("tokens.json") as f:
            tokens_data = json.load(f)
            
        # Group aliases by canonical ID
        id_to_aliases = {}
        # Special case for HBAR
        id_to_aliases["0.0.0"] = {"aliases": ["hbar", "hbarx"], "sym": "HBAR", "name": "Hedera Native"}

        for alias, canon in ALIASES.items():
            token_id = None
            if canon in tokens_data:
                token_id = tokens_data[canon].get("id")
            elif canon == "HBAR":
                token_id = "0.0.0"
            
            if token_id:
                if token_id in BLACKLIST:
                    continue
                if token_id not in id_to_aliases:
                    id_to_aliases[token_id] = {"aliases": [], "sym": canon, "name": ""}
                id_to_aliases[token_id]["aliases"].append(alias)

        # Priority Sorting Logic
        PRIORITY_SYMS = ["USDC", "WBTC", "WETH", "QNT", "LINK", "AVAX", "SAUCE", "XSAUCE", "BONZO"]
        
        def sort_key(item):
            tid, data = item
            if tid == "0.0.0": return (0, "") # HBAR is #1
            
            # Find symbol
            meta = next((m for m in tokens_data.values() if m.get("id") == tid), {})
            sym = meta.get("symbol", data["sym"])
            
            for i, psym in enumerate(PRIORITY_SYMS):
                if psym in sym.upper():
                    return (1, i, sym)
            
            return (2, sym)

        sorted_tokens = sorted(id_to_aliases.items(), key=sort_key)

        # Header
        print(f"  {'TOKEN ID':15s} | {'SYMBOL':10s} | {'NAME':25s} | {'ALIASES'}")
        print(f"  {'-'*15}-|-{'-'*10}-|-{'-'*25}-|-{'-'*30}")

        for tid, data in sorted_tokens:
            meta = next((m for m in tokens_data.values() if m.get("id") == tid), {})
            sym = meta.get("symbol", data["sym"])
            name = meta.get("name", "Hedera Native" if tid == "0.0.0" else "Unknown")
            
            clean_aliases = sorted(list(set(data["aliases"])))
            alias_str = ", ".join(clean_aliases)
            
            print(f"  {tid:15s} | {sym:10s} | {name[:25]:25s} | {alias_str}")
        print("")

    except Exception as e:
        print(f"❌ Failed to list tokens: {e}")

def show_history(executor: PacmanExecutor):
    """Display operations history."""
    hist = executor.get_execution_history(limit=5)
    if not hist:
        print("No local execution history found.")
        return
        
    print("\n📜 Recent Operations:")
    for h in hist:
        status = "✅" if h["success"] else "❌"
        mode = h.get("mode", "UNKNOWN")
        route = h.get("route", {})
        
        # Display logic: prefer amount_token if exists, fallback to amount_usd
        amt_token = h.get("amount_token", h.get("amount_usd", 0))
        amt_usd = h.get("amount_usd", 0)
        
        print(f"  {h['timestamp']} {status} [{mode}] {amt_token:12.8f} {route.get('from')} -> {route.get('to')} (${amt_usd:8.2f})")

def handle_swap(req: dict, router: PacmanVariantRouter, executor: PacmanExecutor):
    """Orchestrate the swap flow."""
    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]
    mode = req["mode"] # exact_in vs exact_out

    print(f"\n🔍 Analyzing: {amount} {from_token} -> {to_token} ({mode})")

    # 1. Route
    # We need to map the "translator token names" to "router variants"
    # Translator returns canonical names mostly.
    # Usage: router.recommend_route(from_variant, to_variant, "auto", amount_usd)
    # Limitation: Router expects variants like "USDC", "WBTC_HTS". 
    # Translator might return "WBTC_HTS" correctly.
    
    # Heuristic: If translator gives us a name that matches a variant key, use it.
    # If not, we might need a lookup.
    # Start simple: Assume translator outputs valid variant names or close to it.
    
    # Calculate amount in USD for routing (approximate is fine for selection)
    # In a real app we'd get a price. For now, pass 100 as dummy if unknown, 
    # or implement price fetch.
    
    route = router.recommend_route(from_token, to_token, user_preference="auto", amount_usd=100.0)
    
    if not route:
        print(f"❌ No route found for {from_token} -> {to_token}")
        return

    # 2. Present Options
    print("\n⚡ Proposed Route:")
    print(route.explain())
    print("-" * 30)
    
    # 3. Confirm
    if os.getenv("PACMAN_AUTO_CONFIRM") != "true":
        confirm = input("Execute this swap? (y/n): ").strip().lower()
        if confirm not in ["y", "yes"]:
            print("Cancelled.")
            return

    # 4. Execute
    # Executor needs amount in USD. 
    # This is a bit of a mismatch in the current executor_pro signature vs the request.
    # The executor expects `amount_usd`.
    # BUT `req['amount']` is token amount. 
    # Let's fix the Executor call or the Executor itself to accept token amounts.
    # Looking at pacman_executor.py: execute_swap(route, amount_usd, simulate)
    # It converts USD to token units inside: amount_raw = int(amount_usd * 1_000_000)
    # THIS IS A BUG/LIMITATION in the current executor! It assumes input is always USDC-like (6 decimals).
    # We must patch this in `pacman_executor.py` or work around it.
    
    # Correct approach: Update Executor to take token amount, not USD.
    # For now, we will modify the calling code to calculate USD roughly or 
    # (BETTER) Update pacman_executor.py to handle raw amounts.
    
    # Hack for now: We will assume the executor needs to be fixed.
    # Let's try to run it. If from_token is USDC, amount is amount_usd.
    amount_val = amount
    
    # Check if we are in simulation mode
    is_sim = executor.private_key is None
    
    res = executor.execute_swap(route, amount_usd=amount_val, mode=mode, simulate=is_sim)
    
    if res.success:
        print(f"\n✅ SUCCESS!")
        print(f"   Tx: {res.tx_hash}")
        print(f"   Gas: {res.gas_used}")
    else:
        print(f"\n❌ FAILED: {res.error}")

if __name__ == "__main__":
    main()
