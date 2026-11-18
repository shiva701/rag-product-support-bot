#!/usr/bin/env bash
# Start and stop the whole app: API (FastAPI/uvicorn) + web UI (Vite), and Ollama if it isn't running.
#
#   ./run.sh start      start everything in the background
#   ./run.sh start --debug     same, but the API runs under debugpy (attach VS Code on port 5678)
#   ./run.sh stop       stop everything this script started
#   ./run.sh restart [--debug]  stop, then start
#   ./run.sh status     show what's running
#   ./run.sh logs [api|ui|ollama]   follow the logs (all by default)
#
# Debug mode: no --reload (breakpoints don't stop in the reload child process), log level debug,
# debugpy listening on DEBUG_PORT (default 5678). Add DEBUG_WAIT=1 to hold startup until the
# debugger attaches, so you can break on startup code.
#
# PIDs and logs go to .run/ in the project root.

set -uo pipefail
set -m   # give each background job its own process group, so stop can kill its children too

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-5173}"
OLLAMA_URL="${OLLAMA_HOST:-http://localhost:11434}"
DEBUG_PORT="${DEBUG_PORT:-5678}"
DEBUG=0

mkdir -p "$RUN_DIR"

c_green=$'\033[32m'; c_red=$'\033[31m'; c_yellow=$'\033[33m'; c_reset=$'\033[0m'
ok()   { echo "${c_green}✔${c_reset} $*"; }
warn() { echo "${c_yellow}!${c_reset} $*"; }
err()  { echo "${c_red}✘${c_reset} $*" >&2; }

pid_file() { echo "$RUN_DIR/$1.pid"; }
log_file() { echo "$RUN_DIR/$1.log"; }

is_running() {  # is_running <name>
  local f; f="$(pid_file "$1")"
  [[ -f "$f" ]] && kill -0 "$(cat "$f")" 2>/dev/null
}

port_in_use() { lsof -ti "tcp:$1" -sTCP:LISTEN >/dev/null 2>&1; }

wait_for_url() {  # wait_for_url <url> <seconds>
  local url="$1" secs="$2" i
  for ((i = 0; i < secs; i++)); do
    curl -fsS -o /dev/null "$url" 2>/dev/null && return 0
    sleep 1
  done
  return 1
}

launch() {  # launch <name> <workdir> <cmd...>
  local name="$1" dir="$2"; shift 2
  (cd "$dir" && exec "$@") >"$(log_file "$name")" 2>&1 &
  echo $! >"$(pid_file "$name")"
}

stop_one() {  # stop_one <name> [port]
  local name="$1" port="${2:-}" f pid
  f="$(pid_file "$name")"
  if [[ -f "$f" ]]; then
    pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then
      # Kill the whole process group (uvicorn reloader + worker, npm + vite/esbuild).
      kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
      for _ in {1..10}; do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
      kill -0 "$pid" 2>/dev/null && kill -KILL -- "-$pid" 2>/dev/null
      ok "Stopped $name"
    fi
    rm -f "$f"
  fi
  rm -f "$RUN_DIR/$name.mode"
  # Anything still holding the port (e.g. a stray child) gets stopped too.
  if [[ -n "$port" ]] && port_in_use "$port"; then
    lsof -ti "tcp:$port" -sTCP:LISTEN | xargs kill 2>/dev/null
    sleep 1
    port_in_use "$port" && lsof -ti "tcp:$port" -sTCP:LISTEN | xargs kill -9 2>/dev/null
    ok "Freed port $port"
  fi
}

