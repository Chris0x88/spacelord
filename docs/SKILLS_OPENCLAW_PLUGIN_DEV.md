# OpenClaw Skills: Pacman Plugin Development

This guide is designed for AI agents (OpenClaw) to build and deploy native plugins for the Pacman trading system.

## 1. Plugin Architecture
All background logic must inherit from `src.core.base_plugin.BasePlugin`. This ensures the daemon can manage the lifecycle, monitor health, and report status to the dashboard.

### Standard Lifecycle
- `__init__(app, name)`: Initialize state. Use `app` (PacmanController) to access the router, balances, and executor.
- `run_loop()`: The main logic implementation. This method is called repeatedly by the thread.
- `get_status()`: (Optional) Return critical stats for the dashboard. Keep this **non-blocking** (use cached data).

## 2. Plugin Template
Copy and paste this template into a new file: `src/plugins/<your_plugin_name>/bot.py`.

```python
from src.core.base_plugin import BasePlugin
from src.logger import logger
import time

class OpenClawBot(BasePlugin):
    def __init__(self, app):
        # Name must be unique and alphanumeric
        super().__init__(app, "OpenClawAlpha")
        self.check_count = 0
        self.last_observation = None

    def run_loop(self):
        """
        Main operation loop.
        The BasePlugin parent handles the while loop and error catching.
        """
        logger.info(f"[{self.plugin_name}] Evaluating market...")
        
        # Access application logic
        # Example: portfolio = self.app.get_balances()
        
        # Perform your logic here
        self.check_count += 1
        self.last_observation = time.time()
        
        # CRITICAL: Always sleep to avoid CPU pinning
        # Recommendation: Use small sleep increments for responsive shutdown
        for _ in range(300): # 5-minute interval
            if not self.running:
                break
            time.sleep(1)

    def get_status(self) -> dict:
        """Add custom metrics to the dashboard."""
        status = super().get_status()
        status.update({
            "checks": self.check_count,
            "last_obs": self.last_observation
        })
        return status
```

## 3. Best Practices
1.  **No Blocking**: Do not perform long network requests in `get_status`.
2.  **Explicit Logging**: Use `from src.logger import logger`. Tag logs with your plugin name.
3.  **State Persistence**: Store data in `data/plugins/<name>.json`.
4.  **Auto-Discovery**: The daemon automatically scans `src/plugins/` subfolders. No need to update core files.

## 4. Testing Your Plugin
1. Drop your code into `src/plugins/my_new_bot/bot.py`.
2. Restart the daemon: `./launch.sh daemon`.
3. Verify it appears in `./launch.sh status-service`.
