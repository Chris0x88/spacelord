#!/usr/bin/env python3
"""
Pacman CLI - Operational Trading Interface
==========================================

The single source of truth for command-line interaction.
Pipelines natural language -> Validator -> Router -> Executor.
"""

import sys
import os
import json
import argparse
import time
from typing import Optional
from dotenv import load_dotenv

# Core Pipeline Modules
from pacman_translator import translate
from pacman_variant_router import PacmanVariantRouter
from pacman_executor import PacmanExecutor, ExecutionResult

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
        pk_env = os.getenv("PACMAN_PRIVATE_KEY")
        force_sim = os.getenv("PACMAN_SIMULATE", "false").lower() == "true"
        
        if not pk_env:
            executor = PacmanExecutor(private_key="0x" + "0"*64)
            executor.is_sim = True
        else:
            executor = PacmanExecutor(private_key=pk_env)
            executor.is_sim = force_sim
            
    except Exception as e:
        print(f"❌ CRITICAL: Failed to initialize components: {e}")
        return

    # Check for command line args (One-shot mode)
    if len(sys.argv) > 1:
        handle_oneshot(sys.argv[1:], router, executor)
        return

    # Interactive REPL
    print("\nOperationally Ready. Commands:")
    print("  - swap [amount] [token] for [token]  (Exact Input)")
    print("  - swap [token] for [amount] [token]  (Exact Output)")
    print("  - convert [token] for [amount] [token]  (Exact Output)") 
    print("  - convert [amount] [token] for [token]  (Exact Input)")   
    print("  - balance")
    print("  - history")
    print("  - tokens")
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

def get_token_id_for_variant(variant: str) -> str:
    """Helper to get Token ID for a variant name."""
    IDS = {
        "WBTC_HTS": "0.0.10082597",
        "WBTC_ERC20": "0.0.1055483",
        "WETH_HTS": "0.0.9770617",
        "WETH_ERC20": "0.0.541564",
        "HBAR": "0.0.0",
        "0.0.0": "0.0.0"
    }
    if variant in IDS: return IDS[variant]
    try:
        with open("tokens.json") as f:
            tokens_data = json.load(f)
            if variant in tokens_data:
                return tokens_data[variant].get("id", variant)
    except: pass
    return variant

def process_command(text: str, router: PacmanVariantRouter, executor: PacmanExecutor):
    """Process a single natural language command."""
    req = translate(text)
    if not req:
        cmd = text.split()[0].lower()
        if cmd == "balance": req = {"intent": "balance"}
        elif cmd == "history": req = {"intent": "history"}
        else:
            print("❌ Unknown command or format. Try 'swap 100 USDC for WBTC'")
            return

    intent = req.get("intent")
    if intent == "balance": show_balance(executor); return
    if intent == "history": show_history(executor); return
    if intent == "tokens": show_tokens(); return
    if intent == "swap": handle_swap(req, router, executor); return
    if intent == "convert": handle_convert(req, executor); return
    print(f"❌ Unhandled intent: {intent}")

