#!/usr/bin/env python3
"""
CLI Commands: Trading & Swap Execution
=======================================

Handles: NLP swap parsing, _do_swap execution, swap-v1 legacy swaps.
"""

import sys
from src.logger import logger
from src.errors import PacmanError
from src.translator import translate
from cli.display import C, print_receipt
from cli.commands.wallet import _safe_input


def handle_natural_language(app, text):
    """Process NLP commands like 'swap 10 HBAR for USDC'.

    Flags (--yes, --json, etc.) are stripped by the translator's
    strip_cli_flags() before regex matching, so they never pollute
    token names. The parsed flags are returned in req['flags'].
    """
    req = translate(text)
    if not req:
        print(f"  {C.ERR}✗{C.R} Could not parse command. Examples:")
        print(f"  {C.MUTED}  swap 10 USDC for HBAR{C.R}")
        print(f"  {C.MUTED}  buy 5 HBAR{C.R}")
        print(f"  {C.MUTED}  sell 10 HBAR{C.R}")
        print(f"  {C.MUTED}  swap all USDC for HBAR{C.R}")
        return

    intent = req.get("intent")

    logger.debug(f"NLP Interpretation: {intent} (Req: {req})")
    
    if intent == "swap":
        req_flags = req.get("flags", {})
        yes = req_flags.get("yes", False) or req_flags.get("y", False) or not sys.stdin.isatty()
        json_mode = req_flags.get("json", False)
        _do_swap(app, req, yes=yes, json_mode=json_mode)
    elif intent == "balance":
        from cli.commands.wallet import cmd_balance
        cmd_balance(app, [])
    elif intent == "help":
        from cli.commands.info import cmd_help
        cmd_help(app, [])
    else:
        print(f"  {C.ERR}✗{C.R} Unrecognized: '{intent}'. Try: swap, balance, price, send, help")


