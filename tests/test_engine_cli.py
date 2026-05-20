"""Tests for the AudioEngine façade and CLI."""

import json
import sys
import wave
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


def _write_wav(path: Path, audio: np.ndarray, sr: int = SR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def _tone(sr: int = SR, seconds: float = 0.2, hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False)
    return np.sin(2.0 * np.pi * hz * t).astype(np.float32)


def test_cli_remaster_batch_subcommand_registered():
    import argparse

    parser = build_parser()
    subparsers_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    assert subparsers_actions
    assert "remaster-batch" in subparsers_actions[0].choices


def test_cli_remaster_batch_smoke(tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    samples_dir = tmp_path / "samples"
    events_dir = tmp_path / "events"

    _write_wav(input_dir / "music" / "track.wav", _tone())
    _write_wav(samples_dir / "orchestral" / "strings" / "section_C4.wav", _tone(hz=261.63))
    events_dir.mkdir(parents=True, exist_ok=True)
    (events_dir / "track.events.json").write_text(
        json.dumps(
            [
                {
                    "instrument": "strings",
                    "note": "E4",
                    "startSeconds": 0.0,
                    "durationSeconds": 0.2,
                }
            ]
        ),
        encoding="utf-8",
    )

    rc = main(
        [
            "remaster-batch",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--samples-dir",
            str(samples_dir),
            "--events-dir",
            str(events_dir),
            "--quiet",
        ]
    )
    assert rc == 0
    assert (output_dir / "music" / "track.wav").exists()
    assert (output_dir / "remaster_batch_result.json").exists()



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


def test_cli_qa_batch_report_has_spectral_check_keys(tmp_path, capsys):
    """qa-batch JSON report must include spectral balance fields."""
    import json

    _write_loud_wav(tmp_path / "loud.wav")
    report_path = tmp_path / "qa_spectral.json"

    main([
        "qa-batch",
        "--input-dir", str(tmp_path),
        "--output-report", str(report_path),
    ])

    data = json.loads(report_path.read_text())
    spectral_keys = {
        "spectral_low_ratio",
        "spectral_mid_ratio",
        "spectral_high_ratio",
        "spectral_centroid_hz",
        "high_freq_ratio",
    }
    for result in data["results"]:
        missing = spectral_keys - result["checks"].keys()
        assert not missing, f"Missing spectral check keys: {missing}"


def test_cli_qa_batch_check_spectral_flag_adds_gate(tmp_path, capsys):
    """--check-spectral should add spectral_balance_ok as a hard gate field."""
    import json

    _write_loud_wav(tmp_path / "loud.wav")
    report_path = tmp_path / "qa_spectral_gate.json"

    main([
        "qa-batch",
        "--input-dir", str(tmp_path),
        "--output-report", str(report_path),
        "--check-spectral",
    ])

    data = json.loads(report_path.read_text())
    for result in data["results"]:
        assert "spectral_balance_ok" in result["checks"]


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
    # Per-file checkmarks must NOT appear when --quiet suppresses them.
    assert "✓" not in captured.out and "✗" not in captured.out


# ---------------------------------------------------------------------------
# export-drafts CLI tests
# ---------------------------------------------------------------------------

def test_cli_export_drafts_subcommand_registered(capsys):
    """export-drafts should be registered in the CLI parser."""
    import argparse

    from audio_engine.cli import build_parser

    parser = build_parser()
    subparsers_actions = [
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    ]
    assert subparsers_actions
    assert "export-drafts" in subparsers_actions[0].choices


def test_cli_export_drafts_missing_directory(tmp_path, capsys):
    """export-drafts with an empty factory root (no drafts) should return non-zero."""
    rc = main([
        "export-drafts",
        "--output-dir", str(tmp_path),
    ])
    assert rc != 0


def test_cli_export_drafts_smoke(tmp_path, capsys):
    """export-drafts should succeed after generate-request-batch produces drafts."""
    batch_file = str(_FIXTURE_DIR / "generation_requests.sfx.v1.json")

    # Step 1: generate drafts.
    rc_gen = main([
        "generate-request-batch",
        "--batch-file", batch_file,
        "--output-dir", str(tmp_path),
    ])
    assert rc_gen == 0

    # Step 2: export.
    rc_exp = main([
        "export-drafts",
        "--output-dir", str(tmp_path),
    ])
    assert rc_exp == 0

    export_root = tmp_path / "exports" / "gamerewritten"
    assert export_root.exists(), "Export directory was not created"
    assert (export_root / "export_manifest.json").exists(), "Export manifest missing"

    # At least some WAV files should have been exported.
    exported_wavs = list((export_root / "Content" / "Audio").rglob("*.wav"))
    assert len(exported_wavs) > 0, "No WAV files exported"


def test_cli_write_review_log_subcommand_registered(capsys):
    """write-review-log should be registered in the CLI parser."""
    import argparse

    parser = build_parser()
    subparsers_actions = [
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    ]
    assert subparsers_actions
    assert "write-review-log" in subparsers_actions[0].choices


def test_cli_review_log_reviewer_default_is_unspecified():
    """Review-log related commands should default reviewer to 'unspecified'."""
    parser = build_parser()
    assert parser.parse_args(["approve-draft", "--factory-root", "x", "--draft-file", "y.wav"]).reviewer == "unspecified"
    assert parser.parse_args(["export-drafts", "--output-dir", "x"]).reviewer == "unspecified"
    assert parser.parse_args(["write-review-log", "--factory-root", "x", "--review-log", "y.json"]).reviewer == "unspecified"


def test_cli_write_review_log_smoke(tmp_path, capsys):
    """write-review-log should generate a machine-readable review log for drafts."""
    import json

    batch_file = str(_FIXTURE_DIR / "generation_requests.sfx.v1.json")
    rc_gen = main([
        "generate-request-batch",
        "--batch-file", batch_file,
        "--output-dir", str(tmp_path),
        "--quiet",
    ])
    assert rc_gen == 0

    review_log = tmp_path / "review_log.json"
    rc_log = main([
        "write-review-log",
        "--factory-root", str(tmp_path),
        "--review-log", str(review_log),
        "--audio-dir", str(tmp_path / "drafts" / "sfx"),
        "--project", "GameRewritten",
        "--scope", "tests",
        "--quiet",
    ])
    assert rc_log == 0
    assert review_log.exists()
    data = json.loads(review_log.read_text())
    assert data["project"] == "GameRewritten"
    assert len(data["entries"]) > 0


def test_cli_write_review_log_from_result(tmp_path):
    """write-review-log --from-result should source entries from request_batch_result.json."""
    import json
    import wave as wv

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    wav_path = output_dir / "sfx_from_result.wav"
    with wv.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 100)

    result_data = {
        "output_dir": str(output_dir),
        "project": "GameRewritten",
        "scope": "from-result-tests",
        "records": [
            {
                "request_id": "req_sfx_from_result_v1",
                "asset_id": "sfx_from_result",
                "type": "sfx",
                "seed": 55,
                "output_path": str(wav_path),
                "status": "ok",
                "error": None,
                "provenance_path": None,
            }
        ],
        "total_duration_seconds": 0.1,
    }
    result_json = tmp_path / "request_batch_result.json"
    result_json.write_text(json.dumps(result_data, indent=2), encoding="utf-8")

    review_log = tmp_path / "review_log.json"
    rc = main([
        "write-review-log",
        "--factory-root", str(tmp_path),
        "--review-log", str(review_log),
        "--from-result", str(result_json),
        "--quiet",
    ])
    assert rc == 0
    data = json.loads(review_log.read_text())
    assert len(data["entries"]) == 1
    assert data["project"] == "GameRewritten"


def test_cli_write_review_log_from_result_honors_project_scope_override(tmp_path):
    """--project/--scope should override result-json values on --from-result flow."""
    import json
    import wave as wv

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    wav_path = output_dir / "sfx_override.wav"
    with wv.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 100)

    result_data = {
        "output_dir": str(output_dir),
        "project": "OriginalProject",
        "scope": "original-scope",
        "records": [
            {
                "request_id": "req_override",
                "asset_id": "sfx_override",
                "type": "sfx",
                "seed": 56,
                "output_path": str(wav_path),
                "status": "ok",
                "error": None,
                "provenance_path": None,
            }
        ],
        "total_duration_seconds": 0.1,
    }
    result_json = tmp_path / "request_batch_result.json"
    result_json.write_text(json.dumps(result_data, indent=2), encoding="utf-8")

    review_log = tmp_path / "review_log.json"
    rc = main([
        "write-review-log",
        "--factory-root", str(tmp_path),
        "--review-log", str(review_log),
        "--from-result", str(result_json),
        "--project", "GameRewritten",
        "--scope", "override-tests",
        "--quiet",
    ])
    assert rc == 0
    data = json.loads(review_log.read_text())
    assert data["project"] == "GameRewritten"
    assert data["scope"] == "override-tests"