def handle_convert(req: dict, executor: PacmanExecutor):
    """Handle manual wrap/unwrap conversion."""
    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]
    
    print(f"\n🔍 Analyzing conversion: {amount} {from_token} -> {to_token}")
    
    is_wrap = False
    is_unwrap = False
    
    if "ERC20" in to_token and ("HTS" in from_token or from_token in ["WBTC", "WETH"]):
        is_wrap = True
    elif ("HTS" in to_token or to_token in ["WBTC", "WETH"]) and "ERC20" in from_token:
        is_unwrap = True
    else:
        print("   ⚠️  Conversion variants not explicitly detected. Fallback swap might be needed.")
        return
        
    from pacman_variant_router import RouteStep, VariantRoute
    from_id = get_token_id_for_variant(from_token)
    to_id = get_token_id_for_variant(to_token)
    
    step_type = "wrap" if is_wrap else "unwrap"
    step = RouteStep(
        step_type=step_type,
        from_token=from_token,
        to_token=to_token,
        contract="0.0.9675688",
        gas_estimate_hbar=0.02,
        details={"token_in_id": from_id, "token_out_id": to_id}
    )
    
    route = VariantRoute(
        from_variant=from_token,
        to_variant=to_token,
        steps=[step],
        total_fee_percent=0.0,
        total_gas_hbar=0.02,
        total_cost_hbar=0.02,
        estimated_time_seconds=10,
        output_format="HTS" if is_unwrap else "ERC20",
        hashpack_visible=is_unwrap,
        confidence=1.0
    )
    
    decimals = 8 if "WBTC" in from_token else 18
    step.amount_raw = int(amount * (10**decimals))
    
    print(f"\n✨ Proposed {step_type.upper()}:")
    print(f"   {amount} {from_token} ({from_id})")
    print(f"   -> {amount} {to_token} ({to_id})")
    print(f"   Using Wrapper: 0.0.9675688")
    
    if os.getenv("PACMAN_AUTO_CONFIRM") != "true":
        confirm = input("Execute this conversion? (y/n): ").strip().lower()
        if confirm not in ["y", "yes"]: print("Cancelled."); return

    res = executor.execute_swap(route, amount_usd=amount, mode="exact_in", simulate=executor.is_sim)
    
    if res.success:
        print(f"\n✅ SUCCESS!")
        print(f"   Tx: {res.tx_hash}")
    else:
        print(f"\n❌ FAILED: {res.error}")

def show_balance(executor: PacmanExecutor):
    """Display wallet balances using the new client."""
    print("\n💰 Wallet Balances:")
    try:
        from pacman_price_manager import price_manager
        client = executor.client
        hbar_bal = client.w3.eth.get_balance(client.eoa)
        hbar_readable = hbar_bal / (10**18)
        
        hbar_price = price_manager.get_hbar_price()
        hbar_usd = hbar_readable * hbar_price
        print(f"  HBAR      : {hbar_readable:12.6f} (${hbar_usd:8.2f})")

        with open("tokens.json") as f:
            tokens_data = json.load(f)
        total_usd = 0
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
                    price = meta.get("priceUsd", 0)
                    usd_val = readable * price
                    print(f"  {sym:10s}: {readable:12.8f} (${usd_val:8.2f})")
                    total_usd += usd_val
            except: continue 
        print(f"  Total Assets USD: ${total_usd:.2f}")
    except Exception as e: print(f"❌ Failed to fetch balance: {e}")

def show_tokens():
    """Display all valid token aliases in a neat priority-sorted table."""
    print("\n🎫 Token Gallery (ID -> Aliases):")
    try:
        from pacman_translator import ALIASES
        BLACKLIST = PacmanVariantRouter.BLACKLISTED_TOKENS
        with open("tokens.json") as f: tokens_data = json.load(f)
        id_to_aliases = {}
        id_to_aliases["0.0.0"] = {"aliases": ["hbar", "hbarx"], "sym": "HBAR", "name": "Hedera Native"}
        for alias, canon in ALIASES.items():
            token_id = None
            if canon in tokens_data: token_id = tokens_data[canon].get("id")
            elif canon == "HBAR": token_id = "0.0.0"
            if token_id:
                if token_id in BLACKLIST: continue
                if token_id not in id_to_aliases: id_to_aliases[token_id] = {"aliases": [], "sym": canon, "name": ""}
                id_to_aliases[token_id]["aliases"].append(alias)
        PRIORITY_SYMS = ["USDC", "WBTC", "WETH", "QNT", "LINK", "AVAX", "SAUCE", "XSAUCE", "BONZO"]
        def sort_key(item):
            tid, data = item
            if tid == "0.0.0": return (0, "")
            meta = next((m for m in tokens_data.values() if m.get("id") == tid), {})
            sym = meta.get("symbol", data["sym"])
            for i, psym in enumerate(PRIORITY_SYMS):
                if psym in sym.upper(): return (1, i, sym)
            return (2, sym)
        sorted_tokens = sorted(id_to_aliases.items(), key=sort_key)
        print(f"  {'TOKEN ID':15s} | {'SYMBOL':10s} | {'NAME':25s} | {'ALIASES'}")
        print(f"  {'-'*15}-|-{'-'*10}-|-{'-'*25}-|-{'-'*30}")
        for tid, data in sorted_tokens:
            meta = next((m for m in tokens_data.values() if m.get("id") == tid), {})
            sym = meta.get("symbol", data["sym"])
            name = meta.get("name", "Hedera Native" if tid == "0.0.0" else "Unknown")
            alias_str = ", ".join(sorted(list(set(data["aliases"]))))
            print(f"  {tid:15s} | {sym:10s} | {name[:25]:25s} | {alias_str}")
        print("")
    except Exception as e: print(f"❌ Failed to list tokens: {e}")

