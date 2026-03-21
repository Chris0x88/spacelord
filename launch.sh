#!/usr/bin/env bash
# ============================================================================
# Pacman Zero-Dependency Launcher (Single-Instance)
# ============================================================================
# Usage:  ./launch.sh [command]
#
# Examples:
#   ./launch.sh              → Interactive mode
#   ./launch.sh balance      → One-shot command
#   ./launch.sh daemon-start → Start background daemon (idempotent)
#   ./launch.sh daemon-stop  → Stop background daemon
#   ./launch.sh daemon-restart → Restart daemon
#   ./launch.sh daemon-status  → Check if daemon is running
#   ./launch.sh dashboard    → Open web dashboard (starts daemon if needed)
#
# Single-instance guarantee:
#   - Only one daemon process runs at a time (PID file lock)
#   - daemon-start is idempotent: if already running, reports status
#   - One-shot commands never interfere with the running daemon
#   - Stale PID files are auto-cleaned
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/data/daemon.pid"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m'

# --- Step 1: Ensure uv is installed ---
if ! command -v uv &> /dev/null; then
    echo -e "${CYAN}[Pacman]${NC} Installing uv (Astral Python manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}[Pacman]${NC} Failed to install uv. See: https://docs.astral.sh/uv/"
        exit 1
    fi
    echo -e "${GREEN}[Pacman]${NC} uv installed."
fi

# --- Helper: Check if daemon is running ---
is_daemon_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    if pgrep -f 'cli.main daemon' > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

get_daemon_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return
        fi
    fi
    pgrep -f 'cli.main daemon' 2>/dev/null | head -1
}

stop_daemon() {
    local pid
    pid=$(get_daemon_pid)
    if [ -z "$pid" ]; then
        return
    fi
    kill "$pid" 2>/dev/null || true
    for i in $(seq 1 5); do
        if ! kill -0 "$pid" 2>/dev/null; then break; fi
        sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
    fi
    lsof -ti:8088 | xargs kill -9 2>/dev/null || true
    rm -f "$PID_FILE" "$SCRIPT_DIR/data/robot.pid"
}

# --- Step 2: Check for .env ---
if [ ! -f "$SCRIPT_DIR/.env" ] && [ "$1" != "init" ] 2>/dev/null; then
    echo -e "${YELLOW}[Pacman]${NC} No .env file found."
    echo -e "${CYAN}[Pacman]${NC} Run: ./launch.sh init    (full first-run wizard)"
    echo -e "${CYAN}[Pacman]${NC}  or: cp .env.template .env && edit manually"
    exit 1
fi

