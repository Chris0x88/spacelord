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
    """Decorator to enforce shared secret authentication. 
    Accepts via X-Pacman-Secret header OR ?secret= query param (for images/links)."""
    def decorated_function(*args, **kwargs):
        header_secret = request.headers.get("X-Pacman-Secret")
        query_secret = request.args.get("secret")
        provided = header_secret or query_secret
        
        if not api_secret or provided != api_secret:
            logger.warning(f"Unauthorized API access attempt from {request.remote_addr}")
            abort(401, description="Unauthorized")
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app_flask.route("/status", methods=["GET"])
@require_auth
def get_status():
    """Return high-level daemon and system status directly from memory."""
    if not pacman_app or not hasattr(pacman_app, 'pm'):
         return jsonify({"error": "Daemon initializing..."}), 503
         
    import time
    
    # Calculate uptime (from app start time if available)
    uptime = 0
    if hasattr(pacman_app, 'start_time'):
        uptime = int(time.time() - pacman_app.start_time)
        
    return jsonify({
        "pid": os.getpid(),
        "uptime_sec": uptime,
        "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plugins": pacman_app.pm.get_all_statuses()
    })

@app_flask.route("/plugins", methods=["GET"])
@require_auth
def get_plugins():
    """Return health for ALL discovered plugins directly from memory."""
    if not pacman_app or not hasattr(pacman_app, 'pm'):
        return jsonify([])
    
    # Get live status from the PluginManager instance
    return jsonify(pacman_app.pm.get_all_statuses())

@app_flask.route("/logs", methods=["GET"])
@require_auth
def get_logs():
    """Return the last 50 lines of the system log."""
    log_path = Path("logs/pacman.log")
    if not log_path.exists():
        return jsonify([])
    
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
            return jsonify(lines[-50:])
    except Exception as e:
        return jsonify([f"Error reading logs: {e}"])

@app_flask.route("/portfolio", methods=["GET"])
@require_auth
def get_portfolio():
    """Proxy to the cached bot portfolio state."""
    if not pacman_app:
        return jsonify({"error": "Controller not initialized"}), 500
    
    try:
        # Get live portfolio from the PowerLaw plugin instance if available
        if hasattr(pacman_app, 'pm'):
            pl_plugin = pacman_app.pm.plugins.get("PowerLaw")
            if pl_plugin and pl_plugin._last_portfolio:
                return jsonify(pl_plugin._last_portfolio)
        
        # Fallback to direct check if needed (blocking)
        balances = pacman_app.get_balances(token_highlights=["WBTC[HTS]", "USDC", "HBAR"])
        return jsonify(balances)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_flask.route("/holdings", methods=["GET"])
@require_auth
def get_holdings():
    """Returns the full dictionary of all non-zero wallet balances with USD values (Aggregated)."""
    if not pacman_app:
        return jsonify({"error": "Controller not initialized"}), 500
    
    try:
        raw_balances = pacman_app.get_aggregated_balances()
        holdings = []
        
        # Filter out NLP aliases (e.g. "DOLLAR", "BITCOIN") by checking standard tokens
        # Or just return all and let frontend decide, but backend is cleaner
        ignore_aliases = {"BITCOIN", "BTC", "DOLLAR", "USD", "ETHEREUM", "ETH", "HTS-WBTC", "HTS-WETH"}
        
        # Preload tokens data for ID resolution
        import json
        tokens_data = {}
        try:
            with open("data/tokens.json") as f:
                tokens_data = json.load(f)
        except: pass
        
        total_portfolio_usd = 0.0
        for sym, bal in raw_balances.items():
            if sym in ignore_aliases:
                continue
                
            token_id = sym
            if sym in tokens_data:
                token_id = tokens_data[sym].get("id", sym)
            
            raw_price = pacman_app.router.price_manager.get_price(token_id)
            price_usd = 1.0 if sym in ("USDC", "USD") else (float(raw_price) if raw_price else 0.0)
            val_usd = bal * price_usd
            total_portfolio_usd += val_usd
            
            holdings.append({
                "symbol": sym,
                "balance": bal,
                "price_usd": price_usd,
                "value_usd": val_usd
            })
            
        # Sort by value descending
        holdings.sort(key=lambda x: x["value_usd"], reverse=True)
            
        return jsonify({
            "holdings": holdings,
            "total_usd": total_portfolio_usd
        })
    except Exception as e:
        logger.error(f"API Error get_holdings: {e}")
        return jsonify({"error": str(e)}), 500

