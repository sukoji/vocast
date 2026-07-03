from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


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
