#!/usr/bin/env python3
"""
Pacman CLI - Operational Trading Interface
==========================================

The single entry point for the Pacman terminal.
Pipelines: Natural Language -> Translator -> Router -> Executor.
"""

import sys
import os
import json

# Load environment early (fast, no heavy deps)
from dotenv import load_dotenv
load_dotenv()


# ---------------------------------------------------------------------------
# Token ID Helper (no heavy deps needed)
# ---------------------------------------------------------------------------

def get_token_id_for_variant(variant: str) -> str:
    """Resolve a variant name to its Hedera Token ID."""
    IDS = {
        "WBTC_HTS": "0.0.10082597",
        "WBTC_ERC20": "0.0.1055483",
        "WETH_HTS": "0.0.9770617",
        "WETH_ERC20": "0.0.541564",
        "HBAR": "0.0.0",
        "0.0.0": "0.0.0"
    }
    if variant in IDS:
        return IDS[variant]
    try:
        with open("data/tokens.json") as f:
            tokens_data = json.load(f)
            if variant in tokens_data:
                return tokens_data[variant].get("id", variant)
    except:
        pass
    return variant


# ---------------------------------------------------------------------------
# Engine Initialization (Lazy — only runs when needed)
# ---------------------------------------------------------------------------

def init_executor():
    """Initialize the executor instantly."""
    from pacman_display import C
    from pacman_executor import PacmanExecutor
    from pacman_logger import logger

    print(f"\n  {C.BOLD}{C.ACCENT}Initializing Engine...{C.R}", end="", flush=True)

    # Imports (Lazy but fast)
    from web3 import Web3
    from saucerswap_v2_client import SaucerSwapV2
    from pacman_price_manager import price_manager

    pk_env = os.getenv("PACMAN_PRIVATE_KEY")
    force_sim = os.getenv("PACMAN_SIMULATE", "false").lower() == "true"

    if not pk_env:
        logger.warning("No private key found. Simulation mode.")
        executor = PacmanExecutor(private_key="0x" + "0" * 64)
        executor.is_sim = True
    else:
        executor = PacmanExecutor(private_key=pk_env)
        executor.is_sim = force_sim

    executor.price_manager = price_manager

    print(f" {C.OK}DONE{C.R}")
    return executor


# ---------------------------------------------------------------------------
# Command Processing
# ---------------------------------------------------------------------------

def process_command(text: str, router, executor):
    """Parse and execute a single command."""
    from pacman_translator import translate
    from pacman_display import (
        show_help, show_balance, show_tokens, show_history,
        show_account, show_price, show_sources, C
    )

    parts = text.strip().split()
    if not parts:
        return

    cmd = parts[0].lower()

    # --- Instant commands (no executor needed) ---
    if cmd in ["help", "--help", "-h", "?"]:
        show_help()
        return

    if cmd == "tokens":
        show_tokens()
        return

    if cmd == "sources":
        show_sources()
        return

    # --- Price check (no executor needed) ---
    if cmd == "price":
        if len(parts) >= 2:
            from pacman_translator import resolve_token
            target = resolve_token(parts[1]) or parts[1]
            show_price(target)
        else:
            from pacman_display import show_all_prices
            show_all_prices()
        return

    # --- Commands that need executor ---
    if executor is None:
        print(f"  {C.ERR}✗{C.R} Engine not initialized. Run a command like 'balance' first.")
        return

    if cmd == "account":
        show_account(executor)
        return

    if cmd == "balance":
        if len(parts) >= 2:
            show_balance(executor, single_token=parts[1])
        else:
            show_balance(executor)
        return

    if cmd == "history":
        show_history(executor)
        return

    if cmd == "send":
        handle_send(text, executor)
        return

    # --- Swap / Convert (translator-driven) ---
    req = translate(text)
    if not req:
        print(f"  {C.ERR}✗{C.R} Unknown command. Type {C.TEXT}help{C.R} for options.")
        return

    intent = req.get("intent")
    if intent == "swap":
        handle_swap(req, router, executor)
    elif intent == "convert":
        handle_convert(req, router, executor)
    elif intent == "balance":
        show_balance(executor)
    elif intent == "help":
        show_help()
    elif intent == "tokens":
        show_tokens()
    elif intent == "history":
        show_history(executor)
    else:
        print(f"  {C.ERR}✗{C.R} Unhandled intent: {intent}")


