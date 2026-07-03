from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
sys.path.insert(0, str(ROOT / "src"))

from vocast.region_rules import sample_params  # noqa: E402


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def test_region_rules_loads() -> None:
    rules = _load("region_rules.yaml")
    assert "regions" in rules
    assert "제주도" in rules.get("skip_regions", [])


def test_counselor_pool_is_shared() -> None:
    rules = _load("region_rules.yaml")
    counselors = rules.get("counselor_voices", [])
    assert counselors
    for region, cfg in rules["regions"].items():
        assert cfg["counselor_voices"] == counselors, region


def test_voices_have_gender() -> None:
    voices = _load("voices.yaml")
    for name in voices["voices"]:
        assert name in voices["gender"], name


def test_pipeline_config_loads() -> None:
    cfg = _load("pipeline.yaml")
    assert cfg["variants"]
    assert any(v["id"] == "tts_only" for v in cfg["variants"])


def test_ci_auto_merge_smoke_marker() -> None:
    """Marker test for PR auto-merge workflow verification."""
    assert True


def test_sample_params_deterministic_by_scenario_id() -> None:
    a = sample_params("강원도", seed=14)
    b = sample_params("강원도", seed=14)
    assert a == b


def test_single_value_list_does_not_consume_rng() -> None:
    """전라도는 citizen_emotions가 [happy] 하나뿐 -> generate_tts.py의 ("fixed", ...)와
    동일하게 rng를 소비하면 안 됨. 소비하면 뒤따르는 intensity 값이 어긋난다(회귀 고정값)."""
    p1 = sample_params("전라도", seed=1)
    p14 = sample_params("전라도", seed=14)
    assert p1.citizen_emotion == "happy" and p1.citizen_intensity == 0.74
    assert p14.citizen_emotion == "happy" and p14.citizen_intensity == 0.72


def test_counselor_voice_seeded_independently_of_citizen_params() -> None:
    """상담원 voice는 seed*7919로 독립 시드 -> 감정 규칙(range/choice/fixed)이 바뀌어도 영향 없음."""
    p = sample_params("강원도", seed=1)
    assert p.counselor_voice == "Hyoeun"
