#!/usr/bin/env python3
"""
CLI Commands: Information & Utilities
=====================================

Handles: help, tokens, sources, price, pools, history, verbose.
"""

import json
from pathlib import Path
from cli.display import (
    C, show_help, show_tokens, show_sources, show_price,
    show_history
)


def cmd_help(app, args):
    import json as _json

    json_mode = "--json" in args
    clean = [a for a in args if a not in ("--json", "--yes", "-y")]
    topic = clean[0] if clean else None

    # Agent workflow search: help how <task>
    if topic and topic.lower() == "how" and len(clean) > 1:
        query = " ".join(clean[1:]).lower()
        return _help_how(query, json_mode)

    # JSON mode: structured command reference for agents
    if json_mode:
        return _help_json(topic)

    # Map Aliases
    aliases = {
        "trade": "swap", "buy": "swap", "get": "swap",
        "transfers": "send", "transfer": "send",
        "wallet": "balance", "prices": "price",
        "natural": "nlp", "rules": "nlp", "grammar": "nlp",
        "accounts": "account",
        "pool-deposit": "liquidity", "pool-withdraw": "liquidity", "lp": "liquidity",
        "assoc": "associate", "association": "associate", "token": "associate",
        "orders": "order",
    }

    if topic and topic.lower() in aliases:
        topic = aliases[topic.lower()]

    show_help(topic)


# ---------------------------------------------------------------------------
# Agent-facing help systems
# ---------------------------------------------------------------------------

