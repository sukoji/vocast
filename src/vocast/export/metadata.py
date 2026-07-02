from __future__ import annotations

import csv
import re
from pathlib import Path

from vocast.export.layout import sample_rel_dir, sample_uid
from vocast.region_rules import SampleParams

# 4도_통합_음성민원데이터_개선_샘플/metadata.csv 와 동일
METADATA_HEADERS = [
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
]


def _meta_num(v: float | str | int | None) -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, str):
        return v
    f = round(float(v), 2)
    if f == int(f):
        return f"{f:.1f}"
    s = f"{f:.2f}".rstrip("0").rstrip(".")
    return s if "." in s else f"{f:.1f}"


def _full_meta_slot(key: str, value: str) -> str:
    v = (value or "").strip()
    if v:
        return v
    if key in ("smell_duration", "suspected_location", "smell_type", "smell_intensity"):
        return "미언급"
    return ""


def _full_dialogue_text(turn_records: list[dict]) -> str:
    return " ".join((t["text"] or "").strip() for t in turn_records)


def build_sample_metadata_rows(
    *,
    job: dict,
    params: SampleParams,
    folder_name: str,
    turn_records: list[dict],
    full_file_name: str,
) -> list[dict]:
    uid = sample_uid(job["region"], job["scenario_id"])
    rel_base = sample_rel_dir(job["region"], folder_name)
    meta = job.get("meta") or {}
    rows: list[dict] = []

    for tr in turn_records:
        rows.append({
            "uid": uid,
            "region": job["region"],
            "scenario_id": str(job["scenario_id"]),
            "turn_index": str(tr["turn_index"]),
            "speaker": tr["speaker"],
            "voice_name": tr["voice_name"],
            "emotion": tr["emotion"],
            "intensity": _meta_num(tr["intensity"]),
            "tempo": _meta_num(tr["tempo"]),
            "location_address": "",
            "location_detail": "",
            "smell_type": "",
            "smell_intensity": "",
            "smell_duration": "",
            "suspected_location": "",
            "text": tr["text"],
            "file": str((rel_base / tr["filename"]).as_posix()),
        })

    rows.append({
        "uid": uid,
        "region": job["region"],
        "scenario_id": str(job["scenario_id"]),
        "turn_index": "full",
        "speaker": "",
        "voice_name": "",
        "emotion": "",
        "intensity": "",
        "tempo": "",
        "location_address": meta.get("location_address", "").strip(),
        "location_detail": meta.get("complainant_location_text", "").strip(),
        "smell_type": _full_meta_slot("smell_type", meta.get("smell_type", "")),
        "smell_intensity": _full_meta_slot("smell_intensity", meta.get("smell_intensity", "")),
        "smell_duration": _full_meta_slot("smell_duration", meta.get("smell_duration", "")),
        "suspected_location": _full_meta_slot("suspected_location", meta.get("suspected_location_text", "")),
        "text": _full_dialogue_text(turn_records),
        "file": str((rel_base / full_file_name).as_posix()),
    })

    return rows


def append_metadata_rows(
    path: Path,
    *,
    job: dict,
    params: SampleParams,
    folder_name: str,
    turn_records: list[dict],
    full_file_name: str,
) -> None:
    """Append one sample block; use rebuild_batch_metadata for clean rewrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_sample_metadata_rows(
        job=job,
        params=params,
        folder_name=folder_name,
        turn_records=turn_records,
        full_file_name=full_file_name,
    )
    write_header = not path.is_file() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=METADATA_HEADERS)
        if write_header:
            w.writeheader()
        w.writerows(rows)


def rebuild_batch_metadata(batch_dir: Path, jobs: list[dict]) -> int:
    """Rewrite metadata.csv for a batch from manifest jobs + on-disk samples."""
    from vocast.export.layout import citizen_turn_name, full_dialogue_name, sample_folder_name
    from vocast.region_rules import sample_params

    dataset_root = batch_dir / "4도_통합_음성민원데이터"
    meta_path = dataset_root / "metadata.csv"
    all_rows: list[dict] = []

    for job in jobs:
        params = sample_params(job["region"], seed=job["param_seed"])
        folder_name = sample_folder_name(
            job["region"], job["scenario_id"], params, variant_id=job["variant_id"]
        )
        sample_dir = dataset_root / job["region"] / folder_name
        if not sample_dir.is_dir():
            prefix = f"{job['region']}_id{job['scenario_id']}_"
            region_dir = dataset_root / job["region"]
            if region_dir.is_dir():
                for cand in sorted(region_dir.iterdir()):
                    if not cand.is_dir() or not cand.name.startswith(prefix):
                        continue
                    if job["variant_id"] == "tts_only" and "__" in cand.name:
                        continue
                    if job["variant_id"] != "tts_only":
                        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", job["variant_id"])
                        if not cand.name.endswith(f"__{slug}"):
                            continue
                    sample_dir = cand
                    folder_name = cand.name
                    break
            if not sample_dir.is_dir():
                continue
        full_name = full_dialogue_name(params)
        if not (sample_dir / full_name).is_file():
            continue

        turn_records = []
        for i, (spk, text) in enumerate(job["turns"]):
            turn_idx = i + 1
            if spk == "상담원":
                fname = f"t{turn_idx:02d}_sang-{params.counselor_voice}.wav"
                emo, intensity, tempo = params.counselor_emotion, params.counselor_intensity, params.counselor_tempo
                vname = params.counselor_voice
            else:
                fname = citizen_turn_name(i, params)
                emo, intensity, tempo = params.citizen_emotion, params.citizen_intensity, params.citizen_tempo
                vname = params.citizen_voice
            if not (sample_dir / fname).is_file():
                continue
            turn_records.append({
                "turn_index": turn_idx,
                "speaker": spk,
                "voice_name": vname,
                "emotion": emo,
                "intensity": intensity,
                "tempo": tempo,
                "text": text,
                "filename": fname,
            })

        if not turn_records:
            continue
        all_rows.extend(
            build_sample_metadata_rows(
                job=job,
                params=params,
                folder_name=folder_name,
                turn_records=turn_records,
                full_file_name=full_name,
            )
        )

    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=METADATA_HEADERS)
        w.writeheader()
        w.writerows(all_rows)
    return len(all_rows)


def merge_metadata_csv(batch_dirs: list[Path], out_path: Path) -> int:
    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for bdir in batch_dirs:
        for mf in sorted(bdir.rglob("metadata.csv")):
            with mf.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    key = (row.get("uid", ""), row.get("turn_index", ""), row.get("file", ""))
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(row)
    rows.sort(key=lambda r: (r.get("region", ""), r.get("uid", ""), r.get("turn_index", "") == "full", r.get("turn_index", "")))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=METADATA_HEADERS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)
