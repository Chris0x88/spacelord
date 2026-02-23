import asyncio
from textual.app import ComposeResult
from textual.containers import Grid, Vertical, Horizontal, VerticalScroll, Container
from textual.widgets import Label, Button, LoadingIndicator, DataTable
from textual.widget import Widget
from textual.reactive import reactive
from textual import work
from rich.text import Text

from src.controller import PacmanController
from lib.prices import price_manager
from cli.pacman_filter import ui_filter
from scripts import refresh_data


class StatBox(Vertical):
    """A premium widget to display a single stat."""
    
    value_text = reactive("---")
    
    def __init__(self, title: str, id: str | None = None) -> None:
        super().__init__(id=id)
        self.title_label = title

    def compose(self) -> ComposeResult:
        yield Label(self.title_label, classes="stat-title")
        yield LoadingIndicator()

    def update_value(self, new_value: str, color_class: str = "") -> None:
        self.value_text = new_value
        loading = self.query(LoadingIndicator)
        if loading:
            loading.first().remove()
        
        val_widgets = self.query(".stat-value")
        if val_widgets:
            lbl = val_widgets.first()
            lbl.update(new_value)
            if color_class:
                lbl.add_class(color_class)
        else:
            lbl = Label(new_value, classes="stat-value")
            if color_class:
                lbl.add_class(color_class)
            self.mount(lbl)


