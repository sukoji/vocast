from __future__ import annotations

from pathlib import Path

import yaml

from vocast.paths import MODELS_DIR


def register_trained_model(
    name: str,
    weights_dir: Path,
    *,
    version: str = "v2",
) -> None:
    """Add or update entry in models/models.yaml after training."""
    pth = weights_dir / f"{name}.pth"
    if not pth.is_file():
        raise FileNotFoundError(pth)

    indices = sorted(weights_dir.glob("added_IVF*.index"))
    index_rel = None
    if indices:
        index_rel = f"{name}/{indices[-1].name}"

    models_yaml = MODELS_DIR / "models.yaml"
    cfg = yaml.safe_load(models_yaml.read_text(encoding="utf-8"))
    cfg.setdefault("models", {})
    cfg["models"][name] = {
        "pth": f"{name}/{name}.pth",
        "index": index_rel,
        "version": version,
    }
    models_yaml.write_text(
        yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    print(f"[register] {name} → models/models.yaml")
