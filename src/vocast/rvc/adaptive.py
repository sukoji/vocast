from __future__ import annotations

import math
from pathlib import Path

from vocast.paths import CONFIG


def _load_pitch_cfg() -> dict:
    import yaml
    return yaml.safe_load((CONFIG / "pipeline.yaml").read_text(encoding="utf-8"))["adaptive_pitch"]


def median_f0_hz(path: Path) -> float:
    import numpy as np
    import pyworld as pw
    import soundfile as sf

    x, sr = sf.read(str(path))
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = x.astype(np.float64)
    _f0, t = pw.dio(x, sr, f0_floor=60, f0_ceil=700, frame_period=10)
    f0 = pw.stonemask(x, _f0, t, sr)
    v = f0[f0 > 0]
    return float(np.median(v)) if len(v) else 0.0


def adaptive_pitch(median_f0: float, direction: str, *, target_f0: float | None = None) -> int:
    """target_f0: 실제 타겟 화자에서 실측한 값(권장, registry.model_target_f0 참고).
    없으면 pipeline.yaml의 남/여 두 버킷 기본값으로 대체(하위 호환)."""
    cfg = _load_pitch_cfg()[direction]
    target = target_f0 if target_f0 else cfg["target_f0"]
    pmin, pmax = cfg["min"], cfg["max"]
    if median_f0 <= 0:
        return 8 if direction == "male_to_female" else -8
    p = int(round(12 * math.log2(target / median_f0)))
    return max(pmin, min(pmax, p))


def rvc_direction(citizen_voice: str) -> str:
    from vocast.region_rules import voice_gender
    g = voice_gender(citizen_voice)
    if g == "female":
        return "female_to_male"
    if g == "male":
        return "male_to_female"
    return "female_to_male"