AGENT_WORKFLOWS = {
    "swap": {
        "description": "Swap one token for another",
        "steps": [
            "balance                           # Check you have enough of the source token",
            "swap <amount> <FROM> for <TO>      # Exact-in: spend exact amount",
            "swap <FROM> for <amount> <TO>      # Exact-out: receive exact amount",
        ],
        "examples": ["swap 5 USDC for HBAR", "swap HBAR for 10 USDC", "swap 1 usdc[hts] for usdc"],
        "notes": "V2 only. Max $100/swap. Aliases: bitcoin→WBTC, dollar→USDC, ethereum→WETH",
    },
    "send": {
        "description": "Transfer tokens to another account",
        "steps": [
            "balance                           # Verify funds",
            "whitelist                          # Check recipient is whitelisted",
            "whitelist add <addr> [nickname]    # Add if needed",
            "send <amount> <token> to <addr>    # Execute transfer",
        ],
        "examples": ["send 10 HBAR to 0.0.12345", "send 1 USDC to 0.0.12345 memo Payment"],
        "notes": "Own accounts (accounts.json) are auto-whitelisted. EVM addresses blocked.",
    },
    "deposit": {
        "description": "Add liquidity to a V2 pool",
        "steps": [
            "balance                           # Check token balances",
            "pool-deposit <amount> <tokenA> <tokenB> range <pct>  # Agent-friendly",
            "pool-deposit <t0> <t1> <a0> <a1> <fee> <tickLo> <tickHi>  # Advanced",
        ],
        "examples": ["pool-deposit 5 USDC HBAR range 5", "pool-deposit 1 USDC SAUCE range full"],
        "notes": "range: 2, 5, 10, or 'full'. Default 5%. Auto-finds best pool by TVL.",
    },
    "withdraw": {
        "description": "Remove liquidity from a V2 pool",
        "steps": [
            "lp                                # List active positions with NFT IDs",
            "pool-withdraw <nft_id> [amount]   # Withdraw (default: 100%)",
            "pool-withdraw all                 # Withdraw all positions",
        ],
        "examples": ["pool-withdraw 12345 100%", "pool-withdraw 12345 50%", "pool-withdraw all"],
        "notes": "Amount can be: raw number, 50%, 100%, or 'all'.",
    },
    "stake": {
        "description": "Stake HBAR to a consensus node for rewards",
        "steps": [
            "balance                           # Check HBAR balance",
            "stake [node_id]                   # Stake (default: node 5 Google)",
        ],
        "examples": ["stake", "stake 5", "unstake"],
        "notes": "Staking is non-custodial. Funds remain usable. Rewards accrue automatically.",
    },
    "associate": {
        "description": "Link a token to your account (required before receiving it)",
        "steps": [
            "receive <token>                   # Check if already associated",
            "associate <token>                 # Associate if needed",
        ],
        "examples": ["associate USDC", "associate 0.0.456858"],
        "notes": "Auto-association happens during swaps. Manual only needed for receiving tokens.",
    },
    "buy-and-lp": {
        "description": "Buy a token and provide liquidity in a V2 pool",
        "steps": [
            "balance                           # Check available funds",
            "price <token>                     # Check token price",
            "swap <amount> USDC for <token>    # Buy the token",
            "balance <token>                   # Verify received amount",
            "pool-deposit <amount> <token> HBAR range 5  # Deposit into LP",
            "lp                                # Verify LP position created",
            "nfts                              # View LP NFT",
        ],
        "examples": [
            "swap 1 USDC for SAUCE",
            "pool-deposit 44 SAUCE HBAR range 5",
        ],
        "notes": "Range options: 2 (tight), 5 (standard), 10 (wide), full. The second token amount is auto-calculated. LP creates an NFT.",
    },
    "fund-robot": {
        "description": "Fund and start the robot rebalancer",
        "steps": [
            "robot status                      # Check if already funded",
            "send <amount> USDC to <robot_id>      # Send USDC to robot",
            "send <amount> WBTC to <robot_id>      # Send WBTC to robot",
            "robot status                      # Verify portfolio > $5",
            "robot start                       # Start the daemon",
        ],
        "examples": ["send 10 USDC to <robot_id>", "send 0.0003 WBTC to <robot_id>"],
        "notes": "Robot needs >= $5 portfolio (USDC + WBTC). Threshold 15%. Min trade $1.",
    },
    "close-lp": {
        "description": "Close an LP position and collect tokens",
        "steps": [
            "lp                                # List positions with NFT IDs",
            "pool-withdraw <nft_id> 100%       # Withdraw all liquidity",
            "balance                           # Verify tokens returned",
        ],
        "examples": ["pool-withdraw 73729 100%", "pool-withdraw all"],
        "notes": "Can withdraw partial: 50%, or custom amount. 'pool-withdraw all' closes everything.",
    },
    "rebalance": {
        "description": "Manage the Power Law BTC rebalancer robot",
        "steps": [
            "robot status                      # Check robot portfolio and signal",
            "robot signal                      # View model signal (no trading)",
            "robot start                       # Start daemon (needs $5+ portfolio)",
            "robot stop                        # Stop daemon",
        ],
        "examples": ["robot status", "robot start"],
        "notes": "Run 'robot status' to see robot account ID. Min portfolio $5. Threshold 15%.",
    },
    "order": {
        "description": "Set limit orders that trigger automatically",
        "steps": [
            "order buy <token> at <price> size <n>   # Buy when price drops",
            "order sell <token> at <price> size <n>   # Sell when price rises",
            "order list                               # View open orders",
            "order on                                 # Start monitoring daemon",
            "order cancel <id>                        # Cancel an order",
        ],
        "examples": ["order buy HBAR at 0.08 size 10", "order sell HBAR at 0.15 size 50"],
        "notes": "Daemon must be ON to auto-execute. 'order off' stops monitoring.",
    },
    "account": {
        "description": "Manage accounts and switch between them",
        "steps": [
            "account                           # View active account + known accounts",
            "account switch <id_or_name>       # Switch active account",
            "account switch <main_id>          # ALWAYS switch back to main after robot ops",
        ],
        "examples": ["account switch <robot_id>", "account rename 0.0.xxx MyLabel"],
        "notes": "Run 'account' to see your account IDs. Always switch back to main after robot ops.",
    },
    "whitelist": {
        "description": "Manage trusted transfer destinations",
        "steps": [
            "whitelist                         # View current whitelist",
            "whitelist add <addr> [nickname]   # Add address",
            "whitelist remove <addr>           # Remove address",
        ],
        "examples": ["whitelist add 0.0.12345 Exchange"],
        "notes": "Whitelist is the most critical safety feature. Own accounts auto-whitelisted.",
    },
}


