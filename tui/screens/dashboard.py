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
            "order_rows": []
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

        # Finish up
        btn = self.query("#btn-refresh")
        if btn: btn.first().disabled = False
        self.app.notify("Dashboard refresh complete.", severity="information", timeout=2)

