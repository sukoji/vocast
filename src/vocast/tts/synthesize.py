from __future__ import annotations

from vocast.env import load_env
from vocast.region_rules import load_voices_config


def resolve_voice_map() -> dict[str, str]:
    """Typecast API voice_name → voice_id, merged with config/voices.yaml."""
    load_env()
    static = load_voices_config().get("voices", {})
    out = {k: v for k, v in static.items() if v}
    try:
        from typecast import Typecast
        client = Typecast()
        for v in client.voices_v2():
            if v.voice_name and v.voice_id:
                out.setdefault(v.voice_name, v.voice_id)
    except Exception:
        pass
    return out


def pick_model(voice_id: str, preferred: str) -> str:
    from typecast import Typecast
    client = Typecast()
    vs = {v.voice_id: v for v in client.voices_v2()}
    v = vs[voice_id]
    versions = [
        (m.version.value if hasattr(m.version, "value") else str(m.version))
        for m in v.models
    ]
    return preferred if preferred in versions else (versions[0] if versions else preferred)


def synth_turn(
    client,
    *,
    voice_id: str,
    text: str,
    emotion: str,
    intensity: float,
    tempo: float,
    model: str,
) -> tuple[bytes, str]:
    from typecast.models import TTSRequest, PresetPrompt, Output, LanguageCode

    actual_model = pick_model(voice_id, model)
    resp = client.text_to_speech(
        TTSRequest(
            text=text,
            model=actual_model,
            voice_id=voice_id,
            language=LanguageCode.KOR,
            prompt=PresetPrompt(
                emotion_type="preset",
                emotion_preset=emotion,
                emotion_intensity=float(intensity),
            ),
            output=Output(audio_format="wav", audio_tempo=float(tempo), audio_pitch=0),
        )
    )
    return resp.audio_data, actual_model
