#!/usr/bin/env bash
set -euo pipefail

# ── config ────────────────────────────────────────────────────────────────────
VENV_DIR=".venv"
SCRIPT="fetch_lyrics.py"
DEBUG=false
RESET=false
# ─────────────────────────────────────────────────────────────────────────────

# ── parse flags ───────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --debug) DEBUG=true ;;
    --reset) RESET=true ;;
    *) echo "Unknown flag: $arg  (valid: --debug, --reset)"; exit 1 ;;
  esac
done

log()  { echo "==> $*"; }
dbg()  { $DEBUG && echo "    [debug] $*" || true; }
info() { echo "    $*"; }

$DEBUG && log "Debug mode enabled"

# ── reset ─────────────────────────────────────────────────────────────────────
if $RESET; then
  log "Resetting virtual environment..."
  dbg "Removing ${VENV_DIR}/"
  rm -rf "${VENV_DIR}"
  log "Done. Continuing with fresh setup..."
  echo ""
fi

# ── python check ──────────────────────────────────────────────────────────────
log "Checking Python 3..."
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install it and try again."
  exit 1
fi
PYTHON_VERSION=$(python3 --version)
dbg "Found: ${PYTHON_VERSION}"
dbg "Path:  $(command -v python3)"

# ── venv ──────────────────────────────────────────────────────────────────────
if [[ -d "${VENV_DIR}" ]]; then
  log "Virtual environment already exists, skipping creation."
  dbg "Using existing ${VENV_DIR}/ -- run with --reset to recreate"
else
  log "Creating virtual environment in ${VENV_DIR}..."
  python3 -m venv "${VENV_DIR}"
  dbg "venv created at $(pwd)/${VENV_DIR}"
fi

log "Activating virtual environment..."
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"
dbg "Active Python: $(which python3)"

# ── dependencies ──────────────────────────────────────────────────────────────
log "Upgrading pip..."
if $DEBUG; then
  pip install --upgrade pip
else
  pip install --upgrade pip --quiet
fi

log "Installing dependencies..."
DEPS="lyricsgenius beautifulsoup4 requests python-dotenv"
dbg "Installing: ${DEPS}"
if $DEBUG; then
  pip install $DEPS
else
  pip install $DEPS --quiet
fi

# ── scaffold .env ─────────────────────────────────────────────────────────────
if [[ ! -f ".env" ]]; then
  if [[ ! -f ".env.example" ]]; then
    echo "WARNING: .env.example not found, skipping .env creation."
    dbg "Expected .env.example in $(pwd)"
  else
    cp .env.example .env
    dbg "Copied .env.example -> .env"
    info "Created .env from .env.example."
  fi
else
  dbg ".env already exists, skipping scaffold"
fi

# ── lyrics folder ─────────────────────────────────────────────────────────────
mkdir -p lyrics
touch lyrics/.gitkeep
dbg "Ensured lyrics/.gitkeep exists"

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "--------------------------------------------------"
echo "  Setup complete."
echo ""
echo "  Add your Genius API token to .env:"
echo "    GENIUS_TOKEN=your_token_here"
echo ""
echo "  Get a free token at: https://genius.com/api-clients"
if $DEBUG; then
  echo ""
  echo "  Debug flag available for the fetch script:"
  echo "    python3 ${SCRIPT} --debug"
fi
echo "--------------------------------------------------"
echo ""

# ── prompt to run ─────────────────────────────────────────────────────────────
read -rp "==> Run ${SCRIPT} now? [y/N] " confirm
confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')

if [[ "$confirm" == "y" ]]; then
  log "Running ${SCRIPT}..."
  if $DEBUG; then
    python3 "${SCRIPT}" --debug
  else
    python3 "${SCRIPT}"
  fi
else
  echo ""
  info "To run later:"
  info "  source ${VENV_DIR}/bin/activate"
  info "  python3 ${SCRIPT}"
  if $DEBUG; then
    info "  python3 ${SCRIPT} --debug   # for verbose output"
  fi
fi
