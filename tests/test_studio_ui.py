from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from audio_engine.ui.studio import (
    _build_preview_catalog,
    _build_new_file_template,
    _build_synth_patch,
    _discover_wav_files,
    _export_synth_patch,
    _new_file_output_targets,
    _parse_float_field,
    _read_studio_preset,
    _SYNTH_FILTER_TYPES,
    _SYNTH_WAVEFORMS,
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


# ---------------------------------------------------------------------------
# Synth Workbench helpers
# ---------------------------------------------------------------------------


def test_synth_waveforms_list_is_nonempty():
    assert len(_SYNTH_WAVEFORMS) > 0
    assert "sine" in _SYNTH_WAVEFORMS


def test_synth_filter_types_includes_none():
    assert "none" in _SYNTH_FILTER_TYPES


def test_build_synth_patch_returns_float32_array():
    audio = _build_synth_patch(
        waveform="sine",
        frequency=440.0,
        duration=0.5,
        amplitude=0.8,
        attack=0.01,
        decay=0.1,
        sustain=0.7,
        release=0.3,
        filter_type="none",
        filter_cutoff=2000.0,
        filter_q=1.0,
    )
    assert isinstance(audio, np.ndarray)
    assert audio.dtype == np.float32


def test_build_synth_patch_correct_length():
    sample_rate = 44100
    duration = 0.5
    audio = _build_synth_patch(
        waveform="sine",
        frequency=440.0,
        duration=duration,
        amplitude=0.8,
        attack=0.01,
        decay=0.1,
        sustain=0.7,
        release=0.3,
        filter_type="none",
        filter_cutoff=2000.0,
        filter_q=1.0,
        sample_rate=sample_rate,
    )
    expected_len = int(sample_rate * duration)
    assert len(audio) == expected_len


def test_build_synth_patch_amplitude_bounded():
    audio = _build_synth_patch(
        waveform="square",
        frequency=220.0,
        duration=0.3,
        amplitude=0.5,
        attack=0.0,
        decay=0.0,
        sustain=1.0,
        release=0.0,
        filter_type="none",
        filter_cutoff=2000.0,
        filter_q=1.0,
    )
    assert float(np.max(np.abs(audio))) <= 1.0 + 1e-6


@pytest.mark.parametrize("waveform", ["sine", "square", "sawtooth", "triangle", "noise"])
def test_build_synth_patch_all_waveforms(waveform):
    audio = _build_synth_patch(
        waveform=waveform,
        frequency=440.0,
        duration=0.2,
        amplitude=0.8,
        attack=0.01,
        decay=0.05,
        sustain=0.7,
        release=0.1,
        filter_type="none",
        filter_cutoff=2000.0,
        filter_q=1.0,
    )
    assert len(audio) > 0
    assert np.all(np.isfinite(audio))


@pytest.mark.parametrize("filter_type", ["lowpass", "highpass", "bandpass"])
def test_build_synth_patch_filters_produce_finite_output(filter_type):
    audio = _build_synth_patch(
        waveform="sawtooth",
        frequency=440.0,
        duration=0.3,
        amplitude=0.8,
        attack=0.01,
        decay=0.05,
        sustain=0.7,
        release=0.1,
        filter_type=filter_type,
        filter_cutoff=1000.0,
        filter_q=1.0,
    )
    assert np.all(np.isfinite(audio))


def test_build_synth_patch_invalid_waveform_raises():
    with pytest.raises((AttributeError, ValueError)):
        _build_synth_patch(
            waveform="invalid_waveform_xyz",
            frequency=440.0,
            duration=0.1,
            amplitude=0.5,
            attack=0.01,
            decay=0.05,
            sustain=0.5,
            release=0.05,
            filter_type="none",
            filter_cutoff=2000.0,
            filter_q=1.0,
        )


def test_build_synth_patch_invalid_filter_type_raises():
    with pytest.raises(ValueError, match="Unknown filter_type"):
        _build_synth_patch(
            waveform="sine",
            frequency=440.0,
            duration=0.1,
            amplitude=0.5,
            attack=0.01,
            decay=0.05,
            sustain=0.5,
            release=0.05,
            filter_type="invalid_filter_xyz",
            filter_cutoff=2000.0,
            filter_q=1.0,
        )


def test_export_synth_patch_writes_wav_file(tmp_path: Path):
    audio = _build_synth_patch(
        waveform="sine",
        frequency=440.0,
        duration=0.2,
        amplitude=0.8,
        attack=0.01,
        decay=0.05,
        sustain=0.7,
        release=0.1,
        filter_type="none",
        filter_cutoff=2000.0,
        filter_q=1.0,
    )
    out = tmp_path / "out" / "patch.wav"
    result = _export_synth_patch(audio, out)
    assert result.exists()
    assert result.suffix == ".wav"
    assert result.stat().st_size > 44  # at least a WAV header