# --- Step 3: Special Commands ---
if [ $# -gt 0 ]; then
    case "$1" in
        init)
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}  Pacman — First Run Setup${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""

            # 1. Create .env from template if missing
            if [ ! -f "$SCRIPT_DIR/.env" ]; then
                cp "$SCRIPT_DIR/.env.template" "$SCRIPT_DIR/.env"
                echo -e "${GREEN}[1/5]${NC} Created .env from template."
            else
                echo -e "${GREEN}[1/5]${NC} .env already exists."
            fi

            # 2. Run interactive setup wizard (key gen, account creation)
            echo -e "${CYAN}[2/5]${NC} Running setup wizard..."
            uv run --project "$SCRIPT_DIR" python -m cli.main setup

            # 3. Sync agent docs if openclaw/ exists
            if [ -d "$SCRIPT_DIR/openclaw" ]; then
                echo -e "${CYAN}[3/5]${NC} Syncing agent documentation..."
                uv run --project "$SCRIPT_DIR" python -m cli.main agent-sync 2>/dev/null || \
                    echo -e "${YELLOW}[Pacman]${NC} agent-sync skipped (run manually if needed)"
            else
                echo -e "${CYAN}[3/5]${NC} OpenClaw workspace not found — skipping agent sync."
            fi

            # 4. Run health check
            echo -e "${CYAN}[4/5]${NC} Running health check..."
            uv run --project "$SCRIPT_DIR" python -m cli.main doctor 2>/dev/null || \
                echo -e "${YELLOW}[Pacman]${NC} Doctor check had warnings — review above."

            # 5. Done
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}  Setup complete!${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""
            echo -e "  Try these commands:"
            echo -e "    ${CYAN}./launch.sh balance${NC}          — View your portfolio"
            echo -e "    ${CYAN}./launch.sh${NC}                  — Interactive mode"
            echo -e "    ${CYAN}./launch.sh dashboard${NC}        — Open web dashboard"
            echo -e "    ${CYAN}./launch.sh telegram-start${NC}   — Start Telegram bot"
            echo -e "    ${CYAN}./launch.sh help${NC}             — See all commands"
            echo ""
            exit 0
            ;;

        dashboard)
            if ! is_daemon_running; then
                echo -e "${YELLOW}[Pacman]${NC} Daemon not running — starting..."
                "$0" daemon-start
                sleep 2
            fi
            echo -e "${CYAN}[Pacman]${NC} Opening dashboard..."
            open "http://127.0.0.1:8088/" 2>/dev/null || echo "http://127.0.0.1:8088/"
            exit 0
            ;;

        daemon-start|start)
            if is_daemon_running; then
                pid=$(get_daemon_pid)
                echo -e "${GREEN}[Pacman]${NC} Daemon already running (PID: $pid)"
                echo -e "${CYAN}[Pacman]${NC} Dashboard: http://127.0.0.1:8088/"
                echo -e "${CYAN}[Pacman]${NC} Stop: ./launch.sh daemon-stop | Restart: ./launch.sh daemon-restart"
                exit 0
            fi

            echo -e "${GREEN}[Pacman]${NC} Starting daemon..."
            mkdir -p "$SCRIPT_DIR/data"

            PYTHON_EXEC=$(uv run --project "$SCRIPT_DIR" which python)
            nohup "$PYTHON_EXEC" -m cli.main daemon > "$SCRIPT_DIR/daemon_output.log" 2>&1 &
            daemon_pid=$!
            echo "$daemon_pid" > "$PID_FILE"
            disown

            sleep 2
            if kill -0 "$daemon_pid" 2>/dev/null; then
                echo -e "${GREEN}[Pacman]${NC} Daemon started (PID: $daemon_pid)"
                echo -e "${CYAN}[Pacman]${NC} Dashboard: http://127.0.0.1:8088/"
                echo -e "${CYAN}[Pacman]${NC} Logs: tail -f daemon_output.log"
            else
                echo -e "${RED}[Pacman]${NC} Daemon failed to start. Check daemon_output.log"
                rm -f "$PID_FILE"
                exit 1
            fi
            exit 0
            ;;

        daemon-stop|stop)
            if ! is_daemon_running; then
                echo -e "${CYAN}[Pacman]${NC} No daemon running."
                lsof -ti:8088 | xargs kill -9 2>/dev/null || true
                rm -f "$PID_FILE"
                exit 0
            fi
            pid=$(get_daemon_pid)
            echo -e "${CYAN}[Pacman]${NC} Stopping daemon (PID: $pid)..."
            stop_daemon
            echo -e "${GREEN}[Pacman]${NC} Daemon stopped."
            exit 0
            ;;

        daemon-restart|restart)
            "$0" daemon-stop
            sleep 1
            "$0" daemon-start
            exit 0
            ;;

        daemon-status)
            if is_daemon_running; then
                pid=$(get_daemon_pid)
                echo -e "${GREEN}[Pacman]${NC} Daemon running (PID: $pid)"
                echo -e "${CYAN}[Pacman]${NC} Dashboard: http://127.0.0.1:8088/"
                if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/health 2>/dev/null | grep -q "200"; then
                    echo -e "${GREEN}[Pacman]${NC} API: healthy"
                else
                    echo -e "${YELLOW}[Pacman]${NC} API: not responding yet"
                fi
            else
                echo -e "${CYAN}[Pacman]${NC} Daemon not running."
                echo -e "${CYAN}[Pacman]${NC} Start: ./launch.sh start"
            fi
            exit 0
            ;;

        telegram-start|tg-start)
            TG_PID_FILE="$SCRIPT_DIR/data/telegram.pid"
            if [ -f "$TG_PID_FILE" ] && kill -0 "$(cat "$TG_PID_FILE")" 2>/dev/null; then
                echo -e "${GREEN}[Pacman]${NC} Telegram bot already running (PID: $(cat "$TG_PID_FILE"))"
                exit 0
            fi
            # Load .env so TELEGRAM_BOT_TOKEN is available
            if [ -f "$SCRIPT_DIR/.env" ]; then
                set -a
                # shellcheck disable=SC1091
                source "$SCRIPT_DIR/.env"
                set +a
            fi
            if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
                echo -e "${RED}[Pacman]${NC} TELEGRAM_BOT_TOKEN not set. Add it to .env first."
                exit 1
            fi
            echo -e "${GREEN}[Pacman]${NC} Starting Telegram bot (long-polling)..."
            mkdir -p "$SCRIPT_DIR/logs"
            PYTHON_EXEC=$(uv run --project "$SCRIPT_DIR" which python)
            nohup "$PYTHON_EXEC" -m src.plugins.tg_wallet_bot.poller \
                > "$SCRIPT_DIR/logs/telegram.log" 2>&1 &
            tg_pid=$!
            echo "$tg_pid" > "$TG_PID_FILE"
            disown
            sleep 3
            if kill -0 "$tg_pid" 2>/dev/null; then
                echo -e "${GREEN}[Pacman]${NC} Telegram bot started (PID: $tg_pid)"
                echo -e "${CYAN}[Pacman]${NC} Logs: tail -f logs/telegram.log"
                echo -e "${CYAN}[Pacman]${NC} No tunnel needed — direct connection to Telegram API"
            else
                echo -e "${RED}[Pacman]${NC} Failed to start. Check logs/telegram.log"
                rm -f "$TG_PID_FILE"
                exit 1
            fi
            exit 0
            ;;

        telegram-stop|tg-stop)
            TG_PID_FILE="$SCRIPT_DIR/data/telegram.pid"
            # Kill by PID file first
            if [ -f "$TG_PID_FILE" ]; then
                tg_pid=$(cat "$TG_PID_FILE" 2>/dev/null)
                if [ -n "$tg_pid" ] && kill -0 "$tg_pid" 2>/dev/null; then
                    kill "$tg_pid" 2>/dev/null || true
                    # Wait gracefully (poller needs up to 2s to flush shutdown)
                    for i in $(seq 1 5); do
                        kill -0 "$tg_pid" 2>/dev/null || break
                        sleep 1
                    done
                    kill -9 "$tg_pid" 2>/dev/null || true
                fi
                rm -f "$TG_PID_FILE"
            fi
            # Belt-and-suspenders: kill any stray poller processes by pattern
            pkill -f "src.plugins.tg_wallet_bot.poller" 2>/dev/null || true
            sleep 1
            if pgrep -f "src.plugins.tg_wallet_bot.poller" > /dev/null 2>&1; then
                echo -e "${YELLOW}[Pacman]${NC} Warning: stray poller still running — forcing kill."
                pkill -9 -f "src.plugins.tg_wallet_bot.poller" 2>/dev/null || true
            fi
            echo -e "${GREEN}[Pacman]${NC} Telegram bot stopped."
            exit 0
            ;;

        telegram-restart|tg-restart)
            "$0" telegram-stop
            sleep 1
            "$0" telegram-start
            exit 0
            ;;

        telegram-status|tg-status)
            TG_PID_FILE="$SCRIPT_DIR/data/telegram.pid"
            # Check PID file first, then fall back to pgrep (launchd doesn't write PID file)
            LIVE_PID=""
            if [ -f "$TG_PID_FILE" ]; then
                _pid=$(cat "$TG_PID_FILE" 2>/dev/null)
                if [ -n "$_pid" ] && kill -0 "$_pid" 2>/dev/null; then
                    LIVE_PID="$_pid"
                fi
            fi
            if [ -z "$LIVE_PID" ]; then
                LIVE_PID=$(pgrep -f "src.plugins.tg_wallet_bot.poller" 2>/dev/null | head -1)
            fi

            if [ -n "$LIVE_PID" ]; then
                # Check whether launchd is managing it
                if launchctl list 2>/dev/null | grep -q "com.pacman.telegram"; then
                    echo -e "${GREEN}[Pacman]${NC} Telegram bot running (PID: $LIVE_PID) — managed by launchd (auto-restarts)"
                else
                    echo -e "${GREEN}[Pacman]${NC} Telegram bot running (PID: $LIVE_PID)"
                fi
                # Pull bot username from last log entry
                BOT_NAME=$(grep "Bot: @" "$SCRIPT_DIR/logs/telegram.log" 2>/dev/null | tail -1 | sed 's/.*Bot: //')
                [ -n "$BOT_NAME" ] && echo -e "${CYAN}[Pacman]${NC} Connected as: $BOT_NAME"
                echo -e "${CYAN}[Pacman]${NC} Logs: tail -f logs/telegram.log"
            else
                echo -e "${CYAN}[Pacman]${NC} Telegram bot not running."
                if launchctl list 2>/dev/null | grep -q "com.pacman.telegram"; then
                    echo -e "${YELLOW}[Pacman]${NC} launchd service exists but process is down — check logs."
                else
                    echo -e "${CYAN}[Pacman]${NC} Start:   ./launch.sh telegram-start"
                    echo -e "${CYAN}[Pacman]${NC} Install: ./launch.sh telegram-install  (auto-start on login)"
                fi
            fi
            exit 0
            ;;

        telegram-install|tg-install)
            # Install as a macOS launchd service — starts on login, restarts on crash
            PLIST_DIR="$HOME/Library/LaunchAgents"
            PLIST_FILE="$PLIST_DIR/com.pacman.telegram.plist"
            mkdir -p "$PLIST_DIR"

            PYTHON_EXEC=$(uv run --project "$SCRIPT_DIR" which python 2>/dev/null)
            if [ -z "$PYTHON_EXEC" ]; then
                echo -e "${RED}[Pacman]${NC} Could not find Python via uv. Run './launch.sh telegram-start' first."
                exit 1
            fi

            cat > "$PLIST_FILE" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.pacman.telegram</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_EXEC</string>
    <string>-m</string>
    <string>src.plugins.tg_wallet_bot.poller</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$SCRIPT_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME</string>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>$SCRIPT_DIR/logs/telegram.log</string>
  <key>StandardErrorPath</key>
  <string>$SCRIPT_DIR/logs/telegram.log</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>10</integer>