def test_cli_write_review_log_from_result_include_skipped(tmp_path):
    """--include-skipped should include skipped records from result JSON."""
    import json
    import wave as wv

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    ok_path = output_dir / "sfx_ok.wav"
    skipped_path = output_dir / "sfx_skipped.wav"
    for wav_path in (ok_path, skipped_path):
        with wv.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(b"\x00\x00" * 100)

    result_data = {
        "output_dir": str(output_dir),
        "project": "GameRewritten",
        "scope": "from-result-tests",
        "records": [
            {
                "request_id": "req_ok",
                "asset_id": "sfx_ok",
                "type": "sfx",
                "seed": 55,
                "output_path": str(ok_path),
                "status": "ok",
                "error": None,
                "provenance_path": None,
            },
            {
                "request_id": "req_skipped",
                "asset_id": "sfx_skipped",
                "type": "sfx",
                "seed": 56,
                "output_path": str(skipped_path),
                "status": "skipped",
                "error": None,
                "provenance_path": None,
            },
        ],
        "total_duration_seconds": 0.1,
    }
    result_json = tmp_path / "request_batch_result.json"
    result_json.write_text(json.dumps(result_data, indent=2), encoding="utf-8")

    review_log = tmp_path / "review_log.json"
    rc = main([
        "write-review-log",
        "--factory-root", str(tmp_path),
        "--review-log", str(review_log),
        "--from-result", str(result_json),
        "--include-skipped",
        "--quiet",
    ])
    assert rc == 0
    data = json.loads(review_log.read_text())
    request_ids = {entry["requestId"] for entry in data["entries"]}
    assert request_ids == {"req_ok", "req_skipped"}


