from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from vocast.csv_reader import read_scenarios
from vocast.paths import CONFIG, ROOT


def load_pipeline_config() -> dict:
    return yaml.safe_load((CONFIG / "pipeline.yaml").read_text(encoding="utf-8"))


def expand_jobs(
    csv_path: Path,
    *,
    variants: list[dict] | None = None,
    batch_id: str | None = None,
    per_region: int = 0,
) -> list[dict]:
    """CSV rows → unique jobs (job_id UUID). 제주도 skipped by csv_reader."""
    cfg = load_pipeline_config()
    variants = variants or cfg["variants"]
    batch_id = batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scenarios = read_scenarios(csv_path)

    if per_region > 0:
        from collections import defaultdict
        by_region: dict[str, list[dict]] = defaultdict(list)
        for sc in scenarios:
            by_region[sc["region"]].append(sc)
        scenarios = []
        for region in sorted(by_region):
            scenarios.extend(by_region[region][:per_region])

    jobs: list[dict] = []

    for sc in scenarios:
        for var in variants:
            job_id = str(uuid.uuid4())
            jobs.append({
                "job_id": job_id,
                "batch_id": batch_id,
                "variant_id": var["id"],
                "rvc": bool(var.get("rvc")),
                "rvc_model": var.get("model"),
                "source_uid": sc.get("uid") or "",
                "scenario_id": sc["scenario_id"],
                "region": sc["region"],
                "source_csv": str(csv_path.relative_to(ROOT)) if csv_path.is_relative_to(ROOT) else str(csv_path),
                "param_seed": sc["scenario_id"],  # generate_tts.py와 동일: scenario_id 기반 재현 가능 시드
                "meta": {
                    "location_address": sc["location_address"],
                    "complainant_location_text": sc["complainant_location_text"],
                    "smell_type": sc["smell_type"],
                    "smell_intensity": sc["smell_intensity"],
                    "smell_duration": sc["smell_duration"],
                    "suspected_location_text": sc["suspected_location_text"],
                },
                "turns": sc["turns"],
                "dialogue": sc["dialogue"],
                "status": "pending",
            })
    return jobs


def write_manifest(jobs: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for job in jobs:
            f.write(json.dumps(job, ensure_ascii=False) + "\n")


def read_manifest(path: Path) -> list[dict]:
    jobs = []
    with path.open(encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                jobs.append(json.loads(ln))
    return jobs


def shard_manifest(jobs: list[dict], shard_idx: int, shard_count: int) -> list[dict]:
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    return [j for i, j in enumerate(jobs) if i % shard_count == shard_idx]


def claim_jobs(manifest_path: Path, job_ids: set[str]) -> list[dict]:
    """Load only jobs whose job_id is in the set."""
    return [j for j in read_manifest(manifest_path) if j["job_id"] in job_ids]
