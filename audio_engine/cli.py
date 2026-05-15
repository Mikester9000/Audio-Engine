"""
Command-line interface for the Audio Engine.

Usage examples
--------------
Generate a battle track (WAV):
    audio-engine generate --style battle --bars 8 --output battle.wav

Generate music from a prompt:
    audio-engine generate-music --prompt "dark ambient dungeon 90 BPM" --duration 60 --loop --output dungeon.wav

Generate a sound effect from a prompt:
    audio-engine generate-sfx --prompt "explosion impact" --duration 1.5 --output boom.wav

Generate a voice line:
    audio-engine generate-voice --text "Welcome, hero." --voice narrator --output hero_greeting.wav

Run quality assurance checks on a WAV file:
    audio-engine qa --input track.wav

Execute a generation-request batch file (factory workflow):
    audio-engine generate-request-batch --batch-file generation_requests.music.v1.json --output-dir /tmp/output

Run batch QA on all WAV files in a directory:
    audio-engine qa-batch --input-dir /tmp/output/drafts/sfx --output-report qa_report.json

Export draft assets to the GameRewritten layout:
    audio-engine export-drafts --output-dir /tmp/factory_output

Generate ALL assets for the Game Engine for Teaching:
    audio-engine generate-game-assets --output-dir ./assets/audio

Verify that all game assets are present:
    audio-engine verify-game-assets --assets-dir ./assets/audio

Execute a factory generation-request batch:
    audio-engine generate-request-batch --request-file generation_requests.sfx.v1.json \\
        --output-dir /tmp/output --write-result

List available styles and instruments:
    audio-engine list-styles
    audio-engine list-instruments

Render a quick SFX chord:
    audio-engine sfx --instrument piano --notes 261.63 329.63 392.0 --output chord.wav
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _cmd_generate(args: argparse.Namespace) -> None:
    from audio_engine import AudioEngine

    engine = AudioEngine(sample_rate=args.sample_rate, seed=args.seed)
    print(f"Generating '{args.style}' track ({args.bars} bars) → {args.output} …")
    audio = engine.generate_track(
        style=args.style,
        bars=args.bars,
        output_path=args.output,
        fmt=args.format,
    )
    duration = len(audio) / args.sample_rate
    print(f"Done. Duration: {duration:.2f}s  |  Samples: {len(audio):,}")


def _cmd_sfx(args: argparse.Namespace) -> None:
    from audio_engine import AudioEngine

    engine = AudioEngine(sample_rate=args.sample_rate)
    print(
        f"Rendering SFX: instrument='{args.instrument}' "
        f"notes={args.notes} duration={args.duration}s → {args.output}"
    )
    audio = engine.render_sfx(
        instrument_name=args.instrument,
        frequencies=[float(n) for n in args.notes],
        duration=args.duration,
        overlap=args.overlap,
    )
    engine.export(audio, args.output, fmt="wav")
    print(f"Done.  {len(audio)} samples written.")


def _cmd_generate_music(args: argparse.Namespace) -> None:
    """Generate music from a text prompt using the AI pipeline."""
    from audio_engine.ai import MusicGen

    gen = MusicGen(sample_rate=args.sample_rate, backend=args.backend, seed=args.seed)
    print(f"Generating music: '{args.prompt}' → {args.output} …")
    path = gen.generate_to_file(
        prompt=args.prompt,
        output_path=args.output,
        duration=args.duration,
        loopable=args.loop,
        fmt=args.format,
    )
    print(f"Done. Saved to: {path}")


def _cmd_generate_sfx(args: argparse.Namespace) -> None:
    """Generate a sound effect from a text prompt."""
    from audio_engine.ai import SFXGen

    gen = SFXGen(sample_rate=args.sample_rate, backend=args.backend, seed=args.seed)
    print(f"Generating SFX: '{args.prompt}' → {args.output} …")
    pitch = float(args.pitch) if args.pitch is not None else None
    path = gen.generate_to_file(
        prompt=args.prompt,
        output_path=args.output,
        duration=args.duration,
        pitch_hz=pitch,
    )
    print(f"Done. Saved to: {path}")


def _cmd_generate_voice(args: argparse.Namespace) -> None:
    """Generate voice/TTS audio from text."""
    from audio_engine.ai import VoiceGen

    gen = VoiceGen(sample_rate=args.sample_rate, backend=args.backend, seed=args.seed)
    print(f"Synthesising voice: '{args.text}' (voice={args.voice}) → {args.output} …")
    path = gen.generate_to_file(
        text=args.text,
        output_path=args.output,
        voice=args.voice,
        speed=args.speed,
    )
    print(f"Done. Saved to: {path}")


def _load_wav_array(input_path: Path) -> "tuple[np.ndarray, int, int]":
    """Load a WAV file and return ``(audio, sample_rate, n_channels)``.

    Returns float32 audio in the range ``[-1, 1]``.
    """
    import wave

    import numpy as np

    with wave.open(str(input_path), "r") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    dtype = {"1": "int8", "2": "int16", "3": "int32", "4": "int32"}.get(str(sampwidth), "int16")
    scale = {1: 128.0, 2: 32768.0, 3: 8388608.0, 4: 2147483648.0}.get(sampwidth, 32768.0)
    samples = np.frombuffer(raw, dtype=np.dtype(dtype)).astype(np.float32) / scale

    if n_channels > 1:
        audio = samples.reshape(-1, n_channels)
    else:
        audio = samples

    return audio, sr, n_channels


def _cmd_qa(args: argparse.Namespace) -> None:
    """Run quality-assurance checks on a WAV file."""
    import numpy as np

    from audio_engine.qa import LoudnessMeter, ClippingDetector, LoopAnalyzer

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        raise FileNotFoundError(f"file not found: {input_path}")

    audio, sr, n_channels = _load_wav_array(input_path)
    n_frames = audio.shape[0] if audio.ndim == 2 else len(audio)

    print(f"\nQA Report: {input_path.name}")
    print(f"  Sample rate : {sr} Hz")
    print(f"  Channels    : {n_channels}")
    print(f"  Duration    : {n_frames / sr:.2f}s  ({n_frames:,} frames)")
    print()

    # Loudness
    meter = LoudnessMeter(sample_rate=sr)
    result = meter.measure(audio)
    print(f"  Integrated loudness : {result.integrated_lufs:.1f} LUFS")
    print(f"  True peak           : {result.true_peak_dbfs:.1f} dBFS")
    print(f"  Loudness range      : {result.loudness_range_lu:.1f} LU")

    # Clipping
    detector = ClippingDetector()
    clip_report = detector.detect(audio)
    print(f"  Clipping            : {clip_report.summary()}")

    # Loop analysis
    if args.check_loop:
        analyzer = LoopAnalyzer(sample_rate=sr)
        loop_report = analyzer.analyze(audio)
        print(f"  Loop boundary       : {loop_report.summary()}")

    print()
    issues = []
    if result.integrated_lufs > -9.0:
        issues.append(f"Loudness too high ({result.integrated_lufs:.1f} LUFS; target ≤ -9 LUFS)")
    if result.integrated_lufs < -30.0:
        issues.append(f"Loudness too low ({result.integrated_lufs:.1f} LUFS; target ≥ -30 LUFS)")
    if result.true_peak_dbfs > -0.1:
        issues.append(f"True peak too high ({result.true_peak_dbfs:.1f} dBFS; should be ≤ -0.1 dBFS)")
    if clip_report.has_clipping:
        issues.append(clip_report.summary())

    if issues:
        print("  ⚠  Issues found:")
        for issue in issues:
            print(f"     • {issue}")
    else:
        print("  ✓  All checks passed.")


def _cmd_qa_batch(args: argparse.Namespace) -> None:
    """Run QA checks on all WAV files in a directory and write a JSON report."""
    import datetime
    import json

    import numpy as np

    from audio_engine.qa import LoudnessMeter, ClippingDetector, LoopAnalyzer

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
        raise FileNotFoundError(f"input directory not found: {input_dir}")

    wav_files = sorted(input_dir.rglob("*.wav") if args.recursive else input_dir.glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(f"No WAV files found in {input_dir}")

    results = []
    n_passed = 0
    n_failed = 0

    for wav_path in wav_files:
        try:
            audio, sr, n_channels = _load_wav_array(wav_path)
        except Exception as exc:
            record = {
                "file": str(wav_path),
                "status": "error",
                "error": str(exc),
                "checks": {},
            }
            results.append(record)
            n_failed += 1
            if not args.quiet:
                print(f"  [err]  {wav_path.name}: {exc}")
            continue

        meter = LoudnessMeter(sample_rate=sr)
        loudness_result = meter.measure(audio)

        detector = ClippingDetector()
        clip_report = detector.detect(audio)

        checks: dict = {
            "loudness_lufs": round(float(loudness_result.integrated_lufs), 2),
            "true_peak_dbfs": round(float(loudness_result.true_peak_dbfs), 2),
            "loudness_range_lu": round(float(loudness_result.loudness_range_lu), 2),
            "has_clipping": bool(clip_report.has_clipping),
            "clipped_samples": int(clip_report.clipped_samples),
            "loudness_ok": bool(-30.0 <= loudness_result.integrated_lufs <= -9.0),
            "peak_ok": bool(loudness_result.true_peak_dbfs <= -0.1),
            "clipping_ok": bool(not clip_report.has_clipping),
        }

        if args.check_loop:
            analyzer = LoopAnalyzer(sample_rate=sr)
            loop_report = analyzer.analyze(audio)
            checks["loop_is_seamless"] = bool(loop_report.is_seamless)
            checks["loop_amplitude_jump_db"] = round(float(loop_report.amplitude_jump_db), 2)
            checks["loop_ok"] = bool(loop_report.is_seamless)

        passed = all(
            v for k, v in checks.items() if k.endswith("_ok")
        )
        status = "pass" if passed else "fail"
        if passed:
            n_passed += 1
        else:
            n_failed += 1

        record = {
            "file": str(wav_path),
            "status": status,
            "checks": checks,
        }
        results.append(record)

        if not args.quiet:
            symbol = "✓" if passed else "✗"
            print(f"  [{symbol}]  {wav_path.name}")

    report = {
        "qaBatchVersion": "1.0.0",
        "inputDir": str(input_dir),
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "summary": {"total": len(results), "passed": n_passed, "failed": n_failed},
        "results": results,
    }

    if args.output_report:
        report_path = Path(args.output_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nQA report written → {report_path}")
    else:
        print()

    print(f"QA batch: {n_passed}/{len(results)} passed, {n_failed} failed")

    if n_failed > 0:
        raise ValueError(f"{n_failed} file(s) failed QA checks")


def _cmd_approve_draft(args: argparse.Namespace) -> None:
    """Approve one or more draft audio files and promote them to approved/."""
    from audio_engine.integration.asset_pipeline import ApprovalWorkflow

    factory_root = Path(args.factory_root)
    quiet = args.quiet

    def _progress(msg: str) -> None:
        if not quiet:
            print(msg)

    workflow = ApprovalWorkflow(progress_callback=_progress)

    draft_paths = [Path(p) for p in args.draft_file]
    if not draft_paths:
        print("Error: at least one --draft-file path is required", file=sys.stderr)
        raise ValueError("at least one --draft-file path is required")

    records = workflow.approve_batch(
        factory_root,
        draft_paths,
        review_log_path=args.review_log,
        reviewer=args.reviewer,
        qa_report_path=args.qa_report,
        project=args.project,
        scope=args.scope,
    )

    n_ok = sum(1 for r in records if r.get("status") == "ok")
    n_err = sum(1 for r in records if r.get("status") == "error")
    print(f"\nApproval complete — {n_ok} approved, {n_err} error(s)")

    if args.output_report:
        import json
        report_path = Path(args.output_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps({"approvals": records}, indent=2), encoding="utf-8")
        print(f"Report written → {report_path}")

    if n_err > 0:
        raise ValueError(f"{n_err} file(s) failed approval")


def _cmd_export_drafts(args: argparse.Namespace) -> None:
    """Copy draft audio files to the GameRewritten export surface."""
    from audio_engine.integration.asset_pipeline import DraftExportPipeline

    factory_root = Path(args.output_dir)

    quiet = args.quiet

    def _progress(msg: str) -> None:
        if not quiet:
            print(msg)

    pipeline = DraftExportPipeline(progress_callback=_progress)
    manifest = pipeline.export(
        factory_root,
        review_log_path=args.review_log,
        reviewer=args.reviewer,
        qa_report_path=args.qa_report,
        project=args.project,
        scope=args.scope,
    )

    n_total = manifest["summary"]["total"]
    print(f"\nExport complete — {n_total} file(s) → {factory_root / 'exports' / 'gamerewritten'}")


def _cmd_write_review_log(args: argparse.Namespace) -> None:
    """Write/update machine-readable review logs from audio+provenance surfaces."""
    import json

    from audio_engine.integration.asset_pipeline import ReviewLogWriter

    factory_root = Path(args.factory_root)
    review_log_path = Path(args.review_log)

    audio_files: list[Path] = []
    if args.audio_file:
        audio_files.extend(Path(p) for p in args.audio_file)
    if args.audio_dir:
        audio_dir = Path(args.audio_dir)
        if not audio_dir.exists():
            raise FileNotFoundError(f"audio directory not found: {audio_dir}")
        audio_files.extend(sorted(audio_dir.rglob("*.wav")))
        audio_files.extend(sorted(audio_dir.rglob("*.ogg")))

    if not audio_files:
        default_dir = factory_root / "drafts"
        if not default_dir.exists():
            raise FileNotFoundError(
                "no --audio-file/--audio-dir provided and default drafts/ directory not found"
            )
        audio_files.extend(sorted(default_dir.rglob("*.wav")))
        audio_files.extend(sorted(default_dir.rglob("*.ogg")))

    # deterministic unique list preserving sorted order
    resolved_map: dict[str, Path] = {}
    for path in audio_files:
        resolved = path.resolve()
        resolved_map[str(resolved)] = resolved
    unique_audio_files = sorted(resolved_map.values())
    if not unique_audio_files:
        raise ValueError("no audio files found for review-log writing")

    variation_family_decisions = None
    if args.variation_family_decisions:
        variation_family_decisions = json.loads(
            Path(args.variation_family_decisions).read_text(encoding="utf-8")
        )
        if not isinstance(variation_family_decisions, list):
            raise ValueError("--variation-family-decisions JSON must be a list")

    writer = ReviewLogWriter(progress_callback=(lambda msg: print(msg) if not args.quiet else None))
    log = writer.append_from_audio_files(
        factory_root=factory_root,
        audio_paths=unique_audio_files,
        review_log_path=review_log_path,
        project=args.project,
        scope=args.scope,
        reviewer=args.reviewer,
        qa_report_path=args.qa_report,
        notes=args.note or [],
        variation_family_decisions=variation_family_decisions,
    )

    print(
        f"Review log updated — {len(log.get('entries', []))} entries, "
        f"{len(log.get('variationFamilyDecisions', []))} family decision(s)"
    )


def _cmd_list_styles(_args: argparse.Namespace) -> None:
    from audio_engine import AudioEngine

    styles = AudioEngine.available_styles()
    print("Available styles:")
    for s in styles:
        print(f"  {s}")


def _cmd_list_instruments(_args: argparse.Namespace) -> None:
    from audio_engine import AudioEngine

    instruments = AudioEngine.available_instruments()
    print("Available instruments:")
    for i in instruments:
        print(f"  {i}")

def _cmd_list_backends(_args: argparse.Namespace) -> None:
    from audio_engine.ai.backend import BackendRegistry

    print("Available generation backends:")
    for evaluation in BackendRegistry.evaluate_backends():
        status = "available" if evaluation["available"] else "unavailable"
        modalities = ", ".join(evaluation["supported_modalities"])
        print(
            f"  {evaluation['name']} ({status})"
            f" — supports: {modalities}; deps: {evaluation['dependency_summary']}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audio-engine",
        description="Audio Engine – produce AI-assisted music, SFX, and voice.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- generate (legacy style-based) ---
    gen = sub.add_parser("generate", help="Generate a music track using the AI composer.")
    gen.add_argument(
        "--style",
        default="battle",
        help="Music style: battle, exploration, ambient, boss, victory, menu. (default: battle)",
    )
    gen.add_argument("--bars", type=int, default=None, help="Number of bars (default: style default)")
    gen.add_argument("--output", "-o", default="output.wav", help="Output file path.")
    gen.add_argument(
        "--format",
        choices=["wav", "ogg"],
        default="wav",
        help="Output format (default: wav).",
    )
    gen.add_argument(
        "--sample-rate", type=int, default=44100, help="Sample rate in Hz (default: 44100)."
    )
    gen.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")

    # --- generate-music (prompt-driven) ---
    gm = sub.add_parser(
        "generate-music",
        help="Generate music from a natural-language prompt.",
    )
    gm.add_argument(
        "--prompt", "-p", required=True,
        help='Natural-language prompt, e.g. "epic battle theme 140 BPM loopable".',
    )
    gm.add_argument("--duration", type=float, default=30.0, help="Duration in seconds (default: 30).")
    gm.add_argument("--loop", action="store_true", help="Generate a seamless loop.")
    gm.add_argument("--output", "-o", default="music.wav", help="Output file path.")
    gm.add_argument(
        "--format",
        choices=["wav", "ogg"],
        default="wav",
        help="Output format (default: wav).",
    )
    gm.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")
    gm.add_argument("--seed", type=int, default=None, help="Random seed.")
    gm.add_argument(
        "--backend",
        default="procedural",
        help="Generation backend name (default: procedural).",
    )

    # --- generate-sfx ---
    gs = sub.add_parser(
        "generate-sfx",
        help="Generate a sound effect from a natural-language prompt.",
    )
    gs.add_argument(
        "--prompt", "-p", required=True,
        help='Description, e.g. "explosion impact 1.5 seconds".',
    )
    gs.add_argument("--duration", type=float, default=1.0, help="Duration in seconds (default: 1).")
    gs.add_argument("--pitch", type=float, default=None, help="Base pitch in Hz (optional).")
    gs.add_argument("--output", "-o", default="sfx.wav", help="Output WAV file.")
    gs.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")
    gs.add_argument("--seed", type=int, default=None, help="Random seed.")
    gs.add_argument(
        "--backend",
        default="procedural",
        help="Generation backend name (default: procedural).",
    )

    # --- generate-voice ---
    gv = sub.add_parser(
        "generate-voice",
        help="Synthesise speech from text using local TTS.",
    )
    gv.add_argument("--text", "-t", required=True, help="Text to speak.")
    gv.add_argument(
        "--voice",
        default="narrator",
        choices=["narrator", "hero", "villain", "announcer", "npc"],
        help="Voice preset (default: narrator).",
    )
    gv.add_argument("--speed", type=float, default=1.0, help="Speech rate multiplier (default: 1.0).")
    gv.add_argument("--output", "-o", default="voice.wav", help="Output WAV file.")
    gv.add_argument("--sample-rate", type=int, default=22050, help="Sample rate in Hz (default: 22050).")
    gv.add_argument("--seed", type=int, default=None, help="Random seed.")
    gv.add_argument(
        "--backend",
        default="procedural",
        help="Generation backend name (default: procedural).",
    )

    # --- qa ---
    qa = sub.add_parser(
        "qa",
        help="Run quality-assurance checks on a WAV file.",
    )
    qa.add_argument("--input", "-i", required=True, help="Path to the WAV file to check.")
    qa.add_argument(
        "--check-loop",
        action="store_true",
        help="Also check for loop boundary click artefacts.",
    )

    # --- qa-batch ---
    qab = sub.add_parser(
        "qa-batch",
        help="Run QA checks on all WAV files in a directory and write a JSON report.",
    )
    qab.add_argument(
        "--input-dir", "-i", required=True,
        help="Directory containing WAV files to check.",
    )
    qab.add_argument(
        "--output-report", "-o",
        help="Path to write the JSON QA report (optional; prints summary to stdout regardless).",
    )
    qab.add_argument(
        "--check-loop",
        action="store_true",
        help="Also check for loop boundary click artefacts.",
    )
    qab.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Recurse into subdirectories when searching for WAV files.",
    )
    qab.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file progress messages.",
    )

    # --- approve-draft ---
    apd = sub.add_parser(
        "approve-draft",
        help=(
            "Approve one or more draft audio files: update provenance reviewStatus "
            "to 'approved' and copy to <factory-root>/approved/<type>/."
        ),
    )
    apd.add_argument(
        "--factory-root", "-f", required=True,
        help="Factory output root directory (contains the drafts/ sub-directory).",
    )
    apd.add_argument(
        "--draft-file", "-d", nargs="+", required=True,
        help="Path(s) to one or more draft audio file(s) to approve.",
    )
    apd.add_argument(
        "--output-report", "-o",
        help="Optional path to write a JSON approval report.",
    )
    apd.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file progress messages.",
    )
    apd.add_argument(
        "--review-log",
        help="Optional path to update a machine-readable review log from approved outputs.",
    )
    apd.add_argument(
        "--reviewer",
        default="agent",
        help="Reviewer label written to review-log entries (default: agent).",
    )
    apd.add_argument(
        "--qa-report",
        help="Optional qa-batch JSON report path used to enrich review-log qaSnapshot fields.",
    )
    apd.add_argument(
        "--project",
        help="Optional project value to set/override in the review log.",
    )
    apd.add_argument(
        "--scope",
        help="Optional scope value to set/override in the review log.",
    )

    # --- export-drafts ---
    exportdrafts = sub.add_parser(
        "export-drafts",
        help=(
            "Copy draft audio files from <output-dir>/drafts/ to "
            "<output-dir>/exports/gamerewritten/Content/Audio/ "
            "using targetImportPath from provenance sidecars."
        ),
    )
    exportdrafts.add_argument(
        "--output-dir", "-o", required=True,
        help="Factory output root directory containing the drafts/ sub-directory.",
    )
    exportdrafts.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file progress messages.",
    )
    exportdrafts.add_argument(
        "--review-log",
        help="Optional path to update a machine-readable review log from exported draft assets.",
    )
    exportdrafts.add_argument(
        "--reviewer",
        default="agent",
        help="Reviewer label written to review-log entries (default: agent).",
    )
    exportdrafts.add_argument(
        "--qa-report",
        help="Optional qa-batch JSON report path used to enrich review-log qaSnapshot fields.",
    )
    exportdrafts.add_argument(
        "--project",
        help="Optional project value to set/override in the review log.",
    )
    exportdrafts.add_argument(
        "--scope",
        help="Optional scope value to set/override in the review log.",
    )

    # --- write-review-log ---
    wrl = sub.add_parser(
        "write-review-log",
        help="Write/update a machine-readable review log from audio files and provenance sidecars.",
    )
    wrl.add_argument(
        "--factory-root", "-f", required=True,
        help="Factory output root directory (used for default drafts lookup).",
    )
    wrl.add_argument(
        "--review-log", "-o", required=True,
        help="Path to write/update the machine-readable review log JSON file.",
    )
    wrl.add_argument(
        "--audio-file", "-a", nargs="+",
        help="Optional explicit audio file path(s) to include.",
    )
    wrl.add_argument(
        "--audio-dir",
        help="Optional directory to scan recursively for .wav/.ogg files (defaults to <factory-root>/drafts).",
    )
    wrl.add_argument(
        "--reviewer",
        default="agent",
        help="Reviewer label written to each entry (default: agent).",
    )
    wrl.add_argument(
        "--qa-report",
        help="Optional qa-batch JSON report path used to enrich qaSnapshot fields.",
    )
    wrl.add_argument(
        "--project",
        help="Optional project value to set/override in the review log.",
    )
    wrl.add_argument(
        "--scope",
        help="Optional scope value to set/override in the review log.",
    )
    wrl.add_argument(
        "--variation-family-decisions",
        help="Optional JSON file containing a list of variationFamilyDecisions entries.",
    )
    wrl.add_argument(
        "--note",
        action="append",
        help="Optional note line to include in every generated entry (repeatable).",
    )
    wrl.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress writer progress messages.",
    )

    # --- sfx (instrument-based) ---
    sfx = sub.add_parser("sfx", help="Render a quick sound effect using an instrument.")
    sfx.add_argument("--instrument", default="piano", help="Instrument name.")
    sfx.add_argument(
        "--notes",
        nargs="+",
        default=["440.0"],
        metavar="FREQ",
        help="One or more frequencies in Hz.",
    )
    sfx.add_argument(
        "--duration", type=float, default=0.5, help="Duration per note in seconds (default: 0.5)."
    )
    sfx.add_argument(
        "--overlap",
        action="store_true",
        help="Play all notes simultaneously (chord) instead of in sequence.",
    )
    sfx.add_argument("--output", "-o", default="sfx.wav", help="Output WAV file.")
    sfx.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")

    # --- list-styles ---
    sub.add_parser("list-styles", help="List available music generation styles.")

    # --- list-instruments ---
    sub.add_parser("list-instruments", help="List available synthesised instruments.")

    # --- list-backends ---
    sub.add_parser("list-backends", help="List available generation backends.")

    # --- generate-request-batch ---
    grb = sub.add_parser(
        "generate-request-batch",
        help="Execute a generation-request batch file to produce draft audio assets.",
    )
    grb.add_argument(
        "--batch-file", "-b",
        help="Path to a generation-request batch JSON file (RequestBatchPipeline path).",
    )
    grb.add_argument(
        "--request-file", "-r",
        help="Path to a generation-request batch JSON fixture (AssetPipeline path).",
    )
    grb.add_argument(
        "--output-dir", "-o", default=".",
        help="Root output directory for drafts (default: current directory).",
    )
    grb.add_argument(
        "--force", action="store_true",
        help="Regenerate assets even if output files already exist.",
    )
    grb.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-asset progress messages.",
    )
    grb.add_argument(
        "--music-duration", type=float, default=30.0,
        help="Default duration in seconds for music requests (default: 30).",
    )
    grb.add_argument(
        "--sfx-duration", type=float, default=2.0,
        help="Default duration in seconds for SFX requests (default: 2).",
    )
    grb.add_argument(
        "--write-result", action="store_true",
        help="Write request_batch_result.json to the output directory.",
    )

    # --- generate-plan-batch ---
    gpb = sub.add_parser(
        "generate-plan-batch",
        help="Execute request batches filtered and ordered by an audio plan.",
    )
    gpb.add_argument(
        "--plan-file", "-p", required=True,
        help="Path to an audio-plan JSON file.",
    )
    gpb.add_argument(
        "--request-file", "-r", nargs="+", required=True,
        help="One or more generation-request batch JSON files.",
    )
    gpb.add_argument(
        "--output-dir", "-o", default=".",
        help="Root output directory for drafts (default: current directory).",
    )
    gpb.add_argument(
        "--force", action="store_true",
        help="Regenerate assets even if output files already exist.",
    )
    gpb.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-asset progress messages.",
    )
    gga = sub.add_parser(
        "generate-game-assets",
        help="Pre-generate ALL audio assets for the Game Engine for Teaching.",
    )
    gga.add_argument(
        "--output-dir", "-o", default="assets/audio",
        help="Root output directory (default: assets/audio).",
    )
    gga.add_argument(
        "--only",
        choices=["music", "sfx", "voice", "all"],
        default="all",
        help="Generate only a subset of assets (default: all).",
    )
    gga.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")
    gga.add_argument("--seed", type=int, default=None, help="Random seed.")
    gga.add_argument(
        "--force", action="store_true",
        help="Regenerate assets even if they already exist.",
    )
    gga.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-asset progress messages.",
    )

    # --- verify-game-assets ---
    vga = sub.add_parser(
        "verify-game-assets",
        help="Check that all expected game audio assets are present on disk.",
    )
    vga.add_argument(
        "--assets-dir", "-d", default="assets/audio",
        help="Root audio assets directory to verify (default: assets/audio).",
    )

    return parser


def _cmd_generate_request_batch(args: argparse.Namespace) -> None:
    """Execute a generation-request batch file deterministically."""
    from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch
    from audio_engine.integration.asset_pipeline import AssetPipeline

    # Support both --batch-file (RequestBatchPipeline path) and --request-file (AssetPipeline path)
    batch_file = args.batch_file or args.request_file
    if not batch_file:
        raise ValueError("Either --batch-file or --request-file must be provided")

    batch_path = Path(batch_file)
    if not batch_path.exists():
        raise FileNotFoundError(f"batch file not found: {batch_path}")

    batch = load_generation_request_batch(batch_path)

    def _progress(msg: str) -> None:
        if not args.quiet:
            print(msg)

    # If --request-file was used, fall back to AssetPipeline path for backward compat
    if args.request_file:
        pipeline = AssetPipeline(progress_callback=_progress)
        print(
            f"Executing request batch: {batch_path.name}"
            f" ({len(batch.requests)} requests) → {args.output_dir}"
        )
        result = pipeline.execute_request_batch(
            batch,
            args.output_dir,
            force=args.force,
            default_music_duration=args.music_duration,
            default_sfx_duration=args.sfx_duration,
        )
        print()
        print(result.summary())
        if args.write_result:
            result_path = Path(args.output_dir) / "request_batch_result.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(result.to_json(), encoding="utf-8")
            print(f"Result written → {result_path}")
        if any(r.status == "error" for r in result.records):
            raise SystemExit(1)
    else:
        pipeline = RequestBatchPipeline(
            progress_callback=_progress,
            skip_existing=not args.force,
        )
        manifest = pipeline.execute(batch, args.output_dir)
        print()
        print(manifest.summary())
        if manifest.errors:
            raise SystemExit(1)

def _cmd_generate_plan_batch(args: argparse.Namespace) -> None:
    """Execute plan-driven generation using one audio plan and request batches."""
    from audio_engine.integration import (
        PlanBatchOrchestrator,
        load_audio_plan,
        load_generation_request_batch,
    )

    plan_path = Path(args.plan_file)
    if not plan_path.exists():
        raise FileNotFoundError(f"plan file not found: {plan_path}")

    request_paths = [Path(p) for p in args.request_file]
    for path in request_paths:
        if not path.exists():
            raise FileNotFoundError(f"request file not found: {path}")

    plan = load_audio_plan(plan_path)
    request_batches = [load_generation_request_batch(path) for path in request_paths]

    def _progress(msg: str) -> None:
        if not args.quiet:
            print(msg)

    orchestrator = PlanBatchOrchestrator(
        progress_callback=_progress,
        skip_existing=not args.force,
    )
    print(
        f"Executing plan batch: {plan_path.name} "
        f"({len(request_paths)} request file(s)) → {args.output_dir}"
    )
    manifest = orchestrator.execute(plan, request_batches, args.output_dir)
    print()
    print(manifest.summary())
    if manifest.errors:
        raise SystemExit(1)


def _cmd_generate_game_assets(args: argparse.Namespace) -> None:
    """Generate the complete audio asset library for the Game Engine for Teaching."""
    from audio_engine.integration.asset_pipeline import AssetPipeline

    def _progress(msg: str) -> None:
        if not args.quiet:
            print(msg)

    pipeline = AssetPipeline(
        sample_rate=args.sample_rate,
        seed=args.seed,
        progress_callback=_progress,
        skip_existing=not args.force,
    )

    print(f"Generating game audio assets → {args.output_dir}")

    if args.only == "music":
        manifest = pipeline.generate_music_only(args.output_dir)
    elif args.only == "sfx":
        manifest = pipeline.generate_sfx_only(args.output_dir)
    elif args.only == "voice":
        manifest = pipeline.generate_voice_only(args.output_dir)
    else:
        manifest = pipeline.generate_all(args.output_dir)

    print()
    print(manifest.summary())
    if manifest.errors:
        return  # errors already printed in summary


def _cmd_verify_game_assets(args: argparse.Namespace) -> None:
    """Verify that all required game audio assets are present."""
    from audio_engine.integration.asset_pipeline import AssetPipeline
    from pathlib import Path

    assets_dir = Path(args.assets_dir)
    if not assets_dir.exists():
        raise FileNotFoundError(f"assets directory not found: {assets_dir}")

    pipeline = AssetPipeline()
    report = pipeline.verify(assets_dir)

    n_present = len(report["present"])
    n_missing = len(report["missing"])
    n_total = n_present + n_missing

    print(f"Verifying game assets: {assets_dir}")
    print(f"  Present : {n_present}/{n_total}")
    print(f"  Missing : {n_missing}/{n_total}")

    if report["missing"]:
        print("\n  Missing files:")
        for f in report["missing"]:
            print(f"    • {f}")
        print(
            "\n  Run:  audio-engine generate-game-assets"
            f" --output-dir {args.assets_dir}"
        )
        raise FileNotFoundError(f"{n_missing} asset(s) missing")
    else:
        print("  ✓  All assets present.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "generate": _cmd_generate,
        "generate-music": _cmd_generate_music,
        "generate-sfx": _cmd_generate_sfx,
        "generate-voice": _cmd_generate_voice,
        "qa": _cmd_qa,
        "qa-batch": _cmd_qa_batch,
        "approve-draft": _cmd_approve_draft,
        "export-drafts": _cmd_export_drafts,
        "write-review-log": _cmd_write_review_log,
        "sfx": _cmd_sfx,
        "list-styles": _cmd_list_styles,
        "list-instruments": _cmd_list_instruments,
        "list-backends": _cmd_list_backends,
        "generate-request-batch": _cmd_generate_request_batch,
        "generate-plan-batch": _cmd_generate_plan_batch,
        "generate-game-assets": _cmd_generate_game_assets,
        "verify-game-assets": _cmd_verify_game_assets,
    }

    handler = dispatch.get(args.command)
    if handler is None:  # pragma: no cover
        parser.print_help()
        return 1

    try:
        handler(args)
        return 0
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover – surface unexpected errors
        print(f"Unexpected error: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())
