"""Tests for the AudioEngine façade and CLI."""

import json
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
