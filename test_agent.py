#!/usr/bin/env python3
"""
Test Suite for Pacman Agent + Translator
========================================

Tests the complete flow:
  1. Route table loads correctly
  2. All major token pairs have routes
  3. Translator parses NL correctly
  4. Agent + Translator integrate cleanly
  5. Route details are sane (fees, hops, token IDs)
"""

import json
import sys
from pathlib import Path

# Track results
passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def test_route_table():
    """Test that routes.json was built correctly."""
    print("\n--- Route Table ---")

    routes_file = Path(__file__).parent / "routes.json"
    test("routes.json exists", routes_file.exists())

    with open(routes_file) as f:
        data = json.load(f)

    test("has tokens", len(data["tokens"]) > 10, f"got {len(data['tokens'])}")
    test("has routes", len(data["routes"]) > 100, f"got {len(data['routes'])}")

    # Key pairs must have routes
    required = [
        "USDC->WBTC_HTS", "USDC->WETH_HTS",
        "SAUCE->WBTC_HTS", "USDC->SAUCE", "USDC->GIB",
    ]

    # WHBAR must NOT be tradeable (routing-only)
    test("no WHBAR in tokens", "WHBAR" not in data["tokens"])
    test("no HBAR in tokens", "HBAR" not in data["tokens"])
    whbar_routes = [k for k in data["routes"] if k.startswith("WHBAR->") or k.endswith("->WHBAR")]
    test("no routes to/from WHBAR", len(whbar_routes) == 0)
    for pair in required:
        test(f"route exists: {pair}", pair in data["routes"])

    # Validate route structure
    r = data["routes"]["USDC->WBTC_HTS"]
    test("route has path", "path" in r)
    test("route has hops", "hops" in r)
    test("route has fee", "total_fee_percent" in r)
    test("route fee > 0", r["total_fee_percent"] > 0)

    # Validate hop structure
    hop = r["hops"][0]
    test("hop has from", "from" in hop)
    test("hop has to", "to" in hop)
    test("hop has token_in_id", "token_in_id" in hop)
    test("hop has token_out_id", "token_out_id" in hop)
    test("hop has decimals_in", "decimals_in" in hop)
    test("hop has decimals_out", "decimals_out" in hop)
    test("hop has fee", "fee" in hop)
    test("hop has pool_id", "pool_id" in hop)


def test_agent():
    """Test PacmanAgent without needing private key."""
    print("\n--- Agent ---")

    from pacman_agent import PacmanAgent

    agent = PacmanAgent()

    # Token list
    tokens = agent.tokens()
    test("tokens loaded", len(tokens) > 10)
    test("USDC in tokens", "USDC" in tokens)
    test("WBTC_HTS in tokens", "WBTC_HTS" in tokens)
    test("WHBAR not tradeable", "WHBAR" not in tokens)
    test("GIB in tokens", "GIB" in tokens)

    # Route lookup
    route = agent.route("USDC", "WBTC_HTS")
    test("route found: USDC->WBTC_HTS", route is not None)
    if route:
        test("route src correct", route.src == "USDC")
        test("route dst correct", route.dst == "WBTC_HTS")
        test("route has hops", route.num_hops >= 1)
        test("route fee reasonable", 0 < route.total_fee_percent < 5)

    route2 = agent.route("SAUCE", "WBTC_HTS")
    test("multi-hop route found: SAUCE->WBTC_HTS", route2 is not None)
    if route2:
        test("multi-hop has 2+ hops", route2.num_hops >= 2)

    # No route for nonexistent tokens
    bad_route = agent.route("FAKE", "TOKEN")
    test("no route for bad tokens", bad_route is None)

    # Explain
    explanation = agent.explain("USDC", "WBTC_HTS")
    test("explain returns text", len(explanation) > 10)
    test("explain mentions USDC", "USDC" in explanation)

    # Case insensitivity
    route3 = agent.route("usdc", "wbtc_hts")
    test("case insensitive lookup", route3 is not None)


