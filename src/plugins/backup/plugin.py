#!/usr/bin/env python3
"""
Backup Plugin
=============

Periodically snapshots the data/ directory to a zip file in backups/.
Implements a retention policy to keep it efficient.
"""

import os
import shutil
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from src.core.base_plugin import BasePlugin
from src.logger import logger

class BackupPlugin(BasePlugin):
    def __init__(self, app):
        super().__init__(app, "BackupService")
        self.root_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.data_dir = self.root_dir / "data"
        self.backup_dir = self.root_dir / "backups"
        self.interval_seconds = 86400  # 24 hours
        self.last_backup = None
        self.retention_days = 30
        
    def run_loop(self):
        """Perform backup once a day."""
        try:
            self._ensure_setup()
            self._create_backup()
            self._cleanup_old_backups()
        except Exception as e:
            logger.error(f"[{self.plugin_name}] Backup failed: {e}")
            self._error_count += 1
            
        # Sleep for 24 hours, but in segments for responsive shutdown
        for _ in range(self.interval_seconds):
            if not self.running:
                break
            time.sleep(1)

    def _ensure_setup(self):
        """Setup directory and .gitignore."""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
            
        gitignore = self.root_dir / ".gitignore"
        if gitignore.exists():
            with open(gitignore, "r") as f:
                content = f.read()
            if "backups/" not in content:
                with open(gitignore, "a") as f:
                    f.write("\n# Backups\nbackups/\n")

    def _create_backup(self):
        """Zip the data directory."""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"pacman_backup_{timestamp}.zip"
        dest_path = self.backup_dir / filename
        
        logger.info(f"[{self.plugin_name}] Creating snapshot: {filename}")
        
        with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.data_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Store relative to data_dir
                    arcname = file_path.relative_to(self.data_dir)
                    zipf.write(file_path, arcname)
                    
        self.last_backup = now.isoformat()
        logger.info(f"[{self.plugin_name}] Snapshot complete.")

    def _cleanup_old_backups(self):
        """Remove backups older than retention policy."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        for file in self.backup_dir.glob("pacman_backup_*.zip"):
            # Extract date from filename: pacman_backup_YYYYMMDD_HHMMSS.zip
            try:
                date_str = file.name.split("_")[2] # YYYYMMDD
                file_date = datetime.strptime(date_str, "%Y%m%d")
                if file_date < cutoff:
                    file.unlink()
                    removed_count += 1
            except Exception:
                continue
                
        if removed_count > 0:
            logger.info(f"[{self.plugin_name}] Purged {removed_count} old backup(s).")

    def get_status(self) -> dict:
        status = super().get_status()
        status.update({
            "last_backup": self.last_backup,
            "backup_count": len(list(self.backup_dir.glob("*.zip"))) if self.backup_dir.exists() else 0
        })
        return status
