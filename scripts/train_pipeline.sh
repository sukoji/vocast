#!/usr/bin/env bash
# Full RVC training pipeline: corpus synth → train → register
# Usage: bash scripts/train_pipeline.sh typecast_seohyeon [--limit 20]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:?target name e.g. typecast_jihoon}"
shift || true
LIMIT_ARGS=()
for arg in "$@"; do LIMIT_ARGS+=("$arg"); done

cd "$ROOT"
export PYTHONPATH="$ROOT/src"
export RVC_STACK_ROOT="${RVC_STACK_ROOT:-$ROOT/rvc_stack}"
export RVC_MODELS_ROOT="${RVC_MODELS_ROOT:-$ROOT/models/weights}"

if [[ ! -d "$RVC_STACK_ROOT/rvc_train" ]]; then
  echo "[!] rvc_train missing — run: bash scripts/setup_rvc_stack.sh"
  exit 1
fi

if [[ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]]; then
  # shellcheck source=/dev/null
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate rvc 2>/dev/null || conda activate tts 2>/dev/null || true
  export RVC_PYTHON="${RVC_PYTHON:-$(which python)}"
fi

echo "[1/2] corpus $TARGET"
python scripts/synth_corpus.py --target "$TARGET" "${LIMIT_ARGS[@]}"

echo "[2/2] train $TARGET"
python scripts/train_rvc.py --target "$TARGET"

echo "[pipeline] DONE $TARGET"
