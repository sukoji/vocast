from __future__ import annotations

import hashlib
import io
import re
import wave
from pathlib import Path


SPK_RE = re.compile(r"^[\-\*\s]*(상담원|민원인)\s*[:：]\s*(.+)$")


def parse_dialogue(text: str) -> list[tuple[str, str]]:
    turns: list[tuple[str, str]] = []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        for ln in block.splitlines():
            m = SPK_RE.match(ln.strip())
            if m:
                turns.append((m.group(1), m.group(2).strip()))
    return turns


def wav_params_bytes(data: bytes):
    with wave.open(io.BytesIO(data), "rb") as w:
        return w.getparams()


def wav_params_path(path: Path):
    with wave.open(str(path), "rb") as w:
        return w.getparams(), w.readframes(w.getnframes())


def wav_frames_bytes(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), "rb") as w:
        return w.readframes(w.getnframes())


def silence_frames(params, ms: int) -> bytes:
    n = int(params.framerate * ms / 1000)
    return b"\x00" * (n * params.sampwidth * params.nchannels)


def write_wav(path: Path, params, segments: list[bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(params.nchannels)
        w.setsampwidth(params.sampwidth)
        w.setframerate(params.framerate)
        for seg in segments:
            w.writeframes(seg)


def stable_seed(job_id: str) -> int:
    h = hashlib.sha256(job_id.encode()).hexdigest()
    return int(h[:12], 16)
