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
    topic = args[0] if args else None
    
    # Map Aliases
    aliases = {
        "trade": "swap",
        "buy":   "swap",
        "get":   "swap",
        "transfers": "send",
        "transfer": "send",
        "wallet": "balance",
        "prices": "price",
        "natural": "nlp",
        "rules":   "nlp",
        "grammar": "nlp",
        "accounts": "account"
    }
    
    if topic and topic.lower() in aliases:
        topic = aliases[topic.lower()]
        
    show_help(topic)


def cmd_tokens(app, args):
    show_tokens()


def cmd_sources(app, args):
    show_sources()


def cmd_price(app, args):
    if len(args) >= 1:
        show_price(args[0])
    else:
        from cli.display import show_all_prices
        show_all_prices()


def cmd_history(app, args):
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
        _pools_list(app)
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
    else:
        print(f"  {C.ERR}✗{C.R} Unknown action: {action}")


def _pools_list(app):
    """Show the currently approved pools from JSON files."""
    registries = [
        ("V2 (Direct)", "data/pools.json"),
        ("V1 (Legacy)", "data/v1_pools_approved.json")
    ]
    
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