@app_flask.route("/accounts", methods=["GET"])
@require_auth
def get_accounts():
    """Returns segregated balances for all accounts (Parent, Robot)."""
    if not pacman_app:
        return jsonify({"error": "Controller not initialized"}), 500
    try:
        all_balances = pacman_app.get_all_account_balances()
        return jsonify(all_balances)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_flask.route("/history", methods=["GET"])
@require_auth
def get_history():
    """Return the recent execution history ledger."""
    if not pacman_app:
        return jsonify({"error": "Controller not initialized"}), 500
    try:
        limit = int(request.args.get("limit", 20))
        history = pacman_app.executor.get_execution_history(limit=limit)
        
        # Inject system logic events from bots (like PowerLaw)
        import json
        from pathlib import Path
        try:
            bot_state = Path("data/robot_state.json")
            if bot_state.exists():
                with open(bot_state) as f:
                    data = json.load(f)
                    for log in data.get("activity_log", []):
                        ts = log.get("timestamp", "").replace("T", " ")[:19]
                        history.append({
                            "timestamp": ts,
                            "type": "POWERLAW",
                            "error": log.get("message", "N/A"),
                            "success": log.get("type") in ["trade", "skip", "log"]
                        })
                        
            # Inject Limit Order background scans
            log_file = Path("pacman.log")
            if log_file.exists():
                with open(log_file) as f:
                    lines = f.readlines()[-300:]
                # E.g. 2026-03-07 14:07:44,123 - INFO - [LimitOrder] Checking 1 active order(s)...
                lo_lines = [l for l in lines if "[LimitOrder]" in l and ("Checking" in l or "TRIGGERED" in l)]
                for l in lo_lines[-10:]: # last 10 scans
                    parts = l.split(" - ", 2)
                    if len(parts) >= 3:
                        msg = parts[2].strip()
                        history.append({
                            "timestamp": parts[0][:19],
                            "type": "LIMIT_ORDER",
                            "error": msg,
                            "success": "TRIGGERED" in msg or "Checking" in msg
                        })
        except: pass
        
        # Sort descending by timestamp
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return jsonify(history[:limit])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_flask.route("/chart.png", methods=["GET"])
@require_auth
def get_powerlaw_chart():
    """Returns a generated PNG chart of the PowerLaw Model."""
    try:
        from src.plugins.power_law.charting import generate_powerlaw_png
        png_bytes = generate_powerlaw_png()
        if not png_bytes:
            return jsonify({"error": "Failed to generate chart"}), 500
        from flask import send_file
        import io
        response = send_file(io.BytesIO(png_bytes), mimetype='image/png')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"[API] Error generating chart: {e}")
        return jsonify({"error": str(e)}), 500

def run_server(app, port=8088):
    """Entry point for the API thread."""
    global pacman_app
    pacman_app = app
    
    if not api_secret:
        logger.error("PACMAN_API_SECRET not set in .env. API starting in insecure mode (LOCAL ONLY).")
    
    logger.info(f"🚀 Pacman API starting on http://127.0.0.1:{port}")
    logger.info(f"   [OpenClaw Integration] 📈 Chart Endpoint: http://127.0.0.1:{port}/chart.png?secret={api_secret or 'YOUR_SECRET'}")
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app_flask.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

def start_api(app, port=8088):
    """Start the API server in a separate thread."""
    api_thread = threading.Thread(target=run_server, args=(app, port), daemon=True)
    api_thread.start()
    return api_thread
