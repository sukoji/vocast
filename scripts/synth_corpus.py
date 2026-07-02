#!/usr/bin/env python3
"""Synthesize RVC training corpus (Typecast → training_data/{name}/vocals)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vocast.train.corpus import (  # noqa: E402
    load_train_config,
    resolve_dataset_path,
    synth_corpus_from_dataset,
    synth_corpus_from_texts,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="train_targets.yaml key e.g. typecast_jihoon")
    ap.add_argument("--dataset", type=Path, default=None, help="audio_dataset root")
    ap.add_argument("--region", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--texts", type=Path, default=None, help="corpus_texts.jsonl (portable mode)")
    ap.add_argument("--no-skip-existing", action="store_true")
    args = ap.parse_args()

    cfg = load_train_config()
    if args.target not in cfg["targets"]:
        sys.exit(f"[!] unknown target: {args.target}")
    t = cfg["targets"][args.target]
    defaults = cfg.get("corpus_defaults", {})
    region = args.region or defaults.get("region", "전라도")
    tts_model = defaults.get("tts_model", "ssfm-v30")

    if args.texts:
        meta = synth_corpus_from_texts(
            name=args.target,
            voice_id=t["voice_id"],
            texts_path=args.texts,
            tts_model=tts_model,
            skip_existing=not args.no_skip_existing,
        )
    else:
        ds = resolve_dataset_path(str(args.dataset) if args.dataset else None)
        meta = synth_corpus_from_dataset(
            name=args.target,
            voice_id=t["voice_id"],
            dataset_root=ds,
            region=region,
            limit=args.limit,
            tts_model=tts_model,
            skip_existing=not args.no_skip_existing,
        )

    print(f"\n[corpus] {meta['n_files']} files · {meta['total_min']} min")
    print(f"  → {meta['out_vocals']}")
    exp = defaults.get("expected_wav_count")
    if exp and meta["n_files"] < exp:
        print(f"  [!] expected ~{exp} wav — corpus incomplete")


if __name__ == "__main__":
    main()