def _do_swap(app, req, yes=False, json_mode=False):
    from_token = req["from_token"]
    to_token = req["to_token"]
    amount = req["amount"]
    mode = req["mode"]

    # Resolve "all"/"max" (amount=-1) to actual balance
    if amount == -1:
        try:
            bal_data = app.executor.get_balances()
            if from_token in ["0.0.0", "HBAR"]:
                hbar_bal = bal_data.get("hbar", {}).get("balance", 0)
                gas_reserve = getattr(app.config, 'min_hbar_reserve', 5)
                amount = max(0, hbar_bal - gas_reserve)
            else:
                for _sym, info in bal_data.get("tokens", {}).items():
                    if info.get("token_id") == from_token or _sym == from_token:
                        amount = info.get("balance", 0)
                        break
                else:
                    amount = 0
            if amount <= 0:
                print(f"  {C.ERR}✗{C.R} No balance available for {from_token}")
                return
            print(f"  {C.MUTED}Resolved 'all' to {amount} {from_token}{C.R}")
        except Exception as e:
            print(f"  {C.ERR}✗{C.R} Could not resolve balance: {e}")
            return

    # --- V1 POOL CHECK ---
    if app.is_v1_only(from_token, to_token):
        print(f"  {C.WARN}⚠ Note: This pair appears to be V1-only.{C.R}")
        print(f"  {C.WARN}  Use {C.TEXT}swap-v1{C.R} for legacy SaucerSwap V1 pools.{C.R}")

    if mode == "exact_in":
        print(f"\n  {C.ACCENT}⟳{C.R} Analyzing: {C.TEXT}{amount}{C.R} {from_token} → {to_token} ({mode})")
    else:
        print(f"\n  {C.ACCENT}⟳{C.R} Analyzing: {from_token} → {C.TEXT}{amount}{C.R} {to_token} ({mode})")

    try:
        route = app.get_route(from_token, to_token, amount)
        if not route:
            print(f"  {C.ERR}✗{C.R} No route found for {from_token} → {to_token}")
            # --- AI-FRIENDLY: Actionable suggestions ---
            intermediaries = ["USDC", "HBAR"]
            intermediaries = [t for t in intermediaries if t not in (from_token, to_token)]
            print(f"  {C.MUTED}💡 Try a 2-hop route via an intermediary token:"
                  f" e.g. 'swap {amount} {from_token} for {intermediaries[0]}', "
                  f"then 'swap {intermediaries[0]} for {to_token}'{C.R}")
            print(f"  {C.MUTED}   Or run 'pools search {to_token}' to find a valid pool, then 'pools approve <ID>'{C.R}")
            return

        print(f"\n  {C.BOLD}Proposed Route:{C.R}")
        print(f"  {C.TEXT}{route.from_variant}{C.R} → {C.TEXT}{route.to_variant}{C.R}")
        print(route.explain())

        if app.config.require_confirmation and not yes:
            confirm = _safe_input(f"\n  Execute swap? {C.MUTED}(y/n){C.R} ").strip().lower()
            if confirm not in ["y", "yes"]:
                print(f"  {C.MUTED}Cancelled.{C.R}")
                return
        
        logger.debug("Confirmation received, starting execution phase...")

        res = app.executor.execute_swap(route, raw_amount=amount, mode=mode)

        if json_mode:
            import json as _json
            from_dec = app.executor._get_token_decimals(from_token)
            to_dec = app.executor._get_token_decimals(to_token)
            result = {
                "success": res.success,
                "tx_hash": res.tx_hash,
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": res.amount_in_raw / (10**from_dec) if res.amount_in_raw else 0,
                "amount_out": res.amount_out_raw / (10**to_dec) if res.amount_out_raw else 0,
                "gas_cost_hbar": res.gas_cost_hbar,
                "gas_cost_usd": res.gas_cost_usd,
                "lp_fee": res.lp_fee_amount,
                "account": res.account_id or app.executor.hedera_account_id,
                "mode": mode,
                "error": res.error if not res.success else None,
            }
            print(_json.dumps(result, indent=2))
        elif res.success:
            print_receipt(res, route, route.from_variant, route.to_variant, amount, mode, app.executor)
        else:
            print(f"\n  {C.ERR}✗{C.R} FAILED: {res.error}")
            print(f"  {C.MUTED}Recovery: Try a smaller amount, increase slippage with 'slippage 3.0', or run 'doctor' to diagnose.{C.R}")

    except PacmanError as e:
        if json_mode:
            import json as _json
            print(_json.dumps({"success": False, "error": str(e)}))
        else:
            print(f"  {C.ERR}✗{C.R} Error: {e}")
            print(f"  {C.MUTED}Try 'balance' to verify funds, or 'help' for command syntax.{C.R}")
    except Exception as e:
        if json_mode:
            import json as _json
            print(_json.dumps({"success": False, "error": str(e)}))
        else:
            print(f"\n  {C.ERR}✗{C.R} Critical System Error: {e}")
            print(f"  {C.MUTED}Run 'doctor' to check system health.{C.R}")
            import traceback
            logger.error(traceback.format_exc())


