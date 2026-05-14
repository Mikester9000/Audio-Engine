"""Tests for the AudioEngine façade and CLI."""

import sys
from pathlib import Path

import numpy as np
import pytest

from audio_engine import AudioEngine
from audio_engine.cli import build_parser, main


SR = 22050


@pytest.fixture(scope="module")
def engine():
    return AudioEngine(sample_rate=SR, seed=7)


def test_available_styles_non_empty(engine):
    assert len(engine.available_styles()) > 0


def test_available_instruments_non_empty(engine):
    assert len(engine.available_instruments()) > 0


def test_generate_track_returns_array(engine):
    audio = engine.generate_track("menu", bars=2)
    assert isinstance(audio, np.ndarray)
    assert audio.ndim == 2


def test_generate_track_writes_file(engine, tmp_path):
    out = tmp_path / "track.wav"
    engine.generate_track("ambient", bars=2, output_path=str(out), fmt="wav")
    assert out.exists()
    assert out.stat().st_size > 0


def test_export_wav(engine, tmp_path):
    audio = np.zeros((SR, 2), dtype=np.float32)
    out = engine.export(audio, tmp_path / "silent.wav")
    assert out.exists()


def test_export_loop_points(engine, tmp_path):
    audio = np.zeros((SR, 2), dtype=np.float32)
    out = engine.export(audio, tmp_path / "loop.wav", loop_start=0, loop_end=SR - 1)
    assert out.exists()


def test_export_loop_without_end_raises(engine, tmp_path):
    audio = np.zeros((SR, 2), dtype=np.float32)
    with pytest.raises(ValueError):
        engine.export(audio, tmp_path / "x.wav", loop_start=0)


def test_render_sfx_arpeggio(engine):
    audio = engine.render_sfx("piano", [261.63, 329.63, 392.0], duration=0.2)
    assert audio.ndim == 1
    assert len(audio) == 3 * int(0.2 * SR)


def test_render_sfx_chord(engine):
    audio = engine.render_sfx("piano", [261.63, 329.63, 392.0], duration=0.2, overlap=True)
    assert audio.ndim == 1
    assert len(audio) == int(0.2 * SR)


def test_create_sequencer(engine):
    seq = engine.create_sequencer(bpm=90)
    assert abs(seq.bpm - 90) < 1e-6


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_list_styles(capsys):
    rc = main(["list-styles"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "battle" in captured.out


def test_cli_list_instruments(capsys):
    rc = main(["list-instruments"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "piano" in captured.out


def test_cli_generate(tmp_path, capsys):
    out = str(tmp_path / "track.wav")
    rc = main(["generate", "--style", "menu", "--bars", "2", "--output", out, "--seed", "1"])
    assert rc == 0
    assert Path(out).exists()


def test_cli_sfx(tmp_path, capsys):
    out = str(tmp_path / "sfx.wav")
    rc = main([
        "sfx",
        "--instrument", "piano",
        "--notes", "440.0", "550.0",
        "--duration", "0.2",
        "--output", out,
    ])
    assert rc == 0
    assert Path(out).exists()


def test_cli_generate_unknown_style(capsys):
    rc = main(["generate", "--style", "nonexistent_xyz", "--output", "/tmp/x.wav"])
    assert rc != 0


# ---------------------------------------------------------------------------
# generate-request-batch CLI tests
# ---------------------------------------------------------------------------

_FIXTURE_DIR = (
    Path(__file__).parent.parent
    / "docs"
    / "AI_FACTORY"
    / "EXAMPLES"
    / "gamerewritten_vertical_slice"
)


def test_cli_generate_request_batch_help(capsys):
    """generate-request-batch --help should exit cleanly."""
    import argparse

    from audio_engine.cli import build_parser

    parser = build_parser()
    # Verify the subcommand exists in the parser.
    subparsers_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    assert subparsers_actions, "No subparsers found"
    choices = subparsers_actions[0].choices
    assert "generate-request-batch" in choices, (
        "'generate-request-batch' subcommand not registered"
    )


def test_cli_generate_request_batch_sfx(tmp_path, capsys):
    """generate-request-batch should execute the SFX fixture and return 0."""
    batch_file = str(_FIXTURE_DIR / "generation_requests.sfx.v1.json")
    rc = main([
        "generate-request-batch",
        "--batch-file", batch_file,
        "--output-dir", str(tmp_path),
    ])
    assert rc == 0
    drafts_sfx = tmp_path / "drafts" / "sfx"
    assert drafts_sfx.exists(), "drafts/sfx directory was not created"
    wav_files = list(drafts_sfx.glob("*.wav"))
    assert len(wav_files) > 0, "No WAV files produced in drafts/sfx"


def test_cli_generate_request_batch_missing_file(tmp_path, capsys):
    """generate-request-batch with a missing batch file should return non-zero."""
    rc = main([
        "generate-request-batch",
        "--batch-file", str(tmp_path / "nonexistent_batch.json"),
        "--output-dir", str(tmp_path),
    ])
    assert rc != 0


def test_cli_generate_request_batch_quiet(tmp_path, capsys):
    """--quiet should suppress per-asset progress output."""
    batch_file = str(_FIXTURE_DIR / "generation_requests.sfx.v1.json")
    rc = main([
        "generate-request-batch",
        "--batch-file", batch_file,
        "--output-dir", str(tmp_path),
        "--quiet",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    # Summary is still printed (not suppressed by --quiet).
    assert "SFX" in captured.out or "sfx" in captured.out.lower()


def test_cli_generate_request_batch_writes_manifest(tmp_path):
    """generate-request-batch should write batch_manifest.json."""
    import json

    batch_file = str(_FIXTURE_DIR / "generation_requests.sfx.v1.json")
    rc = main([
        "generate-request-batch",
        "--batch-file", batch_file,
        "--output-dir", str(tmp_path),
    ])
    assert rc == 0
    manifest_path = tmp_path / "drafts" / "batch_manifest.json"
    assert manifest_path.exists(), "batch_manifest.json was not written"
    data = json.loads(manifest_path.read_text())
    assert "sfx" in data
    assert len(data["sfx"]) > 0
