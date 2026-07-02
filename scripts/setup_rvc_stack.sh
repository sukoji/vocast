#!/usr/bin/env bash
# Link rvc_train from existing dialect install (PIAI server).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STACK="$ROOT/rvc_stack"
SRC="${RVC_TRAIN_SOURCE:-$HOME/dialect/llm_dialect_test/rvc_stack/rvc_train}"

mkdir -p "$STACK"
if [[ -d "$SRC" ]]; then
  ln -sfn "$SRC" "$STACK/rvc_train"
  echo "[+] linked $STACK/rvc_train → $SRC"
else
  echo "[!] source not found: $SRC"
  echo "    Set RVC_TRAIN_SOURCE or copy rvc_train manually"
  exit 1
fi

if [[ -f "$STACK/train_rvc.py" ]]; then
  echo "[+] train_rvc.py present"
else
  echo "[!] train_rvc.py missing in $STACK"
fi

echo ""
echo "Set in .env or shell:"
echo "  export RVC_STACK_ROOT=$STACK"
echo "  export RVC_MODELS_ROOT=$ROOT/models/weights"
echo "  export RVC_PYTHON=\$HOME/miniconda3/envs/rvc/bin/python"
