# -*- coding: utf-8 -*-
"""RVC v2 (40k) training — vocast wrapper (outputs to RVC_MODELS_ROOT)."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path
from random import shuffle

import numpy as np

os.environ.setdefault("USE_LIBUV", "0")

STACK = Path(__file__).resolve().parent
PROJECT = STACK.parent
REPO = STACK / "rvc_train"
MODELS = Path(os.environ.get("RVC_MODELS_ROOT", STACK / "models"))
PY = os.environ.get("RVC_PYTHON", sys.executable)
EXP = os.environ.get("RVC_EXP", "ssk")
SR, SRN, VERSION = "40k", 40000, "v2"
VOCALS = os.environ.get(
    "RVC_VOCALS",
    str(PROJECT / "training_data" / "ssk" / "vocals"),
)
EPOCHS = int(os.environ.get("RVC_EPOCHS", "200"))
SAVE_EVERY = int(os.environ.get("RVC_SAVE_EVERY", "50"))
BS = int(os.environ.get("RVC_BS", "4"))
OUT_NAME = os.environ.get("RVC_OUT", "SungSiKyung")
GPUS = os.environ.get("RVC_GPUS", "0")
PG = os.environ.get("RVC_PG", "assets/pretrained_v2/f0G40k.pth")
PD = os.environ.get("RVC_PD", "assets/pretrained_v2/f0D40k.pth")

os.chdir(REPO)
expdir = os.path.join(REPO, "logs", EXP).replace("\\", "/")
os.makedirs(expdir, exist_ok=True)


def run(cmd: str, label: str) -> None:
    print(f"\n=== {label} ===\n>> {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, cwd=REPO)
    if r.returncode != 0:
        raise SystemExit(f"[FAIL] {label} rc={r.returncode}")


def have(d: str) -> bool:
    return os.path.isdir(d) and len(os.listdir(d)) > 0


if have(f"{expdir}/0_gt_wavs"):
    print("[skip] preprocess (0_gt_wavs present)", flush=True)
else:
    run(
        f'"{PY}" infer/modules/train/preprocess.py "{VOCALS}" {SRN} 4 "{expdir}" False 3.0',
        "preprocess",
    )

if have(f"{expdir}/2a_f0"):
    print("[skip] extract_f0 (2a_f0 present)", flush=True)
else:
    run(
        f'"{PY}" infer/modules/train/extract/extract_f0_rmvpe.py 1 0 0 "{expdir}" True',
        "extract_f0_rmvpe",
    )

if have(f"{expdir}/3_feature768"):
    print("[skip] extract_feature (3_feature768 present)", flush=True)
else:
    run(
        f'"{PY}" infer/modules/train/extract_feature_print.py cuda:0 1 0 0 "{expdir}" {VERSION} True',
        "extract_feature",
    )

gt, feat = f"{expdir}/0_gt_wavs", f"{expdir}/3_feature768"
f0, f0nsf = f"{expdir}/2a_f0", f"{expdir}/2b-f0nsf"
names = (
    set(n.split(".")[0] for n in os.listdir(gt))
    & set(n.split(".")[0] for n in os.listdir(feat))
    & set(n.split(".")[0] for n in os.listdir(f0))
    & set(n.split(".")[0] for n in os.listdir(f0nsf))
)
mute = f"{REPO}/logs/mute".replace("\\", "/")
opt = [
    f"{gt}/{n}.wav|{feat}/{n}.npy|{f0}/{n}.wav.npy|{f0nsf}/{n}.wav.npy|0"
    for n in names
]
for _ in range(2):
    opt.append(
        f"{mute}/0_gt_wavs/mute40k.wav|{mute}/3_feature768/mute.npy|"
        f"{mute}/2a_f0/mute.wav.npy|{mute}/2b-f0nsf/mute.wav.npy|0"
    )
shuffle(opt)
with open(f"{expdir}/filelist.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(opt))
print(f"[filelist] {len(opt)} entries ({len(names)} real samples)", flush=True)
shutil.copy(os.path.join(REPO, "configs", "v1", "40k.json"), f"{expdir}/config.json")

run(
    f'"{PY}" infer/modules/train/train.py -e {EXP} -sr {SR} -f0 1 -bs {BS} -g {GPUS} '
    f'-te {EPOCHS} -se {SAVE_EVERY} -pg {PG} '
    f'-pd {PD} -l 1 -c 1 -sw 1 -v {VERSION}',
    "train",
)

import faiss

npys = [np.load(f"{feat}/{n}") for n in sorted(os.listdir(feat))]
big = np.concatenate(npys, 0)
perm = np.arange(big.shape[0])
np.random.shuffle(perm)
big = big[perm]
n_ivf = min(int(16 * np.sqrt(big.shape[0])), big.shape[0] // 39)
index = faiss.index_factory(768, f"IVF{n_ivf},Flat")
faiss.extract_index_ivf(index).nprobe = 1
index.train(big)
for i in range(0, big.shape[0], 8192):
    index.add(big[i : i + 8192])
idxpath = f"{expdir}/added_IVF{n_ivf}_Flat_nprobe_1_{EXP}_v2.index"
faiss.write_index(index, idxpath)
print(f"[index] {idxpath}", flush=True)

modeldir = MODELS / OUT_NAME
modeldir.mkdir(parents=True, exist_ok=True)
weights = glob.glob(os.path.join(REPO, "assets", "weights", f"{EXP}*.pth"))
weights.sort(key=os.path.getmtime)
if not weights:
    raise SystemExit("[FAIL] no trained weight produced")
shutil.copy(weights[-1], modeldir / f"{OUT_NAME}.pth")
shutil.copy(idxpath, modeldir / os.path.basename(idxpath))
print(
    f"[DONE] -> {modeldir}\n"
    f"  pth: {os.path.basename(weights[-1])}\n"
    f"  idx: {os.path.basename(idxpath)}",
    flush=True,
)
