#!/usr/bin/env bash
# ============================================================================
# Pacman Zero-Dependency Launcher
# ============================================================================
# Usage:  ./launch.sh [command]
#
# Examples:
#   ./launch.sh              → Interactive mode
#   ./launch.sh balance      → One-shot: show balances
#   ./launch.sh swap 10 HBAR for USDC  → One-shot: execute swap
#
# This script:
#   1. Installs 'uv' (Astral's Rust-based Python manager) if missing
#   2. Runs Pacman with auto-resolved Python + dependencies
#   3. No venv, no pip, no manual setup required
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Step 1: Ensure uv is installed ---
if ! command -v uv &> /dev/null; then
    echo -e "${CYAN}[Pacman]${NC} Installing uv (Astral Python manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the env so uv is available in this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}[Pacman]${NC} Failed to install uv. Please install manually: https://docs.astral.sh/uv/"
        exit 1
    fi
    echo -e "${GREEN}[Pacman]${NC} uv installed successfully."
fi

# --- Step 2: Special Commands ---
if [ $# -gt 0 ]; then
    if [ "$1" == "dashboard" ]; then
        echo -e "${CYAN}[Pacman]${NC} Opening dashboard at http://127.0.0.1:8088/..."
        open "http://127.0.0.1:8088/"
        exit 0
    elif [ "$1" == "daemon-start" ]; then
        echo -e "${CYAN}[Pacman]${NC} Killing any existing daemon instances & clearing ports..."
        pkill -f 'cli.main daemon' || true
        lsof -ti:8088 | xargs kill -9 2>/dev/null || true
        sleep 2
        
        echo -e "${GREEN}[Pacman]${NC} Starting background daemon..."
        # We must use the exact venv python binary because `uv run` forwards signals
        # and will terminate the background process when this launcher script exits.
        PYTHON_EXEC=$(uv run --project "$SCRIPT_DIR" which python)
        nohup "$PYTHON_EXEC" -m cli.main daemon > "$SCRIPT_DIR/daemon_output.log" 2>&1 &
        disown
        echo -e "${GREEN}[Pacman]${NC} Daemon started! Output is logging to daemon_output.log"
        exit 0
    elif [ "$1" == "daemon-stop" ]; then
        echo -e "${CYAN}[Pacman]${NC} Stopping the daemon..."
        pkill -f 'cli.main daemon' || true
        lsof -ti:8088 | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}[Pacman]${NC} Daemon and API safely stopped."
        exit 0
    fi
fi

# --- Step 3: Run Pacman ---
cd "$SCRIPT_DIR"

if [ $# -eq 0 ]; then
    # Interactive mode
    uv run --project "$SCRIPT_DIR" python -m cli.main
else
    # One-shot mode: pass all arguments
    uv run --project "$SCRIPT_DIR" python -m cli.main "$@"
fi
