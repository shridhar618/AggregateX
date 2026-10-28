#!/usr/bin/env bash
# Independent reference backend only. React continues to use its existing API.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
umask 077
runtime_base="${XDG_DATA_HOME:-$HOME/.local/share}/witnesstrace-integration"
export WITNESSTRACE_DATA_DIR="${WITNESSTRACE_DATA_DIR:-$runtime_base/data}"
export WITNESSTRACE_OUTPUTS_DIR="${WITNESSTRACE_OUTPUTS_DIR:-$runtime_base/outputs}"
export WITNESSTRACE_WORK_DIR="${WITNESSTRACE_WORK_DIR:-$runtime_base/work}"
reference_port="${WITNESSTRACE_PORT:-8022}"
if [[ ! "$reference_port" =~ ^[0-9]+$ ]] || (( ${#reference_port} > 5 )); then
  echo 'Choose an available unprivileged port other than 8000 or 8001.' >&2
  exit 2
fi
reference_port=$((10#$reference_port))
if (( reference_port < 1024 || reference_port > 65535 || reference_port == 8000 || reference_port == 8001 )); then
  echo 'Choose an available unprivileged port other than 8000 or 8001.' >&2
  exit 2
fi
if [[ ! -x .venv/bin/python ]]; then
  echo 'Create .venv and install requirements-runtime-lock.txt first; see README.md.' >&2
  exit 1
fi
if ! command -v codex >/dev/null 2>&1; then
  echo 'Warning: Codex CLI is unavailable. Saved/local editing works; AI generation requires local sign-in.' >&2
fi
exec .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port "$reference_port"
