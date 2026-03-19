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
from flask import Flask, jsonify, request, abort, send_from_directory
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

@app_flask.route("/", methods=["GET"])
def serve_dashboard():
    """Serve the dashboard UI directly from the root."""
    dashboard_dir = Path(__file__).resolve().parent.parent.parent / "dashboard"
    return send_from_directory(dashboard_dir, "index.html")

@app_flask.route("/config/<filename>", methods=["GET"])
@require_auth
def get_config(filename):
    """Securely serve JSON configuration files from the data directory."""
    if not filename.endswith(".json") or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid request"}), 400
        
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    file_path = data_dir / filename
    
    if not file_path.exists():
        return jsonify({"error": f"Configuration '{filename}' not found"}), 404
        
    try:
        with open(file_path, "r") as f:
            return jsonify(json.load(f))
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@app_flask.route("/health", methods=["GET"])
def health_check():
    """Simple ping for dashboard connectivity."""
    return jsonify({"status": "online", "time": time.time()})

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
        
    try:
        return jsonify({
            "pid": os.getpid(),
            "uptime_sec": uptime,
            "main_account_id": pacman_app.account_id,
            "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "plugins": pacman_app.pm.get_all_statuses(),
            "hcs": {
                "topic_id": getattr(pacman_app.hcs_manager, 'topic_id', None) if hasattr(pacman_app, 'hcs_manager') else None,
                "is_active": hasattr(pacman_app, 'hcs_manager') and pacman_app.hcs_manager is not None and getattr(pacman_app.hcs_manager, 'topic_id', None) is not None
            }
        })
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return jsonify({"error": str(e)}), 500

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
    """Returns enriched, role-segregated balances for all known accounts."""
    if not pacman_app:
        return jsonify({"error": "Controller not initialized"}), 500
    try:
        # 1. Gather all IDs and their roles
        main_id = pacman_app.account_id
        robot_id = pacman_app.config.robot_account_id
        
        # Load registry for nicknames (skip explicitly inactive accounts)
        registry_map = {}
        try:
            with open("data/accounts.json") as f:
                registry = json.load(f)
                for acc in registry:
                    aid = acc.get("id")
                    if aid and acc.get("active") != False:
                        registry_map[aid] = acc.get("nickname")
        except: pass

        # Build unique account list with prioritized roles
        accounts_to_process = {} # id -> role

        # Primary roles
        if main_id:
            accounts_to_process[main_id] = registry_map.get(main_id) or "Main Account"
        
        if robot_id:
            if robot_id == main_id:
                if main_id in accounts_to_process:
                    accounts_to_process[main_id] = f"{accounts_to_process[main_id]} (Robot)"
            else:
                accounts_to_process[robot_id] = registry_map.get(robot_id) or "Robot Account"
        
        # Others from registry
        for aid, nickname in registry_map.items():
            if aid not in accounts_to_process:
                accounts_to_process[aid] = nickname or "Sub Account"

        # Convert to list for enriched processing
        account_ids = [{"id": aid, "role": role} for aid, role in accounts_to_process.items()]

        # 2. Token metadata for prices
        tokens_data = {}
        try:
            with open("data/tokens.json") as f:
                tokens_data = json.load(f)
        except: pass

        def enrich_account(acc_id, role):
            # Use account_id_override for non-main IDs
            try:
                balances = pacman_app.get_balances(account_id=(acc_id if acc_id != main_id else None))
                if balances is None:
                    balances = {}
            except Exception as e:
                logger.warning(f"Failed to fetch balances for {acc_id}: {e}")
                balances = {}

            # Map to store aggregated balances by Token ID
            # { "token_id": { "symbol": "...", "balance": 0.0, "price": 0.0 } }
            aggregated = {}
            total_usd = 0.0
            
            # Ensure HBAR is always present
            if "HBAR" not in balances:
                balances["HBAR"] = 0.0

            for sym, bal in balances.items():
                if bal < 0 and sym != "HBAR": # Skip negative leftovers unless it's gas
                    continue

                # 1. Resolve Token ID & Symbol
                token_id = sym
                preferred_sym = sym
                if sym in tokens_data:
                    token_id = tokens_data[sym].get("id", sym)
                    preferred_sym = tokens_data[sym].get("symbol", sym)
                    # If it's an alias, update token_id
                    token_id = tokens_data[sym].get("alias_for", token_id)
                
                # Native HBAR handling
                if sym == "HBAR" or token_id == "0.0.0":
                    token_id = "0.0.0"
                    preferred_sym = "HBAR"

                # 2. Skip if we already processed this token ID for this account
                # This fixes the "BITCOIN" vs "WBTC_HTS" vs "BTC" duplication root cause
                if token_id in aggregated:
                    # Just add the balance to the existing entry
                    aggregated[token_id]["balance"] += bal
                    continue

                # 3. Get Price
                price_id = token_id
                raw_price = pacman_app.router.price_manager.get_price(price_id)
                price_usd = 1.0 if sym in ("USDC", "USDT") else (float(raw_price) if raw_price else 0.0)
                
                # HBAR price fallback
                if token_id == "0.0.0" and price_usd == 0:
                    price_usd = pacman_app.router.price_manager.hbar_price

                # 4. Store entry
                aggregated[token_id] = {
                    "symbol": preferred_sym,
                    "balance": bal,
                    "price_usd": price_usd,
                    "token_id": token_id
                }

            # Convert map to sorted list
            holdings = []
            for tid, data in aggregated.items():
                val_usd = data["balance"] * data["price_usd"]
                total_usd += val_usd
                holdings.append({
                    "symbol": data["symbol"],
                    "balance": data["balance"],
                    "price_usd": data["price_usd"],
                    "value_usd": val_usd,
                    "token_id": tid
                })

            # SORTING: HBAR FIRST, then by USD value descending
            holdings.sort(key=lambda x: (x["token_id"] != "0.0.0", -x["value_usd"]))

            return {
                "role": role,
                "id": acc_id,
                "total_usd": total_usd,
                "holdings": holdings
            }

        final_results = []
        for entry in account_ids:
            final_results.append(enrich_account(entry["id"], entry["role"]))
        
        return jsonify(final_results)
    except Exception as e:
        logger.error(f"API Error get_accounts: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
        # Inject type for swap records that lack one (executor stores "mode" not "type")
        for rec in history:
            if "type" not in rec:
                rec["type"] = "SWAP"
        
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
            log_file = Path("logs/pacman.log")
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

@app_flask.route("/hcs/messages", methods=["GET"])
@require_auth
def get_hcs_messages():
    """Return recent HCS signals from the active topic."""
    if not pacman_app or not hasattr(pacman_app, 'hcs_manager'):
        return jsonify([])
    try:
        limit = int(request.args.get("limit", 10))
        messages = pacman_app.hcs_manager.get_messages(limit=limit)
        return jsonify(messages)
    except Exception as e:
        logger.error(f"API Error get_hcs_messages: {e}")
        return jsonify([])

@app_flask.route("/readme", methods=["GET"])
@require_auth
def get_readme():
    """Return the Project README content for the dashboard docs tab."""
    try:
        readme_path = Path("README.md")
        if not readme_path.exists():
            return jsonify({"content": "Project documentation (README.md) not found."})
        
        with open(readme_path, "r") as f:
            content = f.read()
            return jsonify({"content": content})
    except Exception as e:
        return jsonify({"content": f"Error loading documentation: {e}"})

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

@app_flask.route("/hedera-prices", methods=["GET"])
@require_auth
def get_hedera_prices():
    """Return daily price history for Hedera ecosystem tokens.

    Query params:
        days: Number of days of history (default: 365, max: 365)
        tokens: Comma-separated token symbols (default: all)

    Response: { "HBAR": [{"date": "2024-03-18", "price": 0.107}, ...], ... }
    """
    try:
        from src.plugins.power_law.hedera_charting import get_hedera_price_history
        days = min(int(request.args.get("days", 365)), 365)

        prices = get_hedera_price_history(days=days)

        # Filter by requested tokens if specified
        tokens_filter = request.args.get("tokens")
        if tokens_filter:
            requested = [t.strip().upper() for t in tokens_filter.split(",")]
            prices = {k: v for k, v in prices.items() if k in requested}

        return jsonify(prices)
    except Exception as e:
        logger.error(f"[API] Error fetching Hedera prices: {e}")
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
    
    try:
        app_flask.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        logger.error(f"🔥 API Server crashed: {e}")
        import traceback
        logger.error(traceback.format_exc())

def start_api(app, port=8088):
    """Start the API server in a separate thread."""
    api_thread = threading.Thread(target=run_server, args=(app, port), daemon=True)
    api_thread.start()
    return api_thread
