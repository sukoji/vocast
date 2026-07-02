#!/usr/bin/env python3
"""Build job manifest from input CSV (제주도 skipped)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.manifest import expand_jobs, shard_manifest, write_manifest  # noqa: E402
from vocast.paths import INPUT_DIR, WORK_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=INPUT_DIR / "20260701_sample.csv")
    ap.add_argument("--batch-id", default=None, help="unique batch id (default: UTC timestamp)")
    ap.add_argument("--out", type=Path, default=None, help="manifest.jsonl path")
    ap.add_argument("--shard", type=int, default=0, help="shard index (0-based)")
    ap.add_argument("--shard-count", type=int, default=1, help="total shards")
    ap.add_argument("--per-region", type=int, default=0, help="max scenarios per region (0=all)")
    ap.add_argument("--variants", default="", help="comma-separated variant ids e.g. tts_only")
    args = ap.parse_args()

    if not args.csv.is_file():
        sys.exit(f"[!] CSV not found: {args.csv}")

    variants = None
    if args.variants.strip():
        want = {v.strip() for v in args.variants.split(",") if v.strip()}
        from vocast.manifest import load_pipeline_config
        cfg = load_pipeline_config()
        variants = [v for v in cfg["variants"] if v["id"] in want]
        if not variants:
            sys.exit(f"[!] no matching variants in {want}")

    jobs = expand_jobs(
        args.csv,
        batch_id=args.batch_id,
        per_region=args.per_region,
        variants=variants,
    )
    if args.shard_count > 1:
        jobs = shard_manifest(jobs, args.shard, args.shard_count)

    out = args.out or WORK_DIR / f"manifest_{args.batch_id or 'latest'}.jsonl"
    if args.shard_count > 1:
        out = out.with_name(f"{out.stem}_shard{args.shard:03d}of{args.shard_count:03d}{out.suffix}")

    write_manifest(jobs, out)
    batch_id = jobs[0]["batch_id"] if jobs else "—"
    print(f"[+] {len(jobs)} jobs → {out}")
    print(f"    batch_id={batch_id}")
    if args.shard_count > 1:
        print(f"    shard {args.shard}/{args.shard_count}")


if __name__ == "__main__":
    main()
