#!/usr/bin/env bash
# Runs WitnessTrace, the Revelio gateway and nginx; if any one exits, stops the rest.
set -euo pipefail
umask 077
mkdir -p "$REVELIO_DATA_DIR" "$WITNESSTRACE_DATA_DIR" "$WITNESSTRACE_OUTPUTS_DIR" "$WITNESSTRACE_WORK_DIR"
command -v codex >/dev/null || echo 'Warning: Codex CLI is not installed. Saved/local editing works; AI generation does not.' >&2

pids=()
stop() { kill -TERM "${pids[@]}" 2>/dev/null || true; }
trap stop TERM INT

(cd /app/witness-backend && exec python -m uvicorn app:app --host 127.0.0.1 --port 8022) & pids+=($!)
(cd /app && exec python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8021 --proxy-headers) & pids+=($!)
nginx -g 'daemon off;' & pids+=($!)

set +e
wait -n
status=$?
stop
wait
exit "$status"
