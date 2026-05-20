from __future__ import annotations

import json

import pytest

from audio_engine.ui.studio import _parse_float_field, _read_studio_preset, _write_studio_preset


def test_studio_preset_roundtrip(tmp_path):
    payload = {
        "music": {
            "style": "battle",
            "profile": "ost",
            "bars": 16,
            "seed": "11",
            "outputPath": "music.wav",
        },
        "sfx": {
            "category": "explosion",
            "durationSeconds": 0.8,
            "pitchHz": "",
            "seed": "12",
            "outputPath": "sfx.wav",
        },
        "voice": {
            "text": "The crystal calls.",
            "preset": "narrator",
            "speed": 1.0,
            "seed": "13",
            "outputPath": "voice.wav",
        },
    }
    preset_path = tmp_path / "presets" / "studio.json"

    _write_studio_preset(preset_path, payload)
    loaded = _read_studio_preset(preset_path)

    assert loaded == payload


def test_read_studio_preset_rejects_non_object_json(tmp_path):
    preset_path = tmp_path / "bad.json"
    preset_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        _read_studio_preset(preset_path)


def test_parse_float_field_has_clear_error():
    with pytest.raises(ValueError, match="sfx.durationSeconds"):
        _parse_float_field("not-a-number", field_name="sfx.durationSeconds")
