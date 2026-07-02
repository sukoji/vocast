from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
import yaml

from vocast.paths import CONFIG, MODELS_DIR, ROOT


def load_models_yaml() -> dict:
    return yaml.safe_load((MODELS_DIR / "models.yaml").read_text(encoding="utf-8"))


def models_root() -> Path:
    import os
    return Path(os.environ.get("RVC_MODELS_ROOT", MODELS_DIR / "weights"))


def resolve_model(name: str) -> tuple[Path, Path | None, str]:
    cfg = load_models_yaml()
    if name in cfg.get("blends", {}):
        blend_path = ensure_blend(name)
        return blend_path, None, cfg["blends"][name].get("version", "v2")

    if name not in cfg.get("models", {}):
        raise KeyError(f"unknown model: {name}")
    meta = cfg["models"][name]
    root = models_root()
    pth = root / meta["pth"]
    if not pth.is_file():
        raise FileNotFoundError(f"model weights missing: {pth}")
    index = None
    if meta.get("index"):
        ip = root / meta["index"]
        if ip.is_file():
            index = ip
    return pth, index, meta.get("version", "v2")


def ensure_blend(blend_name: str) -> Path:
    cfg = load_models_yaml()
    blend = cfg["blends"][blend_name]
    root = models_root()
    out = root / blend["output"]
    if out.is_file():
        return out
    from vocast.rvc.blend import blend_models

    components = blend["components"]
    paths = []
    weights = []
    for c in components:
        pth, _, _ = resolve_model(c["model"])
        paths.append(pth)
        weights.append(float(c["weight"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    blend_models(
        paths[0], paths[1],
        alpha=weights[0] / (weights[0] + weights[1]) if len(weights) == 2 else weights[0],
        sr=blend.get("sr", "40k"),
        version=blend.get("version", "v2"),
        f0=blend.get("f0", 1),
        out=out,
    )
    return out


def inference_defaults() -> dict:
    return load_models_yaml().get("inference_defaults", {})
