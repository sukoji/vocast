#!/bin/bash
#SBATCH --job-name=vocast_train
#SBATCH --partition=V100-32
#SBATCH --nodelist=n18
#SBATCH --gres=gpu:V100-32:1
#SBATCH --output=logs/train_%x_%j.out
#SBATCH --error=logs/train_%x_%j.err
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=8
# Usage: sbatch scripts/sbatch/train_rvc.sbatch typecast_seohyeon
set -uxo pipefail
TARGET="${1:-typecast_seohyeon}"
ROOT="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT"
mkdir -p logs
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate rvc
export PYTHONPATH="$ROOT/src"
export RVC_STACK_ROOT="$ROOT/rvc_stack"
export RVC_MODELS_ROOT="$ROOT/models/weights"
export RVC_PYTHON="$HOME/miniconda3/envs/rvc/bin/python"
echo "[job] $SLURM_JOB_ID target=$TARGET $(date -Is)"
bash scripts/train_pipeline.sh "$TARGET"
echo "[DONE] $(date -Is)"