def _help_how(query, json_mode):
    """Search workflows by keyword and return step-by-step instructions."""
    import json as _json

    matches = []
    for key, wf in AGENT_WORKFLOWS.items():
        score = 0
        searchable = f"{key} {wf['description']} {' '.join(wf.get('examples', []))}".lower()
        for word in query.split():
            if word in searchable:
                score += 1
        if score > 0:
            matches.append((score, key, wf))

    matches.sort(key=lambda x: -x[0])

    if json_mode:
        results = []
        for _, key, wf in matches[:3]:
            results.append({"workflow": key, **wf})
        print(_json.dumps({"query": query, "results": results}, indent=2))
        return

    if not matches:
        print(f"  {C.WARN}⚠{C.R} No workflows found for '{query}'.")
        print(f"  {C.MUTED}Available: {', '.join(AGENT_WORKFLOWS.keys())}{C.R}")
        return

    for _, key, wf in matches[:3]:
        print(f"\n  {C.BOLD}{C.ACCENT}HOW TO: {wf['description']}{C.R}")
        print(f"  {C.CHROME}{'─' * 60}{C.R}")
        for step in wf["steps"]:
            print(f"  {C.TEXT}{step}{C.R}")
        if wf.get("examples"):
            print(f"\n  {C.MUTED}Examples:{C.R}")
            for ex in wf["examples"]:
                print(f"    {C.ACCENT}{ex}{C.R}")
        if wf.get("notes"):
            print(f"  {C.MUTED}Note: {wf['notes']}{C.R}")
    print()


def _help_json(topic):
    """Return structured command reference for agents."""
    import json as _json

    commands = {
        "balance": {"syntax": "balance [token]", "description": "Token balances + USD values", "flags": ["--json"]},
        "status": {"syntax": "status", "description": "Account + portfolio + robot snapshot", "flags": ["--json"], "aliases": ["whoami", "info"]},
        "account": {"syntax": "account [switch <id>] [rename <id> <name>] [--new]", "description": "Account management", "flags": ["--json"]},
        "swap": {"syntax": "swap <amt> <FROM> for <TO> | swap <FROM> for <amt> <TO>", "description": "DEX swap (V2)", "flags": ["--json"]},
        "send": {"syntax": "send <amt> <token> to <addr> [memo <text>]", "description": "Transfer tokens", "flags": ["--json"]},
        "receive": {"syntax": "receive [token]", "description": "Show deposit address + association check"},
        "associate": {"syntax": "associate <token|id>", "description": "Link token to account", "flags": ["--json"]},
        "whitelist": {"syntax": "whitelist [add <addr> [nick]] [remove <addr>]", "description": "Manage transfer whitelist"},
        "price": {"syntax": "price [token]", "description": "Live token prices", "flags": ["--json"]},
        "tokens": {"syntax": "tokens", "description": "Supported token list with aliases"},
        "history": {"syntax": "history", "description": "Recent transaction history", "flags": ["--json"]},
        "pools": {"syntax": "pools [list|search <q>|approve <id>]", "description": "Pool registry management"},
        "pool-deposit": {"syntax": "pool-deposit <amt> <tokenA> <tokenB> [range <pct>]", "description": "Add V2 liquidity (agent-friendly)", "flags": ["--json", "--dry-run"]},
        "pool-withdraw": {"syntax": "pool-withdraw <nft_id> [amount|pct|all]", "description": "Remove V2 liquidity", "flags": ["--json", "--dry-run"]},
        "lp": {"syntax": "lp", "description": "View active LP positions"},
        "stake": {"syntax": "stake [node_id]", "description": "Stake HBAR (default: node 5 Google)"},
        "unstake": {"syntax": "unstake", "description": "Stop staking"},
        "slippage": {"syntax": "slippage [percent]", "description": "View or set max slippage (0.1-5.0%)"},
        "order": {"syntax": "order buy|sell <token> at <price> size <n> | order list|cancel <id>|on|off", "description": "Limit orders"},
        "robot": {"syntax": "robot status|signal|start|stop", "description": "Power Law BTC rebalancer", "flags": ["--json"]},
        "fund": {"syntax": "fund", "description": "Fiat onramp link (MoonPay)", "flags": ["--json"]},
        "doctor": {"syntax": "doctor", "description": "System health diagnostics"},
        "refresh": {"syntax": "refresh", "description": "Refresh pool & price data", "aliases": ["sync"]},
        "logs": {"syntax": "logs [count]", "description": "Agent interaction log"},
        "nfts": {"syntax": "nfts [view <token_id> <serial>]", "description": "NFT inventory"},
        "backup-keys": {"syntax": "backup-keys [--file]", "description": "Key backup", "flags": ["--json"]},
        "verbose": {"syntax": "verbose [on|off]", "description": "Toggle debug logging"},
        "help": {"syntax": "help [topic] | help how <task> | help --json", "description": "Command reference"},
    }

    if topic:
        topic_lower = topic.lower()
        cmd = commands.get(topic_lower)
        if cmd:
            print(_json.dumps({topic_lower: cmd}, indent=2))
        else:
            # Search workflows
            _help_how(topic_lower, json_mode=True)
    else:
        out = {"commands": commands, "workflows": list(AGENT_WORKFLOWS.keys()),
               "usage": "help how <task> for step-by-step guides. help <command> --json for syntax."}
        print(_json.dumps(out, indent=2))
    return


