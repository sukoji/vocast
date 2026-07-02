from __future__ import annotations

import csv
from pathlib import Path

from vocast.export.layout import (
    citizen_turn_name,
    counselor_turn_name,
    sample_rel_dir,
    sample_uid,
)
from vocast.region_rules import SampleParams

METADATA_HEADERS = [
    "job_id",
    "batch_id",
    "variant_id",
    "uid",
    "region",
    "scenario_id",
    "turn_index",
    "speaker",
    "voice_name",
    "emotion",
    "intensity",
    "tempo",
    "location_address",
    "location_detail",
    "smell_type",
    "smell_intensity",
    "smell_duration",
    "suspected_location",
    "text",
    "file",
    "rvc_applied",
    "rvc_model",
]


def append_metadata_rows(
    path: Path,
    *,
    job: dict,
    params: SampleParams,
    folder_name: str,
    turn_records: list[dict],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.is_file() or path.stat().st_size == 0
    uid = sample_uid(job["region"], job["scenario_id"])
    rel_base = sample_rel_dir(job["region"], folder_name)

    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=METADATA_HEADERS)
        if write_header:
            w.writeheader()
        meta = job.get("meta") or {}
        for tr in turn_records:
            rel_file = rel_base / tr["filename"]
            w.writerow({
                "job_id": job["job_id"],
                "batch_id": job["batch_id"],
                "variant_id": job["variant_id"],
                "uid": uid,
                "region": job["region"],
                "scenario_id": job["scenario_id"],
                "turn_index": tr["turn_index"],
                "speaker": tr["speaker"],
                "voice_name": tr["voice_name"],
                "emotion": tr["emotion"],
                "intensity": tr["intensity"],
                "tempo": tr["tempo"],
                "location_address": meta.get("location_address", ""),
                "location_detail": meta.get("complainant_location_text", ""),
                "smell_type": meta.get("smell_type", ""),
                "smell_intensity": meta.get("smell_intensity", ""),
                "smell_duration": meta.get("smell_duration", ""),
                "suspected_location": meta.get("suspected_location_text", ""),
                "text": tr["text"],
                "file": str(rel_file).replace("\\", "/"),
                "rvc_applied": job.get("rvc", False),
                "rvc_model": job.get("rvc_model") or "",
            })


def merge_metadata_csv(batch_dirs: list[Path], out_path: Path) -> int:
    rows: list[dict] = []
    seen_jobs: set[str] = set()
    for bdir in batch_dirs:
        for mf in sorted(bdir.rglob("metadata.csv")):
            with mf.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    jid = row.get("job_id", "")
                    if jid in seen_jobs:
                        continue
                    seen_jobs.add(jid)
                    rows.append(row)
    rows.sort(key=lambda r: (r.get("batch_id", ""), r.get("job_id", "")))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=METADATA_HEADERS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)