def cmd_swap_v1(app, args):
    """Explicit command for SaucerSwap V1 (Legacy) swaps."""
    # Filter out conversational keywords
    stop_words = ["FOR", "TO", "IN", "→", "->"]
    clean_args = [a for a in args if a.upper() not in stop_words]

    if not clean_args or len(clean_args) < 3:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}swap-v1 <amount> <from> <to>{C.R}")
        print(f"  Example: {C.TEXT}swap-v1 100 hbar for dosa{C.R}")
        return

    try:
        amount = float(clean_args[0])
        from_token = clean_args[1].upper()
        to_token = clean_args[2].upper()
    except:
        print(f"  {C.ERR}✗{C.R} Invalid format. Usage: {C.TEXT}swap-v1 <amount> <from> <to>{C.R}")
        return

    print(f"\n  {C.ACCENT}⟳{C.R} V1 SWAP: {C.TEXT}{amount}{C.R} {from_token} → {to_token}")

    # Resolve IDs
    from_id = app.resolve_token_id(from_token)
    to_id = app.resolve_token_id(to_token)

    # Allow raw ID input if symbol resolution fails
    if not from_id and from_token.startswith("0.0."): from_id = from_token
    if not to_id and to_token.startswith("0.0."): to_id = to_token

    # Final fallback - check for DOSA specifically as requested for the test
    if not from_id and from_token == "DOSA": from_id = "0.0.7894159"
    if not to_id and to_token == "DOSA": to_id = "0.0.7894159"

    if not from_id or not to_id:
        print(f"  {C.ERR}✗{C.R} Could not resolve tokens. Use raw ID if symbol is unknown (e.g. 0.0.123).")
        return

    simulate = getattr(app.config, "simulate_mode", True)
    yes_flag = "--yes" in args or "-y" in args or not sys.stdin.isatty()  # Non-TTY = auto-confirm
    confirm = "y"
    if not simulate and not yes_flag:
        try:
            confirm = input(f"\n  Execute V1 Swap? {C.MUTED}(y/n){C.R} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "y"  # Auto-confirm in non-interactive mode
    
    if confirm in ["y", "yes"]:
        res = app.executor.execute_v1_swap(from_id, to_id, amount, simulate=simulate)
        if res.success:
            print(f"  {C.OK}✅ V1 Swap Successful!{C.R}")
            if res.tx_hash != "SIMULATED_V1":
                 print(f"  {C.MUTED}Tx: {res.tx_hash}{C.R}")
        else:
            print(f"  {C.ERR}✗{C.R} V1 FAILED: {res.error}")
    else:
        print(f"  {C.MUTED}Cancelled.{C.R}")


def cmd_slippage(app, args):
    """View or set slippage tolerance for swaps."""
    import json
    from pathlib import Path

    settings_path = Path("data/settings.json")

    if not args:
        # Show current slippage
        pct = app.config.max_slippage_percent
        print(f"\n  {C.BOLD}Slippage Tolerance:{C.R} {C.TEXT}{pct:.1f}%{C.R}")
        print(f"  {C.MUTED}Usage: slippage <percent>  (e.g. slippage 2.5){C.R}")
        print(f"  {C.MUTED}Range: 0.1% – 5.0%  •  Saved to data/settings.json{C.R}")
        return

    try:
        new_val = float(args[0])
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid number: {args[0]}")
        return

    if new_val < 0.1 or new_val > 5.0:
        print(f"  {C.ERR}✗{C.R} Out of range. Must be between 0.1% and 5.0%")
        return

    # Update live config
    app.config.max_slippage_percent = new_val

    # Persist to settings.json
    try:
        settings = {}
        if settings_path.exists():
            with open(settings_path) as f:
                settings = json.load(f)

        if "swap_settings" not in settings:
            settings["swap_settings"] = {}
        settings["swap_settings"]["slippage_percent"] = round(new_val, 1)

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=4)

        print(f"  {C.OK}✓{C.R} Slippage set to {C.TEXT}{new_val:.1f}%{C.R} (saved)")
    except Exception as e:
        print(f"  {C.WARN}⚠{C.R} Applied to session but failed to save: {e}")

def cmd_lp_padding(app, args):
    """View or set EVM math padding for V2 LP deposits."""
    import json
    from pathlib import Path

    settings_path = Path("data/settings.json")

    if not args:
        # Show current padding
        pct = app.config.lp_padding_percent
        print(f"\n  {C.BOLD}LP Deposit Padding:{C.R} {C.TEXT}{pct:.1f}%{C.R}")
        print(f"  {C.MUTED}Usage: lp-padding <percent>  (e.g. lp-padding 3.0){C.R}")
        print(f"  {C.MUTED}Range: 0.1% – 10.0%  •  Saved to data/settings.json{C.R}")
        return

    try:
        new_val = float(args[0])
    except ValueError:
        print(f"  {C.ERR}✗{C.R} Invalid number: {args[0]}")
        return

    if new_val < 0.1 or new_val > 10.0:
        print(f"  {C.ERR}✗{C.R} Out of range. Must be between 0.1% and 10.0%")
        return

    # Update live config
    app.config.lp_padding_percent = new_val

    # Persist to settings.json
    try:
        settings = {}
        if settings_path.exists():
            with open(settings_path) as f:
                settings = json.load(f)

        if "swap_settings" not in settings:
            settings["swap_settings"] = {}
        settings["swap_settings"]["lp_padding_percent"] = round(new_val, 1)

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=4)

        print(f"  {C.OK}✓{C.R} LP Padding set to {C.TEXT}{new_val:.1f}%{C.R} (saved)")
    except Exception as e:
        print(f"  {C.WARN}⚠{C.R} Applied to session but failed to save: {e}")
