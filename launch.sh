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

# --- Step 2: Special Commands ---
if [ $# -gt 0 ]; then
    case "$1" in
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

        daemon-status|status)
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

        kill)
            echo -e "${CYAN}[Pacman]${NC} Killing ALL Pacman processes..."
            pkill -9 -f "cli.main" 2>/dev/null || true
            lsof -ti:8088 | xargs kill -9 2>/dev/null || true
            rm -f "$PID_FILE" "$SCRIPT_DIR/data/robot.pid"
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

# --- Step 3: Run Pacman ---
cd "$SCRIPT_DIR"

if [ $# -eq 0 ]; then
    # Interactive mode
    uv run --project "$SCRIPT_DIR" python -m cli.main
else
    # One-shot mode
    uv run --project "$SCRIPT_DIR" python -m cli.main "$@"
fi
