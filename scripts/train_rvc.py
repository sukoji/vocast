#!/usr/bin/env python3
"""Train RVC model from training_data/{target}/vocals."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.train.corpus import load_train_config  # noqa: E402
from vocast.train.paths import TRAINING_DATA  # noqa: E402
from vocast.train.register import register_trained_model  # noqa: E402
from vocast.train.runner import run_training  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--gpu", default=None)
    ap.add_argument("--no-register", action="store_true")
    args = ap.parse_args()

    cfg = load_train_config()
    if args.target not in cfg["targets"]:
        sys.exit(f"[!] unknown target: {args.target}")
    t = cfg["targets"][args.target]
    tr = t.get("train", {})

    vocals = TRAINING_DATA / args.target / "vocals"
    out_dir = run_training(
        name=args.target,
        vocals_dir=vocals,
        out_model=args.target,
        epochs=args.epochs or tr.get("epochs", 200),
        batch_size=args.batch_size or tr.get("batch_size", 8),
        gpu=args.gpu or tr.get("gpu", "0"),
    )

    if not args.no_register:
        register_trained_model(args.target, out_dir)
    print(f"\n[done] {out_dir}")


if __name__ == "__main__":
    main()
