#!/usr/bin/env python3
"""Merge result/batches/* into result/merged/ (dedupe by job_id)."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.export.metadata import merge_metadata_csv  # noqa: E402
from vocast.paths import BATCHES_DIR, DATASET_ROOT_NAME, MERGED_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=MERGED_DIR / DATASET_ROOT_NAME)
    args = ap.parse_args()

    batch_dirs = sorted(p for p in BATCHES_DIR.iterdir() if p.is_dir())
    if not batch_dirs:
        sys.exit("[!] no batches in result/batches/")

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    # copy audio trees (job_id folders are unique by construction)
    for bdir in batch_dirs:
        src = bdir / DATASET_ROOT_NAME
        if not src.is_dir():
            continue
        for region_dir in src.iterdir():
            if not region_dir.is_dir() or region_dir.name == "metadata.csv":
                continue
            if region_dir.name.endswith(".csv"):
                continue
            dest_region = args.out / region_dir.name
            dest_region.mkdir(parents=True, exist_ok=True)
            for sample in region_dir.iterdir():
                dest = dest_region / sample.name
                if dest.exists():
                    print(f"[!] skip duplicate folder (should not happen): {dest}")
                    continue
                if sample.is_dir():
                    shutil.copytree(sample, dest)

        rules = src / "룰.txt"
        if rules.is_file():
            shutil.copy(rules, args.out / "룰.txt")

    n = merge_metadata_csv(batch_dirs, args.out / "metadata.csv")
    print(f"[+] merged {len(batch_dirs)} batches → {args.out}")
    print(f"    metadata rows (unique job_id): {n}")


if __name__ == "__main__":
    main()