</dict>
</plist>
PLIST_EOF

            # Unload any existing instance, then load fresh
            launchctl unload "$PLIST_FILE" 2>/dev/null || true
            # Kill any competing poller so launchd owns the connection cleanly
            pkill -f "src.plugins.tg_wallet_bot.poller" 2>/dev/null || true
            sleep 1
            launchctl load "$PLIST_FILE"
            sleep 2
            if launchctl list | grep -q "com.pacman.telegram"; then
                echo -e "${GREEN}[Pacman]${NC} Telegram bot installed as launchd service."
                echo -e "${CYAN}[Pacman]${NC} It will now start automatically on login and restart on crash."
                echo -e "${CYAN}[Pacman]${NC} Logs: tail -f logs/telegram.log"
                echo ""
                echo -e "${YELLOW}[Pacman]${NC} IMPORTANT: Disconnect OpenClaw from this bot's Telegram account."
                echo -e "           Two connections = 409 Conflict. OpenClaw must NOT poll this bot token."
            else
                echo -e "${RED}[Pacman]${NC} launchd load may have failed. Check: launchctl list | grep pacman"
            fi
            exit 0
            ;;

        telegram-uninstall|tg-uninstall)
            PLIST_FILE="$HOME/Library/LaunchAgents/com.pacman.telegram.plist"
            if [ -f "$PLIST_FILE" ]; then
                launchctl unload "$PLIST_FILE" 2>/dev/null || true
                rm -f "$PLIST_FILE"
                echo -e "${GREEN}[Pacman]${NC} Telegram launchd service removed."
            else
                echo -e "${CYAN}[Pacman]${NC} No launchd service installed."
            fi
            pkill -f "src.plugins.tg_wallet_bot.poller" 2>/dev/null || true
            exit 0
            ;;

        telegram-webhook|tg-webhook)
            # Set/inspect Telegram webhook via setup_webhook.py
            action="${2:-info}"
            uv run --project "$SCRIPT_DIR" python -m src.plugins.telegram.setup_webhook "$action"
            exit $?
            ;;

        telegram-ngrok|tg-ngrok)
            # Start ngrok tunnel and auto-configure webhook
            PORT="${TELEGRAM_PORT:-8443}"
            echo -e "${GREEN}[Pacman]${NC} Starting ngrok tunnel on port $PORT..."
            NGROK_LOG="$SCRIPT_DIR/logs/ngrok.log"
            nohup ngrok http "$PORT" --log "$NGROK_LOG" --log-format json > /dev/null 2>&1 &
            echo $! > "$SCRIPT_DIR/data/ngrok.pid"
            disown
            sleep 3
            # Fetch public URL from ngrok API
            NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
                | python3 -c "import sys,json; t=json.load(sys.stdin).get('tunnels',[]); print(next((x['public_url'] for x in t if x['proto']=='https'),''))" 2>/dev/null)
            if [ -z "$NGROK_URL" ]; then
                echo -e "${RED}[Pacman]${NC} Could not get ngrok URL. Check logs/ngrok.log"
                exit 1
            fi
            echo -e "${GREEN}[Pacman]${NC} ngrok URL: $NGROK_URL"
            # Write to .env
            if grep -q "TELEGRAM_WEBHOOK_URL" "$SCRIPT_DIR/.env" 2>/dev/null; then
                sed -i.bak "s|TELEGRAM_WEBHOOK_URL=.*|TELEGRAM_WEBHOOK_URL=$NGROK_URL|" "$SCRIPT_DIR/.env"
            else
                echo "TELEGRAM_WEBHOOK_URL=$NGROK_URL" >> "$SCRIPT_DIR/.env"
            fi
            echo -e "${GREEN}[Pacman]${NC} TELEGRAM_WEBHOOK_URL set in .env"
            # Set the webhook
            TELEGRAM_WEBHOOK_URL="$NGROK_URL" uv run --project "$SCRIPT_DIR" \
                python -m src.plugins.telegram.setup_webhook set
            exit $?
            ;;

        # ── Discord Bot ─────────────────────────────────────────────

        discord-start|dc-start)
            DC_PID_FILE="$SCRIPT_DIR/data/discord.pid"
            if [ -f "$DC_PID_FILE" ] && kill -0 "$(cat "$DC_PID_FILE")" 2>/dev/null; then
                echo -e "${GREEN}[Pacman]${NC} Discord bot already running (PID: $(cat "$DC_PID_FILE"))"
                exit 0
            fi
            # Load .env so DISCORD_BOT_TOKEN is available
            if [ -f "$SCRIPT_DIR/.env" ]; then
                set -a
                # shellcheck disable=SC1091
                source "$SCRIPT_DIR/.env"
                set +a
            fi
            if [ -z "${DISCORD_BOT_TOKEN:-}" ]; then
                echo -e "${RED}[Pacman]${NC} DISCORD_BOT_TOKEN not set. Add it to .env first."
                echo -e "${CYAN}[Pacman]${NC} Get one at: https://discord.com/developers/applications"
                exit 1
            fi
            echo -e "${GREEN}[Pacman]${NC} Starting Discord bot..."
            mkdir -p "$SCRIPT_DIR/logs"
            PYTHON_EXEC=$(uv run --project "$SCRIPT_DIR" which python)
            nohup "$PYTHON_EXEC" -m src.plugins.discord_bot.poller \
                > "$SCRIPT_DIR/logs/discord.log" 2>&1 &
            dc_pid=$!
            echo "$dc_pid" > "$DC_PID_FILE"
            disown
            sleep 3
            if kill -0 "$dc_pid" 2>/dev/null; then
                echo -e "${GREEN}[Pacman]${NC} Discord bot started (PID: $dc_pid)"
                echo -e "${CYAN}[Pacman]${NC} Logs: tail -f logs/discord.log"
            else
                echo -e "${RED}[Pacman]${NC} Failed to start. Check logs/discord.log"
                rm -f "$DC_PID_FILE"
                exit 1
            fi
            exit 0
            ;;

        discord-stop|dc-stop)
            DC_PID_FILE="$SCRIPT_DIR/data/discord.pid"
            if [ -f "$DC_PID_FILE" ]; then
                dc_pid=$(cat "$DC_PID_FILE" 2>/dev/null)
                if [ -n "$dc_pid" ] && kill -0 "$dc_pid" 2>/dev/null; then
                    kill "$dc_pid" 2>/dev/null || true
                    for i in $(seq 1 5); do
                        kill -0 "$dc_pid" 2>/dev/null || break
                        sleep 1
                    done
                    kill -9 "$dc_pid" 2>/dev/null || true
                fi
                rm -f "$DC_PID_FILE"
            fi
            pkill -f "src.plugins.discord_bot.poller" 2>/dev/null || true
            sleep 1
            if pgrep -f "src.plugins.discord_bot.poller" > /dev/null 2>&1; then
                echo -e "${YELLOW}[Pacman]${NC} Warning: stray Discord bot still running — forcing kill."
                pkill -9 -f "src.plugins.discord_bot.poller" 2>/dev/null || true
            fi
            echo -e "${GREEN}[Pacman]${NC} Discord bot stopped."
            exit 0
            ;;

        discord-restart|dc-restart)
            "$0" discord-stop
            sleep 1
            "$0" discord-start
            exit 0
            ;;

        discord-status|dc-status)
            DC_PID_FILE="$SCRIPT_DIR/data/discord.pid"
            LIVE_PID=""
            if [ -f "$DC_PID_FILE" ]; then
                _pid=$(cat "$DC_PID_FILE" 2>/dev/null)
                if [ -n "$_pid" ] && kill -0 "$_pid" 2>/dev/null; then
                    LIVE_PID="$_pid"
                fi
            fi
            if [ -z "$LIVE_PID" ]; then
                LIVE_PID=$(pgrep -f "src.plugins.discord_bot.poller" 2>/dev/null | head -1)
            fi

            if [ -n "$LIVE_PID" ]; then
                echo -e "${GREEN}[Pacman]${NC} Discord bot running (PID: $LIVE_PID)"
                BOT_NAME=$(grep "Bot:" "$SCRIPT_DIR/logs/discord.log" 2>/dev/null | tail -1 | sed 's/.*Bot: //')
                [ -n "$BOT_NAME" ] && echo -e "${CYAN}[Pacman]${NC} Connected as: $BOT_NAME"
                echo -e "${CYAN}[Pacman]${NC} Logs: tail -f logs/discord.log"
            else
                echo -e "${CYAN}[Pacman]${NC} Discord bot not running."
                echo -e "${CYAN}[Pacman]${NC} Start: ./launch.sh discord-start"
            fi
            exit 0
            ;;

        discord-install|dc-install)
            PLIST_DIR="$HOME/Library/LaunchAgents"
            PLIST_FILE="$PLIST_DIR/com.pacman.discord.plist"
            mkdir -p "$PLIST_DIR"

            PYTHON_EXEC=$(uv run --project "$SCRIPT_DIR" which python 2>/dev/null)
            if [ -z "$PYTHON_EXEC" ]; then
                echo -e "${RED}[Pacman]${NC} Could not find Python via uv. Run './launch.sh discord-start' first."
                exit 1
            fi

            cat > "$PLIST_FILE" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.pacman.discord</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_EXEC</string>
    <string>-m</string>
    <string>src.plugins.discord_bot.poller</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$SCRIPT_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME</string>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>$SCRIPT_DIR/logs/discord.log</string>
  <key>StandardErrorPath</key>
  <string>$SCRIPT_DIR/logs/discord.log</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>10</integer>
