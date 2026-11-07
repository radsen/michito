#!/usr/bin/env bash
# ==============================================================================
# Michito Engine — TMUX Development Infrastructure Launcher
# Starts all services in dedicated TMUX tabs (windows):
#   Tab 1: [api]      -> FastAPI Backend (:8000)
#   Tab 2: [firebase] -> Firebase Emulators (Hosting :5005, Storage :9199, Pub/Sub :8085, UI :4001, Hub :4401)
#   Tab 3: [worker]   -> Asynchronous Order Worker Daemon
#   Tab 4: [dev]      -> Interactive Dev Shell & Test Runner
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
echo "🚀 MICHITO TMUX DEVELOPMENT ENVIRONMENT LAUNCHER (TABBED LAYOUT)"
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

# 3. Create TMUX Session & Dedicated Tabs (Windows)
echo -e "${YELLOW}[3/4] Initializing TMUX Session '${SESSION_NAME}' with dedicated Tabs...${NC}"

# Common setup script string to run in every tab
SETUP_CMD="cd '$SCRIPT_DIR' && source venv/bin/activate && export DATABASE_URL='$DB_URL' && export PYTHONPATH='$SCRIPT_DIR'"

# Tab 1: FastAPI Backend (:8000)
tmux new-session -d -s "$SESSION_NAME" -n "api" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:api" "$SETUP_CMD && clear && echo '🚀 Starting FastAPI Backend (Port 8000)...' && uvicorn src.entrypoints.api.main:app --host 0.0.0.0 --port 8000 --reload" C-m

# Tab 2: Firebase Emulators (Hosting :5005, Storage :9199, Pub/Sub :8085, UI :4001, Hub :4401)
tmux new-window -t "$SESSION_NAME" -n "firebase" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:firebase" "$SETUP_CMD && clear && echo '📦 Starting Firebase Emulators (Hosting :5005, Storage :9199, Pub/Sub :8085, UI :4001)...' && firebase emulators:start --only hosting,storage,pubsub" C-m

# Tab 3: Order Worker Daemon
tmux new-window -t "$SESSION_NAME" -n "worker" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:worker" "$SETUP_CMD && clear && echo '⚙️ Starting Asynchronous Order Worker Daemon...' && sleep 2 && python3 order_worker.py --interval 3" C-m

# Tab 4: Interactive Dev Shell & Test Runner
tmux new-window -t "$SESSION_NAME" -n "dev" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME:dev" "$SETUP_CMD && clear && echo '💻 Michito Interactive Dev Shell' && echo 'Quick test command: venv/bin/pytest' && echo ''" C-m

# TMUX UI Styling & Tab Bar
tmux set-option -t "$SESSION_NAME" mouse on 2>/dev/null || true
tmux set-option -t "$SESSION_NAME" status on 2>/dev/null || true
tmux set-option -t "$SESSION_NAME" status-position bottom 2>/dev/null || true
tmux set-option -t "$SESSION_NAME" status-style "bg=colour236,fg=colour252" 2>/dev/null || true
tmux set-option -t "$SESSION_NAME" window-status-current-style "bg=colour39,fg=colour232,bold" 2>/dev/null || true
tmux set-option -t "$SESSION_NAME" window-status-format " #I:#W " 2>/dev/null || true
tmux set-option -t "$SESSION_NAME" window-status-current-format " #[bold]#I:#W* " 2>/dev/null || true

# Focus on the Dev Shell tab by default
tmux select-window -t "$SESSION_NAME:dev"

echo -e "\n${GREEN}[4/4] Launching TMUX Tabbed Environment...${NC}"
echo -e "${CYAN}--------------------------------------------------------------------------------"
echo -e "TMUX Tab Controls:"
echo -e " • Direct Tab Switch: Press [Ctrl+B] then [0] (api), [1] (firebase), [2] (worker), [3] (dev)"
echo -e " • Next / Prev Tab:   Press [Ctrl+B] then [N] (next) or [P] (previous)"
echo -e " • Click Tabs:        Click any tab in the bottom status bar with your mouse"
echo -e " • Detach Session:    Press [Ctrl+B] then [D] (Services continue running in background)"
echo -e " • Re-attach:         Run: ./start_dev_env.sh"
echo -e " • Stop All:          Run: ./start_dev_env.sh --stop"
echo -e "--------------------------------------------------------------------------------${NC}"

# Attach to the tmux session
exec tmux attach-session -t "$SESSION_NAME"