# ---------------------------------------------------------------------------
# Swap Handler
# ---------------------------------------------------------------------------

def handle_swap(req: dict, router, executor):
    """Execute a token swap."""
    from pacman_display import print_receipt, C

    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]
    mode = req["mode"]

    print(f"\n  {C.ACCENT}⟳{C.R} Analyzing: {C.TEXT}{amount}{C.R} {from_token} → {to_token} ({mode})")

    route = router.recommend_route(from_token, to_token, user_preference="auto", amount_usd=100.0)
    if not route:
        print(f"  {C.ERR}✗{C.R} No route found for {from_token} → {to_token}")
        return

    from_id = get_token_id_for_variant(route.from_variant)
    to_id = get_token_id_for_variant(route.to_variant)

    print(f"\n  {C.BOLD}Proposed Route:{C.R}")
    print(f"  {C.TEXT}{route.from_variant}{C.R} {C.MUTED}({from_id}){C.R} → {C.TEXT}{route.to_variant}{C.R} {C.MUTED}({to_id}){C.R}")
    print(route.explain())

    if os.getenv("PACMAN_AUTO_CONFIRM") != "true":
        confirm = input(f"\n  Execute swap? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    res = executor.execute_swap(route, amount_usd=amount, mode=mode, simulate=executor.is_sim)

    if res.success:
        print_receipt(res, route, route.from_variant, route.to_variant, amount, mode, executor)
    else:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {res.error}")


# ---------------------------------------------------------------------------
# Convert Handler (Wrap/Unwrap)
# ---------------------------------------------------------------------------

def handle_convert(req: dict, router, executor):
    """Handle wrap/unwrap conversion requests."""
    from pacman_variant_router import RouteStep, VariantRoute
    from pacman_display import C
    from pacman_logger import logger

    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]

    is_wrap = ("ERC20" in to_token or "LZ" in to_token)
    is_unwrap = ("HTS" in to_token and ("ERC20" in from_token or "LZ" in from_token))

    if not is_wrap and not is_unwrap:
        if "ERC20" in to_token and ("HTS" in from_token or from_token in ["WBTC", "WETH"]):
            is_wrap = True
        elif ("HTS" in to_token or to_token in ["WBTC", "WETH"]) and "ERC20" in from_token:
            is_unwrap = True

    if not is_wrap and not is_unwrap:
        print(f"  {C.WARN}⚠{C.R}  Cannot determine conversion type.")
        return

    from_id = get_token_id_for_variant(from_token)
    to_id = get_token_id_for_variant(to_token)
    step_type = "wrap" if is_wrap else "unwrap"

    step = RouteStep(
        step_type=step_type, from_token=from_token, to_token=to_token,
        contract="0.0.9675688", gas_estimate_hbar=0.02,
        details={"token_in_id": from_id, "token_out_id": to_id}
    )
    route = VariantRoute(
        from_variant=from_token, to_variant=to_token, steps=[step],
        total_fee_percent=0.0, total_gas_hbar=0.02, total_cost_hbar=0.02,
        estimated_time_seconds=10, output_format="HTS" if is_unwrap else "ERC20",
        hashpack_visible=is_unwrap, confidence=1.0
    )

    decimals = 8 if "WBTC" in from_token else 18
    step.amount_raw = int(amount * (10**decimals))

    print(f"\n  {C.BOLD}{step_type.upper()}{C.R}")
    print(f"  {C.TEXT}{amount}{C.R} {from_token} {C.MUTED}({from_id}){C.R}")
    print(f"  → {C.TEXT}{amount}{C.R} {to_token} {C.MUTED}({to_id}){C.R}")

    if os.getenv("PACMAN_AUTO_CONFIRM") != "true":
        confirm = input(f"\n  Execute? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    res = executor.execute_swap(route, amount_usd=amount, mode="exact_in", simulate=executor.is_sim)

    if res.success:
        print(f"\n  {C.OK}✓{C.R} {step_type.upper()} complete: {res.tx_hash}")
    else:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {res.error}")


# ---------------------------------------------------------------------------
# Transfer Handler (Send)
# ---------------------------------------------------------------------------

def handle_send(text: str, executor):
    """
    Handle send command: send <amount> <token> to <recipient>
    """
    from pacman_display import C, print_transfer_receipt
    from pacman_transfers import execute_transfer
    
    parts = text.strip().split()
    # Canonical format: send 100 HBAR to 0.0.123
    # parts: [0]send [1]amt [2]token [3]to [4]recipient
    
    if len(parts) < 5 or parts[3].lower() != "to":
        print(f"  {C.ERR}✗{C.R} Usage: {C.BOLD}send <amount> <token> to <recipient>{C.R}")
        print(f"  {C.MUTED}Example: send 100 HBAR to 0.0.12345{C.R}")
        return

    try:
        amount = float(parts[1])
    except:
        print(f"  {C.ERR}✗{C.R} Invalid amount: {parts[1]}")
        return
        
    symbol = parts[2].upper()
    recipient = parts[4]
    
    # Confirmation Prompt
    print(f"\n  {C.ACCENT}↗{C.R} Transfer: {C.TEXT}{amount} {symbol}{C.R} → {C.TEXT}{recipient}{C.R}")
    
    if os.getenv("PACMAN_AUTO_CONFIRM") != "true":
        confirm = input(f"  Confirm? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return
            
    # Execute
    print(f"  {C.MUTED}Submitting...{C.R}")
    res = execute_transfer(executor, symbol, amount, recipient)
    
    if res["success"]:
        print_transfer_receipt(res)
    else:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {res['error']}")



# ---------------------------------------------------------------------------
# One-shot Mode
# ---------------------------------------------------------------------------

def handle_oneshot(args: list, router):
    """Handle a single CLI command and exit."""
    from pacman_display import show_help, show_tokens, show_price, show_sources

    cmd = args[0].lower()

    # Instant commands
    if cmd in ["help", "--help", "-h", "?"]:
        show_help()
        return
    if cmd == "tokens":
        show_tokens()
        return
    if cmd == "sources":
        show_sources()
        return
    if cmd == "price":
        if len(args) >= 2:
            from pacman_translator import resolve_token
            target = resolve_token(args[1]) or args[1]
            show_price(target)
        else:
            from pacman_display import show_all_prices
            show_all_prices()
        return

    # Commands requiring engine
    executor = init_executor()
    command = " ".join(args)
    process_command(command, router, executor)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    from pacman_display import PACMAN_BANNER, print_security_warning, show_help, C

    # Print banner instantly (zero imports needed)
    print(PACMAN_BANNER)
    print_security_warning()

    # Load router (fast — no web3)
    try:
        from pacman_variant_router import PacmanVariantRouter
        router = PacmanVariantRouter()
        router.load_pools(pools_file="data/pacman_data_raw.json")
    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Failed to initialize: {e}")
        return

    # One-shot mode
    if len(sys.argv) > 1:
        handle_oneshot(sys.argv[1:], router)
        return

    # Interactive REPL
    show_help()
    executor = None

    while True:
        try:
            user_input = input(f"\n  {C.ACCENT}ᗧ{C.R} ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print(f"  {C.MUTED}Shutting down.{C.R}")
                break

            # Lazy-init executor for commands that need it
            needs_engine = any(w in user_input.lower() for w in [
                "swap", "buy", "sell", "convert", "balance", "history", "account", "send"
            ])
            if needs_engine and executor is None:
                executor = init_executor()

            process_command(user_input, router, executor)

        except KeyboardInterrupt:
            print(f"\n  {C.MUTED}Interrupted.{C.R}")
            break
        except Exception as e:
            from pacman_display import C as _C
            print(f"  {_C.ERR}✗{_C.R} {e}")


if __name__ == "__main__":
    main()