class GiantDashboard(VerticalScroll):
    """A single-page consolidated dashboard view."""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-container"):
            yield Label("P A C T U I   G I A N T   D A S H B O A R D", id="dashboard-title")
            
            # --- Top Tier: Global Stats ---
            with Grid(id="stats-grid"):
                yield StatBox("Portfolio Value", id="stat-portfolio")
                yield StatBox("Active Orders", id="stat-orders")
                yield StatBox("Network Status", id="stat-network")
                yield StatBox("Daemon Engine", id="stat-daemon")

            # --- Middle Tier: Portfolio & Orders Split ---
            with Horizontal(id="data-layers"):
                with Vertical(classes="data-panel", id="panel-wallet"):
                    yield Label("PORTFOLIO ASSETS", classes="panel-header")
                    yield DataTable(id="dashboard-wallet-table")
                
                with Vertical(classes="data-panel", id="panel-orders"):
                    yield Label("ACTIVE LIMIT ORDERS", classes="panel-header")
                    yield DataTable(id="dashboard-orders-table")

            # --- Bottom Tier: Liquidity Positions ---
            with Vertical(classes="data-panel", id="panel-liquidity"):
                yield Label("V2 LIQUIDITY POSITIONS (NFTS)", classes="panel-header")
                yield DataTable(id="dashboard-liquidity-table")

            with Horizontal(id="action-bar"):
                yield Button("↻ Refresh All Data", id="btn-refresh", variant="primary")
                yield Label("Auto-refreshing every 60s", id="refresh-hint")

    def on_mount(self) -> None:
        """Initialize tables and start data flow."""
        # Setup Tables
        wallet_table = self.query_one("#dashboard-wallet-table", DataTable)
        wallet_table.add_columns("Asset", "Balance", "Value", "Price")
        wallet_table.cursor_type = "row"

        orders_table = self.query_one("#dashboard-orders-table", DataTable)
        orders_table.add_columns("ID", "Type", "Asset", "Trigger", "Mark Price", "Size", "Status")
        orders_table.cursor_type = "row"

        lp_table = self.query_one("#dashboard-liquidity-table", DataTable)
        lp_table.add_columns("ID", "Pair", "Fee", "Range", "Status", "Holdings")
        lp_table.cursor_type = "row"

        try:
            self.pacman = PacmanController()
            self.refresh_all()
            # Start auto-refresh timer
            self.set_interval(60, self.refresh_all)
        except Exception as e:
            self.app.notify(f"Dashboard Init Error: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh":
            self.refresh_all()

    def refresh_all(self) -> None:
        """Triggers a full async refresh of all data sources."""
        btn = self.query("#btn-refresh")
        if btn: btn.first().disabled = True
        self._fetch_all_data_worker()

    @work(thread=True)
    def _fetch_all_data_worker(self) -> None:
        """
        Giant data fetcher with high resilience. 
        Each section is wrapped to ensure total failure of one doesn't kill the dashboard.
        """
        data = {
            "portfolio_usd": 0.0,
            "order_count": 0,
            "network": "---",
            "daemon": "---",
            "daemon_active": False,
            "wallet_rows": [],
            "order_rows": [],
            "lp_rows": []
        }

        # 1. Base network info
        try:
            data["network"] = self.pacman.executor.network.upper()
        except: pass

        # 2. Daemon Status
        try:
            # Use is_running property from LimitOrderEngine
            daemon_running = self.pacman.limit_engine.is_running
            data["daemon"] = "● ACTIVE" if daemon_running else "○ STOPPED"
            data["daemon_active"] = daemon_running
        except: pass

        # 3. Prices & Balances (Portfolio)
        try:
            refresh_data.refresh() # Fetch freshest network API prices
            price_manager.reload()
            all_balances = self.pacman.get_balances()
            # Native HBAR
            try:
                hbar_bal = self.pacman.executor.client.w3.eth.get_balance(self.pacman.executor.eoa)
                hbar_readable = hbar_bal / (10**18)
                hbar_price = price_manager.get_hbar_price()
                hbar_usd = hbar_readable * hbar_price
                data["portfolio_usd"] += hbar_usd
                data["wallet_rows"].append((
                    Text("HBAR", style="bold cyan"),
                    Text(f"{hbar_readable:.8f}", style="bold green" if hbar_readable > 0 else ""),
                    f"${hbar_usd:.2f}",
                    f"${hbar_price:.6f}"
                ))
            except Exception as e:
                self.app.call_from_thread(self.app.notify, f"HBAR Fetch Error: {e}", severity="warning")

            # Tokens
            tokens_data = ui_filter.get_token_metadata()
            for sym, bal in all_balances.items():
                if sym == "HBAR": continue
                try:
                    meta = tokens_data.get(sym) or next((m for m in tokens_data.values() if m.get("symbol") == sym), None)
                    if not meta or ui_filter.is_blacklisted(meta.get("id", "")): continue
                    
                    price = price_manager.get_price(meta.get("id"))
                    usd_val = bal * price
                    data["portfolio_usd"] += usd_val
                    
                    data["wallet_rows"].append((
                        Text(sym, style="bold cyan"),
                        Text(f"{bal:.8f}", style="bold green" if bal > 0 else ""),
                        f"${usd_val:.2f}",
                        f"${price:.6f}"
                    ))
                except: continue
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Price/Wallet Error: {e}", severity="error")

        # 4. Orders
        try:
            orders = self.pacman.limit_engine.list_orders()
            active_orders = [o for o in orders if o.status == "active"]
            data["order_count"] = len(active_orders)
            for o in active_orders:
                o_id = o.id[:8]
                o_type = "BUY" if o.condition == "below" else "SELL"
                asset = o.token_symbol
                cond = f"{'<=' if o_type == 'BUY' else '>='} ${o.target_price:.6f}"
                
                # Fetch mark price
                mark = price_manager.get_price(o.token_id)
                mark_str = f"${mark:.6f}" if mark > 0 else "—"

                # Extract size
                parts = o.action_string.split(":")
                size = "—"
                if parts[0] == "swap" and len(parts) >= 4:
                    amt = parts[3]
                    size = f"{amt} {parts[1]}"
                elif parts[0] == "transfer" and len(parts) >= 3:
                    size = f"{parts[2]} {parts[1]}"
                
                data["order_rows"].append((
                    o_id,
                    Text(o_type, style="bold green" if o_type == "BUY" else "bold yellow"),
                    asset,
                    cond,
                    mark_str,
                    size,
                    Text("ACTIVE", style="bold cyan")
                ))
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Orders Fetch Error: {e}", severity="error")

        # 5. Liquidity Positions
        try:
            import math
            positions = self.pacman.get_liquidity_positions()
            tokens_data = ui_filter.get_token_metadata()

            def evm_to_id(addr):
                return f"0.0.{int(addr.lower(), 16)}"

            def get_sym(tid):
                if tid == "0.0.1456986": return "HBAR", 8
                meta = next((m for m in tokens_data.values() if m.get("id") == tid), None)
                if meta:
                    return meta.get("symbol", tid), meta.get("decimals", 8)
                return tid, 8

            for pos in positions:
                t0_sym, dec0 = get_sym(evm_to_id(pos['token0']))
                t1_sym, dec1 = get_sym(evm_to_id(pos['token1']))
                pair = f"{t0_sym}/{t1_sym}"
                fee_pct = f"{pos['fee'] / 10000:.2f}%"
                
                tick_lower = pos.get('tick_lower', 0)
                tick_upper = pos.get('tick_upper', 0)
                tick_current = pos.get('tick_current', tick_lower)
                in_range = tick_lower <= tick_current < tick_upper
                status = Text("IN RANGE", style="bold green") if in_range else Text("OUT OF RANGE", style="bold yellow")
                
                # Estimated Holdings Logic (V3)
                liq = pos.get('liquidity', 0)
                est_t0, est_t1 = 0.0, 0.0
                try:
                    sqp = math.sqrt(1.0001 ** tick_current)
                    sqpa = math.sqrt(1.0001 ** tick_lower)
                    sqpb = math.sqrt(1.0001 ** tick_upper)
                    if sqpa > sqpb: sqpa, sqpb = sqpb, sqpa
                    if tick_current < tick_lower:
                        est_t0 = liq * (1.0/sqpa - 1.0/sqpb) / (10**dec0)
                    elif tick_current >= tick_upper:
                        est_t1 = liq * (sqpb - sqpa) / (10**dec1)
                    else:
                        est_t0 = liq * (1.0/sqp - 1.0/sqpb) / (10**dec0)
                        est_t1 = liq * (sqp - sqpa) / (10**dec1)
                except: pass
                
                h_parts = []
                if est_t0 > 0: h_parts.append(f"{est_t0:.4f} {t0_sym}")
                if est_t1 > 0: h_parts.append(f"{est_t1:.4f} {t1_sym}")
                holdings = " + ".join(h_parts) or "0.00"

                data["lp_rows"].append((
                    str(pos['id']),
                    pair,
                    fee_pct,
                    f"{tick_lower} : {tick_upper}",
                    status,
                    holdings
                ))
            if not positions:
                self.app.call_from_thread(self.app.notify, "No Liquidity Positions found for this account.", severity="warning")
            else:
                self.app.call_from_thread(self.app.notify, f"Fetched {len(positions)} LP positions.", severity="information")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"LP Fetch Error: {e}", severity="error")

        # Final Update
        self.app.call_from_thread(self._update_ui, data)

    def _update_ui(self, data: dict) -> None:
        """Apply the fetched data to the UI components."""
        # Stats
        self.query_one("#stat-portfolio", StatBox).update_value(f"${data['portfolio_usd']:,.2f}", "color-positive")
        self.query_one("#stat-orders", StatBox).update_value(str(data["order_count"]), "color-positive" if data["order_count"] > 0 else "")
        self.query_one("#stat-network", StatBox).update_value(data["network"], "color-accent")
        self.query_one("#stat-daemon", StatBox).update_value(data["daemon"], "color-positive" if data["daemon_active"] else "color-warning")

        # Wallet Table
        w_table = self.query_one("#dashboard-wallet-table", DataTable)
        w_table.clear()
        w_table.add_rows(data["wallet_rows"])

        # Orders Table
        o_table = self.query_one("#dashboard-orders-table", DataTable)
        o_table.clear()
        o_table.add_rows(data["order_rows"])

        # Liquidity Table
        lp_table = self.query_one("#dashboard-liquidity-table", DataTable)
        lp_table.clear()
        lp_table.add_rows(data["lp_rows"])

        # Finish up
        btn = self.query("#btn-refresh")
        if btn: btn.first().disabled = False
        self.app.notify("Dashboard refresh complete.", severity="information", timeout=2)

