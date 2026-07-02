#!/usr/bin/env python3
"""Rebuild metadata.csv from manifest + existing wav output (zip format)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.export.metadata import rebuild_batch_metadata  # noqa: E402
from vocast.manifest import read_manifest  # noqa: E402
from vocast.paths import BATCHES_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()

    jobs = read_manifest(args.manifest)
    batch_dir = BATCHES_DIR / args.batch_id
    n = rebuild_batch_metadata(batch_dir, jobs)
    print(f"[+] metadata rows: {n}")
    print(f"    → {batch_dir / '4도_통합_음성민원데이터' / 'metadata.csv'}")


if __name__ == "__main__":
    main()