def cmd_tokens(app, args):
    show_tokens()


def cmd_sources(app, args):
    show_sources()


def cmd_price(app, args):
    json_mode = "--json" in args
    clean = [a for a in args if a not in ("--json", "--yes", "-y")]
    if json_mode:
        import json as _json
        from lib.prices import price_manager
        try:
            from scripts import refresh_data
        except ImportError:
            import refresh_data
        refresh_data.refresh()
        price_manager.reload()
        if clean:
            from cli.display import _resolve_token_id
            token_id = _resolve_token_id(clean[0])
            if token_id:
                price = price_manager.get_price(token_id)
                print(_json.dumps({"token": clean[0].upper(), "token_id": token_id, "price_usd": price}))
            else:
                print(_json.dumps({"error": f"Unknown token: {clean[0]}"}))
        else:
            all_prices = {}
            for tid, p in price_manager.prices.items():
                all_prices[tid] = p
            all_prices["hbar"] = price_manager.get_hbar_price()
            print(_json.dumps({"prices": all_prices}))
        return
    if len(clean) >= 1:
        show_price(clean[0])
    else:
        from cli.display import show_all_prices
        show_all_prices()


def cmd_history(app, args):
    if "--json" in args:
        import json as _json
        from pathlib import Path
        records_dir = Path("execution_records")
        if not records_dir.exists():
            print(_json.dumps({"records": []}))
            return
        records = []
        for f in sorted(records_dir.glob("*.json"), reverse=True)[:20]:
            try:
                records.append(_json.loads(f.read_text()))
            except Exception:
                pass
        print(_json.dumps({"records": records}, indent=2, default=str))
        return
    show_history(app.executor)


def cmd_verbose(app, args):
    """Toggle or set verbose mode."""
    if not args:
        enabled = app.toggle_verbose()
    else:
        val = args[0].lower()
        if val in ["on", "true", "1"]:
            enabled = app.toggle_verbose(True)
        elif val in ["off", "false", "0"]:
            enabled = app.toggle_verbose(False)
        else:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}verbose [on/off]{C.R}")
            return
    
    status = f"{C.OK}ON{C.R}" if enabled else f"{C.WARN}OFF{C.R}"
    print(f"  Verbose Mode: {status}")


def cmd_pools(app, args):
    """
    Manage pool registries (search, list, approve, delete).
    Usage: pools <action> [args] [--v1|--v2]
    """
    if not args:
        print(f"\n  {C.BOLD}POOLS COMMANDS{C.R}")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  {C.TEXT}pools list{C.R}             List all approved pools")
        print(f"  {C.TEXT}pools search <q>{C.R}       Search on-chain pools (symbol/ID)")
        print(f"  {C.TEXT}pools approve <id>{C.R}    Add pool to approved list")
        print(f"  {C.TEXT}pools deposit{C.R}         Liquidity deposit wizard")
        print(f"  {C.TEXT}pools withdraw{C.R}        Liquidity withdrawal wizard")
        print(f"  {C.TEXT}pools delete <id>{C.R}     Remove pool from list")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  {C.MUTED}Flags: -1 (V1), -2 (V2). Default: V2{C.R}")
        print()
        return

    # 1. Robust Flag Extraction (Any position, various aliases)
    v1_aliases = ["--v1", "-v1", "--1", "-1"]
    v2_aliases = ["--v2", "-v2", "--2", "-2", "v--2", "--v2"]
    
    v1_flag = any(f in args for f in v1_aliases)
    v2_flag = any(f in args for f in v2_aliases)
    
    # Clean args from flags
    clean_args = [a for a in args if a not in v1_aliases and a not in v2_aliases]
    
    if not clean_args:
        return cmd_pools(app, [])  # Show help if no action left

    action = clean_args[0].lower()
    sub_args = clean_args[1:]
    
    protocol = "v1" if v1_flag else "v2"

    if action == "list":
        _pools_list(app, json_mode="--json" in args)
    elif action == "search":
        if not sub_args:
            print(f"  {C.ERR}✗{C.R} Missing search query.")
            return
        _pools_search(app, sub_args[0], protocol if (v1_flag or v2_flag) else "both")
    elif action == "approve":
        if not sub_args:
            print(f"  {C.ERR}✗{C.R} Missing pool ID.")
            return
        _pools_approve(app, sub_args[0], protocol)
    elif action == "delete" or action == "remove":
        if not sub_args:
            print(f"  {C.ERR}✗{C.R} Missing pool ID.")
            return
        if not (v1_flag or v2_flag):
            _pools_delete(app, sub_args[0], "both")
        else:
            _pools_delete(app, sub_args[0], protocol)
    elif action == "withdraw":
        from cli.commands.liquidity import cmd_pool_withdraw
        return cmd_pool_withdraw(app, sub_args)
    elif action == "deposit":
        from cli.commands.liquidity import cmd_pool_deposit
        return cmd_pool_deposit(app, sub_args)
    else:
        print(f"  {C.ERR}✗{C.R} Unknown action: {action}")


