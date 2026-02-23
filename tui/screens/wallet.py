from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import DataTable, Label, Button
from textual import work
from rich.text import Text

from src.controller import PacmanController
from lib.prices import price_manager
from cli.pacman_filter import ui_filter

class WalletPane(VerticalScroll):
    """Screen displaying token balances and prices."""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="wallet-container"):
            yield Label("P O R T F O L I O   W A L L E T", id="wallet-title", classes="pane-title")
            yield DataTable(id="wallet-table")
            with Horizontal(id="action-bar"):
                yield Button("↻ Refresh Data", id="btn-refresh-wallet", variant="primary")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Asset", "Balance", "USD Value", "Price", "Action")
        table.cursor_type = "row"
        
        try:
            self.pacman = PacmanController()
            self.refresh_wallet()
        except Exception as e:
            self.app.notify(f"Initialization Error: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-wallet":
            self.refresh_wallet()

    def refresh_wallet(self) -> None:
        refresh_btn = self.query("#btn-refresh-wallet")
        if refresh_btn:
            refresh_btn.first().disabled = True
            
        table = self.query_one(DataTable)
        table.clear()
            
        self._fetch_wallet_data()

    @work(thread=True)
    def _fetch_wallet_data(self) -> None:
        try:
            price_manager.reload()
            all_balances = self.pacman.get_balances()
            hbar_bal = self.pacman.executor.client.w3.eth.get_balance(self.pacman.executor.eoa)
            hbar_readable = hbar_bal / (10**18)
            hbar_price = price_manager.get_hbar_price()
            hbar_usd = hbar_readable * hbar_price

            tokens_data = ui_filter.get_token_metadata()
            
            rows = []
            
            # Format HBAR
            bal_h = Text(f"{hbar_readable:.6f}", style="bold green" if hbar_readable > 0 else "")
            usd_h = Text(f"${hbar_usd:.2f}", style="bold green" if hbar_usd > 0 else "")
            rows.append((Text("HBAR", style="bold cyan"), bal_h, usd_h, f"${hbar_price:.4f}", "Native"))

            # Add other tokens
            for sym, bal in all_balances.items():
                if sym == "HBAR": continue
                meta = tokens_data.get(sym)
                if not meta:
                    for k, m in tokens_data.items():
                        if m.get("symbol") == sym:
                            meta = m
                            break
                if not meta: continue
                token_id = meta.get("id")
                if not token_id or ui_filter.is_blacklisted(token_id): continue
                if token_id == "0.0.1456986": continue
                
                price = price_manager.get_price(token_id)
                usd_val = bal * price
                
                bal_t = Text(f"{bal:.6f}", style="bold green" if bal > 0 else "")
                usd_t = Text(f"${usd_val:.2f}", style="bold green" if usd_val > 0 else "")
                sym_t = Text(sym, style="bold cyan")
                
                rows.append((sym_t, bal_t, usd_t, f"${price:.4f}", f"ID: {token_id}"))

            # Update the table
            self.app.call_from_thread(self._update_table, rows)
            
        except Exception as e:
            self.app.call_from_thread(self._handle_error, str(e))

    def _update_table(self, rows: list) -> None:
        """Update the DataTable."""
        table = self.query_one(DataTable)
        table.clear()
        for row in rows:
            table.add_row(*row)
            
        refresh_btn = self.query("#btn-refresh-wallet")
        if refresh_btn:
            refresh_btn.first().disabled = False

    def _handle_error(self, err: str) -> None:
        self.app.notify(f"Failed to fetch wallet balances: {err}", severity="error", timeout=6)
        refresh_btn = self.query("#btn-refresh-wallet")
        if refresh_btn:
            refresh_btn.first().disabled = False