</dict>
</plist>
PLIST_EOF

            launchctl unload "$PLIST_FILE" 2>/dev/null || true
            pkill -f "src.plugins.discord_bot.poller" 2>/dev/null || true
            sleep 1
            launchctl load "$PLIST_FILE"
            sleep 2
            if launchctl list | grep -q "com.pacman.discord"; then
                echo -e "${GREEN}[Pacman]${NC} Discord bot installed as launchd service."
                echo -e "${CYAN}[Pacman]${NC} It will now start automatically on login and restart on crash."
                echo -e "${CYAN}[Pacman]${NC} Logs: tail -f logs/discord.log"
            else
                echo -e "${RED}[Pacman]${NC} launchd load may have failed. Check: launchctl list | grep pacman"
            fi
            exit 0
            ;;

        discord-uninstall|dc-uninstall)
            PLIST_FILE="$HOME/Library/LaunchAgents/com.pacman.discord.plist"
            if [ -f "$PLIST_FILE" ]; then
                launchctl unload "$PLIST_FILE" 2>/dev/null || true
                rm -f "$PLIST_FILE"
                echo -e "${GREEN}[Pacman]${NC} Discord launchd service removed."
            else
                echo -e "${CYAN}[Pacman]${NC} No Discord launchd service installed."
            fi
            pkill -f "src.plugins.discord_bot.poller" 2>/dev/null || true
            exit 0
            ;;

        openclaw-setup|agent-setup)
            echo -e "${CYAN}[Pacman]${NC} Starting OpenClaw agent setup..."
            uv run --project "$SCRIPT_DIR" python scripts/openclaw_setup.py
            exit $?
            ;;

        kill)
            echo -e "${CYAN}[Pacman]${NC} Killing ALL Pacman processes..."
            pkill -9 -f "cli.main" 2>/dev/null || true
            pkill -9 -f "src.plugins.discord_bot.poller" 2>/dev/null || true
            lsof -ti:8088 | xargs kill -9 2>/dev/null || true
            rm -f "$PID_FILE" "$SCRIPT_DIR/data/robot.pid" "$SCRIPT_DIR/data/discord.pid"
            sleep 1
            remaining=$(pgrep -f "cli.main" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$remaining" -eq 0 ]; then
                echo -e "${GREEN}[Pacman]${NC} All clear. No Pacman processes running."
            else
                echo -e "${YELLOW}[Pacman]${NC} $remaining process(es) still running — try again."
            fi
            exit 0
            ;;
    esac
fi

# --- Step 4: Run Pacman ---
cd "$SCRIPT_DIR"

if [ $# -eq 0 ]; then
    # Interactive mode — ensure daemons are running
    if ! is_daemon_running; then
        echo -e "${CYAN}[Pacman]${NC} Starting background daemons..."
        PYTHON_EXEC=$(uv run --project "$SCRIPT_DIR" which python)
        mkdir -p "$SCRIPT_DIR/data"
        nohup "$PYTHON_EXEC" -m cli.main daemon > "$SCRIPT_DIR/daemon_output.log" 2>&1 &
        daemon_pid=$!
        echo "$daemon_pid" > "$PID_FILE"
        disown
        sleep 2
        if kill -0 "$daemon_pid" 2>/dev/null; then
            echo -e "${GREEN}[Pacman]${NC} Daemons started (PID: $daemon_pid)"
        else
            echo -e "${YELLOW}[Pacman]${NC} Daemon start failed — check daemon_output.log"
            rm -f "$PID_FILE"
        fi
    else
        pid=$(get_daemon_pid)
        echo -e "${GREEN}[Pacman]${NC} Daemons running (PID: $pid)"
    fi
    uv run --project "$SCRIPT_DIR" python -m cli.main
else
    # One-shot mode
    uv run --project "$SCRIPT_DIR" python -m cli.main "$@"
fi
