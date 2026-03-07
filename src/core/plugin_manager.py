#!/usr/bin/env python3
"""
Plugin Manager
==============

Dynamically discovers and manages background robots/daemons.
"""

import os
import importlib
import inspect
from pathlib import Path
from src.core.base_plugin import BasePlugin
from src.logger import logger

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins = {} # name -> instance
        self.plugins_dir = Path(__file__).parent.parent / "plugins"
        
    def discover_and_load(self):
        """Scan src/plugins/ for BasePlugin subclasses."""
        if not self.plugins_dir.exists():
            return
            
        logger.info("[PluginManager] Scanning for plugins...")
        
        # Iterate through subdirectories
        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                # Potential plugin package
                plugin_name = item.name
                if plugin_name.startswith("__"):
                    continue
                    
                # Look for bot.py, engine.py or similar in the folder
                # We'll try to find any module that defines a BasePlugin subclass
                self._load_from_directory(item)

    def _load_from_directory(self, directory: Path):
        """Search a directory for subclasses of BasePlugin."""
        for file in directory.glob("*.py"):
            if file.name.startswith("__"):
                continue
                
            module_path = f"src.plugins.{directory.name}.{file.stem}"
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        # Instantiate the plugin
                        instance = obj(self.app)
                        if instance.plugin_name not in self.plugins:
                            self.plugins[instance.plugin_name] = instance
                            logger.info(f"[PluginManager] Registered: {instance.plugin_name}")
            except Exception as e:
                logger.error(f"[PluginManager] Failed to load {module_path}: {e}")

    def start_all(self):
        """Start all registered plugins."""
        for p in self.plugins.values():
            p.start_plugin()

    def stop_all(self):
        """Stop all plugins."""
        for p in self.plugins.values():
            p.stop_plugin()

    def get_all_statuses(self) -> list:
        """Get health data for all plugins."""
        return [p.get_status() for p in self.plugins.values()]
