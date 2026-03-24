#!/usr/bin/env python3
"""
Live Test: Limit Order Engine — End-to-End Fill Test
=====================================================

Creates a limit order that SHOULD trigger immediately because
HBAR is currently ~$0.098 and the target is "below $0.10".

Action: swap 5 HBAR → USDC (well within $1 safety limit).

This manually calls _check_orders() instead of waiting 10 min.
"""

import sys
import os
import time

sys.path.insert(0, ".")

# Force NON-simulation mode for a real fill test
os.environ["SPACELORD_SIMULATE"] = "false"
os.environ["SPACELORD_CONFIRM"] = "false"  # No interactive confirmation

from src.controller import SpaceLordController
from src.limit_orders import LimitOrderEngine
from lib.prices import price_manager

print("=" * 60)
print("  LIVE LIMIT ORDER FILL TEST")
print("=" * 60)

# 1. Init
app = SpaceLordController()
print(f"\n✅ Controller initialized (mode: {'SIM' if app.config.simulate_mode else 'LIVE'})")
print(f"   Account: {app.account_id}")
print(f"   Network: {app.network}")

# 2. Get current price
price_manager.reload()
hbar_price = price_manager.get_hbar_price()
print(f"\n📊 Current HBAR price: ${hbar_price:.6f}")

# 3. Access limit engine
engine = app.limit_engine
print(f"\n📋 Orders loaded: {len(engine.orders)} ({engine.get_active_count()} active)")

# 4. Create an order that should trigger immediately
# HBAR is ~$0.098, so "below $0.10" → should match
target = 0.10
oid = engine.add_order(
    token_symbol="HBAR",
    token_id="0.0.0",
    condition="below",
    target_price=target,
    action_type="swap",
    action_string="swap:HBAR:USDC:5:exact_in",
    description=f"LIVE TEST: Swap 5 HBAR → USDC when HBAR below ${target}",
)
print(f"\n✅ Order created: {oid}")
print(f"   Trigger: HBAR below ${target:.4f}")
print(f"   Action:  swap 5 HBAR → USDC (exact_in)")
print(f"   Current: ${hbar_price:.6f} → {'SHOULD TRIGGER' if hbar_price <= target else 'will NOT trigger'}")

# 5. Manually run check_orders (instead of waiting 10 min)
print(f"\n⟳ Running _check_orders() NOW...")
engine._controller = app
engine._check_orders()

# 6. Report results
order = next(o for o in engine.orders if o.id == oid)
print(f"\n{'=' * 60}")
print(f"  RESULT")
print(f"{'=' * 60}")
print(f"  Status:       {order.status}")
print(f"  Triggered at: {order.triggered_at or 'N/A'}")
print(f"  Error:        {order.error or 'None'}")

if order.status == "triggered":
    print(f"\n  🎉 ORDER FILLED SUCCESSFULLY!")
elif order.status == "failed":
    print(f"\n  ❌ ORDER TRIGGERED BUT EXECUTION FAILED")
else:
    print(f"\n  ⏳ Order still active (price didn't match condition)")

print(f"\n{'=' * 60}")
print("  LIVE TEST COMPLETE")
print(f"{'=' * 60}")
