#!/usr/bin/env python3
"""
Pacman Limit Order Engine
=========================

A generic, function-agnostic limit order system.

DESIGN:
- Orders store a structured "action string" (not a callable) so they can
  be JSON-serialized and survive restarts.
- A background daemon thread polls prices at a configurable interval and
  triggers matched orders automatically (no user confirmation — remote robot).
- Works with ANY action: swaps, LP deposits, transfers, etc.

ACTION STRING FORMAT:
    "swap:<from>:<to>:<amount>:<mode>"
    "transfer:<token>:<amount>:<recipient>"
    (extensible — add new action types to _dispatch_action)

USAGE:
    from src.limit_orders import LimitOrderEngine
    engine = LimitOrderEngine()
    engine.add_order("HBAR", "0.0.0", "below", 0.10, "swap", "swap:USDC:HBAR:100:exact_in", "Buy dip")
    engine.start_monitor(controller)
"""

import json
import time
import uuid
import threading
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, List

from src.logger import logger

# ---------------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ORDERS_FILE = BASE_DIR / "data" / "orders.json"
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"
DEFAULT_POLL_SECONDS = 600   # 10 minutes


# ---------------------------------------------------------------------------
# Order Model
# ---------------------------------------------------------------------------
@dataclass
class LimitOrder:
    id: str
    token_id: str               # Hedera ID to watch (e.g. "0.0.0")
    token_symbol: str           # Human label (e.g. "HBAR")
    condition: str              # "above" or "below"
    target_price: float         # USD trigger price
    action_type: str            # Human label: "swap", "transfer", etc.
    action_string: str          # Serialized action (e.g. "swap:USDC:HBAR:100:exact_in")
    description: str            # Human-readable summary
    created_at: str = ""        # ISO timestamp
    status: str = "active"      # "active", "triggered", "cancelled", "failed"
    triggered_at: Optional[str] = None
    error: Optional[str] = None
    account_id: str = ""        # Hedera ID of the account that owns this order

    def matches(self, current_price: float) -> bool:
        """Check if the current price satisfies the trigger condition."""
        if self.condition == "above":
            return current_price >= self.target_price
        elif self.condition == "below":
            return current_price <= self.target_price
        return False


# ---------------------------------------------------------------------------
# Action Dispatcher
# ---------------------------------------------------------------------------
def _dispatch_action(controller, order: LimitOrder) -> bool:
    """
    Parse the action string and execute the corresponding controller method.
    Returns True on success, False on failure.
    """
    parts = order.action_string.split(":")
    action = parts[0].lower()

    try:
        if action == "swap":
            if len(parts) < 5:
                raise ValueError(f"Swap action needs 5 parts, got {len(parts)}: {order.action_string}")
            from_token = parts[1]
            to_token = parts[2]
            amount = float(parts[3])
            mode = parts[4]
            
            logger.info(f"[LimitOrder {order.id}] Executing swap: {amount} {from_token} → {to_token} ({mode})")
            result = controller.swap(from_token, to_token, amount, mode=mode)
            if result and result.success:
                logger.info(f"[LimitOrder {order.id}] Swap SUCCESS: tx={result.tx_hash}")
                return True
            else:
                err = result.error if result else "No result returned"
                logger.error(f"[LimitOrder {order.id}] Swap FAILED: {err}")
                order.error = str(err)
                return False

        elif action == "transfer":
            if len(parts) < 4:
                raise ValueError(f"Transfer action needs 4 parts, got {len(parts)}: {order.action_string}")
            token = parts[1]
            amount = float(parts[2])
            recipient = parts[3]
            
            logger.info(f"[LimitOrder {order.id}] Executing transfer: {amount} {token} → {recipient}")
            result = controller.transfer(token, amount, recipient)
            if result and result.get("success"):
                logger.info(f"[LimitOrder {order.id}] Transfer SUCCESS")
                return True
            else:
                err = result.get("error", "Unknown error") if result else "No result returned"
                logger.error(f"[LimitOrder {order.id}] Transfer FAILED: {err}")
                order.error = str(err)
                return False

        else:
            logger.error(f"[LimitOrder {order.id}] Unknown action type: {action}")
            order.error = f"Unknown action: {action}"
            return False

    except Exception as e:
        logger.error(f"[LimitOrder {order.id}] Execution error: {e}")
        order.error = str(e)
        return False


