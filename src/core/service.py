#!/usr/bin/env python3
"""
Space Lord Service Manager
======================

Handles native OS persistence (macOS launchd and Linux systemd).
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from src.logger import logger

class C:
    OK = "\033[92m"
    WARN = "\033[93m"
    ERR = "\033[91m"
    BOLD = "\033[1m"
    R = "\033[0m"

ROOT_DIR = Path(__file__).parent.parent.parent
BIN_DIR = ROOT_DIR / ".bin"
BIN_DIR.mkdir(exist_ok=True)

class ServiceManager:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.user = os.getenv("USER") or os.getenv("USERNAME")
        self.label = "com.chris0x88.spacelord"
        self.service_name = "spacelord"
        
    def get_service_path(self) -> Path:
        if self.os_type == "darwin":
            return Path(os.path.expanduser("~/Library/LaunchAgents")) / f"{self.label}.plist"
        elif self.os_type == "linux":
            return Path(os.path.expanduser("~/.config/systemd/user")) / f"{self.service_name}.service"
        return None

    def generate_plist(self) -> str:
        """Generate macOS launchd plist content."""
        python_exe = sys.executable
        main_py = ROOT_DIR / "cli/main.py"
        launch_sh = ROOT_DIR / "launch.sh"
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{launch_sh}</string>
        <string>daemon</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{ROOT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{ROOT_DIR}/data/logs/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>{ROOT_DIR}/data/logs/daemon.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{os.environ.get('PATH', '')}</string>
        <key>SPACELORD_NETWORK</key>
        <string>{os.environ.get('SPACELORD_NETWORK', 'mainnet')}</string>
    </dict>
</dict>
</plist>
"""

    def generate_systemd(self) -> str:
        """Generate Linux systemd service content."""
        launch_sh = ROOT_DIR / "launch.sh"
        return f"""[Unit]
Description=Space Lord Trading Daemon
After=network.target

[Service]
ExecStart={launch_sh} daemon
WorkingDirectory={ROOT_DIR}
Restart=always
RestartSec=10
StandardOutput=append:{ROOT_DIR}/data/logs/daemon.log
StandardError=append:{ROOT_DIR}/data/logs/daemon.log

[Install]
WantedBy=default.target
"""

    def install(self):
        path = self.get_service_path()
        if not path:
            print(f"  {C.ERR}✗{C.R} OS '{self.os_type}' not supported for native services.")
            return False

        path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"  {C.BOLD}🔧 Installing Space Lord Service...{C.R}")
        
        if self.os_type == "darwin":
            content = self.generate_plist()
            path.write_text(content)
            # Load the service
            try:
                subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
                subprocess.run(["launchctl", "load", str(path)], check=True)
                print(f"  {C.OK}✓{C.R} macOS LaunchAgent installed and loaded.")
                print(f"  {C.BOLD}To monitor:{C.R} tail -f data/logs/daemon.log")
            except Exception as e:
                print(f"  {C.ERR}✗{C.R} Failed to load macOS service: {e}")
                return False
                
        elif self.os_type == "linux":
            content = self.generate_systemd()
            path.write_text(content)
            try:
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
                subprocess.run(["systemctl", "--user", "enable", self.service_name], check=True)
                subprocess.run(["systemctl", "--user", "restart", self.service_name], check=True)
                print(f"  {C.OK}✓{C.R} Linux systemd service installed and started.")
            except Exception as e:
                print(f"  {C.ERR}✗{C.R} Failed to start Linux service: {e}")
                return False
                
        return True

    def uninstall(self):
        path = self.get_service_path()
        if not path or not path.exists():
            print(f"  {C.WARN}⚠{C.R} Service file not found.")
            return False

        print(f"  {C.BOLD}🗑 Uninstalling Space Lord Service...{C.R}")
        
        if self.os_type == "darwin":
            subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
            path.unlink()
            print(f"  {C.OK}✓{C.R} macOS LaunchAgent removed.")
            
        elif self.os_type == "linux":
            subprocess.run(["systemctl", "--user", "stop", self.service_name], capture_output=True)
            subprocess.run(["systemctl", "--user", "disable", self.service_name], capture_output=True)
            path.unlink()
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            print(f"  {C.OK}✓{C.R} Linux systemd service removed.")
            
        return True

    def status(self):
        if self.os_type == "darwin":
            res = subprocess.run(["launchctl", "list", self.label], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"  {C.OK}● Service Running (launchd){C.R}")
                print(res.stdout)
            else:
                print(f"  {C.ERR}○ Service Inactive{C.R}")
        elif self.os_type == "linux":
            res = subprocess.run(["systemctl", "--user", "status", self.service_name], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"  {C.OK}● Service Running (systemd){C.R}")
            else:
                print(f"  {C.ERR}○ Service Inactive{C.R}")
            print(res.stdout)
