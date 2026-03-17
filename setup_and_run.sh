#!/bin/bash
# ─────────────────────────────────────────────────────────────
# setup_and_run.sh
# One-shot setup + launch for macOS (M1/M2/M3/M4)
# Usage:  bash setup_and_run.sh
# ─────────────────────────────────────────────────────────────

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="python3"

echo ""
echo "╔═════════════════════════════════════════╗"
echo "║   Semiconductor SPC Dashboard Setup     ║"
echo "╚═════════════════════════════════════════╝"
echo ""

# 1. Check Python ─────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌  python3 not found."
    echo "    Install from https://www.python.org/downloads/ or via Homebrew:"
    echo "    brew install python"
    exit 1
fi

PY_VER=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "✅  Python $PY_VER found"

# 2. Create virtualenv if needed ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "📦  Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# 3. Install / upgrade packages ───────────────────────────────
echo "📥  Installing packages (first run may take ~1 min)..."
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_DIR/requirements.txt"
echo "✅  All packages installed"

# 4. Create data directory ─────────────────────────────────────
mkdir -p "$PROJECT_DIR/data"

# 5. Launch Streamlit ─────────────────────────────────────────
echo ""
echo "🚀  Launching SPC Dashboard..."
echo "    Open your browser at  http://localhost:8501"
echo "    Press Ctrl+C to stop."
echo ""

streamlit run "$PROJECT_DIR/app.py" \
    --server.port 8501 \
    --server.headless false \
    --theme.base dark \
    --theme.primaryColor "#0ea5e9" \
    --theme.backgroundColor "#0b1120" \
    --theme.secondaryBackgroundColor "#0f172a" \
    --theme.textColor "#e2e8f0"
