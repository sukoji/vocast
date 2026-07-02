from __future__ import annotations

import argparse
import sys
import traceback
from collections import OrderedDict
from pathlib import Path

import torch


def load_weight_and_cfg(path: Path):
    c = torch.load(path, map_location="cpu")
    cfg = c.get("config")
    if "model" in c:
        a = c["model"]
        w = OrderedDict()
        for k in a.keys():
            if "enc_q" in k:
                continue
            w[k] = a[k]
    else:
        w = c["weight"]
    return w, cfg


def blend_models(
    a: Path,
    b: Path,
    *,
    alpha: float,
    sr: str,
    version: str,
    f0: int,
    out: Path,
) -> Path:
    w1, cfg = load_weight_and_cfg(a)
    w2, _ = load_weight_and_cfg(b)
    if sorted(w1.keys()) != sorted(w2.keys()):
        raise ValueError(f"architecture mismatch: {a.name} vs {b.name}")
    opt = OrderedDict()
    opt["weight"] = {}
    for k in w1.keys():
        if k == "emb_g.weight" and w1[k].shape != w2[k].shape:
            m = min(w1[k].shape[0], w2[k].shape[0])
            opt["weight"][k] = (alpha * w1[k][:m].float() + (1 - alpha) * w2[k][:m].float()).half()
        else:
            opt["weight"][k] = (alpha * w1[k].float() + (1 - alpha) * w2[k].float()).half()
    opt["config"] = cfg
    opt["sr"] = sr
    opt["f0"] = f0
    opt["version"] = version
    opt["info"] = f"blend {alpha:.2f}*A + {1-alpha:.2f}*B"
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(opt, out)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Blend two RVC .pth models")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--sr", default="40k")
    ap.add_argument("--version", default="v2")
    ap.add_argument("--f0", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        blend_models(
            Path(args.a), Path(args.b),
            alpha=args.alpha, sr=args.sr, version=args.version, f0=args.f0,
            out=Path(args.out),
        )
        print(f"[+] {args.out}")
    except Exception:
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
