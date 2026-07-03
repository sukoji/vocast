from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from vocast.paths import CONFIG


@dataclass
class SampleParams:
    citizen_voice: str
    counselor_voice: str
    citizen_emotion: str
    citizen_intensity: float
    citizen_tempo: float
    counselor_emotion: str
    counselor_intensity: float
    counselor_tempo: float


def _load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def load_region_rules() -> dict:
    return _load_yaml("region_rules.yaml")


def load_voices_config() -> dict:
    return _load_yaml("voices.yaml")


def _sample_range(rng: random.Random, spec: dict) -> float:
    t = spec["type"]
    if t == "fixed":
        return float(spec["value"])
    if t == "choice":
        return float(rng.choice(spec["values"]))
    if t == "uniform":
        return round(rng.uniform(spec["min"], spec["max"]), 2)
    raise ValueError(f"unknown range type: {t}")


def sample_params(region: str, *, seed: int) -> SampleParams:
    """generate_tts.py와 동일한 규칙: 민원인 파라미터는 seed 하나의 rng에서 순서대로,
    상담원 voice만 seed*7919로 독립 시드(성우 배정이 감정/강도와 서로 안 얽히게)."""
    rules = load_region_rules()
    if region in rules.get("skip_regions", []):
        raise ValueError(f"region skipped: {region}")
    cfg = rules["regions"][region]
    rng = random.Random(seed)

    citizen_voices = cfg["citizen_voices"]
    # ponytail: voice가 1개뿐이면 뽑지 않고 그대로 사용(현재 전 지역 1개). 2개 이상 되면
    # generate_tts.py처럼 시나리오 정렬 순서로 절반씩 나누는 로직이 필요 — 지금은 rng.choice로 대체.
    citizen_voice = citizen_voices[0] if len(citizen_voices) == 1 else rng.choice(citizen_voices)
    citizen_emotions = cfg["citizen_emotions"]
    # ponytail: 값이 하나뿐이면 fixed와 동일하게 rng를 소비하지 않음(generate_tts.py의 ("fixed", v) 규칙)
    citizen_emotion = citizen_emotions[0] if len(citizen_emotions) == 1 else rng.choice(citizen_emotions)
    citizen_intensity = _sample_range(rng, cfg["citizen_intensity"])
    citizen_tempo = _sample_range(rng, cfg["citizen_tempo"])

    if cfg.get("counselor_neutral"):
        counselor_emotion = "normal"
        counselor_intensity = 1.0
        counselor_tempo = 1.0
    else:
        counselor_emotion = cfg.get("counselor_emotion", "normal")
        counselor_intensity = _sample_range(rng, cfg["counselor_intensity"])
        counselor_tempo = _sample_range(rng, cfg["counselor_tempo"])

    counselor_voices = cfg["counselor_voices"]
    couns_rng = random.Random(seed * 7919)
    counselor_voice = (
        counselor_voices[0] if len(counselor_voices) == 1 else couns_rng.choice(counselor_voices)
    )

    return SampleParams(
        citizen_voice=citizen_voice,
        counselor_voice=counselor_voice,
        citizen_emotion=citizen_emotion,
        citizen_intensity=citizen_intensity,
        citizen_tempo=citizen_tempo,
        counselor_emotion=counselor_emotion,
        counselor_intensity=counselor_intensity,
        counselor_tempo=counselor_tempo,
    )


def voice_id(name: str, *, api_map: dict[str, str] | None = None) -> str:
    cfg = load_voices_config()
    static = cfg.get("voices", {})
    if name in static and static[name]:
        return static[name]
    if api_map and name in api_map:
        return api_map[name]
    raise KeyError(f"voice_id not found for {name!r} — update config/voices.yaml or run list_voices")


def voice_gender(name: str) -> str:
    return load_voices_config().get("gender", {}).get(name, "unknown")
