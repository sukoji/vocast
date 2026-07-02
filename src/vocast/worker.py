from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from vocast.audio import (
    silence_frames,
    wav_frames_bytes,
    wav_params_bytes,
    write_wav,
)
from vocast.env import load_env
from vocast.export.layout import (
    citizen_turn_name,
    counselor_turn_name,
    full_dialogue_name,
    sample_folder_name,
    sample_rel_dir,
)
from vocast.export.metadata import append_metadata_rows
from vocast.manifest import load_pipeline_config
from vocast.paths import BATCHES_DIR, CONFIG, DATASET_ROOT_NAME, WORK_DIR
from vocast.region_rules import SampleParams, sample_params, voice_id
from vocast.tts.synthesize import resolve_voice_map, synth_turn


def batch_output_dir(batch_id: str) -> Path:
    return BATCHES_DIR / batch_id / DATASET_ROOT_NAME


def process_job(job: dict, *, device: str | None = None) -> dict:
    """Run one manifest job → write wav + metadata into result/batches/{batch_id}/."""
    load_env()
    cfg = load_pipeline_config()
    tts_model = cfg.get("tts_model", "ssfm-v30")
    gap_ms = int(cfg.get("gap_ms", 300))
    device = device or os.environ.get("RVC_DEVICE", "cuda:0")

    params = sample_params(job["region"], seed=job["param_seed"])
    voice_map = resolve_voice_map()
    folder_name = sample_folder_name(
        job["region"], job["scenario_id"], params, variant_id=job["variant_id"]
    )
    out_root = batch_output_dir(job["batch_id"])
    sample_dir = out_root / sample_rel_dir(job["region"], folder_name)
    sample_dir.mkdir(parents=True, exist_ok=True)

    work_dir = WORK_DIR / job["job_id"]
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    from typecast import Typecast
    client = Typecast()

    cz_vid = voice_id(params.citizen_voice, api_map=voice_map)
    cs_vid = voice_id(params.counselor_voice, api_map=voice_map)

    turn_records: list[dict] = []
    segs: list[bytes] = []
    wav_params = None

    for i, (spk, text) in enumerate(job["turns"]):
        is_counselor = spk == "상담원"
        if is_counselor:
            emo, intensity, tempo = params.counselor_emotion, params.counselor_intensity, params.counselor_tempo
            vid, vname = cs_vid, params.counselor_voice
        else:
            emo, intensity, tempo = params.citizen_emotion, params.citizen_intensity, params.citizen_tempo
            vid, vname = cz_vid, params.citizen_voice

        audio, _ = synth_turn(
            client,
            voice_id=vid,
            text=text,
            emotion=emo,
            intensity=intensity,
            tempo=tempo,
            model=tts_model,
        )
        if wav_params is None:
            wav_params = wav_params_bytes(audio)

        tts_path = work_dir / f"tts_{i:02d}.wav"
        tts_path.write_bytes(audio)

        final_path = sample_dir
        if is_counselor:
            fname = counselor_turn_name(i, params.counselor_voice)
            out_wav = sample_dir / fname
            out_wav.write_bytes(audio)
        else:
            fname = citizen_turn_name(i, params)
            if job.get("rvc"):
                from vocast.rvc.adaptive import adaptive_pitch, median_f0_hz, rvc_direction
                from vocast.rvc.engine import RvcEngine
                direction = rvc_direction(params.citizen_voice)
                f0 = median_f0_hz(tts_path)
                pitch = adaptive_pitch(f0, direction)
                engine = RvcEngine(job["rvc_model"], device=device, f0up_key=pitch)
                out_wav = sample_dir / fname
                engine.convert_file(tts_path, out_wav)
            else:
                out_wav = sample_dir / fname
                out_wav.write_bytes(audio)

        if segs:
            segs.append(silence_frames(wav_params, gap_ms))
        segs.append(wav_frames_bytes(out_wav.read_bytes()))

        turn_records.append({
            "turn_index": i + 1,
            "speaker": spk,
            "voice_name": vname,
            "emotion": emo,
            "intensity": intensity,
            "tempo": tempo,
            "text": text,
            "filename": fname,
        })

    full_path = sample_dir / full_dialogue_name(params)
    write_wav(full_path, wav_params, segs)

    meta_path = batch_output_dir(job["batch_id"]) / "metadata.csv"
    append_metadata_rows(
        meta_path,
        job=job,
        params=params,
        folder_name=folder_name,
        turn_records=turn_records,
        full_file_name=full_dialogue_name(params),
    )

    rules_src = CONFIG / "region_rules.yaml"
    rules_dst = out_root / "룰.txt"
    if not rules_dst.is_file() and (CONFIG / "룰.txt").is_file():
        shutil.copy(CONFIG / "룰.txt", rules_dst)

    shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "job_id": job["job_id"],
        "status": "done",
        "sample_dir": str(sample_dir),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
