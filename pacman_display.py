#!/usr/bin/env python3
"""
Pacman Display - Terminal UI Rendering Engine
==============================================

Pure rendering module — takes data, prints formatted output.
All ANSI color, ASCII art, progress animations, and layout logic lives here.
No business logic, no side-effects beyond stdout.
"""

import json
import sys
import time
from typing import Optional


# ---------------------------------------------------------------------------
# ANSI Colors & Styles
# ---------------------------------------------------------------------------

class C:
    """Semantic color theme — dark mode optimized.

    Every color has a *role*. To change the entire look,
    edit only the ANSI codes here — no need to touch any
    print() call elsewhere in the file.
    """
    R     = "\033[0m"       # Reset
    BOLD  = "\033[1m"

    # ── Semantic Roles ──────────────────────────────────
    TEXT   = "\033[97m"     # Primary text  (bright white)
    MUTED  = "\033[37m"     # Secondary     (std white — visible on dark!)
    ACCENT = "\033[96m"     # Emphasis      (bright cyan)
    OK     = "\033[92m"     # Success       (bright green)
    WARN   = "\033[93m"     # Warning       (bright yellow)
    ERR    = "\033[91m"     # Error         (bright red)
    BRAND  = "\033[95m"     # Hedera purple (bright magenta)
    CHROME = "\033[36m"     # Borders       (std cyan)

    @staticmethod
    def strip(text: str) -> str:
        """Remove ANSI codes from text for length calculations."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)


# ---------------------------------------------------------------------------
# ASCII Art Banner
# ---------------------------------------------------------------------------

PACMAN_BANNER = f"""{C.ACCENT}
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝{C.R}

