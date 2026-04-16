#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${1:-$ROOT_DIR/outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live}"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing virtualenv python at ${PYTHON_BIN}" >&2
  exit 1
fi

echo "Running preflight for ${RUN_DIR}"
PREFLIGHT_JSON="$(
  cd "$ROOT_DIR" && \
  PYTHONPATH=src "$PYTHON_BIN" -m anti_omission preflight --run-dir "$RUN_DIR"
)"
echo "$PREFLIGHT_JSON"

python - <<'PY' "$PREFLIGHT_JSON"
import json
import sys

payload = json.loads(sys.argv[1])
errors = []

if not payload.get("ready_to_run"):
    errors.append("run directory is not clean; do not reuse it")

runtime = payload.get("openai_runtime", {})
if not runtime.get("is_set"):
    errors.append("OPENAI_API_KEY is not set")
if not runtime.get("starts_with_sk"):
    errors.append("OPENAI_API_KEY does not look like an API key")
if runtime.get("has_newline"):
    errors.append("OPENAI_API_KEY contains a newline")
if runtime.get("looks_like_shell_text"):
    errors.append("OPENAI_API_KEY appears to contain pasted shell command text")
if runtime.get("api_mode") not in {"responses", "chat_completions"}:
    errors.append(f"unsupported OpenAI SDK mode: {runtime.get('api_mode')}")

if errors:
    for error in errors:
        print(f"Preflight failed: {error}", file=sys.stderr)
    raise SystemExit(1)
PY

echo "Running locked confirmatory manifest"
cd "$ROOT_DIR"
PYTHONPATH=src "$PYTHON_BIN" -m anti_omission run --run-dir "$RUN_DIR"

echo "Exporting blind annotation CSV"
PYTHONPATH=src "$PYTHON_BIN" -m anti_omission export-labels --run-dir "$RUN_DIR"
