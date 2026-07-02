from __future__ import annotations

import re
from pathlib import Path

from vocast.region_rules import SampleParams


def _fmt_num(v: float) -> str:
    """Zip sample paths always use two decimal places (e.g. i1.30, tempo0.95)."""
    return f"{v:.2f}"


def sample_uid(region: str, scenario_id: int, *, source_uid: str = "") -> str:
    """Zip format uid: {region}_id{scenario_id}. source_uid kept for internal manifest only."""
    return f"{region}_id{scenario_id}"


def sample_folder_name(
    region: str,
    scenario_id: int,
    params: SampleParams,
    *,
    variant_id: str,
) -> str:
    base = (
        f"{region}_id{scenario_id}"
        f"_min-{params.citizen_voice}"
        f"_{params.citizen_emotion}"
        f"_i{_fmt_num(params.citizen_intensity)}"
        f"_tempo{_fmt_num(params.citizen_tempo)}"
        f"_sang-{params.counselor_voice}"
    )
    if variant_id == "tts_only":
        return base
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", variant_id)
    return f"{base}__{slug}"


def citizen_turn_name(turn_idx: int, params: SampleParams) -> str:
    n = turn_idx + 1
    return (
        f"t{n:02d}_min_{params.citizen_emotion}"
        f"_i{_fmt_num(params.citizen_intensity)}"
        f"_tempo{_fmt_num(params.citizen_tempo)}.wav"
    )


def counselor_turn_name(turn_idx: int, counselor_voice: str) -> str:
    n = turn_idx + 1
    return f"t{n:02d}_sang-{counselor_voice}.wav"


def full_dialogue_name(params: SampleParams) -> str:
    return (
        f"full__min_{params.citizen_emotion}"
        f"_i{_fmt_num(params.citizen_intensity)}"
        f"_tempo{_fmt_num(params.citizen_tempo)}.wav"
    )


def sample_rel_dir(region: str, folder_name: str) -> Path:
    return Path(region) / folder_name