def _pools_list(app, json_mode=False):
    """Show the currently approved pools from JSON files."""
    registries = [
        ("V2 (Direct)", "data/pools_v2.json"),
        ("V1 (Legacy)", "data/pools_v1.json")
    ]

    if json_mode:
        import json as _json
        result = {}
        for label, path_str in registries:
            p = Path(path_str)
            if p.exists():
                with open(p) as f:
                    result[label] = _json.load(f)
        print(_json.dumps(result, indent=2))
        return

    # Pre-load tokens metadata for symbol resolution
    tokens = {}
    tokens_path = Path("data/tokens.json")
    if tokens_path.exists():
        try:
            with open(tokens_path) as f:
                tokens = json.load(f)
        except Exception:
            pass

    print(f"\n{C.BOLD}{C.TEXT}  APPROVED POOL REGISTRIES{C.R}")
    
    for label, path_str in registries:
        p = Path(path_str)
        print(f"\n  {C.ACCENT}■ {label}{C.R} {C.MUTED}({path_str}){C.R}")
        if not p.exists():
            print(f"    {C.MUTED}No file found.{C.R}")
            continue
            
        with open(p) as f:
            data = json.load(f)
            if not data:
                print(f"    {C.MUTED}Registry is empty.{C.R}")
            else:
                print(f"    {C.CHROME}{'ID':<12} {'LABEL':<20} {'FEE':<6}{C.R}")
                for entry in data:
                    cid = entry.get("contractId", "N/A")
                    lbl = entry.get("label", "Unknown")
                    
                    # Fix: Resolve symbols if label is Unknown
                    if lbl == "Unknown":
                        idA = entry.get("tokenA")
                        idB = entry.get("tokenB")
                        # Look up symbols in tokens.json
                        symA = tokens.get(idA, {}).get("symbol") if idA else None
                        symB = tokens.get(idB, {}).get("symbol") if idB else None
                        # Fallback to ID if symbol not found
                        if symA or symB:
                            lbl = f"{symA or idA}/{symB or idB}"

                    fee = entry.get("fee")
                    fee_str = str(fee) if fee is not None else "N/A"
                    print(f"    {C.TEXT}{cid:<12} {lbl:<20} {fee_str:<6}{C.R}")
    print()


def _pools_search(app, query, protocol):
    """Perform on-chain discovery using the Sidecar module."""
    from src.discovery import DiscoveryManager
    discovery = DiscoveryManager()
    
    protocols = ["v1", "v2"] if protocol == "both" else [protocol]
    
    print(f"\n  {C.ACCENT}🔍 Searching on-chain...{C.R} (Query: {C.BOLD}{query}{C.R})")
    
    found_any = False
    for p_type in protocols:
        results = discovery.search_pools(query, protocol=p_type)
        if not results:
            continue
            
        found_any = True
        print(f"\n  {C.BOLD}{p_type.upper()} Liquidity Sources{C.R}")
        print(f"  {C.CHROME}{'ID':<12} {'PAIR':<25} {'FEE':<8}{C.R}")
        print(f"  {C.CHROME}{'─' * 50}{C.R}")
        
        for r in results[:10]:
            cid = r.get("contractId", "N/A")
            tA = r.get("tokenA", {}).get("symbol", "???")
            tB = r.get("tokenB", {}).get("symbol", "???")
            idA = r.get("tokenA", {}).get("id", "???")
            idB = r.get("tokenB", {}).get("id", "???")
            
            fee = r.get("fee")
            if p_type == "v1" and fee is None:
                fee = 3000
            fee_str = f"{fee/10000:.2f}%" if fee is not None else "N/A"
            
            print(f"  {C.TEXT}{cid:<12} {tA}/{tB:<24} {fee_str:<8}{C.R}")
            print(f"               {C.MUTED}{idA} / {idB}{C.R}")
            
    if not found_any:
        print(f"  {C.WARN}⚠ No pools found matching query.{C.R}")
    else:
        print(f"\n  {C.MUTED}Type 'pools approve <ID>' to add a pool to your registry.{C.R}")
    print()


