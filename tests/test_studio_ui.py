from __future__ import annotations

import json
from pathlib import Path

import pytest

from audio_engine.ui.studio import (
    _build_preview_catalog,
    _build_new_file_template,
    _discover_wav_files,
    _new_file_output_targets,
    _parse_float_field,
    _read_studio_preset,
    _write_new_file_template,
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
    (tmp_path / "z.wav").write_bytes(b"RIFF")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.wav").write_bytes(b"RIFF")
    (nested / "ignore.txt").write_text("x", encoding="utf-8")

    found = _discover_wav_files(tmp_path)

    assert found == [tmp_path / "a.wav", nested / "b.wav", tmp_path / "z.wav"]


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


def test_build_preview_catalog_excludes_missing_outputs(tmp_path: Path):
    examples_root = tmp_path / "examples"
    examples_root.mkdir()

    catalog = _build_preview_catalog(
        music_output=tmp_path / "missing_music.wav",
        sfx_output=tmp_path / "missing_sfx.wav",
        voice_output=tmp_path / "missing_voice.wav",
        examples_root=examples_root,
    )

    assert catalog["Music"] == []
    assert catalog["SFX"] == []
    assert catalog["Vocal"] == []
    assert catalog["Examples"] == []


def test_new_file_output_targets_use_base_name_and_dir(tmp_path: Path):
    targets = _new_file_output_targets("quest_intro", tmp_path / "renders", fmt="ogg")
    assert targets["music"].endswith("quest_intro_music.ogg")
    assert targets["sfx"].endswith("quest_intro_sfx.wav")
    assert targets["voice"].endswith("quest_intro_voice.wav")


def test_new_file_output_targets_sanitize_name_and_format(tmp_path: Path):
    targets = _new_file_output_targets("../quest intro?!", tmp_path / "renders", fmt="mp3")
    assert targets["music"].endswith("quest_intro_music.wav")
    assert targets["sfx"].endswith("quest_intro_sfx.wav")
    assert targets["voice"].endswith("quest_intro_voice.wav")


def test_write_new_file_template_roundtrip(tmp_path: Path):
    payload = _build_new_file_template(
        project_name="quest_intro",
        preset_path="studio_preset.json",
        output_targets={
            "music": "output/quest_intro_music.wav",
            "sfx": "output/quest_intro_sfx.wav",
            "voice": "output/quest_intro_voice.wav",
        },
        preset_payload={"music": {"style": "battle"}},
    )
    path = tmp_path / "new_file.json"
    _write_new_file_template(path, payload)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["projectName"] == "quest_intro"
    assert loaded["outputTargets"]["music"].endswith("quest_intro_music.wav")
