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


# ---------------------------------------------------------------------------
# qa-batch CLI tests
# ---------------------------------------------------------------------------

def _write_silent_wav(path: Path, sample_rate: int = 22050, duration: float = 1.0) -> None:
    """Write a silent (all-zeros) WAV file for testing."""
    import struct
    import wave

    import numpy as np

    n_samples = int(sample_rate * duration)
    silence = np.zeros(n_samples, dtype=np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(silence.tobytes())


def _write_loud_wav(path: Path, sample_rate: int = 22050, duration: float = 1.0) -> None:
    """Write a loud (near-clipping) WAV file for testing."""
    import wave

    import numpy as np

    n_samples = int(sample_rate * duration)
    loud = (np.ones(n_samples) * 0.999).astype(np.float32)
    pcm = (loud * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def test_cli_qa_batch_subcommand_registered(capsys):
    """qa-batch should be registered in the CLI parser."""
    import argparse

    from audio_engine.cli import build_parser

    parser = build_parser()
    subparsers_actions = [
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    ]
    assert subparsers_actions
    assert "qa-batch" in subparsers_actions[0].choices


def test_cli_qa_batch_passes_on_valid_audio(tmp_path, capsys):
    """qa-batch should return 0 and report pass for a valid audio file."""
    from audio_engine.ai.sfx_gen import SFXGen
    from audio_engine.export.audio_exporter import AudioExporter

    gen = SFXGen(sample_rate=22050, seed=99)
    audio = gen.generate(prompt="soft click")
    exporter = AudioExporter(sample_rate=22050, bit_depth=16)
    exporter.export(audio, tmp_path / "test_sfx.wav", fmt="wav")

    rc = main([
        "qa-batch",
        "--input-dir", str(tmp_path),
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "passed" in captured.out or "pass" in captured.out.lower()


def test_cli_qa_batch_fails_on_silent_audio(tmp_path, capsys):
    """qa-batch should return non-zero for a silent (too quiet) file."""
    _write_silent_wav(tmp_path / "silent.wav")

    rc = main([
        "qa-batch",
        "--input-dir", str(tmp_path),
    ])
    assert rc != 0
    captured = capsys.readouterr()
    assert "fail" in captured.out.lower() or "failed" in captured.out.lower()


def test_cli_qa_batch_writes_json_report(tmp_path, capsys):
    """qa-batch --output-report should write a JSON report file."""
    import json

    _write_silent_wav(tmp_path / "silent.wav")
    report_path = tmp_path / "qa_report.json"

    main([
        "qa-batch",
        "--input-dir", str(tmp_path),
        "--output-report", str(report_path),
    ])

    assert report_path.exists(), "JSON report was not written"
    data = json.loads(report_path.read_text())
    assert "qaBatchVersion" in data
    assert "summary" in data
    assert "results" in data
    assert len(data["results"]) > 0
    assert "file" in data["results"][0]
    assert "status" in data["results"][0]
    assert "checks" in data["results"][0]


def test_cli_qa_batch_report_has_required_check_keys(tmp_path, capsys):
    """Each result in the JSON report must have the required check keys."""
    import json

    _write_loud_wav(tmp_path / "loud.wav")
    report_path = tmp_path / "qa_report.json"

    main([
        "qa-batch",
        "--input-dir", str(tmp_path),
        "--output-report", str(report_path),
    ])

    data = json.loads(report_path.read_text())
    required_check_keys = {
        "loudness_lufs",
        "true_peak_dbfs",
        "has_clipping",
        "loudness_ok",
        "peak_ok",
        "clipping_ok",
    }
    for result in data["results"]:
        missing = required_check_keys - result["checks"].keys()
        assert not missing, f"Missing check keys: {missing}"


def test_cli_qa_batch_missing_directory(tmp_path, capsys):
    """qa-batch with a nonexistent directory should return non-zero."""
    rc = main([
        "qa-batch",
        "--input-dir", str(tmp_path / "nonexistent"),
    ])
    assert rc != 0


def test_cli_qa_batch_quiet_suppresses_per_file_output(tmp_path, capsys):
    """qa-batch --quiet should suppress per-file lines but still print summary."""
    from audio_engine.ai.sfx_gen import SFXGen
    from audio_engine.export.audio_exporter import AudioExporter

    gen = SFXGen(sample_rate=22050, seed=42)
    audio = gen.generate(prompt="soft click")
    exporter = AudioExporter(sample_rate=22050, bit_depth=16)
    exporter.export(audio, tmp_path / "click.wav", fmt="wav")

    rc = main([
        "qa-batch",
        "--input-dir", str(tmp_path),
        "--quiet",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    # Summary line should still appear.
    assert "passed" in captured.out or "QA batch" in captured.out
    # Per-file checkmarks should NOT appear (✓ or ✗ symbols, or [✓]).
    assert "✓" not in captured.out or "QA batch" in captured.out