def test_cli_approve_draft_with_review_log(tmp_path, capsys):
    """approve-draft should optionally update a review log."""
    import json
    import wave as wv

    drafts_sfx = tmp_path / "drafts" / "sfx"
    drafts_sfx.mkdir(parents=True, exist_ok=True)
    wav_path = drafts_sfx / "req_cli_review.wav"
    with wv.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 100)
    prov = {
        "provenanceVersion": "1.0.0",
        "requestId": "req_cli_review",
        "assetId": "sfx_cli_review",
        "type": "sfx",
        "reviewStatus": "draft",
        "generatedOutputPath": str(wav_path),
        "targetImportPath": "Content/Audio/req_cli_review.wav",
    }
    wav_path.with_name(wav_path.stem + ".provenance.json").write_text(
        json.dumps(prov, indent=2), encoding="utf-8"
    )

    review_log = tmp_path / "review_log.json"
    rc = main([
        "approve-draft",
        "--factory-root", str(tmp_path),
        "--draft-file", str(wav_path),
        "--review-log", str(review_log),
        "--project", "GameRewritten",
        "--scope", "tests",
    ])
    assert rc == 0
    data = json.loads(review_log.read_text())
    assert len(data["entries"]) == 1
    assert data["entries"][0]["reviewStatus"] == "approved"

def test_cli_generate_request_batch_sfx_via_request_file(tmp_path, capsys):
    """generate-request-batch should return 0 and create output files for the SFX fixture."""
    rc = main([
        "generate-request-batch",
        "--request-file", str(_FIXTURE_DIR / "generation_requests.sfx.v1.json"),
        "--output-dir", str(tmp_path),
        "--sfx-duration", "0.1",
        "--quiet",
    ])
    assert rc == 0
    # At least one output file should exist under tmp_path
    output_files = list(tmp_path.rglob("*.wav"))
    assert output_files, "No output WAV files created"


def test_cli_generate_request_batch_missing_file_via_request_file(tmp_path, capsys):
    """generate-request-batch should return non-zero when the request file is missing."""
    rc = main([
        "generate-request-batch",
        "--request-file", str(tmp_path / "nonexistent.json"),
        "--output-dir", str(tmp_path),
    ])
    assert rc != 0
    captured = capsys.readouterr()
    assert captured.err.count("Error: batch file not found:") == 1


