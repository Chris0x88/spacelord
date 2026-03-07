#!/usr/bin/env python3
"""
Pacman Secure API
=================

Lightweight REST API providing authenticated access to the daemon state.
Strictly binds to 127.0.0.1 for local security.
"""

import os
import threading
import time
import json
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from pathlib import Path
from src.logger import logger

app_flask = Flask(__name__)
CORS(app_flask) # Enable CORS for the local dashboard

# Shared context
pacman_app = None
api_secret = os.getenv("PACMAN_API_SECRET")

def require_auth(f):
    """Decorator to enforce shared secret authentication."""
    def decorated_function(*args, **kwargs):
        header_secret = request.headers.get("X-Pacman-Secret")
        if not api_secret or header_secret != api_secret:
            logger.warning(f"Unauthorized API access attempt from {request.remote_addr}")
            abort(401, description="Unauthorized")
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app_flask.route("/status", methods=["GET"])
@require_auth
def get_status():
    """Return high-level daemon and system status."""
    status_file = Path("data/status.json")
    if status_file.exists():
        with open(status_file, "r") as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify({"error": "No status found"}), 404

@app_flask.route("/plugins", methods=["GET"])
@require_auth
def get_plugins():
    """Return detailed health for all active plugins."""
    # Assuming pm is accessible globally or through the pacman_app
    # For now, we'll read from its status reporting mechanism
    status_file = Path("data/status.json")
    if status_file.exists():
        with open(status_file, "r") as f:
            data = json.load(f)
        return jsonify(data.get("plugins", []))
    return jsonify([])

@app_flask.route("/portfolio", methods=["GET"])
@require_auth
def get_portfolio():
    """Proxy to the controller's balance/portfolio state."""
    if not pacman_app:
        return jsonify({"error": "Controller not initialized"}), 500
    
    try:
        # We try to get the active plugin's cached state first
        status_file = Path("data/status.json")
        if status_file.exists():
             with open(status_file, "r") as f:
                data = json.load(f)
             for p in data.get("plugins", []):
                 if p.get("name") == "PowerLaw" and p.get("portfolio"):
                     return jsonify(p["portfolio"])
        
        # Fallback to direct check if needed (blocking)
        balances = pacman_app.get_balances()
        return jsonify(balances)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_server(app, port=8088):
    """Entry point for the API thread."""
    global pacman_app
    pacman_app = app
    
    if not api_secret:
        logger.error("PACMAN_API_SECRET not set in .env. API starting in insecure mode (LOCAL ONLY).")
    
    logger.info(f"🚀 Pacman API starting on http://127.0.0.1:{port}")
    # Disable flask banners for cleaner logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app_flask.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

def start_api(app, port=8088):
    """Start the API server in a separate thread."""
    api_thread = threading.Thread(target=run_server, args=(app, port), daemon=True)
    api_thread.start()
    return api_thread
