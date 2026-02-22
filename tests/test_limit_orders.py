#!/usr/bin/env python3
"""
Tests for the Limit Order Engine.

Tests order lifecycle, price matching, persistence, and action parsing.
No live network calls — all tests are offline.
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.limit_orders import LimitOrder, LimitOrderEngine


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def _make_engine(tmp_path: str = None) -> LimitOrderEngine:
    """Create an engine with a temp file for isolation."""
    if tmp_path is None:
        fd, tmp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(tmp_path, "w") as f:
            json.dump([], f)
    return LimitOrderEngine(orders_file=tmp_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_add_order():
    """Orders are created with correct fields."""
    engine = _make_engine()
    oid = engine.add_order(
        token_symbol="HBAR",
        token_id="0.0.0",
        condition="below",
        target_price=0.08,
        action_type="swap",
        action_string="swap:HBAR:USDC:100:exact_in",
        description="Buy USDC when HBAR dips",
    )
    assert len(oid) == 8, f"Expected 8-char ID, got {len(oid)}"
    assert engine.get_active_count() == 1

    order = engine.orders[0]
    assert order.status == "active"
    assert order.token_symbol == "HBAR"
    assert order.condition == "below"
    assert order.target_price == 0.08
    assert order.action_string == "swap:HBAR:USDC:100:exact_in"
    print("✅ test_add_order PASSED")


def test_cancel_order():
    """Cancellation works by prefix match."""
    engine = _make_engine()
    oid = engine.add_order("HBAR", "0.0.0", "below", 0.05, "swap", "swap:HBAR:USDC:50:exact_in")
    
    # Cancel by full ID
    assert engine.cancel_order(oid) == True
    assert engine.get_active_count() == 0
    assert engine.orders[0].status == "cancelled"
    
    # Can't cancel again
    assert engine.cancel_order(oid) == False
    print("✅ test_cancel_order PASSED")


def test_cancel_prefix_match():
    """Cancellation works with partial ID prefix."""
    engine = _make_engine()
    oid = engine.add_order("HBAR", "0.0.0", "below", 0.05, "swap", "swap:HBAR:USDC:50:exact_in")
    
    # Cancel by first 4 chars
    assert engine.cancel_order(oid[:4]) == True
    assert engine.get_active_count() == 0
    print("✅ test_cancel_prefix_match PASSED")


def test_list_orders_filter():
    """Listing filters by status correctly."""
    engine = _make_engine()
    engine.add_order("HBAR", "0.0.0", "below", 0.08, "swap", "swap:HBAR:USDC:100:exact_in")
    oid2 = engine.add_order("SAUCE", "0.0.731861", "above", 0.05, "swap", "swap:SAUCE:USDC:500:exact_in")
    engine.cancel_order(oid2)
    
    assert len(engine.list_orders(status="active")) == 1
    assert len(engine.list_orders(status="cancelled")) == 1
    assert len(engine.list_orders()) == 2
    print("✅ test_list_orders_filter PASSED")


def test_price_matching_below():
    """'below' condition triggers when price <= target."""
    order = LimitOrder(
        id="test1234", token_id="0.0.0", token_symbol="HBAR",
        condition="below", target_price=0.10,
        action_type="swap", action_string="swap:HBAR:USDC:100:exact_in",
        description="test"
    )
    assert order.matches(0.09) == True   # Below target
    assert order.matches(0.10) == True   # Equal to target
    assert order.matches(0.11) == False  # Above target
    print("✅ test_price_matching_below PASSED")


def test_price_matching_above():
    """'above' condition triggers when price >= target."""
    order = LimitOrder(
        id="test5678", token_id="0.0.0", token_symbol="HBAR",
        condition="above", target_price=0.20,
        action_type="swap", action_string="swap:HBAR:USDC:100:exact_in",
        description="test"
    )
    assert order.matches(0.21) == True   # Above target
    assert order.matches(0.20) == True   # Equal to target
    assert order.matches(0.19) == False  # Below target
    print("✅ test_price_matching_above PASSED")


def test_persistence_roundtrip():
    """Orders survive save/load cycle."""
    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(tmp_path, "w") as f:
        json.dump([], f)

    # Create and populate
    engine1 = LimitOrderEngine(orders_file=tmp_path)
    engine1.add_order("HBAR", "0.0.0", "below", 0.08, "swap", "swap:HBAR:USDC:100:exact_in", "test order")
    engine1.add_order("SAUCE", "0.0.731861", "above", 0.05, "swap", "swap:SAUCE:USDC:500:exact_in")
    
    # Reload from same file
    engine2 = LimitOrderEngine(orders_file=tmp_path)
    assert len(engine2.orders) == 2
    assert engine2.orders[0].token_symbol == "HBAR"
    assert engine2.orders[1].token_symbol == "SAUCE"
    assert engine2.orders[0].description == "test order"
    
    # Clean up
    os.unlink(tmp_path)
    print("✅ test_persistence_roundtrip PASSED")


def test_action_string_parsing():
    """Verify swap action strings parse correctly."""
    action_str = "swap:HBAR:USDC:100:exact_in"
    parts = action_str.split(":")
    assert parts[0] == "swap"
    assert parts[1] == "HBAR"
    assert parts[2] == "USDC"
    assert float(parts[3]) == 100.0
    assert parts[4] == "exact_in"
    
    # Transfer format
    action_str2 = "transfer:USDC:50:0.0.12345"
    parts2 = action_str2.split(":")
    assert parts2[0] == "transfer"
    assert parts2[1] == "USDC"
    assert float(parts2[2]) == 50.0
    assert parts2[3] == "0.0.12345"
    print("✅ test_action_string_parsing PASSED")


def test_invalid_condition():
    """Invalid condition raises ValueError."""
    engine = _make_engine()
    try:
        engine.add_order("HBAR", "0.0.0", "sideways", 0.10, "swap", "swap:HBAR:USDC:100:exact_in")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "above" in str(e) and "below" in str(e)
    print("✅ test_invalid_condition PASSED")


def test_invalid_price():
    """Zero/negative price raises ValueError."""
    engine = _make_engine()
    try:
        engine.add_order("HBAR", "0.0.0", "below", 0.0, "swap", "swap:HBAR:USDC:100:exact_in")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    try:
        engine.add_order("HBAR", "0.0.0", "below", -1.0, "swap", "swap:HBAR:USDC:100:exact_in")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("✅ test_invalid_price PASSED")


def test_daemon_not_running_initially():
    """Daemon should not be running after init."""
    engine = _make_engine()
    assert engine.is_running == False
    print("✅ test_daemon_not_running_initially PASSED")


def test_empty_check_orders_no_crash():
    """_check_orders on empty list should not crash."""
    engine = _make_engine()
    engine._check_orders()  # should be a no-op
    print("✅ test_empty_check_orders_no_crash PASSED")


def test_parse_interval():
    """Human-readable interval parser works correctly."""
    from src.limit_orders import parse_interval, format_interval
    assert parse_interval("5m") == 300
    assert parse_interval("1h") == 3600
    assert parse_interval("30s") == 30
    assert parse_interval("1d") == 86400
    assert parse_interval("600") == 600
    assert parse_interval("2 hours") == 7200
    assert parse_interval("invalid") is None
    
    assert format_interval(300) == "5m"
    assert format_interval(3600) == "1h"
    assert format_interval(3660) == "1h 1m"
    print("✅ test_parse_interval PASSED")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_add_order,
        test_cancel_order,
        test_cancel_prefix_match,
        test_list_orders_filter,
        test_price_matching_below,
        test_price_matching_above,
        test_persistence_roundtrip,
        test_action_string_parsing,
        test_invalid_condition,
        test_invalid_price,
        test_daemon_not_running_initially,
        test_empty_check_orders_no_crash,
        test_parse_interval,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__} FAILED: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