def test_cli_generate_request_batch_writes_result_json(tmp_path, capsys):
    """--write-result should create request_batch_result.json in the output directory."""
    rc = main([
        "generate-request-batch",
        "--request-file", str(_FIXTURE_DIR / "generation_requests.sfx.v1.json"),
        "--output-dir", str(tmp_path),
        "--sfx-duration", "0.1",
        "--write-result",
        "--quiet",
    ])
    assert rc == 0
    result_json = tmp_path / "request_batch_result.json"
    assert result_json.exists(), "request_batch_result.json not written"
    import json
    data = json.loads(result_json.read_text())
    assert data["project"] == "GameRewritten"
    assert "records" in data


def test_cli_generate_request_batch_request_file_writes_batch_manifest_json(tmp_path):
    """Legacy request-file CLI path should write batch_manifest.json."""
    rc = main([
        "generate-request-batch",
        "--request-file", str(_FIXTURE_DIR / "generation_requests.sfx.v1.json"),
        "--output-dir", str(tmp_path),
        "--sfx-duration", "0.1",
        "--quiet",
    ])
    assert rc == 0

    manifest_path = tmp_path / "batch_manifest.json"
    assert manifest_path.exists(), "batch_manifest.json not written"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "sfx" in data
    assert "errors" in data
    assert data["errors"] == []


def test_cli_generate_request_batch_write_provenance_creates_sidecars(tmp_path):
    """--write-provenance should create .provenance.json sidecars for every generated file."""
    rc = main([
        "generate-request-batch",
        "--request-file", str(_FIXTURE_DIR / "generation_requests.sfx.v1.json"),
        "--output-dir", str(tmp_path),
        "--sfx-duration", "0.1",
        "--write-provenance",
        "--quiet",
    ])
    assert rc == 0
    prov_files = list(tmp_path.rglob("*.provenance.json"))
    assert prov_files, "No provenance sidecars written by --write-provenance"


def test_cli_generate_request_batch_no_provenance_by_default(tmp_path):
    """Without --write-provenance, no .provenance.json sidecars should be created."""
    rc = main([
        "generate-request-batch",
        "--request-file", str(_FIXTURE_DIR / "generation_requests.sfx.v1.json"),
        "--output-dir", str(tmp_path),
        "--sfx-duration", "0.1",
        "--quiet",
    ])
    assert rc == 0
    prov_files = list(tmp_path.rglob("*.provenance.json"))
    assert not prov_files, f"Unexpected provenance sidecars: {prov_files}"


def test_cli_generate_request_batch_request_file_honors_request_duration_seconds(
    tmp_path, monkeypatch
):
    """Legacy request-file CLI path should prefer request durationSeconds over default flags."""
    from audio_engine.ai.sfx_gen import SFXGen

    request = {
        "requestBatchVersion": "1.0.0",
        "project": "GameRewritten",
        "scope": "cli-duration-tests",
        "requests": [
            {
                "requestVersion": "1.0.0",
                "requestId": "req_cli_sfx_duration_v1",
                "assetId": "sfx_cli_duration",
                "type": "sfx",
                "backend": "procedural",
                "seed": 7,
                "prompt": "short confirm chirp",
                "styleFamily": "heroic-sci-fantasy",
                "durationSeconds": 0.23,
                "output": {
                    "targetPath": "Content/Audio/sfx_cli_duration.wav",
                    "format": "wav",
                    "sampleRate": 44100,
                    "channels": 1,
                },
                "qa": {
                    "loopRequired": False,
                    "reviewStatus": "draft",
                    "notes": [],
                },
            }
        ],
    }
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")

    observed_durations: list[float] = []

    def _patched_generate(self, prompt, duration=1.0, pitch_hz=None):
        observed_durations.append(duration)
        return np.zeros(2048, dtype=np.float32)

    monkeypatch.setattr(SFXGen, "generate", _patched_generate)

    rc = main([
        "generate-request-batch",
        "--request-file", str(request_path),
        "--output-dir", str(tmp_path),
        "--sfx-duration", "0.1",
        "--quiet",
    ])

    assert rc == 0
    assert observed_durations == [0.23]
    assert (tmp_path / "Content" / "Audio" / "sfx_cli_duration.wav").exists()


