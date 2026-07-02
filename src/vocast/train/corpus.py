from __future__ import annotations

import json
import re
import wave
from io import BytesIO
from pathlib import Path

import yaml

from vocast.env import load_env
from vocast.paths import CONFIG, ROOT
from vocast.train.paths import TRAINING_DATA

SAMPLE_RE = re.compile(r"^.+\d{4}$")

COUNSELOR_TTS = {
    "emotion_preset": "normal",
    "emotion_intensity": 1.0,
    "audio_tempo": 1.0,
    "audio_pitch": 0,
}


def load_train_config() -> dict:
    return yaml.safe_load((CONFIG / "train_targets.yaml").read_text(encoding="utf-8"))


def resolve_dataset_path(override: str | None = None) -> Path:
    import os
    if override:
        return Path(override).expanduser().resolve()
    cfg = load_train_config()
    ds = cfg.get("corpus_defaults", {}).get("source_dataset")
    if ds:
        return Path(ds).expanduser().resolve()
    env = os.environ.get("VOCAST_CORPUS_DATASET")
    if env:
        return Path(env).expanduser().resolve()
    # server default fallback
    fallback = ROOT.parent / "dialect" / "llm_dialect_test" / "audio_dataset"
    if fallback.is_dir():
        return fallback
    raise FileNotFoundError(
        "corpus dataset not found. Set VOCAST_CORPUS_DATASET or --dataset "
        "to audio_dataset path (전라도/*/meta.json)"
    )


def write_wav(path: Path, params, frames: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(params.nchannels)
        w.setsampwidth(params.sampwidth)
        w.setframerate(params.framerate)
        w.writeframes(frames)


def synth_corpus_from_dataset(
    *,
    name: str,
    voice_id: str,
    dataset_root: Path,
    region: str = "전라도",
    limit: int = 0,
    tts_model: str = "ssfm-v30",
    skip_existing: bool = True,
) -> dict:
    """Resynthesize counselor turns with target Typecast voice → training_data/{name}/vocals."""
    load_env()
    from typecast import Typecast
    from typecast.models import TTSRequest, PresetPrompt, Output, LanguageCode

    client = Typecast()
    vs = {v.voice_id: v for v in client.voices_v2()}
    if voice_id not in vs:
        raise KeyError(f"voice_id not found: {voice_id}")
    vinfo = vs[voice_id]
    versions = [
        m.version.value if hasattr(m.version, "value") else str(m.version)
        for m in vinfo.models
    ]
    mdl = tts_model if tts_model in versions else (versions[0] if versions else tts_model)

    region_root = dataset_root / region
    out_dir = TRAINING_DATA / name / "vocals"
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = sorted(d for d in region_root.iterdir() if d.is_dir() and SAMPLE_RE.match(d.name))
    if limit:
        samples = samples[:limit]

    total_sec = 0.0
    n = 0
    sample_ids: list[str] = []

    for sample_dir in samples:
        mp = sample_dir / "meta.json"
        if not mp.is_file():
            continue
        rec = json.loads(mp.read_text(encoding="utf-8"))
        sid = rec.get("sample_id") or sample_dir.name
        for turn in rec.get("turns") or []:
            if turn.get("speaker") != "상담원":
                continue
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            fname = f"{sid}_t{turn['turn_idx']:02d}.wav"
            out_path = out_dir / fname
            if skip_existing and out_path.is_file() and out_path.stat().st_size > 0:
                with wave.open(str(out_path), "rb") as w:
                    total_sec += w.getnframes() / w.getframerate()
                n += 1
                continue

            resp = client.text_to_speech(
                TTSRequest(
                    text=text,
                    model=mdl,
                    voice_id=voice_id,
                    language=LanguageCode.KOR,
                    prompt=PresetPrompt(
                        emotion_type="preset",
                        emotion_preset=COUNSELOR_TTS["emotion_preset"],
                        emotion_intensity=COUNSELOR_TTS["emotion_intensity"],
                    ),
                    output=Output(
                        audio_format="wav",
                        audio_tempo=COUNSELOR_TTS["audio_tempo"],
                        audio_pitch=COUNSELOR_TTS["audio_pitch"],
                    ),
                )
            )
            wb = resp.audio_data
            with wave.open(BytesIO(wb), "rb") as w:
                params = w.getparams()
                frames = w.readframes(w.getnframes())
                total_sec += w.getnframes() / w.getframerate()
            write_wav(out_path, params, frames)
            n += 1
            if n % 50 == 0:
                print(f"  ... {n} wav")

        sample_ids.append(sid)

    meta = {
        "name": name,
        "voice_id": voice_id,
        "voice_name": vinfo.voice_name,
        "gender": str(vinfo.gender),
        "region": region,
        "dataset_root": str(dataset_root),
        "samples": sample_ids,
        "n_files": n,
        "total_min": round(total_sec / 60, 2),
        "tts_model": mdl,
        "out_vocals": str(out_dir),
    }
    (out_dir.parent / "corpus_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def synth_corpus_from_texts(
    *,
    name: str,
    voice_id: str,
    texts_path: Path,
    tts_model: str = "ssfm-v30",
    skip_existing: bool = True,
) -> dict:
    """Synthesize from training/corpus_texts.jsonl ({\"text\": \"...\"} per line)."""
    load_env()
    from typecast import Typecast
    from typecast.models import TTSRequest, PresetPrompt, Output, LanguageCode

    client = Typecast()
    vs = {v.voice_id: v for v in client.voices_v2()}
    vinfo = vs[voice_id]
    versions = [
        m.version.value if hasattr(m.version, "value") else str(m.version)
        for m in vinfo.models
    ]
    mdl = tts_model if tts_model in versions else (versions[0] if versions else tts_model)

    out_dir = TRAINING_DATA / name / "vocals"
    out_dir.mkdir(parents=True, exist_ok=True)
    total_sec = 0.0
    n = 0

    with texts_path.open(encoding="utf-8") as f:
        for i, ln in enumerate(f):
            ln = ln.strip()
            if not ln:
                continue
            rec = json.loads(ln)
            text = (rec.get("text") or "").strip()
            if not text:
                continue
            fname = f"line_{i:05d}.wav"
            out_path = out_dir / fname
            if skip_existing and out_path.is_file():
                n += 1
                continue
            resp = client.text_to_speech(
                TTSRequest(
                    text=text,
                    model=mdl,
                    voice_id=voice_id,
                    language=LanguageCode.KOR,
                    prompt=PresetPrompt(emotion_type="preset", emotion_preset="normal", emotion_intensity=1.0),
                    output=Output(audio_format="wav", audio_tempo=1.0, audio_pitch=0),
                )
            )
            wb = resp.audio_data
            with wave.open(BytesIO(wb), "rb") as w:
                params = w.getparams()
                frames = w.readframes(w.getnframes())
                total_sec += w.getnframes() / w.getframerate()
            write_wav(out_path, params, frames)
            n += 1

    meta = {
        "name": name,
        "voice_id": voice_id,
        "voice_name": vinfo.voice_name,
        "texts_path": str(texts_path),
        "n_files": n,
        "total_min": round(total_sec / 60, 2),
        "out_vocals": str(out_dir),
    }
    (out_dir.parent / "corpus_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta
