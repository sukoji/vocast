from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
INPUT_DIR = ROOT / "input"
MODELS_DIR = ROOT / "models"
RESULT_DIR = ROOT / "result"
WORK_DIR = ROOT / "work"
BATCHES_DIR = RESULT_DIR / "batches"
MERGED_DIR = RESULT_DIR / "merged"

DATASET_ROOT_NAME = "4도_통합_음성민원데이터"


def repo_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)