{C.CHROME}    ╭──────────────────────────────────────────────────────╮{C.R}
{C.ACCENT}     ᗧ{C.R}{C.MUTED}· · ·{C.R}{C.OK} 👾{C.R}  {C.TEXT}SaucerSwap V2{C.R} {C.MUTED}on{C.R} {C.BRAND}Hedera{C.R} {C.MUTED}Hashgraph{C.R}
{C.CHROME}    ╰──────────────────────────────────────────────────────╯{C.R}"""


# ---------------------------------------------------------------------------
# Loading / Progress
# ---------------------------------------------------------------------------

def show_loading(message: str):
    """Show a simple loading message."""
    sys.stdout.write(f"\r  {C.ACCENT}{message}{C.R}...")
    sys.stdout.flush()

def hide_loading(message: str = "Done"):
    """Complete the loading line."""
    sys.stdout.write(f" {C.OK}{message}{C.R}\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Security Warning
# ---------------------------------------------------------------------------

def print_security_warning():
    """Display a compact security disclaimer."""
    print(f"\n{C.CHROME}{'━' * 60}{C.R}")
    print(f"  {C.ERR}⚠  SECURITY WARNING{C.R}")
    print(f"  {C.MUTED}Testing mode only • Use a dedicated Hot Account{C.R}")
    print(f"  {C.MUTED}See SECURITY.md for safety best practices{C.R}")
    print(f"{C.CHROME}{'━' * 60}{C.R}")


# ---------------------------------------------------------------------------
# Help Menu
# ---------------------------------------------------------------------------

def show_help():
    """Display the command reference."""
    print(f"\n{C.BOLD}{C.TEXT}  COMMANDS{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")

    commands = [
        ("swap <amt> <A> for <B>",   "Exact input swap"),
        ("swap <A> for <amt> <B>",   "Exact output swap"),
        ("convert <A> for <amt> <B>","Wrap / Unwrap tokens"),
        ("send <amt> <tk> to <rcp>", "Transfer crypto"),
        ("receive <token>",          "Get addr & associate"),
        ("balance",                  "All wallet balances"),
        ("balance <token>",          "Single token balance"),
        ("price",                    "List all market prices"),
        ("price <token>",            "Check single price"),
        ("sources",                  "Show all price sources"),
        ("account",                  "Wallet & network info"),
        ("tokens",                   "Supported token list"),
        ("history",                  "Transaction history"),
        ("verbose",                  "Toggle debug logging"),
        ("help",                     "This menu"),
        ("exit",                     "Quit Pacman"),
    ]

    for cmd, desc in commands:
        print(f"  {C.ACCENT}{cmd:30s}{C.R} {C.MUTED}{desc}{C.R}")

    print(f"\n{C.BOLD}  EXAMPLES{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.MUTED}${C.R} swap 10 HBAR for USDC")
    print(f"  {C.MUTED}${C.R} swap USDC for 0.001 WBTC")
    print(f"  {C.MUTED}${C.R} balance HBAR")
    print(f"  {C.MUTED}${C.R} price SAUCE")
    print()


# ---------------------------------------------------------------------------
# Account Info
# ---------------------------------------------------------------------------

def show_account(executor):
    """Display wallet and network information."""
    print(f"\n{C.BOLD}{C.TEXT}  ACCOUNT{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    print(f"  {C.MUTED}Hedera ID{C.R}    {C.TEXT}{executor.hedera_account_id}{C.R}")
    print(f"  {C.MUTED}EVM Address{C.R}  {C.TEXT}{executor.eoa}{C.R}")
    print(f"  {C.MUTED}Network{C.R}      {C.OK}{executor.network.upper()}{C.R}")
    print(f"  {C.MUTED}RPC{C.R}          {C.MUTED}{executor.rpc_url}{C.R}")

    sim_status = f"{C.WARN}SIMULATION{C.R}" if executor.is_sim else f"{C.OK}LIVE{C.R}"
    print(f"  {C.MUTED}Mode{C.R}         {sim_status}")
    print()


# ---------------------------------------------------------------------------
# Price Check
# ---------------------------------------------------------------------------

def show_price(token_name: str):
    """Show the current price for a specific token."""
    from pacman_price_manager import price_manager
    price_manager.reload()

    # Try to resolve token name to ID
    token_id = _resolve_token_id(token_name)
    if not token_id:
        print(f"  {C.ERR}✗{C.R} Unknown token: {token_name}")
        return

    if token_name.upper() == "HBAR":
        price, source = price_manager.get_price_with_source("0.0.0")
    elif token_name.upper() == "WHBAR":
        price, source = price_manager.get_price_with_source("0.0.1456986")
    else:
        price, source = price_manager.get_price_with_source(token_id)

    if price > 0:
        print(f"\n  {C.TEXT}{token_name.upper()}{C.R}  {C.OK}${price:,.6f}{C.R}")
        print(f"  {C.MUTED}Source: {source}{C.R}")
    else:
        print(f"\n  {C.TEXT}{token_name.upper()}{C.R}  {C.MUTED}Price unavailable{C.R}")
    print()


def show_all_prices():
    """Display prices for all tracked tokens."""
    from pacman_price_manager import price_manager
    import refresh_data
    
    # 1. Fetch fresh data (Online)
    refresh_data.refresh()
    
    # 2. Reload manager (Offline/Cache)
    price_manager.reload()
    
    print(f"\n{C.BOLD}{C.TEXT}  MARKET PRICES (Live){C.R}")
    
    # Header
    print(f"  {C.MUTED}{'SYMBOL':10s}  {'PRICE':12s}  SOURCE{C.R}")
    print(f"  {C.CHROME}{'─'*10}  {'─'*12}  {'─'*40}{C.R}")
    
    # HBAR First
    hp = price_manager.get_hbar_price()
    _, hs = price_manager.get_price_with_source("0.0.0")
    print(f"  {C.ACCENT}{'HBAR':10s}{C.R}  {C.OK}${hp:<11,.4f}{C.R}  {C.MUTED}{hs}{C.R}")
    
    # Sort by Symbol if possible, else ID
    # We need to map IDs to symbols for display
    try:
        with open("data/tokens.json") as f:
            tdata = json.load(f)
    except:
        tdata = {}

    # Create a look-up map: ID -> Symbol
    id_to_sym = {}
    for sym, m in tdata.items():
        if "id" in m: id_to_sym[m["id"]] = sym

    # Gather data list
    items = []
    for tid, price in price_manager.prices.items():
        if tid == "0.0.1456986": continue # Skip WHBAR (redundant with HBAR)
        sym = id_to_sym.get(tid, tid)
        source = price_manager.sources.get(tid, "")
        items.append((sym, price, source))
        
    # Sort alphabetically by symbol
    items.sort(key=lambda x: x[0].upper())
    
    for sym, price, source in items:
        # truncate source if too long? No, user wants detail.
        print(f"  {C.ACCENT}{sym:10s}{C.R}  {C.OK}${price:<11,.4f}{C.R}  {C.MUTED}{source}{C.R}")
    print()


def show_sources():
    """Display the sources of all tracked prices."""
    from pacman_price_manager import price_manager
    price_manager.reload()
    
    print(f"\n{C.BOLD}{C.TEXT}  PRICE SOURCES{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    
    # Tokens (HBAR is included in price_manager.sources as 0.0.0)
    for tid, source in sorted(price_manager.sources.items()):
        if tid == "0.0.1456986": continue # skip redundant WHBAR
        print(f"  {C.ACCENT}{tid:12s}{C.R} {C.MUTED}{source}{C.R}")
    print()


# ---------------------------------------------------------------------------
# Balance (All & Single)
# ---------------------------------------------------------------------------

def show_balance(executor, single_token: str = None):
    """Display wallet balances. If single_token is given, show only that one."""
    from pacman_price_manager import price_manager
    price_manager.reload()

    if single_token:
        _show_single_balance(executor, single_token, price_manager)
        return

    _show_all_balances(executor, price_manager)


def _show_single_balance(executor, token_name: str, price_manager):
    """Show balance for a single token."""
    token_name_upper = token_name.upper()

    # HBAR special case
    if token_name_upper in ["HBAR", "WHBAR"]:
        hbar_bal = executor.w3.eth.get_balance(executor.eoa)
        readable = hbar_bal / (10**18)
        price = price_manager.get_hbar_price()
        usd_val = readable * price

        print(f"\n  {C.BOLD}{C.TEXT}HBAR{C.R}")
        print(f"  {C.CHROME}{'─' * 40}{C.R}")
        print(f"  {C.TEXT}{readable:18.6f}{C.R} HBAR")
        print(f"  {C.OK}${usd_val:18.2f}{C.R} USD")
        print(f"  {C.MUTED}@ ${price:.6f}/HBAR{C.R}")
        print()
        return

    # Token lookup
    try:
        with open("data/tokens.json") as f:
            tokens_data = json.load(f)
    except:
        print(f"  {C.ERR}✗{C.R} Could not load tokens.json")
        return

    # Find the token
    meta = None
    for sym, m in tokens_data.items():
        if sym.upper() == token_name_upper or m.get("symbol", "").upper() == token_name_upper:
            meta = m
            meta["_sym"] = sym
            break

    if not meta:
        print(f"  {C.ERR}✗{C.R} Unknown token: {token_name}")
        return

    token_id = meta.get("id")
    try:
        raw_bal = executor.client.get_token_balance(token_id)
        decimals = meta.get("decimals", 8)
        readable = raw_bal / (10**decimals)
        price = price_manager.get_price(token_id)
        usd_val = readable * price

        print(f"\n  {C.BOLD}{C.TEXT}{meta.get('symbol', meta['_sym'])}{C.R}")
        print(f"  {C.CHROME}{'─' * 40}{C.R}")
        print(f"  {C.TEXT}{readable:18.8f}{C.R} {meta['_sym']}")
        print(f"  {C.OK}${usd_val:18.2f}{C.R} USD")
        if price > 0:
            print(f"  {C.MUTED}@ ${price:,.6f}/{meta['_sym']}{C.R}")
        print(f"  {C.MUTED}Token ID: {token_id}{C.R}")
        print()
    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Error fetching balance: {e}")


def _show_all_balances(executor, price_manager):
    """Display all wallet balances in a formatted table."""
    from pacman_variant_router import PacmanVariantRouter

    print(f"\n{C.BOLD}{C.TEXT}  WALLET{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")

    try:
        # HBAR
        hbar_bal = executor.client.w3.eth.get_balance(executor.client.eoa)
        hbar_readable = hbar_bal / (10**18)
        hbar_price = price_manager.get_hbar_price()
        hbar_usd = hbar_readable * hbar_price

        print(f"  {C.ACCENT}HBAR{C.R}       {C.TEXT}{hbar_readable:>14.6f}{C.R}  {C.OK}${hbar_usd:>10.2f}{C.R}")

        with open("data/tokens.json") as f:
            tokens_data = json.load(f)

        total_usd = hbar_usd
        BLACKLIST = PacmanVariantRouter.BLACKLISTED_TOKENS

        def sort_key(item):
            sym = item[0]
            if "USDC" in sym: return (0, sym)
            if "WBTC" in sym: return (1, sym)
            if "WETH" in sym: return (2, sym)
            return (3, sym)

        sorted_tokens = sorted(tokens_data.items(), key=sort_key)
        for sym, meta in sorted_tokens:
            token_id = meta.get("id")
            if not token_id or token_id in BLACKLIST:
                continue
            try:
                raw_bal = executor.client.get_token_balance(token_id)
                if raw_bal > 0:
                    decimals = meta.get("decimals", 8)
                    readable = raw_bal / (10**decimals)
                    price = price_manager.get_price(token_id)
                    usd_val = readable * price

                    assoc = ""
                    if not executor.check_token_association(token_id):
                        assoc = f" {C.WARN}[!]{C.R}"

                    sym_display = meta.get("symbol", sym)[:10]
                    print(f"  {C.ACCENT}{sym_display:10s}{C.R} {C.TEXT}{readable:>14.8f}{C.R}  {C.OK}${usd_val:>10.2f}{C.R}{assoc}")
                    total_usd += usd_val
            except:
                continue

        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  {C.BOLD}{'TOTAL':10s}{C.R} {' ':>14s}  {C.BOLD}{C.OK}${total_usd:>10.2f}{C.R}")
        print()

    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Failed to fetch balances: {e}")


# ---------------------------------------------------------------------------
# Token Gallery
# ---------------------------------------------------------------------------

def show_tokens():
    """Display all supported tokens in a clean formatted table."""
    print(f"\n{C.BOLD}{C.TEXT}  TOKENS{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")

    try:
        from pacman_translator import ALIASES
        from pacman_variant_router import PacmanVariantRouter

        BLACKLIST = PacmanVariantRouter.BLACKLISTED_TOKENS
        with open("data/tokens.json") as f:
            tokens_data = json.load(f)

        id_to_aliases = {}
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

        PRIORITY_SYMS = ["USDC", "WBTC", "WETH", "QNT", "LINK", "AVAX", "SAUCE", "XSAUCE", "BONZO"]

        def sort_key(item):
            tid, data = item
            if tid == "0.0.0": return (0, "")
            meta = next((m for m in tokens_data.values() if m.get("id") == tid), {})
            sym = meta.get("symbol", data["sym"])
            for i, psym in enumerate(PRIORITY_SYMS):
                if psym in sym.upper():
                    return (1, i, sym)
            return (2, sym)

        # Header
        print(f"  {C.MUTED}{'ID':15s}  {'SYMBOL':10s}  {'NAME':20s}  ALIASES{C.R}")
        print(f"  {C.CHROME}{'─'*15}  {'─'*10}  {'─'*20}  {'─'*20}{C.R}")

        sorted_tokens = sorted(id_to_aliases.items(), key=sort_key)
        for tid, data in sorted_tokens:
            meta = next((m for m in tokens_data.values() if m.get("id") == tid), {})
            sym = meta.get("symbol", data["sym"])
            name = meta.get("name", "Hedera Native" if tid == "0.0.0" else "Unknown")
            alias_str = ", ".join(sorted(list(set(data["aliases"]))))[:28]

            print(f"  {C.MUTED}{tid:15s}{C.R}  {C.ACCENT}{sym:10s}{C.R}  {C.TEXT}{name[:20]:20s}{C.R}  {C.MUTED}{alias_str}{C.R}")

        print()
    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Failed to list tokens: {e}")


# ---------------------------------------------------------------------------
# Transaction History
# ---------------------------------------------------------------------------

def show_history(executor):
    """Display operations history with live-priced USD values."""
    from pacman_price_manager import price_manager

    hist = executor.get_execution_history(limit=10)
    if not hist:
        print(f"\n  {C.MUTED}No transaction history found.{C.R}\n")
        return

    print(f"\n{C.BOLD}{C.TEXT}  HISTORY{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")

    price_manager.reload()

    # Load token metadata
    tokens_map = {}
    try:
        with open("data/tokens.json") as f:
            tdata = json.load(f)
            for k, v in tdata.items():
                tokens_map[k] = v
                if "id" in v: tokens_map[v["id"]] = v
                if "symbol" in v: tokens_map[v["symbol"]] = v
    except:
        pass

    for h in hist:
        status_icon = f"{C.OK}✓{C.R}" if h["success"] else f"{C.ERR}✗{C.R}"
        mode = h.get("mode", "?")
        route = h.get("route", {})
        ft = route.get("from", "?")
        tt = route.get("to", "?")

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
            token_id = None
            meta = tokens_map.get(ft)
            if not meta:
                if ft.upper() in ["HBAR", "0.0.0", "WHBAR", "0.0.1456986"]:
                    decimals = 8
                    token_id = "0.0.1456986"
            else:
                decimals = meta.get("decimals", 8)
                token_id = meta.get("id")

            if token_id:
                price = price_manager.get_price(token_id)
            elif ft.upper() == "HBAR":
                price = price_manager.get_hbar_price()

            if decimals > 0:
                amt_real = raw_in / (10**decimals)
                amt_token = amt_real
                if price > 0:
                    amt_usd = amt_token * price

        to_amt = h.get('to_amount_token', 0.0)
        ts = h.get('timestamp', '?')[:19]

        if to_amt > 0:
            print(f"  {status_icon} {C.MUTED}{ts}{C.R}  {C.TEXT}{amt_token:>12.6f}{C.R} {C.ACCENT}{ft:6s}{C.R} → {C.TEXT}{to_amt:>12.6f}{C.R} {C.ACCENT}{tt:6s}{C.R}  {C.OK}${amt_usd:>8.2f}{C.R}")
        else:
            print(f"  {status_icon} {C.MUTED}{ts}{C.R}  {C.TEXT}{amt_token:>12.6f}{C.R} {C.ACCENT}{ft:6s}{C.R} → {C.ACCENT}{tt:6s}{C.R}  {C.OK}${amt_usd:>8.2f}{C.R}")

    print()


# ---------------------------------------------------------------------------
# Transaction Receipt
# ---------------------------------------------------------------------------

def print_receipt(res, route, from_token: str, to_token: str, amount_val: float,
                  mode: str, executor):
    """Print a premium transaction receipt."""
    width = 62
    border_color = C.CHROME

    def hline(char="─"):
        print(f"  {border_color}{char * width}{C.R}")

    def row(label: str, value: str, value_color=C.TEXT):
        padding = width - 4 - len(C.strip(label)) - len(C.strip(str(value)))
        if padding < 1: padding = 1
        print(f"  {border_color}│{C.R} {C.MUTED}{label}{C.R}{'.' * padding}{value_color}{value}{C.R} {border_color}│{C.R}")

    def section(title: str):
        padding = width - 4 - len(title)
        print(f"  {border_color}├{'─' * (width)}{C.R}")
        print(f"  {border_color}│{C.R} {C.BOLD}{C.TEXT}{title}{C.R}{' ' * padding} {border_color}│{C.R}")

    print()
    print(f"  {border_color}╭{'─' * width}╮{C.R}")
    title = "HEDERA TRANSACTION RECORD"
    pad = (width - len(title) - 2) // 2
    print(f"  {border_color}│{C.R}{' ' * pad}{C.BOLD}{C.TEXT}{title}{C.R}{' ' * (width - pad - len(title) - 2)} {border_color}│{C.R}")
    hline("─")

    timestamp = res.timestamp or time.strftime("%Y-%m-%d %H:%M:%S")
    row("Date/Time", timestamp)
    row("Account", res.account_id or executor.hedera_account_id)
    row("Network", executor.network.upper(), C.OK)

    section("TRANSFER")
    from_decimals = executor._get_token_decimals(from_token)
    to_decimals = executor._get_token_decimals(to_token)
    amount_in = res.amount_in_raw / (10**from_decimals)
    amount_out = res.amount_out_raw / (10**to_decimals)

    row("Sent", f"{amount_in:.8f} {from_token}", C.ERR)
    row("Received", f"{amount_out:.8f} {to_token}", C.OK)

    section("RATES")
    actual_net_rate = amount_out / amount_in if amount_in > 0 else 0
    fee_pct = (res.lp_fee_amount / amount_in) if amount_in > 0 else 0
    gross_rate = actual_net_rate / (1 - fee_pct) if (0 < fee_pct < 1) else actual_net_rate

    row(f"Market", f"1 {from_token} = {gross_rate:.8f} {to_token}")
    row(f"Effective", f"1 {from_token} = {actual_net_rate:.8f} {to_token}", C.OK)

    section("FEES")
    if res.lp_fee_amount > 0:
        row("LP Fee", f"{res.lp_fee_amount:.8f} {res.lp_fee_token}")
    row("Gas", f"{res.gas_cost_hbar:.8f} HBAR")
    row("Gas (USD)", f"${res.gas_cost_usd:.4f}")
    row("HBAR Price", f"${res.hbar_usd_price:.4f}")

    section("SETTLEMENT")
    if to_token.upper() in ["HBAR", "0.0.0", "WHBAR", "0.0.1456986"]:
        net_received = amount_out - res.gas_cost_hbar
        settle_usd = net_received * res.hbar_usd_price
    elif "USDC" in to_token.upper():
        net_received = amount_out
        settle_usd = net_received
    else:
        net_received = amount_out
        from pacman_cli import get_token_id_for_variant
        tp = executor.price_manager.get_price(get_token_id_for_variant(to_token))
        settle_usd = net_received * tp if tp > 0 else 0

    row("Net Received", f"{net_received:.8f} {to_token}", C.OK)
    row("Value", f"${settle_usd:,.2f} USD", C.OK)

    if res.tx_hash and res.tx_hash != "SIMULATED":
        row("Status", "CONSENSUS FINALIZED", C.OK)
        row("Hash", res.tx_hash[:32])
        row("", res.tx_hash[32:])
    else:
        row("Status", "SIMULATED", C.WARN)

    print(f"  {border_color}╰{'─' * width}╯{C.R}")

    if res.tx_hash and res.tx_hash != "SIMULATED":
        print(f"\n  {C.MUTED}🔗 https://hashscan.io/mainnet/transaction/{res.tx_hash}{C.R}\n")


def print_transfer_receipt(res: dict):
    """Print a receipt for a transfer."""
    width = 62
    border_color = C.CHROME

    def row(label: str, value: str, value_color=C.TEXT):
        padding = width - 4 - len(C.strip(label)) - len(C.strip(str(value)))
        if padding < 1: padding = 1
        print(f"  {border_color}│{C.R} {C.MUTED}{label}{C.R}{'.' * padding}{value_color}{value}{C.R} {border_color}│{C.R}")

    def hline(char="─"):
        print(f"  {border_color}{char * width}{C.R}")

    print()
    print(f"  {border_color}╭{'─' * width}╮{C.R}")
    title = "CRYPTO TRANSFER"
    pad = (width - len(title) - 2) // 2
    print(f"  {border_color}│{C.R}{' ' * pad}{C.BOLD}{C.ACCENT}{title}{C.R}{' ' * (width - pad - len(title) - 2)} {border_color}│{C.R}")
    hline("─")

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    row("Date/Time", ts)
    row("Status", "SUCCESS", C.OK)
    
    hline()
    row("Amount", f"{res['amount']} {res['symbol']}", C.TEXT)
    row("Recipient", res['recipient'], C.ACCENT)
    
    hline()
    if 'tx_hash' in res:
        row("Tx Hash", res['tx_hash'][:32], C.MUTED)
        row("", res['tx_hash'][32:], C.MUTED)
        
    if 'gas_used' in res:
        row("Gas Used", f"{res['gas_used']}", C.MUTED)

    print(f"  {border_color}╰{'─' * width}╯{C.R}")
    if 'tx_hash' in res and res.get('success'):
        print(f"\n  {C.MUTED}🔗 https://hashscan.io/mainnet/transaction/{res['tx_hash']}{C.R}\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_token_id(token_name: str) -> Optional[str]:
    """Resolve a token name/symbol to its Hedera token ID."""
    name = token_name.upper()
    if name in ["HBAR", "WHBAR"]:
        return "0.0.1456986"

    try:
        with open("data/tokens.json") as f:
            tokens_data = json.load(f)
        for sym, meta in tokens_data.items():
            if sym.upper() == name or meta.get("symbol", "").upper() == name:
                return meta.get("id")
    except:
        pass
    return None
