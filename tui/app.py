from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding

from tui.screens.dashboard import GiantDashboard

class PacmanTUI(App):
    """The advanced Pacman consolidated dashboard."""

    CSS_PATH = "styles/app.tcss"
    THEME = "textual-dark"

    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_all", "Manual Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Create the giant consolidated dashboard shell."""
        yield Header(show_clock=True)
        yield GiantDashboard()
        yield Footer()

    def action_refresh_all(self) -> None:
        """Trigger global refresh in the dashboard widget."""
        dash = self.query_one(GiantDashboard)
        dash.refresh_all()

    def action_toggle_dark(self) -> None:
        self.theme = "vscode_dark" if self.theme != "vscode_dark" else "textual-light"

if __name__ == "__main__":
    app = PacmanTUI()
    app.run()