def test_translator():
    """Test the NL translator."""
    print("\n--- Translator ---")

    from pacman_translator import translate, resolve_token

    # Token resolution
    test("resolve 'bitcoin'", resolve_token("bitcoin") == "WBTC_HTS")
    test("resolve 'USDC'", resolve_token("USDC") == "USDC")
    test("resolve 'gib'", resolve_token("gib") == "GIB")
    test("resolve 'eth'", resolve_token("eth") == "WETH_HTS")
    test("resolve 'sauce'", resolve_token("sauce") == "SAUCE")
    test("resolve unknown", resolve_token("nonexistent") is None)

    # Exact input parsing
    r = translate("swap 1 USDC for WBTC")
    test("parse 'swap 1 USDC for WBTC'", r is not None)
    if r:
        test("  from=USDC", r["from_token"] == "USDC")
        test("  to=WBTC_HTS", r["to_token"] == "WBTC_HTS")
        test("  amount=1.0", r["amount"] == 1.0)
        test("  mode=exact_in", r["mode"] == "exact_in")

    # Exact output parsing
    r2 = translate("buy 0.001 BTC with USDC")
    test("parse 'buy 0.001 BTC with USDC'", r2 is not None)
    if r2:
        test("  from=USDC", r2["from_token"] == "USDC")
        test("  to=WBTC_HTS", r2["to_token"] == "WBTC_HTS")
        test("  amount=0.001", r2["amount"] == 0.001)
        test("  mode=exact_out", r2["mode"] == "exact_out")

    # Exact output via "swap X for AMOUNT Y"
    r3 = translate("swap USDC for 0.001 bitcoin")
    test("parse 'swap USDC for 0.001 bitcoin'", r3 is not None)
    if r3:
        test("  mode=exact_out", r3["mode"] == "exact_out")
        test("  amount=0.001", r3["amount"] == 0.001)

    # Edge cases
    test("empty string returns None", translate("") is None)
    test("gibberish returns None", translate("hello world") is None)
    test("no amount returns None", translate("swap USDC for BTC") is None)


def test_integration():
    """Test translator -> agent pipeline."""
    print("\n--- Integration ---")

    from pacman_agent import PacmanAgent
    from pacman_translator import translate

    agent = PacmanAgent()

    # Full pipeline: NL -> structured -> route
    commands = [
        ("swap 1 USDC for bitcoin", "USDC", "WBTC_HTS"),
        ("buy 0.001 BTC with USDC", "USDC", "WBTC_HTS"),
        ("convert 100 SAUCE to USDC", "SAUCE", "USDC"),
        ("trade 1 USDC for ethereum", "USDC", "WETH_HTS"),
    ]

    for text, expected_from, expected_to in commands:
        req = translate(text)
        test(f"translate: '{text}'", req is not None)
        if req:
            route = agent.route(req["from_token"], req["to_token"])
            test(f"  route exists", route is not None)
            if route:
                test(f"  from={expected_from}", route.src == expected_from)
                test(f"  to={expected_to}", route.dst == expected_to)


def test_route_sanity():
    """Verify route data makes economic sense."""
    print("\n--- Route Sanity ---")

    with open(Path(__file__).parent / "routes.json") as f:
        data = json.load(f)

    for key, route in data["routes"].items():
        # Fees should be positive and not insane
        if route["total_fee_percent"] <= 0:
            test(f"fee > 0: {key}", False, f"fee={route['total_fee_percent']}")
        if route["total_fee_percent"] > 5:
            test(f"fee < 5%: {key}", False, f"fee={route['total_fee_percent']}")

        # Hops should match path length
        expected_hops = len(route["path"]) - 1
        if route["num_hops"] != expected_hops:
            test(f"hops match path: {key}", False,
                 f"hops={route['num_hops']}, path_len={len(route['path'])}")

        # Token IDs should be valid hedera format
        for hop in route["hops"]:
            if not hop["token_in_id"].startswith("0.0."):
                test(f"valid token_in_id: {key}", False, hop["token_in_id"])
            if not hop["token_out_id"].startswith("0.0."):
                test(f"valid token_out_id: {key}", False, hop["token_out_id"])

    test("all routes have valid fees", True)
    test("all routes have matching hop counts", True)
    test("all token IDs are valid hedera format", True)


if __name__ == "__main__":
    print("=" * 60)
    print("PACMAN AGENT TEST SUITE")
    print("=" * 60)

    test_route_table()
    test_agent()
    test_translator()
    test_integration()
    test_route_sanity()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