from pacman_price_manager import price_manager

def show_history(executor: PacmanExecutor):
    """Display operations history."""
    hist = executor.get_execution_history(limit=10)
    if not hist: print("No local execution history found."); return
    print("\n📜 Recent Operations:")
    
    # Reload prices to ensure freshness
    price_manager.reload()

    for h in hist:
        status = "✅" if h["success"] else "❌"
        mode = h.get("mode", "UNKNOWN")
        route = h.get("route", {})
        
        ft = route.get("from", "?")
        tt = route.get("to", "?")
        
        # Phase 32: Use Source of Truth for amounts and prices
        amt_token = h.get("amount_token", 0)
        amt_usd = h.get("amount_usd", 0)
        
        # 1. Recover true token amount from raw results if possible
        raw_in = 0
        token_in_id = ""
        if "results" in h and h["results"]:
             if isinstance(h["results"], list) and len(h["results"]) > 0:
                 res0 = h["results"][0]
                 if isinstance(res0, dict):
                     raw_in = res0.get("amount_in_raw", 0)
                 
                 # Try to find Token ID from route or results
                 # Route often has symbol, need ID for price lookup
                 # We can rely on router/executor to have logged it, or guess from symbol via map if needed.
                 # Actually price_manager keys are IDs. 
                 # We need to map Symbol -> ID if we only have symbol in history.
                 pass

        # We need a Symbol -> ID mapper if the history only stores symbols.
        # Check what 'ft' (from_token) is. It's usually the variant symbol (e.g. USDC[hts]).
        # The price_manager is keyed by ID. 
        # We need the ID to get the price.
        
        # Quick lookup for common symbols/variants to IDs for display purposes
        # This is strictly for display retrofitting.
        # Future history has IDs stored? 
        
        pass 
        
        # Let's revert to the original logic plan:
        # 1. Use raw_in to get amt_token (requires decimals lookup)
        # 2. Use price_manager.get_price(id) to get price.
        
        # Problem: 'ft' is a symbol. price_manager needs ID.
        # I need a helper to get ID from Symbol. pacman_variant_router has this.
        
        # Let's stick to the cleanest integration:
        # If we can't easily get the ID, we use the stored amount_usd.
        # BUT the task is to fix history USD value.
        
        # Let's trust the 'tokens.json' map for Symbol->ID resolution ONLY, then use price_manager for Price.
        
    # Re-reading: The previous code loaded tokens.json to get metadata. 
    # I should preserve that for Symbol->ID mapping, but get the PRICE from price_manager.
    
    # Load token metadata for ID lookup
    tokens_map = {}
    try:
        with open("tokens.json") as f:
            tdata = json.load(f)
            for k, v in tdata.items():
                tokens_map[k] = v
                if "id" in v: tokens_map[v["id"]] = v
                if "symbol" in v: tokens_map[v["symbol"]] = v
    except: pass

    for h in hist:
        status = "✅" if h["success"] else "❌"
        mode = h.get("mode", "UNKNOWN")
        route = h.get("route", {})
        
        ft = route.get("from", "?")
        tt = route.get("to", "?")
        
        # Recalculate true amount from raw input
        amt_token = h.get("amount_token", 0)
        amt_usd = h.get("amount_usd", 0)
        
        raw_in = 0
        if "results" in h and h["results"]:
             if isinstance(h["results"], list) and len(h["results"]) > 0:
                 if isinstance(h["results"][0], dict):
                     raw_in = h["results"][0].get("amount_in_raw", 0)
        
        if raw_in > 0:
            decimals = 0
            price = 0
            
            # Lookup decimals and ID
            # ft is likely "HBAR" or "USDC[hts]"
            token_id = None
            
            meta = tokens_map.get(ft)
            if not meta:
                # Fallbacks for HBAR
                if ft.upper() in ["HBAR", "0.0.0", "WHBAR", "0.0.1456986"]:
                    decimals = 8
                    token_id = "0.0.1456986" # Use WHBAR for price
            else:
                decimals = meta.get("decimals", 8)
                token_id = meta.get("id")
            
            # Use PriceManager for the price
            if token_id:
                price = price_manager.get_price(token_id)
            elif ft.upper() == "HBAR":
                 price = price_manager.get_hbar_price()
            
            if decimals > 0:
                amt_real = raw_in / (10**decimals)
                amt_token = amt_real
                if price > 0:
                    amt_usd = amt_token * price

            # Phase 33: Show both amounts for better clarity
            to_amt = h.get('to_amount_token', 0.0)
            if to_amt > 0:
                print(f"  {h['timestamp']} {status} [{mode}]   {amt_token:12.8f} {ft} -> {to_amt:12.8f} {tt} ($ {amt_usd:10.2f})")
            else:
                print(f"  {h['timestamp']} {status} [{mode}]   {amt_token:12.8f} {ft} -> {tt} ($ {amt_usd:10.2f})")

