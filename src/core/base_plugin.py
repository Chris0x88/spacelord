#!/usr/bin/env python3
"""
Base Plugin Interface
=====================

Standard base class for all background daemons, bots, and scanners.
Ensures a consistent lifecycle and health monitoring.
"""

import threading
import time
from abc import ABC, abstractmethod
from src.logger import logger

class BasePlugin(ABC, threading.Thread):
    def __init__(self, app, name: str):
        super().__init__(name=name, daemon=True)
        self.app = app
        self.plugin_name = name
        self.running = False
        self._last_heartbeat = 0
        self._error_count = 0
        
    def start_plugin(self):
        """Standard wrapper to start the thread."""
        if not self.running:
            self.running = True
            self.start()
            logger.info(f"[Plugin:{self.plugin_name}] Started.")

    def stop_plugin(self):
        """Signal the thread to stop."""
        self.running = False
        logger.info(f"[Plugin:{self.plugin_name}] Stopping...")

    @abstractmethod
    def run_loop(self):
        """The actual work loop — implemented by subclasses."""
        pass

    def run(self):
        """Threading entry point."""
        while self.running:
            try:
                self._last_heartbeat = time.time()
                self.run_loop()
            except Exception as e:
                self._error_count += 1
                logger.error(f"[Plugin:{self.plugin_name}] Error in loop: {e}")
                # Exponential backoff on errors
                time.sleep(min(300, 2 ** self._error_count))
            
    def get_status(self) -> dict:
        """Return health and stats for this plugin."""
        return {
            "name": self.plugin_name,
            "running": self.running and self.is_alive(),
            "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._last_heartbeat)),
            "errors": self._error_count
        }