def _pools_approve(app, pool_id, protocol):
    """Fetch pool metadata and save to registry."""
    from src.discovery import DiscoveryManager
    discovery = DiscoveryManager()
    
    print(f"  Verifying pool {pool_id} metadata...")
    results = discovery.search_pools(pool_id, protocol=protocol)
    
    if not results:
        other = "v1" if protocol == "v2" else "v2"
        results = discovery.search_pools(pool_id, protocol=other)
        if results:
            protocol = other
            
    if not results:
        print(f"  {C.ERR}✗{C.R} Could not find metadata for pool {pool_id}.")
        return

    pool_data = None
    for r in results:
        if r.get("contractId") == pool_id:
            pool_data = r
            break
            
    if not pool_data:
        pool_data = results[0]

    success = app.approve_pool(pool_data, protocol=protocol)
    if success:
        print(f"  {C.OK}✅ Approved {protocol.upper()} pool {pool_id}!{C.R}")
    else:
        print(f"  {C.WARN}⚠ Pool already in registry or error occurred.{C.R}")


def _pools_delete(app, pool_id, protocol):
    """Remove pool from registry."""
    if protocol == "both":
        success = app.remove_pool(pool_id, protocol="v1")
        if not success:
            success = app.remove_pool(pool_id, protocol="v2")
            if success:
                print(f"  {C.OK}✅ Removed V2 pool {pool_id} from registry.{C.R}")
            else:
                print(f"  {C.WARN}⚠ Pool {pool_id} not found in V1 or V2 registries.{C.R}")
        else:
            print(f"  {C.OK}✅ Removed V1 pool {pool_id} from registry.{C.R}")
    else:
        success = app.remove_pool(pool_id, protocol=protocol)
        if success:
            print(f"  {C.OK}✅ Removed {protocol.upper()} pool {pool_id} from registry.{C.R}")
        else:
            print(f"  {C.WARN}⚠ Pool not found in {protocol.upper()} registry.{C.R}")


def cmd_refresh(app, args):
    """
    Refresh all pool and token data from SaucerSwap API.
    Fetches ALL V2 pools, updates tokens.json with every tradeable token,
    and injects NLP aliases (BITCOIN, ETH, USD, etc.).
    """
    force = "--force" in args or "-f" in args
    try:
        from scripts.refresh_data import refresh
        print(f"  {C.BOLD}📡 Refreshing pool and token data...{C.R}")
        refresh(force=force)
        # Also re-load the router graph
        app.router.load_pools()
        print(f"  {C.OK}✓{C.R}  Router graph reloaded.")
    except Exception as e:
        print(f"  {C.ERR}✗{C.R}  Refresh failed: {e}")


def cmd_install_service(app, args):
    """Install Space Lord as a native OS service (launchd/systemd)."""
    from src.core.service import ServiceManager
    sm = ServiceManager()
    sm.install()


def cmd_uninstall_service(app, args):
    """Remove the native OS service."""
    from src.core.service import ServiceManager
    sm = ServiceManager()
    sm.uninstall()


