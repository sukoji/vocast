from __future__ import annotations

from vocast.export.layout import sample_folder_name, sample_uid
from vocast.export.metadata import METADATA_HEADERS, build_sample_metadata_rows
from vocast.region_rules import SampleParams


def _params() -> SampleParams:
    return SampleParams(
        citizen_voice="Cheolyong",
        counselor_voice="Wonwoo",
        citizen_emotion="happy",
        citizen_intensity=0.7,
        citizen_tempo=1.0,
        counselor_emotion="normal",
        counselor_intensity=0.7,
        counselor_tempo=1.05,
    )


def test_metadata_headers_match_zip_format() -> None:
    assert METADATA_HEADERS == [
        "uid",
        "region",
        "scenario_id",
        "turn_index",
        "speaker",
        "voice_name",
        "emotion",
        "intensity",
        "tempo",
        "location_address",
        "location_detail",
        "smell_type",
        "smell_intensity",
        "smell_duration",
        "suspected_location",
        "text",
        "file",
    ]


def test_sample_uid_format() -> None:
    assert sample_uid("강원도", 10) == "강원도_id10"


def test_folder_and_file_paths_use_two_decimals() -> None:
    params = _params()
    folder = sample_folder_name("강원도", 10, params, variant_id="tts_only")
    assert "_i0.70_tempo1.00_" in folder


def test_build_sample_metadata_rows() -> None:
    params = _params()
    folder = sample_folder_name("강원도", 10, params, variant_id="tts_only")
    job = {
        "region": "강원도",
        "scenario_id": 10,
        "meta": {
            "location_address": "원주시",
            "complainant_location_text": "동보렉스5차아파트",
            "smell_type": "똥 냄새",
            "smell_intensity": "밤이 깊어질수록 심해짐",
            "smell_duration": "",
            "suspected_location_text": "",
        },
    }
    turn_records = [
        {
            "turn_index": 1,
            "speaker": "상담원",
            "voice_name": "Wonwoo",
            "emotion": "normal",
            "intensity": 0.7,
            "tempo": 1.05,
            "text": "안녕하세요.",
            "filename": "t01_sang-Wonwoo.wav",
        },
        {
            "turn_index": 2,
            "speaker": "민원인",
            "voice_name": "Cheolyong",
            "emotion": "happy",
            "intensity": 0.7,
            "tempo": 1.0,
            "text": "냄새가 심합니다.",
            "filename": "t02_min_happy_i0.70_tempo1.00.wav",
        },
    ]
    rows = build_sample_metadata_rows(
        job=job,
        params=params,
        folder_name=folder,
        turn_records=turn_records,
        full_file_name="full__min_happy_i0.70_tempo1.00.wav",
    )

    assert len(rows) == 3
    assert rows[0]["location_address"] == ""
    assert rows[0]["file"].endswith("t01_sang-Wonwoo.wav")
    assert rows[-1]["turn_index"] == "full"
    assert rows[-1]["speaker"] == ""
    assert rows[-1]["location_address"] == "원주시"
    assert rows[-1]["smell_duration"] == "미언급"
    assert rows[-1]["text"] == "안녕하세요. 냄새가 심합니다."
