from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import DataTable, Button, Label
from textual import work
from rich.text import Text

from src.controller import PacmanController

class OrdersPane(VerticalScroll):
    """Screen displaying active limit orders."""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="orders-container"):
            yield Label("A C T I V E   O R D E R S", id="orders-title", classes="pane-title")
            yield DataTable(id="orders-table")
            with Horizontal(id="action-bar"):
                yield Button("↻ Refresh Data", id="btn-refresh-orders", variant="primary")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Type", "Asset", "Price Trigger", "Status")
        table.cursor_type = "row"
        
        try:
            self.pacman = PacmanController()
            self.refresh_orders()
        except Exception as e:
            self.app.notify(f"Initialization Error: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-orders":
            self.refresh_orders()

    def refresh_orders(self) -> None:
        refresh_btn = self.query("#btn-refresh-orders")
        if refresh_btn:
            refresh_btn.first().disabled = True
            
        table = self.query_one(DataTable)
        table.clear()
        
        self._fetch_orders_data()

    @work(thread=True)
    def _fetch_orders_data(self) -> None:
        try:
            orders = self.pacman.limit_engine().get_orders()
            rows = []
            
            for o in orders:
                if o.get("status") != "active":
                    continue
                o_id = o.get("id", "Unknown")[:8]
                o_type = "BUY" if o.get("is_buy") else "SELL"
                asset = o.get("target_token_symbol", "Unknown")
                
                if o_type == "BUY":
                    cond = f"<= ${o.get('target_price', 0):.4f}"
                else:
                    cond = f">= ${o.get('target_price', 0):.4f}"
                    
                status = o.get("status", "Unknown").upper()
                
                # Apply rich formatting to status and type
                type_styled = Text(o_type, style="bold green" if o_type == "BUY" else "bold red")
                status_styled = Text(status, style="bold cyan")
                
                rows.append((o_id, type_styled, asset, cond, status_styled))

            self.app.call_from_thread(self._update_table, rows)
            
        except Exception as e:
            self.app.call_from_thread(self._handle_error, str(e))

    def _update_table(self, rows: list) -> None:
        """Update the DataTable."""
        table = self.query_one(DataTable)
        table.clear()
        for row in rows:
            table.add_row(*row)
            
        refresh_btn = self.query("#btn-refresh-orders")
        if refresh_btn:
            refresh_btn.first().disabled = False

    def _handle_error(self, err: str) -> None:
        self.app.notify(f"Failed to fetch orders: {err}", severity="error", timeout=6)
        refresh_btn = self.query("#btn-refresh-orders")
        if refresh_btn:
            refresh_btn.first().disabled = False
