#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/back-end"
FRONTEND_DIR="$ROOT_DIR/front-end"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5180}"
PYTHON="${PYTHON:-python3}"
VENV_DIR="$BACKEND_DIR/.venv"

backend_pid=""
frontend_pid=""

log() { printf '[flaming-view] %s\n' "$*"; }

stop_services() {
  trap - EXIT INT TERM
  for pid in "$frontend_pid" "$backend_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  [[ -z "$frontend_pid" ]] || wait "$frontend_pid" 2>/dev/null || true
  [[ -z "$backend_pid" ]] || wait "$backend_pid" 2>/dev/null || true
  log "Serviços encerrados."
}

trap stop_services EXIT INT TERM

if [[ -f "$ROOT_DIR/.env" ]]; then                    # segredos locais (FIRMS_MAP_KEY, ANTHROPIC_API_KEY)
  set -a; source "$ROOT_DIR/.env"; set +a
fi

for command in "$PYTHON" node npm; do
  if ! command -v "$command" >/dev/null 2>&1; then
    log "Comando obrigatório não encontrado: $command"
    exit 1
  fi
done

if [[ ! -s "$ROOT_DIR/serving/release/CURRENT" ]]; then
  log "Release de dados não encontrada em serving/release. Gere-a com: make -C infra && make -C serving publish"
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  log "Criando ambiente Python do backend..."
  "$PYTHON" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c 'import fastapi, duckdb, pandas, pyarrow, uvicorn, anthropic' >/dev/null 2>&1; then
  log "Instalando dependências do backend..."
  "$VENV_DIR/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
fi

if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/vite" ]]; then
  log "Instalando dependências do front end..."
  (cd "$FRONTEND_DIR" && npm ci)
fi

if [[ -n "${FIRMS_MAP_KEY:-}" ]]; then
  log "Tempo real FIRMS habilitado."
else
  log "FIRMS_MAP_KEY não definida; histórico e globo funcionam, mas /current ficará indisponível."
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  log "Assistente habilitado (claude-opus-5)."
else
  log "ANTHROPIC_API_KEY não definida; o assistente fica indisponível e o relatório usa os textos das regras."
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/cert.pem}"   # Python do python.org não usa o chaveiro do macOS
  CACHE_ROOT="${HOME}/Library/Caches/flaming-view"
else
  CACHE_ROOT="${XDG_CACHE_HOME:-${HOME}/.cache}/flaming-view"
fi
mkdir -p "$CACHE_ROOT"

log "Iniciando backend em http://localhost:$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  export FV_RELEASE="$ROOT_DIR/serving/release"
  export FV_CACHE="${FV_CACHE:-$CACHE_ROOT/realtime.db}"
  export FV_VERIFY_SHA="${FV_VERIFY_SHA:-1}"
  exec "$VENV_DIR/bin/python" -m uvicorn app.main:create_app --factory \
    --host 127.0.0.1 --port "$BACKEND_PORT" --reload
) &
backend_pid=$!

log "Aguardando o backend validar os dados e ficar pronto..."
backend_ready=0
for ((attempt = 0; attempt < 30; attempt++)); do
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    log "O backend encerrou durante a inicialização."
    exit 1
  fi
  if "$VENV_DIR/bin/python" -c \
    'import sys, urllib.request; urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/health", timeout=1)' \
    "$BACKEND_PORT" >/dev/null 2>&1; then
    backend_ready=1
    break
  fi
  sleep 1
done
if [[ "$backend_ready" != 1 ]]; then
  log "O backend não ficou pronto em 30 segundos."
  exit 1
fi

log "Iniciando front end em http://localhost:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:$BACKEND_PORT}"
  exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
) &
frontend_pid=$!

log "API docs: http://localhost:$BACKEND_PORT/docs"
log "Pressione Ctrl+C para encerrar os serviços."

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

log "Um dos serviços foi encerrado. Finalizando o restante."
exit 1
