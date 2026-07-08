#!/usr/bin/env python3
"""화자별 RVC 학습 코퍼스에서 median F0을 실측해 models.yaml에 target_f0로 캐싱.

adaptive_pitch()는 원래 남/여 두 버킷(target_f0=220Hz/140Hz 고정)만으로 피치를
보정했다. 실제 타겟 화자의 음역대가 그 버킷값과 다르면 보정이 부정확해지고,
화자가 늘어나도(train_targets.yaml 참고) 버킷은 여전히 2개뿐이라 확장이 안 됨.
이 스크립트로 학습에 쓴 코퍼스(모델별 wav 폴더)에서 median F0를 직접 재서
models.yaml에 넣어두면, adaptive_pitch()가 그 값을 우선 사용한다(없으면 기존
버킷 기본값으로 자동 대체 — 하위 호환).

사용:
  python scripts/measure_target_f0.py --model typecast_jihoon --corpus /path/to/train/wavs
  python scripts/measure_target_f0.py --model typecast_jihoon --corpus /path/to/train/wavs --write
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.paths import MODELS_DIR  # noqa: E402


def median_f0_hz(path: Path) -> float:
    x, sr = sf.read(str(path))
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = x.astype(np.float64)
    _f0, t = pw.dio(x, sr, f0_floor=60, f0_ceil=700, frame_period=10)
    f0 = pw.stonemask(x, _f0, t, sr)
    v = f0[f0 > 0]
    return float(np.median(v)) if len(v) else 0.0


AUDIO_EXTS = ("*.wav", "*.flac")


def corpus_median_f0(corpus_dir: Path) -> float:
    files = sorted(f for ext in AUDIO_EXTS for f in corpus_dir.glob(ext))
    values = [f0 for f in files if (f0 := median_f0_hz(f)) > 0]
    if not values:
        sys.exit(f"[에러] {corpus_dir} 안에 유효한 오디오 없음 (wav/flac)")
    return float(np.median(values))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="models.yaml의 모델(또는 blend) 이름")
    ap.add_argument("--corpus", required=True, type=Path, help="학습에 쓴 wav/flac 코퍼스 폴더")
    ap.add_argument("--write", action="store_true", help="측정값을 models.yaml에 바로 기록")
    args = ap.parse_args()

    f0 = corpus_median_f0(args.corpus)
    print(f"{args.model}: target_f0 = {f0:.1f}Hz  (코퍼스: {args.corpus})")

    if not args.write:
        return

    path = MODELS_DIR / "models.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    section = "models" if args.model in cfg.get("models", {}) else "blends" if args.model in cfg.get("blends", {}) else None
    if section is None:
        sys.exit(f"[에러] models.yaml에 '{args.model}' 없음")
    cfg[section][args.model]["target_f0"] = round(f0, 1)
    path.write_text(yaml.dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"-> {path} 갱신")


if __name__ == "__main__":
    main()