# ---------------------------------------------------------------------------
# Interval Parser
# ---------------------------------------------------------------------------
def parse_interval(text: str) -> Optional[int]:
    """
    Parse a human-friendly interval string into seconds.
    
    Supported formats:
        300         → 300 seconds
        5m          → 5 minutes = 300s
        1h          → 1 hour = 3600s
        30s         → 30 seconds
        1d          → 1 day = 86400s
        10 min      → 10 minutes
        2 hours     → 2 hours
    
    Returns seconds, or None if unparseable.
    """
    text = text.strip().lower()
    
    # Pure number → seconds
    try:
        return int(float(text))
    except ValueError:
        pass
    
    # Unit suffixes
    multipliers = {
        "s": 1, "sec": 1, "second": 1, "seconds": 1,
        "m": 60, "min": 60, "minute": 60, "minutes": 60,
        "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
        "d": 86400, "day": 86400, "days": 86400,
    }
    
    # Try "5m", "10min", "1h" etc
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if text.endswith(suffix):
            num_part = text[:-len(suffix)].strip()
            try:
                return int(float(num_part) * mult)
            except ValueError:
                continue
    
    return None


def format_interval(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m" if s == 0 else f"{m}m {s}s"
    elif seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h" if m == 0 else f"{h}h {m}m"
    else:
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        return f"{d}d" if h == 0 else f"{d}d {h}h"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class LimitOrderEngine:
    """
    Core limit order engine.
    
    - Manages a list of orders (persisted to data/orders.json)
    - Runs a background daemon that checks prices at a configurable interval
    - Executes matched orders without user confirmation
    - Only fetches prices for tokens that have active orders (efficient)
    """

    def __init__(self, orders_file: str = None):
        self.orders_file = Path(orders_file) if orders_file else ORDERS_FILE
        self.orders: List[LimitOrder] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._controller = None
        self._poll_interval = self._load_interval()
        self._daemon_enabled = self._load_daemon_enabled()
        self._load()

    # --- Interval Configuration -----------------------------------------------

    @property
    def poll_interval(self) -> int:
        """Current poll interval in seconds."""
        return self._poll_interval

    def set_interval(self, seconds: int) -> int:
        """
        Set the polling interval in seconds.
        Minimum 60s to avoid API rate limits.
        Persists to settings.json.
        """
        if seconds < 60:
            seconds = 60  # Hard floor
        self._poll_interval = seconds
        self._save_interval(seconds)
        logger.info(f"[LimitOrder] Poll interval set to {format_interval(seconds)}")
        return seconds

    def _load_interval(self) -> int:
        """Load poll interval from settings.json, or use default."""
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE) as f:
                    settings = json.load(f)
                return settings.get("limit_order_poll_seconds", DEFAULT_POLL_SECONDS)
        except Exception:
            pass
        return DEFAULT_POLL_SECONDS

    def _save_interval(self, seconds: int):
        """Persist poll interval to settings.json."""
        self._update_settings("limit_order_poll_seconds", seconds)

    def _load_daemon_enabled(self) -> bool:
        """Load daemon state from settings.json."""
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE) as f:
                    settings = json.load(f)
                return settings.get("limit_order_daemon_enabled", False)
        except Exception:
            pass
        return False

    def _save_daemon_enabled(self, enabled: bool):
        """Persist daemon state to settings.json."""
        self._update_settings("limit_order_daemon_enabled", enabled)

    def _update_settings(self, key: str, value):
        """Helper to update a specific key in settings.json."""
        try:
            settings = {}
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE) as f:
                    settings = json.load(f)
            settings[key] = value
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logger.error(f"[LimitOrder] Failed to update settings '{key}': {e}")

    # --- Order Management ---------------------------------------------------

    def add_order(
        self,
        token_symbol: str,
        token_id: str,
        condition: str,
        target_price: float,
        action_type: str,
        action_string: str,
        description: str = "",
        account_id: str = "",
    ) -> str:
        """
        Create a new limit order, optionally scoped to an account.
        Returns the order ID (8-char UUID).
        """
        if condition not in ("above", "below"):
            raise ValueError(f"Condition must be 'above' or 'below', got '{condition}'")
        if target_price <= 0:
            raise ValueError("Target price must be positive")

        order_id = uuid.uuid4().hex[:8]
        order = LimitOrder(
            id=order_id,
            token_id=token_id,
            token_symbol=token_symbol.upper(),
            condition=condition,
            target_price=target_price,
            action_type=action_type,
            action_string=action_string,
            description=description or f"{action_type} when {token_symbol} is {condition} ${target_price:.4f}",
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            account_id=account_id,
        )
        self.orders.append(order)
        self._save()
        logger.info(f"[LimitOrder] Created order {order_id} for {account_id or 'any'}: {order.description}")
        return order_id

    def cancel_order(self, order_id: str, account_id: str = None) -> bool:
        """Cancel an active order by ID (prefix match). If account_id is provided, must match."""
        for order in self.orders:
            if order.id.startswith(order_id) and order.status == "active":
                if account_id and order.account_id and order.account_id != account_id:
                    continue
                order.status = "cancelled"
                self._save()
                logger.info(f"[LimitOrder] Cancelled order {order.id}")
                return True
        return False

    def list_orders(self, status: str = None, account_id: str = None) -> List[LimitOrder]:
        """List orders, optionally filtered by status and account."""
        results = self.orders
        if status:
            results = [o for o in results if o.status == status]
        if account_id:
            results = [o for o in results if not o.account_id or o.account_id == account_id]
        return results

    def get_active_count(self, account_id: str = None) -> int:
        """Number of active orders for the specified account."""
        return len(self.list_orders(status="active", account_id=account_id))

    # --- Monitor Daemon -----------------------------------------------------

    def check_orders(self):
        """
        Public trigger for checking orders.
        Evaluationpass: reload prices and trigger active orders.
        """
        self._check_orders()

    def _check_orders(self):
        """
        Single pass: reload only needed prices, evaluate active orders.
        
        Efficiency: Instead of reloading ALL price data, we only query
        the specific tokens that have active orders for the CURRENT account.
        Orders belonging to other sub-accounts are ignored until the user switches to them.
        """
        if not self._controller:
            return
            
        current_account = getattr(self._controller, "account_id", "")
        
        active = [o for o in self.orders if o.status == "active" and (not o.account_id or o.account_id == current_account)]
        if not active:
            return

        from lib.prices import price_manager
        
        # Collect unique tokens we need prices for
        needed_tokens = set()
        for o in active:
            needed_tokens.add((o.token_id, o.token_symbol))

        # Reload price data (loads from disk cache, very fast)
        price_manager.reload()

        logger.info(f"[LimitOrder] Checking {len(active)} active order(s) across {len(needed_tokens)} token(s)...")

        # Fetch prices only for needed tokens
        prices = {}
        for token_id, token_symbol in needed_tokens:
            try:
                if token_symbol in ("HBAR", "ℏ") or token_id == "0.0.0":
                    prices[token_id] = price_manager.get_hbar_price()
                else:
                    prices[token_id] = price_manager.get_price(token_id)
            except Exception as e:
                logger.debug(f"[LimitOrder] Price fetch failed for {token_symbol}: {e}")

        triggered_any = False
        for order in active:
            current_price = prices.get(order.token_id, 0)
            if current_price <= 0:
                logger.debug(f"[LimitOrder] No price for {order.token_symbol}, skipping.")
                continue

            logger.debug(
                f"[LimitOrder] {order.token_symbol}: ${current_price:.6f} "
                f"(target: {order.condition} ${order.target_price:.6f})"
            )

            if order.matches(current_price):
                logger.info(
                    f"[LimitOrder] *** TRIGGERED *** Order {order.id}: "
                    f"{order.token_symbol} ${current_price:.6f} is {order.condition} ${order.target_price:.6f}"
                )
                success = _dispatch_action(self._controller, order)
                order.triggered_at = time.strftime("%Y-%m-%d %H:%M:%S")
                order.status = "triggered" if success else "failed"
                triggered_any = True

        if triggered_any:
            self._save()

    # --- Daemon Control -----------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Whether the monitor daemon thread is currently alive."""
        return self._monitor_thread is not None and self._monitor_thread.is_alive()

    def start_monitor(self, controller) -> bool:
        """
        Start the background monitoring daemon.

        Returns True when daemon starts, False if it is already running.
        """
        if self.is_running:
            return False

        self._controller = controller
        self._stop_event.clear()
        self._daemon_enabled = True
        self._save_daemon_enabled(True)

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="pacman-limit-orders",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info(f"[LimitOrder] Daemon started (interval={format_interval(self._poll_interval)}).")
        return True

    def stop_monitor(self):
        """Stop the background monitoring daemon gracefully."""
        self._daemon_enabled = False
        self._save_daemon_enabled(False)
        self._stop_event.set()

        t = self._monitor_thread
        if t and t.is_alive():
            t.join(timeout=3)

        self._monitor_thread = None
        logger.info("[LimitOrder] Daemon stopped.")

    def _monitor_loop(self):
        """Background daemon loop for periodic limit-order checks."""
        logger.info("[LimitOrder] Monitor loop active.")
        while not self._stop_event.is_set():
            try:
                self._check_orders()
            except Exception as e:
                logger.error(f"[LimitOrder] Monitor loop error: {e}")

            wait_seconds = max(int(self._poll_interval), 1)
            if self._stop_event.wait(wait_seconds):
                break

        logger.info("[LimitOrder] Monitor loop exited.")

    # --- Persistence --------------------------------------------------------

    def _save(self):
        """Persist all orders to disk."""
        try:
            self.orders_file.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(o) for o in self.orders]
            with open(self.orders_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"[LimitOrder] Failed to save orders: {e}")

    def _load(self):
        """Load orders from disk."""
        try:
            if self.orders_file.exists():
                with open(self.orders_file) as f:
                    data = json.load(f)
                self.orders = [LimitOrder(**d) for d in data]
                logger.info(f"[LimitOrder] Loaded {len(self.orders)} orders ({self.get_active_count()} active).")
        except Exception as e:
            logger.error(f"[LimitOrder] Failed to load orders: {e}")
            self.orders = []
