from __future__ import annotations

import csv
from pathlib import Path

from vocast.audio import parse_dialogue

SKIP_REGIONS = {"제주도"}


def read_scenarios(csv_path: Path) -> list[dict]:
    rows: list[dict] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            region = (row.get("region_name") or "").strip()
            if region in SKIP_REGIONS:
                continue
            dialogue = (row.get("out__claude-opus-4-8") or "").strip()
            turns = parse_dialogue(dialogue)
            if len(turns) < 4:
                continue
            rows.append({
                "scenario_id": int(row["scenario_id"]),
                "region": region,
                "location_address": row.get("location_address", ""),
                "complainant_location_text": row.get("complainant_location_text", ""),
                "smell_type": row.get("smell_type", ""),
                "smell_intensity": row.get("smell_intensity", ""),
                "smell_duration": row.get("smell_duration", ""),
                "suspected_location_text": row.get("suspected_location_text", ""),
                "turns": turns,
                "dialogue": "\n\n".join(f"{s}: {t}" for s, t in turns),
            })
    return rows
