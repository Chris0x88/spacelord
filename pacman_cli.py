#!/usr/bin/env python3
"""
Pacman CLI - Operational Trading Interface
==========================================

The View Layer.
Responsible ONLY for:
1. Handling User Input (Arguments, Interactive)
2. Displaying Output (Colors, Tables, Errors)
3. Calling the Logic Layer (PacmanApp)
"""

import sys
import json
from pacman_app import PacmanApp
from pacman_errors import PacmanError, ConfigurationError
from pacman_display import (
    C, PACMAN_BANNER, print_security_warning,
    show_help, show_tokens, show_sources, show_price,
    show_balance, show_account, show_history,
    print_receipt, print_transfer_receipt
)
from pacman_translator import translate

# ---------------------------------------------------------------------------
# Command Handlers (View Logic)
# ---------------------------------------------------------------------------

def cmd_help(app, args):
    show_help()

def cmd_tokens(app, args):
    show_tokens()

def cmd_sources(app, args):
    show_sources()

def cmd_price(app, args):
    if len(args) >= 1:
        show_price(args[0])
    else:
        # Show all
        from pacman_display import show_all_prices
        show_all_prices()

def cmd_account(app, args):
    show_account(app.executor)

def cmd_balance(app, args):
    token = args[0] if args else None
    show_balance(app.executor, single_token=token)

def cmd_history(app, args):
    show_history(app.executor)

def cmd_send(app, args):
    # Syntax: send <amount> <token> to <recipient>
    # args: [100, HBAR, to, 0.0.123]
    if len(args) < 4 or args[2].lower() != "to":
        print(f"  {C.ERR}✗{C.R} Usage: {C.BOLD}send <amount> <token> to <recipient>{C.R}")
        return

    try:
        amount = float(args[0])
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid amount: {args[0]}")
        return

    symbol = args[1].upper()
    recipient = args[3]

    print(f"\n  {C.ACCENT}↗{C.R} Transfer: {C.TEXT}{amount} {symbol}{C.R} → {C.TEXT}{recipient}{C.R}")

    if app.config.require_confirmation:
        confirm = input(f"  Confirm? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    print(f"  {C.MUTED}Submitting...{C.R}")
    res = app.transfer(symbol, amount, recipient)

    if res["success"]:
        print_transfer_receipt(res)
    else:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {res.get('error')}")

def handle_natural_language(app, text):
    """Process NLP commands like 'swap 10 HBAR for USDC'."""
    req = translate(text)
    if not req:
        print(f"  {C.ERR}✗{C.R} Unknown command. Type {C.TEXT}help{C.R} for options.")
        return

    intent = req.get("intent")

    if intent == "swap":
        _do_swap(app, req)
    elif intent == "convert":
        _do_swap(app, req) # Convert is handled by swap logic in App
    elif intent == "balance":
        cmd_balance(app, [])
    elif intent == "help":
        cmd_help(app, [])
    else:
        print(f"  {C.ERR}✗{C.R} Unhandled intent: {intent}")

def _do_swap(app, req):
    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]
    mode = req["mode"]

    print(f"\n  {C.ACCENT}⟳{C.R} Analyzing: {C.TEXT}{amount}{C.R} {from_token} → {to_token} ({mode})")

    try:
        route = app.get_route(from_token, to_token, amount)
        if not route:
            print(f"  {C.ERR}✗{C.R} No route found for {from_token} → {to_token}")
            return

        print(f"\n  {C.BOLD}Proposed Route:{C.R}")
        print(f"  {C.TEXT}{route.from_variant}{C.R} → {C.TEXT}{route.to_variant}{C.R}")
        print(route.explain())

        if app.config.require_confirmation:
            confirm = input(f"\n  Execute swap? {C.MUTED}(y/n){C.R} ").strip().lower()
            if confirm not in ["y", "yes"]:
                print(f"  {C.MUTED}Cancelled.{C.R}")
                return

        res = app.executor.execute_swap(route, amount_usd=amount, mode=mode)

        if res.success:
            print_receipt(res, route, route.from_variant, route.to_variant, amount, mode, app.executor)
        else:
            print(f"\n  {C.ERR}✗{C.R} FAILED: {res.error}")

    except PacmanError as e:
        print(f"  {C.ERR}✗{C.R} Error: {e}")

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

COMMANDS = {
    "help": cmd_help, "?": cmd_help, "-h": cmd_help,
    "tokens": cmd_tokens,
    "sources": cmd_sources,
    "price": cmd_price,
    "account": cmd_account,
    "balance": cmd_balance,
    "history": cmd_history,
    "send": cmd_send
}

def process_input(app, text):
    parts = text.strip().split()
    if not parts: return

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in COMMANDS:
        try:
            COMMANDS[cmd](app, args)
        except PacmanError as e:
            print(f"  {C.ERR}✗{C.R} {e}")
        except Exception as e:
            print(f"  {C.ERR}✗{C.R} Unexpected Error: {e}")
    else:
        # Fallback to NLP
        try:
            handle_natural_language(app, text)
        except PacmanError as e:
            print(f"  {C.ERR}✗{C.R} {e}")

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    print(PACMAN_BANNER)
    print_security_warning()

    # Initialize App (Logic)
    try:
        app = PacmanApp()
        print(f"\n  {C.BOLD}{C.ACCENT}System Online{C.R}")
    except ConfigurationError as e:
        print(f"  {C.ERR}✗{C.R} Config Error: {e}")
        return

    # One-Shot Mode
    if len(sys.argv) > 1:
        process_input(app, " ".join(sys.argv[1:]))
        return

    # Interactive Mode
    cmd_help(app, [])
    while True:
        try:
            user_input = input(f"\n  {C.ACCENT}ᗧ{C.R} ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print(f"  {C.MUTED}Shutting down.{C.R}")
                break

            process_input(app, user_input)

        except KeyboardInterrupt:
            print(f"\n  {C.MUTED}Interrupted.{C.R}")
            break

if __name__ == "__main__":
    main()