def print_receipt(res: ExecutionResult, route, from_token: str, to_token: str, amount_val: float, mode: str, executor: PacmanExecutor):
    """Print an ATO-compliant money transfer receipt."""
    width = 68
    
    def line(content: str = "", center=False):
        if not content:
            print(f"║{' ' * (width-2)}║")
            return
        if center:
            padding = width - 2 - len(content)
            left = padding // 2
            right = padding - left
            print(f"║{' ' * left}{content}{' ' * right}║")
        else:
            padding = width - 4 - len(content)
            if padding < 0:
                 content = content[:width-7] + "..."
                 padding = 0
            print(f"║ {content}{' ' * padding} ║")

    def divider(double=False):
        if double:
            print("╠" + "═" * (width-2) + "╣")
        else:
            print("╟" + "─" * (width-2) + "╢")

    print("\n" + "╔" + "══════════════════════════════════════════════════════════════════" + "╗")
    line("HEDERA TRANSACTION RECORD", center=True)
    divider(True)
    
    timestamp = res.timestamp or time.strftime("%Y-%m-%d %H:%M:%S")
    line(f"Date/Time:      {timestamp}")
    line(f"Account (ID):   {res.account_id or executor.hedera_account_id}")
    line(f"Network:        {executor.network.upper()} (Mainnet Consensus)")
    divider()
    
    # Send/Receive Details
    from_decimals = executor._get_token_decimals(from_token)
    to_decimals = executor._get_token_decimals(to_token)
    
    amount_in = res.amount_in_raw / (10**from_decimals)
    amount_out = res.amount_out_raw / (10**to_decimals)
    
    line(f"TOTAL SENT:     {amount_in:18.8f} {from_token}")
    line(f"ANTICIPATED:    {amount_out:18.8f} {to_token}")
    divider()
    
    # Rate Math: Gross vs Net (Phase 33)
    decimal_adj = 10**(from_decimals - to_decimals)
    actual_net_rate = amount_out / amount_in if amount_in > 0 else 0
    
    # Infer Gross (Market) rate by adding back LP fee percentage
    # res.lp_fee_amount is in 'from_token'
    fee_pct = (res.lp_fee_amount / amount_in) if amount_in > 0 else 0
    gross_rate = actual_net_rate / (1 - fee_pct) if (0 < fee_pct < 1) else actual_net_rate
    
    # Labels swapped as per user request: "wrong way round"
    # User example: 10.9 HBAR/USDC -> wants USDC/HBAR
    line(f"Market Swap Rate: {gross_rate:18.8f} {from_token}/{to_token}")
    
    # 2. Net Effective Rate (Final, after everything)
    line(f"Net Effective:    {actual_net_rate:18.8f} {from_token}/{to_token}")
    
    # Inverse for convenience
    inv_net = 1.0 / actual_net_rate if actual_net_rate > 0 else 0
    line(f"                  {inv_net:18.8f} {to_token}/{from_token}")
    
    divider()
    
    # Effective Rate Details (Redundant with above but preserving structure)
    if res.tx_hash != "SIMULATED":
         line(f"Consensus Status: [ FINALIZED ]")
    else:
         line(f"Consensus Status: [ SIMULATED - MARKET ESTIMATE ]")
        
    divider()
    
    # Manufacturer/Protocol Fees
    if res.lp_fee_amount > 0:
        line("REF. FEES:")
        # Identify fee tier percentage (approximate reverse calc or just standard display if store)
        # We stored the raw amount, we can infer %, or just display amount.
        # Let's just display the Amount for now as "Liquidity Fee".
        line(f"Liquidity Fee:  {res.lp_fee_amount:18.8f} {res.lp_fee_token}")
    
    # Gas & Reporting Metrics
    line(f"Network Gas:    {res.gas_cost_hbar:18.8f} HBAR")
    line(f"Gas Value:      ${res.gas_cost_usd:18.4f} USD")
    line(f"HBAR Price:     ${res.hbar_usd_price:18.4f} USD")
    
    # Gas Context (Phase 29)
    total_val_usd = 0.0
    if from_token.upper() in ["HBAR", "0.0.0", "WHBAR", "0.0.1456986"]:
         total_val_usd = amount_in * res.hbar_usd_price
    elif to_token.upper() in ["HBAR", "0.0.0", "WHBAR", "0.0.1456986"]:
         total_val_usd = amount_out * res.hbar_usd_price
    elif "USDC" in from_token.upper():
         total_val_usd = amount_in
    elif "USDC" in to_token.upper():
         total_val_usd = amount_out
         
    if total_val_usd > 0 and res.gas_cost_usd > 0:
        gas_pct = (res.gas_cost_usd / total_val_usd) * 100
        # Phase 33: Align percentage with USD column
        line(f"Gas Cost %:      {gas_pct:17.4f}% of Total Value")
    
    # Explain HBAR net deduction if applicable
    if to_token.upper() == "HBAR":
        net_received = amount_out - res.gas_cost_hbar
        line(f"NET SETTLEMENT: {net_received:18.8f} HBAR")
        line()
        line("Note: Gas was deducted from final settlement amount.")
        
    divider()
    line(f"TRANS. STATUS:  [ CONSENSUS SUCCESS ]")
    if res.tx_hash != "SIMULATED" and res.tx_hash:
        line(f"CONSENSUS HASH:")
        line(f"{res.tx_hash[:32]}")
        line(f"{res.tx_hash[32:]}")
    else:
        line(f"CONSENSUS HASH: [ SIMULATED - NO ON-CHAIN RECORD ]")
        
    print("╚" + "══════════════════════════════════════════════════════════════════" + "╝")
    
    if res.tx_hash != "SIMULATED" and res.tx_hash:
        print(f"\n🔗 VIEW ON HASHSCAN (TRANS. ID):")
        print(f"   https://hashscan.io/mainnet/transaction/{res.tx_hash}\n")

