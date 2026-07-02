#!/usr/bin/env python3
"""Process manifest jobs into result/batches/{batch_id}/."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.manifest import read_manifest  # noqa: E402
from vocast.worker import process_job  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0, help="max jobs (0=all)")
    ap.add_argument("--skip-done", action="store_true", help="skip jobs with done marker")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    jobs = read_manifest(args.manifest)
    if args.limit:
        jobs = jobs[: args.limit]

    done = 0
    for job in jobs:
        marker = Path(job.get("sample_dir", ""))  # not set pre-run
        status_path = ROOT / "work" / f"{job['job_id']}.done"
        if args.skip_done and status_path.is_file():
            continue
        print(f"\n[job] {job['job_id']} scenario={job['scenario_id']} variant={job['variant_id']}")
        try:
            result = process_job(job, device=args.device)
            status_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            done += 1
        except Exception as e:
            print(f"[!] FAILED {job['job_id']}: {e}")
            err = ROOT / "work" / f"{job['job_id']}.error"
            err.write_text(str(e), encoding="utf-8")

    print(f"\n[+] completed {done}/{len(jobs)} jobs")


if __name__ == "__main__":
    main()