def test_cli_list_backends(capsys):
    rc = main(["list-backends"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "procedural" in captured.out
    assert "supports:" in captured.out


# ---------------------------------------------------------------------------
# SESSION-028: verify-backends tests
# ---------------------------------------------------------------------------

def test_cli_verify_backends_subcommand_registered():
    import argparse

    parser = build_parser()
    subparsers_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    assert subparsers_actions
    assert "verify-backends" in subparsers_actions[0].choices


def test_cli_verify_backends_returns_json(tmp_path, capsys):
    import json

    report_path = tmp_path / "preflight.json"
    rc = main(["verify-backends", "--output-report", str(report_path)])
    # rc is 0 when all backends available; procedural is always available
    assert rc in (0, 2)
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "backends" in report
    assert "generatedAt" in report
    assert "allAvailable" in report
    assert isinstance(report["backends"], list)
    names = [b["backend"] for b in report["backends"]]
    assert "procedural" in names


def test_cli_verify_backends_procedural_available(tmp_path):
    import json

    report_path = tmp_path / "preflight.json"
    main(["verify-backends", "--output-report", str(report_path), "--quiet"])
    report = json.loads(report_path.read_text())
    procedural = next(b for b in report["backends"] if b["backend"] == "procedural")
    assert procedural["available"] is True


def test_cli_verify_backends_prints_to_stdout_when_no_report(capsys):
    import json

    rc = main(["verify-backends", "--quiet"])
    captured = capsys.readouterr()
    # Output should be valid JSON even when no --output-report path given
    report = json.loads(captured.out)
    assert "backends" in report


def test_cli_verify_backends_smoke_run_procedural(tmp_path):
    import json

    report_path = tmp_path / "preflight_smoke.json"
    rc = main(["verify-backends", "--smoke", "--output-report", str(report_path), "--quiet"])
    assert rc in (0, 2)
    report = json.loads(report_path.read_text())
    assert report["smokeRunEnabled"] is True
    procedural = next(b for b in report["backends"] if b["backend"] == "procedural")
    assert procedural["smoke_run"] is not None
    # At least music should pass for the procedural backend
    assert procedural["smoke_run"].get("music") == "pass"


def test_cli_verify_backends_exits_2_when_backend_unavailable(tmp_path, monkeypatch):
    from audio_engine.ai.backend import BackendRegistry

    class _UnavailableBackend:
        def is_available(self):
            return False

        def availability_reason(self):
            return "simulated unavailable"

        def supported_modalities(self):
            return ("music",)

        def dependency_summary(self):
            return "simulated dependency"

    monkeypatch.setattr(
        BackendRegistry,
        "available_backends",
        classmethod(lambda cls: ["simulated_backend"]),
    )
    monkeypatch.setattr(
        BackendRegistry,
        "get",
        classmethod(lambda cls, name, **kwargs: _UnavailableBackend()),
    )

    report_path = tmp_path / "preflight_unavailable.json"
    with pytest.raises(SystemExit) as excinfo:
        main(["verify-backends", "--output-report", str(report_path), "--quiet"])

    assert excinfo.value.code == 2
    report = json.loads(report_path.read_text())
    assert report["allAvailable"] is False
    assert report["backends"][0]["available"] is False


def test_cli_verify_backends_report_schema(tmp_path):
    import json

    report_path = tmp_path / "preflight_schema.json"
    main(["verify-backends", "--output-report", str(report_path), "--quiet"])
    report = json.loads(report_path.read_text())
    for backend in report["backends"]:
        assert "backend" in backend
        assert "available" in backend
        assert "availability_reason" in backend
        assert "supported_modalities" in backend
        assert "dependency_summary" in backend
        assert "smoke_run" in backend


def test_cli_generate_plan_batch_subcommand_registered(capsys):
    import argparse

    parser = build_parser()
    subparsers_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    assert subparsers_actions
    assert "generate-plan-batch" in subparsers_actions[0].choices


def test_cli_generate_plan_batch_sfx_smoke(tmp_path, capsys):
    import json

    request_path = _FIXTURE_DIR / "generation_requests.sfx.v1.json"
    batch = json.loads(request_path.read_text(encoding="utf-8"))
    requests = batch["requests"][:2]
    plan = {
        "planVersion": "1.0.0",
        "project": "GameRewritten",
        "scope": "vertical-slice",
        "priorities": {"music": "high", "sfx": "high", "voice": "low"},
        "styleFamilies": ["heroic-sci-fantasy"],
        "assetGroups": [
            {
                "groupId": "sfx-required",
                "type": "sfx",
                "required": True,
                "targets": [
                    {
                        "assetId": req["assetId"],
                        "gameplayRole": f"role-{index}",
                        "targetPath": req["output"]["targetPath"],
                        "loop": req["qa"]["loopRequired"],
                        "durationTargetSeconds": 0.2,
                    }
                    for index, req in enumerate(requests)
                ],
            }
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    rc = main([
        "generate-plan-batch",
        "--plan-file", str(plan_path),
        "--request-file", str(request_path),
        "--output-dir", str(tmp_path),
        "--quiet",
    ])
    assert rc == 0
    output_files = list((tmp_path / "drafts" / "sfx").glob("*.wav"))
    assert len(output_files) == 2


def test_cli_generate_voice_accepts_seed_and_backend(tmp_path):
    out = str(tmp_path / "voice.wav")
    rc = main([
        "generate-voice",
        "--text", "Welcome, hero.",
        "--voice", "narrator",
        "--output", out,
        "--seed", "7",
        "--backend", "procedural",
    ])
    assert rc == 0
    assert Path(out).exists()


# ---------------------------------------------------------------------------
# SESSION-035: mastering profile tests
# ---------------------------------------------------------------------------

def test_cli_generate_music_profile_flag_vocal_mix(tmp_path):
    """--profile vocal_mix should be accepted and produce a WAV output."""
    out = str(tmp_path / "music_vocal.wav")
    rc = main([
        "generate-music",
        "--prompt", "calm ambient exploration",
        "--duration", "0.5",
        "--output", out,
        "--seed", "42",
        "--profile", "vocal_mix",
    ])
    assert rc == 0
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_cli_generate_music_profile_flag_ost(tmp_path):
    """--profile ost should be accepted and produce a WAV output."""
    out = str(tmp_path / "music_ost.wav")
    rc = main([
        "generate-music",
        "--prompt", "orchestral overworld theme",
        "--duration", "0.5",
        "--output", out,
        "--seed", "7",
        "--profile", "ost",
    ])
    assert rc == 0
    assert Path(out).exists()


def test_cli_generate_music_profile_flag_default_game(tmp_path):
    """--profile game is the default and should work without explicit flag."""
    out = str(tmp_path / "music_game.wav")
    rc = main([
        "generate-music",
        "--prompt", "battle theme",
        "--duration", "0.5",
        "--output", out,
        "--seed", "1",
    ])
    assert rc == 0
    assert Path(out).exists()


def test_cli_generate_music_profile_choices_match_offline_bounce():
    import argparse

    from audio_engine.render.offline_bounce import VALID_PROFILES

    parser = build_parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    gm_parser = subparsers_action.choices["generate-music"]
    profile_action = next(
        action for action in gm_parser._actions if action.dest == "profile"
    )
    assert list(profile_action.choices) == list(VALID_PROFILES)


# ---------------------------------------------------------------------------
# export-wav-delivery CLI tests (SESSION-037)
# ---------------------------------------------------------------------------

def _make_approved_wav(factory_root: Path, category: str, stem: str) -> Path:
    """Write a minimal WAV into <factory_root>/approved/<category>/."""
    import struct, wave
    approved_dir = factory_root / "approved" / category
    approved_dir.mkdir(parents=True, exist_ok=True)
    wav_path = approved_dir / f"{stem}.wav"
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(struct.pack("<100h", *([0] * 100)))
    return wav_path


def test_cli_export_wav_delivery_subcommand_registered():
    """export-wav-delivery must be registered in the CLI parser."""
    import argparse
    parser = build_parser()
    sub_action = next(
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert "export-wav-delivery" in sub_action.choices


def test_cli_export_wav_delivery_basic(tmp_path):
    """export-wav-delivery should copy WAVs and write delivery_manifest.json."""
    import json
    factory_root = tmp_path / "factory"
    delivery_dir = tmp_path / "delivery"
    _make_approved_wav(factory_root, "sfx", "laser_shot")

    rc = main([
        "export-wav-delivery",
        "--factory-root", str(factory_root),
        "--delivery-dir", str(delivery_dir),
        "--quiet",
    ])
    assert rc == 0
    manifest_path = delivery_dir / "delivery_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["summary"]["copied"] == 1
    assert len(data["entries"]) == 1


def test_cli_export_wav_delivery_deterministic_naming(tmp_path):
    """Delivery filenames must follow the deterministic naming contract."""
    import json
    factory_root = tmp_path / "factory"
    delivery_dir = tmp_path / "delivery"
    _make_approved_wav(factory_root, "music", "bgm_field")

    rc = main([
        "export-wav-delivery",
        "--factory-root", str(factory_root),
        "--delivery-dir", str(delivery_dir),
        "--quiet",
    ])
    assert rc == 0
    manifest_path = delivery_dir / "delivery_manifest.json"
    data = json.loads(manifest_path.read_text())
    entry = data["entries"][0]
    # Deterministic name must include category and stem
    assert entry["category"] == "music"
    assert "music__" in entry["deliveryName"]
    assert entry["deliveryName"].endswith(".wav")
    # File must actually exist
    assert Path(entry["deliveryPath"]).exists()


def test_cli_export_wav_delivery_category_filter(tmp_path):
    """--categories should limit which approved categories are packaged."""
    import json
    factory_root = tmp_path / "factory"
    delivery_dir = tmp_path / "delivery"
    _make_approved_wav(factory_root, "music", "bgm_boss")
    _make_approved_wav(factory_root, "sfx", "explosion")

    rc = main([
        "export-wav-delivery",
        "--factory-root", str(factory_root),
        "--delivery-dir", str(delivery_dir),
        "--categories", "sfx",
        "--quiet",
    ])
    assert rc == 0
    data = json.loads((delivery_dir / "delivery_manifest.json").read_text())
    assert data["summary"]["total"] == 1
    assert data["entries"][0]["category"] == "sfx"


def test_cli_export_wav_delivery_missing_approved(tmp_path):
    """export-wav-delivery must return non-zero when approved/ is absent."""
    factory_root = tmp_path / "empty_factory"
    factory_root.mkdir()
    rc = main([
        "export-wav-delivery",
        "--factory-root", str(factory_root),
        "--delivery-dir", str(tmp_path / "delivery"),
        "--quiet",
    ])
    assert rc != 0


def test_cli_export_wav_delivery_manifest_schema(tmp_path):
    """delivery_manifest.json must have required top-level keys."""
    import json
    factory_root = tmp_path / "factory"
    delivery_dir = tmp_path / "delivery"
    _make_approved_wav(factory_root, "voice", "narrator_intro")

    main([
        "export-wav-delivery",
        "--factory-root", str(factory_root),
        "--delivery-dir", str(delivery_dir),
        "--quiet",
    ])
    data = json.loads((delivery_dir / "delivery_manifest.json").read_text())
    assert "deliveryManifestVersion" in data
    assert "factoryRoot" in data
    assert "deliveryDir" in data
    assert "generatedAt" in data
    assert "summary" in data
    assert "entries" in data


def test_cli_export_wav_delivery_ignores_ogg_inputs(tmp_path):
    """WAV delivery should package only WAV files from approved/."""
    import json
    factory_root = tmp_path / "factory"
    delivery_dir = tmp_path / "delivery"
    approved_sfx = factory_root / "approved" / "sfx"
    approved_sfx.mkdir(parents=True, exist_ok=True)
    _make_approved_wav(factory_root, "sfx", "laser_shot")
    (approved_sfx / "legacy.ogg").write_bytes(b"OggS")

    rc = main([
        "export-wav-delivery",
        "--factory-root", str(factory_root),
        "--delivery-dir", str(delivery_dir),
        "--quiet",
    ])
    assert rc == 0
    data = json.loads((delivery_dir / "delivery_manifest.json").read_text())
    assert data["summary"]["total"] == 1
    assert data["entries"][0]["sourcePath"].endswith(".wav")


def test_cli_export_wav_delivery_normalizes_invalid_seed_to_zero(tmp_path):
    """Invalid provenance seed values should fall back to seed0000."""
    import json
    factory_root = tmp_path / "factory"
    delivery_dir = tmp_path / "delivery"
    wav_path = _make_approved_wav(factory_root, "voice", "line_a")
    prov_path = wav_path.with_name(f"{wav_path.stem}.provenance.json")
    prov_path.write_text(
        json.dumps({"assetId": "voice_line_a", "seed": None}),
        encoding="utf-8",
    )

    rc = main([
        "export-wav-delivery",
        "--factory-root", str(factory_root),
        "--delivery-dir", str(delivery_dir),
        "--quiet",
    ])
    assert rc == 0
    data = json.loads((delivery_dir / "delivery_manifest.json").read_text())
    entry = data["entries"][0]
    assert "__seed0000.wav" in entry["deliveryName"]
    assert entry["seed"] == 0
