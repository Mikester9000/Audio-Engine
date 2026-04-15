"""Tests for the new AI pipeline CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from audio_engine.cli import main


# ---------------------------------------------------------------------------
# generate-music
# ---------------------------------------------------------------------------

def test_cli_generate_music(tmp_path, capsys):
    out = str(tmp_path / "music.wav")
    rc = main(["generate-music", "--prompt", "battle theme", "--duration", "2", "--output", out])
    assert rc == 0
    assert Path(out).exists()
    captured = capsys.readouterr()
    assert "Done" in captured.out


def test_cli_generate_music_loop(tmp_path, capsys):
    out = str(tmp_path / "loop.wav")
    rc = main([
        "generate-music", "--prompt", "ambient loop", "--duration", "2",
        "--loop", "--output", out
    ])
    assert rc == 0
    assert Path(out).exists()


def test_cli_generate_music_with_seed(tmp_path):
    out = str(tmp_path / "seed.wav")
    rc = main([
        "generate-music", "--prompt", "exploration", "--duration", "2",
        "--seed", "42", "--output", out
    ])
    assert rc == 0


# ---------------------------------------------------------------------------
# generate-sfx
# ---------------------------------------------------------------------------

def test_cli_generate_sfx(tmp_path, capsys):
    out = str(tmp_path / "sfx.wav")
    rc = main(["generate-sfx", "--prompt", "explosion", "--duration", "0.5", "--output", out])
    assert rc == 0
    assert Path(out).exists()
    captured = capsys.readouterr()
    assert "Done" in captured.out


def test_cli_generate_sfx_with_pitch(tmp_path):
    out = str(tmp_path / "laser.wav")
    rc = main([
        "generate-sfx", "--prompt", "laser", "--duration", "0.5",
        "--pitch", "800.0", "--output", out
    ])
    assert rc == 0
    assert Path(out).exists()


def test_cli_generate_sfx_various_types(tmp_path):
    for sfx_type in ["coin", "jump", "magic", "whoosh"]:
        out = str(tmp_path / f"{sfx_type}.wav")
        rc = main(["generate-sfx", "--prompt", sfx_type, "--duration", "0.3", "--output", out])
        assert rc == 0


# ---------------------------------------------------------------------------
# generate-voice
# ---------------------------------------------------------------------------

def test_cli_generate_voice(tmp_path, capsys):
    out = str(tmp_path / "voice.wav")
    rc = main(["generate-voice", "--text", "Hello, hero!", "--output", out])
    assert rc == 0
    assert Path(out).exists()
    captured = capsys.readouterr()
    assert "Done" in captured.out


def test_cli_generate_voice_all_presets(tmp_path):
    for voice in ["narrator", "hero", "villain", "announcer", "npc"]:
        out = str(tmp_path / f"voice_{voice}.wav")
        rc = main([
            "generate-voice", "--text", "Test line.", "--voice", voice, "--output", out
        ])
        assert rc == 0


def test_cli_generate_voice_speed(tmp_path):
    out = str(tmp_path / "fast_voice.wav")
    rc = main([
        "generate-voice", "--text", "Quick delivery.", "--speed", "1.5", "--output", out
    ])
    assert rc == 0


# ---------------------------------------------------------------------------
# qa
# ---------------------------------------------------------------------------

def test_cli_qa_clean_file(tmp_path, capsys):
    """QA should pass cleanly on a well-behaved WAV."""
    import wave
    import numpy as np

    out = tmp_path / "clean.wav"
    t = np.arange(22050) / 22050
    samples = (0.3 * np.sin(2.0 * 3.14159 * 440.0 * t) * 32767).astype("int16")
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(samples.tobytes())

    rc = main(["qa", "--input", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "LUFS" in captured.out


def test_cli_qa_with_loop_check(tmp_path, capsys):
    import wave
    import numpy as np

    out = tmp_path / "loop_check.wav"
    t = np.arange(22050) / 22050
    samples = (0.3 * np.sin(2.0 * 3.14159 * 440.0 * t) * 32767).astype("int16")
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(samples.tobytes())

    rc = main(["qa", "--input", str(out), "--check-loop"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Loop boundary" in captured.out


def test_cli_qa_missing_file(tmp_path):
    rc = main(["qa", "--input", str(tmp_path / "nonexistent.wav")])
    assert rc != 0