def cmd_service_status(app, args):
    """Check the status of the native service and daemon heartbeat."""
    from src.core.service import ServiceManager
    sm = ServiceManager()
    
    print(f"\n  {C.BOLD}🖥 OS Service Status{C.R}")
    print(f"  {'─' * 45}")
    sm.status()
    
    status_file = Path("data/status.json")
    if status_file.exists():
        try:
            with open(status_file) as f:
                data = json.load(f)
            
            print(f"\n  {C.BOLD}🤖 Daemon Status{C.R}")
            print(f"  {'─' * 45}")
            print(f"  PID:    {data.get('pid')}")
            print(f"  Uptime: {data.get('uptime_sec')}s")
            print(f"  Last:   {data.get('last_heartbeat')}")
            print(f"  Sync:   {data.get('last_pool_sync')}")

            plugins = data.get("plugins", [])
            if plugins:
                print(f"\n  {C.BOLD}🧩 Active Plugins{C.R}")
                for p in plugins:
                    p_name = p.get('name', '???')
                    status = f"{C.OK}RUN{C.R}" if p.get('running') else f"{C.ERR}OFF{C.R}"
                    errs = p.get('errors', 0)
                    err_str = f" ({C.ERR}{errs} errs{C.R})" if errs > 0 else ""
                    print(f"  [{status}] {p_name:<12} {p.get('last_heartbeat')}{err_str}")
        except Exception as e:
            print(f"  {C.WARN}⚠ Error reading daemon status: {e}{C.R}")
    else:
        print(f"\n  {C.WARN}⚠ No daemon status found at data/status.json{C.R}")


# ---------------------------------------------------------------------------
# docs — User-facing document reader
# ---------------------------------------------------------------------------

# Documents available to users/agents (NOT developer docs like CLAUDE.md, OPERATIONS.md)
_DOCS_REGISTRY = {
    "security": {
        "file": "SECURITY.md",
        "title": "Security Best Practices",
        "description": "Private keys, whitelists, safety limits, agent safety rules",
    },
    "readme": {
        "file": "README.md",
        "title": "README",
        "description": "What Space Lord is, features, quickstart, architecture overview",
    },
    "changelog": {
        "file": "CHANGELOG.md",
        "title": "Changelog",
        "description": "Version history and recent changes",
    },
    "limits": {
        "file": "data/governance.json",
        "title": "Safety Limits & Governance",
        "description": "Max swap, daily limit, slippage, gas reserve, account roles",
    },
}


def cmd_docs(app, args):
    """
    Read user-facing reference documents.
    Usage:
      docs                  → list available documents
      docs <name>           → display a document
      docs <name> --json    → return document content as JSON
    """
    import json as _json

    json_mode = "--json" in args
    clean = [a for a in args if a not in ("--json", "--yes", "-y")]
    topic = clean[0].lower() if clean else None

    root = Path(__file__).resolve().parent.parent.parent

    if not topic:
        # List available docs
        if json_mode:
            print(_json.dumps({k: {"title": v["title"], "description": v["description"]}
                              for k, v in _DOCS_REGISTRY.items()}, indent=2))
            return

        print(f"\n  {C.BOLD}{C.TEXT}DOCUMENTS{C.R}")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        for key, doc in _DOCS_REGISTRY.items():
            print(f"  {C.ACCENT}{key:<14}{C.R} {C.MUTED}{doc['description']}{C.R}")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  {C.MUTED}Read a document:{C.R} {C.TEXT}docs <name>{C.R}")
        print()
        return

    doc = _DOCS_REGISTRY.get(topic)
    if not doc:
        if json_mode:
            print(_json.dumps({"error": f"Unknown document: {topic}",
                              "available": list(_DOCS_REGISTRY.keys())}))
        else:
            print(f"  {C.ERR}✗{C.R} Unknown document: {topic}")
            print(f"  {C.MUTED}Available: {', '.join(_DOCS_REGISTRY.keys())}{C.R}")
        return

    filepath = root / doc["file"]
    if not filepath.exists():
        if json_mode:
            print(_json.dumps({"error": f"File not found: {doc['file']}"}))
        else:
            print(f"  {C.ERR}✗{C.R} File not found: {doc['file']}")
        return

    content = filepath.read_text()

    if json_mode:
        print(_json.dumps({"document": topic, "title": doc["title"],
                          "content": content}, indent=2))
        return

    # Pretty print with header
    print(f"\n  {C.BOLD}{C.TEXT}{doc['title']}{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    # Render markdown content with basic formatting
    for line in content.split("\n"):
        if line.startswith("# "):
            print(f"\n  {C.BOLD}{C.TEXT}{line[2:]}{C.R}")
        elif line.startswith("## "):
            print(f"\n  {C.BOLD}{line[3:]}{C.R}")
        elif line.startswith("### "):
            print(f"  {C.ACCENT}{line[4:]}{C.R}")
        elif line.startswith("- "):
            print(f"  {C.MUTED}  {line}{C.R}")
        elif line.startswith("|"):
            print(f"  {C.TEXT}{line}{C.R}")
        elif line.strip():
            print(f"  {C.MUTED}{line}{C.R}")
    print()

