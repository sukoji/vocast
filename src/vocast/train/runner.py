from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from vocast.paths import ROOT

TRAINING_DATA = ROOT / "training_data"
RVC_STACK = Path(os.environ.get("RVC_STACK_ROOT", ROOT / "rvc_stack"))
TRAIN_SCRIPT = RVC_STACK / "train_rvc.py"
RVC_TRAIN_REPO = RVC_STACK / "rvc_train"


def models_weights_root() -> Path:
    return Path(os.environ.get("RVC_MODELS_ROOT", ROOT / "models" / "weights"))


def rvc_python() -> Path:
    if env := os.environ.get("RVC_PYTHON"):
        return Path(env)
    for c in (ROOT / ".venv" / "bin" / "python", sys.executable):
        if Path(c).is_file():
            return Path(c)
    return Path(sys.executable)


def ensure_stack() -> None:
    if not TRAIN_SCRIPT.is_file():
        raise FileNotFoundError(
            f"RVC train script missing: {TRAIN_SCRIPT}\n"
            "  Run: bash scripts/setup_rvc_stack.sh"
        )
    if not RVC_TRAIN_REPO.is_dir():
        raise FileNotFoundError(
            f"RVC training repo missing: {RVC_TRAIN_REPO}\n"
            "  Symlink or copy rvc_train (~26GB) — see rvc_stack/README.md"
        )


def normalize_gpus(gpu: str) -> tuple[str, str]:
    gpu = gpu.strip()
    if "-" in gpu and "," not in gpu:
        parts = [p.strip() for p in gpu.split("-") if p.strip()]
        return "-".join(parts), ",".join(parts)
    if "," in gpu:
        parts = [p.strip() for p in gpu.split(",") if p.strip()]
        return "-".join(parts), ",".join(parts)
    return gpu, gpu


def run_training(
    *,
    name: str,
    vocals_dir: Path,
    out_model: str | None = None,
    epochs: int = 200,
    batch_size: int = 8,
    gpu: str = "0",
    exp: str | None = None,
) -> Path:
    ensure_stack()
    if not vocals_dir.is_dir() or not list(vocals_dir.glob("*.wav")):
        raise FileNotFoundError(f"no training wavs in {vocals_dir}")

    py = rvc_python()
    out_name = out_model or name
    exp_name = exp or name.replace("-", "_")
    rvc_gpus, cuda_devices = normalize_gpus(gpu)
    n_gpus = len(rvc_gpus.split("-"))
    bs = batch_size * n_gpus if n_gpus > 1 else batch_size

    env = os.environ.copy()
    env["RVC_VOCALS"] = str(vocals_dir.resolve())
    env["RVC_EXP"] = exp_name
    env["RVC_OUT"] = out_name
    env["RVC_EPOCHS"] = str(epochs)
    env["RVC_BS"] = str(bs)
    env["RVC_GPUS"] = rvc_gpus
    env["CUDA_VISIBLE_DEVICES"] = cuda_devices
    env["RVC_PYTHON"] = str(py)
    env.setdefault("RVC_STACK_ROOT", str(RVC_STACK))
    env.setdefault("RVC_MODELS_ROOT", str(models_weights_root()))

    print(f"[train] vocals={vocals_dir} ({len(list(vocals_dir.glob('*.wav')))} wav)")
    print(f"        exp={exp_name} epochs={epochs} out={out_name} gpu={rvc_gpus}")

    r = subprocess.run([str(py), str(TRAIN_SCRIPT)], env=env, cwd=str(TRAIN_SCRIPT.parent))
    if r.returncode != 0:
        raise RuntimeError(f"training failed rc={r.returncode}")

    out_dir = models_weights_root() / out_name
    pth = out_dir / f"{out_name}.pth"
    if not pth.is_file():
        raise FileNotFoundError(f"expected weight not found: {pth}")
    return out_dir
