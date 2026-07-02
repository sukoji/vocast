# RVC training stack (not in git — ~26GB)

`rvc_train/` and pretrained assets are **not** committed. Use one of:

## Option A — Symlink from existing server install (recommended)

```bash
cd vocast
bash scripts/setup_rvc_stack.sh
# Links rvc_train from ~/dialect/llm_dialect_test/rvc_stack
```

## Option B — Environment variables

```bash
export RVC_STACK_ROOT=/path/to/rvc_stack   # must contain rvc_train/ + train_rvc.py
export RVC_MODELS_ROOT=/path/to/vocast/models/weights
export RVC_PYTHON=/path/to/conda/envs/rvc/bin/python
```

## Training flow

```bash
# 1) Corpus (Typecast resynth of counselor texts, ~599 wav)
python scripts/synth_corpus.py --target typecast_seohyeon

# 2) Train (GPU, ~1–4h for 200 epochs)
python scripts/train_rvc.py --target typecast_seohyeon

# Or full pipeline:
bash scripts/train_pipeline.sh typecast_seohyeon
```

Outputs: `models/weights/{name}/{name}.pth` + `.index`, auto-registered in `models/models.yaml`.

Training logs/cache: `rvc_stack/rvc_train/logs/{exp}/` (skip-existing on re-run).
