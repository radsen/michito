#!/usr/bin/env bash
# ==============================================================================
# Michito Engine — TMUX Development Infrastructure Launcher
# Starts all services in a 2x2 synchronized TMUX dashboard:
#   ┌───────────────────────────────┬───────────────────────────────┐
#   │ Pane 0: FastAPI Backend :8000 │ Pane 1: Firebase Hosting :5000│
#   ├───────────────────────────────┼───────────────────────────────┤
#   │ Pane 2: Order Worker Daemon   │ Pane 3: Interactive Dev Shell │
#   └───────────────────────────────┴───────────────────────────────┘
# ==============================================================================

set -e

SESSION_NAME="michito"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Handle Stop / Kill Flag
if [ "$1" == "--stop" ] || [ "$1" == "stop" ] || [ "$1" == "kill" ]; then
    echo -e "${YELLOW}🛑 Stopping TMUX session '${SESSION_NAME}'...${NC}"
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    echo -e "${GREEN}✓ All services in '${SESSION_NAME}' stopped.${NC}"
    exit 0
fi

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo -e "${YELLOW}ℹ️  TMUX session '${SESSION_NAME}' is already active.${NC}"
    echo -e "${CYAN}Attaching to session... (Detach anytime with Ctrl+B then D)${NC}"
    exec tmux attach-session -t "$SESSION_NAME"
fi

echo -e "${CYAN}"
echo "================================================================================"
echo "🚀 MICHITO TMUX DEVELOPMENT ENVIRONMENT LAUNCHER"
echo "================================================================================"
echo -e "${NC}"

# 1. Check Prerequisites
echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"

if ! command -v tmux &> /dev/null; then
    echo -e "${RED}❌ tmux is not installed. Install via: brew install tmux${NC}"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️ Virtualenv 'venv' not found. Creating one...${NC}"
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
fi

# 2. Database Setup (PostgreSQL)
echo -e "${YELLOW}[2/4] Configuring Database (PostgreSQL)...${NC}"
DEFAULT_PG_URL="postgresql+psycopg://127.0.0.1:5432/michito"
if command -v psql &> /dev/null && psql -h 127.0.0.1 -p 5432 -U $(whoami) -lqt 2>/dev/null; then
    createdb -h 127.0.0.1 -p 5432 michito 2>/dev/null || true
    DB_URL="$DEFAULT_PG_URL"
    echo -e "${GREEN}✓ PostgreSQL active on 127.0.0.1:5432 (Database: michito)${NC}"
else
    DB_URL="sqlite:///michito_orders.db"
    echo -e "${YELLOW}ℹ️ PostgreSQL daemon not reachable on port 5432. Using SQLite (${DB_URL})${NC}"
fi

# 3. Create TMUX Session & Panes in 2x2 Grid
echo -e "${YELLOW}[3/4] Initializing TMUX 4-Pane Grid Session '${SESSION_NAME}'...${NC}"

# Common setup script string to run in every pane
SETUP_CMD="cd '$SCRIPT_DIR' && source venv/bin/activate && export DATABASE_URL='$DB_URL' && export PYTHONPATH='$SCRIPT_DIR'"

# Start Session with Pane 0 (FastAPI Backend)
tmux new-session -d -s "$SESSION_NAME" -n "michito-stack" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:0.0" "$SETUP_CMD && clear && echo '🚀 Starting FastAPI Backend (Port 8000)...' && uvicorn src.entrypoints.api.main:app --host 0.0.0.0 --port 8000 --reload" C-m

# Split horizontally -> Pane 1 (Firebase Emulators: Hosting & Storage)
tmux split-window -h -t "$SESSION_NAME:0.0" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:0.1" "$SETUP_CMD && clear && echo '📦 Starting Firebase Emulators (Hosting :5000, Storage :9199)...' && firebase emulators:start --only hosting,storage" C-m

# Split Pane 0 vertically -> Pane 2 (Order Worker Daemon)
tmux split-window -v -t "$SESSION_NAME:0.0" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:0.2" "$SETUP_CMD && clear && echo '⚙️ Starting Asynchronous Order Worker Daemon...' && sleep 3 && python3 order_worker.py --interval 3" C-m

# Split Pane 1 vertically -> Pane 3 (Interactive Dev Shell & Tests)
tmux split-window -v -t "$SESSION_NAME:0.1" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:0.3" "$SETUP_CMD && clear && echo '💻 Michito Interactive Dev Shell' && echo 'Quick test command: venv/bin/pytest' && echo ''" C-m

# Balance layout to clean 2x2 grid
tmux select-layout -t "$SESSION_NAME" tiled

# Set pane titles
tmux select-pane -t "$SESSION_NAME:0.0" -T "FastAPI API :8000"
tmux select-pane -t "$SESSION_NAME:0.1" -T "Hosting :5000 | Storage :9199"
tmux select-pane -t "$SESSION_NAME:0.2" -T "Order Worker Daemon"
tmux select-pane -t "$SESSION_NAME:0.3" -T "Dev Shell"

# Select the Dev Shell pane (Pane 3) for immediate typing
tmux select-pane -t "$SESSION_NAME:0.3"

echo -e "\n${GREEN}[4/4] Launching TMUX Dashboard...${NC}"
echo -e "${CYAN}--------------------------------------------------------------------------------"
echo -e "TMUX Controls:"
echo -e " • Switch Panes:     Press [Ctrl+B] then [Arrow Key]"
echo -e " • Detach Session:   Press [Ctrl+B] then [D] (Services continue running)"
echo -e " • Re-attach:        Run: ./start_dev_env.sh"
echo -e " • Stop All:         Run: ./start_dev_env.sh --stop"
echo -e "--------------------------------------------------------------------------------${NC}"

# Attach to the tmux session
exec tmux attach-session -t "$SESSION_NAME"
