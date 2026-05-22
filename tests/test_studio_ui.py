from __future__ import annotations

import json
from pathlib import Path

import pytest

from audio_engine.ui.studio import (
    _build_preview_catalog,
    _discover_wav_files,
    _parse_float_field,
    _read_studio_preset,
    _write_studio_preset,
)


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


def test_discover_wav_files_lists_nested_files(tmp_path: Path):
    (tmp_path / "a.wav").write_bytes(b"RIFF")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.wav").write_bytes(b"RIFF")
    (nested / "ignore.txt").write_text("x", encoding="utf-8")

    found = _discover_wav_files(tmp_path)

    assert found == [tmp_path / "a.wav", nested / "b.wav"]


def test_build_preview_catalog_groups_outputs_and_examples(tmp_path: Path):
    music = tmp_path / "music.wav"
    sfx = tmp_path / "sfx.wav"
    voice = tmp_path / "voice.wav"
    examples_root = tmp_path / "examples"
    examples_root.mkdir()
    example = examples_root / "example.wav"
    music.write_bytes(b"RIFF")
    sfx.write_bytes(b"RIFF")
    voice.write_bytes(b"RIFF")
    example.write_bytes(b"RIFF")

    catalog = _build_preview_catalog(
        music_output=music,
        sfx_output=sfx,
        voice_output=voice,
        examples_root=examples_root,
    )

    assert catalog["Music"] == [music]
    assert catalog["SFX"] == [sfx]
    assert catalog["Vocal"] == [voice]
    assert catalog["Examples"] == [example]
