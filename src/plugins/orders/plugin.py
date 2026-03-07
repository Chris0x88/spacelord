#!/usr/bin/env python3
"""
Limit Order Plugin
==================

Bridges the core LimitOrderEngine with the PluginManager.
"""

from src.core.base_plugin import BasePlugin
from src.logger import logger

class LimitOrderPlugin(BasePlugin):
    def __init__(self, app):
        super().__init__(app, "LimitOrders")
        # Reuse the existing engine instance from app
        self.engine = app.limit_engine
        
    def run_loop(self):
        """Standard work loop called by BasePlugin."""
        # Check if daemon is enabled in settings
        if not self.engine._daemon_enabled:
            import time
            time.sleep(60) # Idle if disabled
            return

        try:
            # Re-implement the check passing the controller
            self.engine._check_orders()
        except Exception as e:
            logger.error(f"[LimitOrders] Pass failed: {e}")
            
        # Sleep for the configured interval
        import time
        for _ in range(self.engine.poll_interval):
            if not self.running:
                break
            time.sleep(1)
            
    def get_status(self) -> dict:
        status = super().get_status()
        status["active_orders"] = self.engine.get_active_count()
        status["interval"] = self.engine.poll_interval
        return status