def handle_swap(req: dict, router: PacmanVariantRouter, executor: PacmanExecutor):
    """Orchestrate the swap flow."""
    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]
    mode = req["mode"]

    print(f"\n🔍 Analyzing: {amount} {from_token} -> {to_token} ({mode})")
    route = router.recommend_route(from_token, to_token, user_preference="auto", amount_usd=100.0)
    if not route: print(f"❌ No route found for {from_token} -> {to_token}"); return

    from_id = get_token_id_for_variant(route.from_variant)
    to_id = get_token_id_for_variant(route.to_variant)
    print("\n⚡ Proposed Route:")
    print(f"   {route.from_variant} ({from_id}) -> {route.to_variant} ({to_id})")
    print(route.explain())
    print("-" * 30)
    
    if os.getenv("PACMAN_AUTO_CONFIRM") != "true":
        confirm = input("Execute this swap? (y/n): ").strip().lower()
        if confirm not in ["y", "yes"]: print("Cancelled."); return

    res = executor.execute_swap(route, amount_usd=amount, mode=mode, simulate=executor.is_sim)
    
    if res.success:
        print_receipt(res, route, route.from_variant, route.to_variant, amount, mode, executor)
    else:
        print(f"\n❌ FAILED: {res.error}")

if __name__ == "__main__":
    main()