start() {
  # --- prerequisites ---
  local uvicorn="$ROOT/.venv/bin/uvicorn"
  if [[ ! -x "$uvicorn" ]]; then
    err "No .venv found. Run: poetry install"; exit 1
  fi
  if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
    warn "Installing UI dependencies (npm install)..."
    (cd "$ROOT/frontend" && npm install) || { err "npm install failed"; exit 1; }
  fi
  if [[ ! -d "$ROOT/index" ]] || [[ -z "$(ls -A "$ROOT/index" 2>/dev/null)" ]]; then
    warn "No index found. Build it with: .venv/bin/python ingest.py"
  fi

  # --- Ollama ---
  if curl -fsS -o /dev/null "$OLLAMA_URL" 2>/dev/null; then
    ok "Ollama already running"
  elif command -v ollama >/dev/null; then
    launch ollama "$ROOT" ollama serve
    if wait_for_url "$OLLAMA_URL" 20; then ok "Started Ollama"; else err "Ollama didn't start; see $(log_file ollama)"; fi
  else
    warn "Ollama not installed or not running; chat replies will fail"
  fi

  # --- API ---
  if is_running api; then
    ok "API already running"
    if ((DEBUG)) && [[ ! -f "$RUN_DIR/api.mode" ]]; then
      warn "It's running in normal mode. Use ./run.sh restart --debug to switch to debug mode."
    elif ((!DEBUG)) && [[ -f "$RUN_DIR/api.mode" ]]; then
      warn "It's running in debug mode. Use ./run.sh restart to switch to normal mode."
    fi
  elif port_in_use "$API_PORT"; then
    err "Port $API_PORT is in use by another process (lsof -i tcp:$API_PORT)"; exit 1
  else
    local wait_secs=120
    if ((DEBUG)); then
      if ! "$ROOT/.venv/bin/python" -c "import debugpy" 2>/dev/null; then
        err "debugpy isn't installed. Run: poetry install --with dev"; exit 1
      fi
      if port_in_use "$DEBUG_PORT"; then
        err "Debug port $DEBUG_PORT is in use (lsof -i tcp:$DEBUG_PORT)"; exit 1
      fi
      local wait_flag=()
      if [[ "${DEBUG_WAIT:-0}" == 1 ]]; then wait_flag=(--wait-for-client); wait_secs=600; fi
      PYTHONUNBUFFERED=1 launch api "$ROOT" "$ROOT/.venv/bin/python" -m debugpy \
        --listen "127.0.0.1:$DEBUG_PORT" ${wait_flag[@]+"${wait_flag[@]}"} \
        -m uvicorn api:app --port "$API_PORT" --log-level debug
      echo debug >"$RUN_DIR/api.mode"
      ok "Debugger listening on 127.0.0.1:$DEBUG_PORT (VS Code: \"Attach to run.sh --debug\")"
      [[ ${#wait_flag[@]} -gt 0 ]] && warn "DEBUG_WAIT=1: the API won't start until a debugger attaches"
    else
      launch api "$ROOT" "$uvicorn" api:app --reload --port "$API_PORT"
    fi
    echo -n "  Starting API (loading models can take a moment)"
    local i
    for ((i = 0; i < wait_secs; i++)); do
      curl -fsS -o /dev/null "http://localhost:$API_PORT/api/health" 2>/dev/null && break
      is_running api || break
      echo -n "."; sleep 1
    done
    echo
    if curl -fsS -o /dev/null "http://localhost:$API_PORT/api/health" 2>/dev/null; then
      ok "API     http://localhost:$API_PORT"
    else
      err "API failed to start. Last log lines:"; tail -n 20 "$(log_file api)" >&2
      stop_one api "$API_PORT"; exit 1
    fi
  fi

  # --- UI ---
  if is_running ui; then
    ok "UI already running"
  elif port_in_use "$UI_PORT"; then
    err "Port $UI_PORT is in use by another process (lsof -i tcp:$UI_PORT)"; exit 1
  else
    launch ui "$ROOT/frontend" npm run dev -- --port "$UI_PORT" --strictPort
    if wait_for_url "http://localhost:$UI_PORT" 30; then
      ok "UI      http://localhost:$UI_PORT"
    else
      err "UI failed to start. Last log lines:"; tail -n 20 "$(log_file ui)" >&2
      stop_one ui "$UI_PORT"; exit 1
    fi
  fi

  echo
  echo "Logs: ./run.sh logs     Stop: ./run.sh stop"
}

stop() {
  stop_one ui "$UI_PORT"
  stop_one api "$API_PORT"
  stop_one ollama   # only stops Ollama if this script started it
  ok "All stopped"
}

status() {
  local name port
  for entry in "api:$API_PORT" "ui:$UI_PORT"; do
    name="${entry%%:*}"; port="${entry##*:}"
    if port_in_use "$port"; then
      if [[ "$name" == api && -f "$RUN_DIR/api.mode" ]]; then
        ok "$name running on port $port (debug mode, debugger on port $DEBUG_PORT)"
      else
        ok "$name running on port $port"
      fi
    else
      err "$name not running"
    fi
  done
  if curl -fsS -o /dev/null "$OLLAMA_URL" 2>/dev/null; then
    ok "ollama running$(is_running ollama && echo ' (started by run.sh)')"
  else
    err "ollama not running"
  fi
}

logs() {
  local which="${1:-}"
  if [[ -n "$which" ]]; then
    tail -n 50 -f "$(log_file "$which")"
  else
    tail -n 20 -f "$RUN_DIR"/*.log
  fi
}

cmd="${1:-}"; shift || true
if [[ "$cmd" == start || "$cmd" == restart ]]; then
  for arg in "$@"; do
    case "$arg" in
      --debug|-d) DEBUG=1 ;;
      *) err "Unknown option: $arg"; exit 1 ;;
    esac
  done
fi

case "$cmd" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  logs)    logs "${1:-}" ;;
  *) echo "Usage: $0 {start [--debug]|stop|restart [--debug]|status|logs [api|ui|ollama]}"; exit 1 ;;
esac
