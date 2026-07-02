# vocast

방언 민원 대화 **Typecast TTS → (선택) RVC → 4도 통합 포맷** 파이프라인.

## Layout

```text
vocast/
├── input/           # 시나리오 CSV (20260701_sample.csv 형식)
├── config/          # 룰.txt, region_rules.yaml, voices.yaml
├── models/
│   ├── models.yaml  # RVC 모델 + 블렌드 비율
│   └── weights/     # .pth / .index (gitignore)
├── training_data/   # RVC 학습 코퍼스 (gitignore)
├── rvc_stack/       # train_rvc.py + symlink rvc_train/
├── training/        # portable corpus_texts.jsonl
│   ├── batches/     # worker별 격리 출력 (동시 실행 안전)
│   └── merged/      # merge_batches.py 결과
└── src/vocast/      # 핵심 모듈
```

## ID 정책 (다중 worker / merge 안전)

| 키 | 역할 |
|----|------|
| `job_id` | UUID — **전역 유일키** (metadata·work 추적) |
| `batch_id` | worker 실행 단위 (`result/batches/{batch_id}/`) |
| `variant_id` | `tts_only` / `rvc_*` — 같은 scenario도 variant별 별도 job |
| `uid` | 사람이 읽는 키 (`강원도_id5`) — metadata 참조용 |

- 제주도: **스킵** (`config/region_rules.yaml`)
- TTS 파라미터 시드: `hash(job_id)` — worker 간 재현·충돌 방지
- merge: `job_id` 기준 dedupe → 폴더명 충돌 없음 (variant suffix)

## Quick start

```bash
cd vocast
cp .env.example .env   # TYPECAST_API_KEY
pip install -e .

# 1) manifest (497 scenarios × variants, 제주 제외 → 397×3 = 1191 jobs)
python scripts/build_manifest.py --csv input/20260701_sample.csv --batch-id run01

# 2) shard 분배 (4명이 동시 실행 예시)
python scripts/build_manifest.py --batch-id run01 --shard 0 --shard-count 4
python scripts/build_manifest.py --batch-id run01 --shard 1 --shard-count 4
# ...

# 3) worker (GPU node for RVC jobs)
python scripts/run_worker.py --manifest work/manifest_run01_shard000of004.jsonl

# 4) merge
python scripts/merge_batches.py
# → result/merged/4도_통합_음성민원데이터/
```

## TTS 규칙

`config/룰.txt` / `config/region_rules.yaml` — zip 샘플과 동일 권역별 voice·감정·강도·속도.

## RVC 추론

- `config/pipeline.yaml` → `variants` 에서 `tts_only` / `rvc_*` 지정
- 민원인 턴만 변환, **result에는 최종본만** (TTS 중간파일은 `work/` 임시)
- `models/models.yaml` — 단일 모델 + `blends` (가중치 자동 합성)

## RVC 모델 학습

`rvc_train/` (~26GB)은 Git에 포함되지 않음. 서버에서는 symlink:

```bash
bash scripts/setup_rvc_stack.sh
export VOCAST_CORPUS_DATASET=~/dialect/llm_dialect_test/audio_dataset  # optional
```

| 단계 | 명령 |
|------|------|
| 코퍼스 합성 | `python scripts/synth_corpus.py --target typecast_seohyeon` |
| 학습 (GPU) | `python scripts/train_rvc.py --target typecast_seohyeon` |
| 한방 | `bash scripts/train_pipeline.sh typecast_seohyeon` |
| Slurm | `sbatch scripts/sbatch/train_rvc.sbatch typecast_jihoon` |

- 코퍼스: 전라도 `audio_dataset` 상담원 턴 텍스트 → Typecast 목표 voice로 재합성 (~599 wav)
- 학습 타깃: `config/train_targets.yaml` (jihoon, seohyeon, skylar, yejin, …)
- 산출: `models/weights/{name}/` + `models/models.yaml` 자동 등록
- portable 코퍼스: `python scripts/export_corpus_texts.py` → `training/corpus_texts.jsonl`

자세한 스택 설정: `rvc_stack/README.md`

## Output format

`result/merged/4도_통합_음성민원데이터/` — zip 압축 해제와 동일:

- `{권역}/{권역}_id{N}_min-{민원인}_..._sang-{상담원}/`
- `t01_sang-*.wav`, `t02_min_*.wav`, `full__min_*.wav`
- `metadata.csv` (+ `job_id`, `batch_id`, `variant_id` 컬럼)

RVC variant 폴더는 zip 호환 이름 뒤에 `__rvc-{variant}` suffix.

## Slurm 예시

```bash
BATCH=run01
SHARD=$SLURM_ARRAY_TASK_ID
COUNT=100
python scripts/build_manifest.py --batch-id $BATCH --shard $SHARD --shard-count $COUNT
python scripts/run_worker.py --manifest work/manifest_${BATCH}_shard$(printf '%03d' $SHARD)of$(printf '%03d' $COUNT).jsonl
```

## 모델 가중치

서버에서 학습된 `.pth`를 `models/weights/{name}/`에 복사 후 `models/models.yaml` 경로 확인.

```bash
python -m vocast.rvc.blend models/weights/a.pth models/weights/b.pth --alpha 0.5 --out models/weights/blends/out.pth
```
