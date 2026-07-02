#!/usr/bin/env python3
"""Export counselor texts from audio_dataset → portable training/corpus_texts.jsonl."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.train.corpus import resolve_dataset_path  # noqa: E402

SAMPLE_RE = re.compile(r"^.+\d{4}$")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=None)
    ap.add_argument("--region", default="전라도")
    ap.add_argument("--out", type=Path, default=ROOT / "training" / "corpus_texts.jsonl")
    args = ap.parse_args()

    ds = resolve_dataset_path(str(args.dataset) if args.dataset else None)
    region_root = ds / args.region
    args.out.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with args.out.open("w", encoding="utf-8") as f:
        for sample_dir in sorted(region_root.iterdir()):
            if not sample_dir.is_dir() or not SAMPLE_RE.match(sample_dir.name):
                continue
            mp = sample_dir / "meta.json"
            if not mp.is_file():
                continue
            rec = json.loads(mp.read_text(encoding="utf-8"))
            sid = rec.get("sample_id") or sample_dir.name
            for turn in rec.get("turns") or []:
                if turn.get("speaker") != "상담원":
                    continue
                text = (turn.get("text") or "").strip()
                if text:
                    f.write(json.dumps({"sample_id": sid, "turn_idx": turn["turn_idx"], "text": text}, ensure_ascii=False) + "\n")
                    n += 1

    print(f"[+] {n} lines → {args.out}")


if __name__ == "__main__":
    main()
