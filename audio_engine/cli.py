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


def _resolve_backend(args: argparse.Namespace) -> str:
    """Resolve the effective backend name from CLI flags.

    Priority order (highest first):
    1. ``--backend`` explicit flag
    2. ``--samples-dir`` → ``sample`` backend
    3. ``--orchestral`` flag → ``synth_orchestral`` backend
    4. ``--ps1`` flag → ``ps1`` backend
    5. Default ``"procedural"``
    """
    if args.backend and args.backend != "procedural":
        return args.backend
    if getattr(args, "samples_dir", None):
        return "sample"
    if getattr(args, "orchestral", False):
        return "synth_orchestral"
    if getattr(args, "ps1", False):
        return "ps1"
    return args.backend or "procedural"


def _make_backend(args: argparse.Namespace):
    """Instantiate the backend, wiring sample_dir for SampleBackend."""
    from audio_engine.ai.backend import BackendRegistry

    backend_name = _resolve_backend(args)
    samples_dir = getattr(args, "samples_dir", None)

    if backend_name == "sample":
        from audio_engine.ai.sample_backend import SampleBackend
        base = "ps1" if getattr(args, "ps1", False) else "synth_orchestral"
        return SampleBackend(
            samples_dir=samples_dir or "samples/",
            sample_rate=args.sample_rate,
            seed=args.seed,
            base_backend=base,
        )
    if backend_name == "ps1":
        from audio_engine.ai.ps1_backend import PS1Backend
        reverb = getattr(args, "ps1_reverb", "room")
        return PS1Backend(sample_rate=args.sample_rate, seed=args.seed, reverb_mode=reverb)
    if backend_name == "synth_orchestral":
        from audio_engine.ai.synth_orchestral_backend import SynthOrchestralBackend
        return SynthOrchestralBackend(sample_rate=args.sample_rate, seed=args.seed)

    return BackendRegistry.get(backend_name, sample_rate=args.sample_rate, seed=args.seed)


def _cmd_generate_music(args: argparse.Namespace) -> None:
    """Generate music from a text prompt using the AI pipeline."""
    from audio_engine.ai import MusicGen

    backend = _make_backend(args)
    profile = getattr(args, "profile", "game") or "game"
    gen = MusicGen(sample_rate=args.sample_rate, backend=backend, seed=args.seed,
                   mastering_profile=profile)
    mode_label = _resolve_backend(args)
    print(f"Generating music [{mode_label}] [{profile}]: '{args.prompt}' → {args.output} …")
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

    backend = _make_backend(args)
    gen = SFXGen(sample_rate=args.sample_rate, backend=backend, seed=args.seed)
    mode_label = _resolve_backend(args)
    print(f"Generating SFX [{mode_label}]: '{args.prompt}' → {args.output} …")
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

    backend = _make_backend(args)
    gen = VoiceGen(sample_rate=args.sample_rate, backend=backend, seed=args.seed)
    mode_label = _resolve_backend(args)
    print(f"Synthesising voice [{mode_label}]: '{args.text}' (voice={args.voice}) → {args.output} …")
    path = gen.generate_to_file(
        text=args.text,
        output_path=args.output,
        voice=args.voice,
        speed=args.speed,
    )
    print(f"Done. Saved to: {path}")


def _cmd_studio(args: argparse.Namespace) -> None:
    """Launch local Tkinter studio GUI."""
    from audio_engine.ui import launch_studio

    launch_studio()


def _cmd_remaster(args: argparse.Namespace) -> None:
    """Remaster an existing WAV file using sample substitution + synth fallback."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        raise FileNotFoundError(f"file not found: {input_path}")

    from audio_engine.render.remaster import RemasterPipeline

    samples_dir = args.samples_dir or "samples/"
    base_backend = "ps1" if args.ps1 else "synth_orchestral"
    pipeline = RemasterPipeline(seed=args.seed, base_backend=base_backend)
    print(
        f"Remastering: {input_path.name}  "
        f"(samples: {samples_dir}, style: {args.style}) → {args.output} …"
    )
    out_path = pipeline.remaster_file(
        input_path=input_path,
        output_path=args.output,
        style=args.style,
        samples_dir=samples_dir,
        events_json=getattr(args, "events_json", None),
        fmt=args.format,
    )
    print(f"Done. Saved to: {out_path}")


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

    from audio_engine.qa import LoudnessMeter, ClippingDetector, LoopAnalyzer, SpectralAnalyzer

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

    # Spectral balance + intelligibility
    sa = SpectralAnalyzer(sample_rate=sr)
    spectral_report = sa.analyze(audio)
    print(f"  Spectral balance    : {spectral_report.summary()}")

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
    if not spectral_report.spectral_balance_ok:
        issues.append(
            f"Spectral imbalance detected (dominant band ≥ 90% of energy; "
            f"L:{spectral_report.low_ratio:.2f} M:{spectral_report.mid_ratio:.2f} "
            f"H:{spectral_report.high_ratio:.2f})"
        )

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

    from audio_engine.qa import LoudnessMeter, ClippingDetector, LoopAnalyzer, SpectralAnalyzer

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

        sa = SpectralAnalyzer(sample_rate=sr)
        spectral_report = sa.analyze(audio)

        checks: dict = {
            "loudness_lufs": round(float(loudness_result.integrated_lufs), 2),
            "true_peak_dbfs": round(float(loudness_result.true_peak_dbfs), 2),
            "loudness_range_lu": round(float(loudness_result.loudness_range_lu), 2),
            "has_clipping": bool(clip_report.has_clipping),
            "clipped_samples": int(clip_report.clipped_samples),
            "loudness_ok": bool(-30.0 <= loudness_result.integrated_lufs <= -9.0),
            "peak_ok": bool(loudness_result.true_peak_dbfs <= -0.1),
            "clipping_ok": bool(not clip_report.has_clipping),
            # Spectral data is always recorded for review reference (not a hard gate by default)
            "spectral_low_ratio": round(float(spectral_report.low_ratio), 4),
            "spectral_mid_ratio": round(float(spectral_report.mid_ratio), 4),
            "spectral_high_ratio": round(float(spectral_report.high_ratio), 4),
            "spectral_centroid_hz": round(float(spectral_report.spectral_centroid_hz), 2),
            "high_freq_ratio": round(float(spectral_report.high_freq_ratio), 4),
        }

        # Spectral balance gate: only enforced when --check-spectral is set
        if args.check_spectral:
            checks["spectral_balance_ok"] = bool(spectral_report.spectral_balance_ok)

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

    writer = ReviewLogWriter(progress_callback=(lambda msg: print(msg) if not args.quiet else None))

    variation_family_decisions = None
    if args.variation_family_decisions:
        variation_family_decisions = json.loads(
            Path(args.variation_family_decisions).read_text(encoding="utf-8")
        )
        if not isinstance(variation_family_decisions, list):
            raise ValueError("--variation-family-decisions JSON must be a list")

    # --from-result path: source entries from a request_batch_result.json
    if args.from_result:
        log = writer.append_from_result_json(
            result_json_path=Path(args.from_result),
            review_log_path=review_log_path,
            factory_root=factory_root,
            reviewer=args.reviewer,
            qa_report_path=args.qa_report,
            notes=args.note or [],
            variation_family_decisions=variation_family_decisions,
            include_skipped=args.include_skipped,
            project=args.project,
            scope=args.scope,
        )
        print(
            f"Review log updated — {len(log.get('entries', []))} entries, "
            f"{len(log.get('variationFamilyDecisions', []))} family decision(s)"
        )
        return

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


def _cmd_compose_piece(args: argparse.Namespace) -> None:
    """Compose a full structured musical piece with optional vocal overlay."""
    from audio_engine.ai.piece_composer import PieceComposer
    from audio_engine.export.audio_exporter import AudioExporter

    # Resolve backend
    if args.samples_dir:
        backend = "sample"
    elif args.orchestral:
        backend = "synth_orchestral"
    elif args.ps1:
        backend = "ps1"
    else:
        backend = "synth_orchestral"

    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    print(
        f"Composing piece: style={args.style}, sections={sections}, "
        f"vocals={'yes' if args.with_vocals else 'no'}, "
        f"backend={backend}, duration={args.duration}s"
    )

    composer = PieceComposer(
        sample_rate=args.sample_rate,
        seed=args.seed,
        backend=backend,
        vocal_preset=args.vocal_preset,
    )

    audio = composer.compose(
        style=args.style,
        sections=sections,
        with_vocals=args.with_vocals,
        duration=args.duration,
        quiet=args.quiet,
    )

    exporter = AudioExporter(sample_rate=args.sample_rate)
    out_path = exporter.export(audio, args.output, fmt=args.format)
    print(f"\nDone. Saved to: {out_path}")


def _cmd_list_music_library(args: argparse.Namespace) -> None:
    """Browse and filter the full music style catalog."""
    from audio_engine.ai.music_library import MusicLibrary
    lib = MusicLibrary()

    entries = lib.all_entries()
    if getattr(args, "game", None):
        entries = lib.by_game(args.game)
    elif getattr(args, "track_type", None):
        entries = lib.by_type(args.track_type)
    elif getattr(args, "search", None):
        entries = lib.search(args.search)
    if getattr(args, "vocals", False):
        entries = [e for e in entries if e.with_vocals]

    if getattr(args, "as_json", False):
        import json
        data = [
            {
                "style_key": e.style_key,
                "display_name": e.display_name,
                "game": e.game,
                "track_type": e.track_type,
                "bpm": e.bpm_approx,
                "mood": e.key_mood,
                "composer": e.composer,
                "with_vocals": e.with_vocals,
                "tags": e.tags,
            }
            for e in entries
        ]
        print(json.dumps(data, indent=2))
        return

    print(f"{'Style Key':<25} {'Display Name':<35} {'Game':<6} {'Type':<12} {'BPM':<5} {'Mood'}")
    print("-" * 100)
    for e in entries:
        v = " ♪" if e.with_vocals else ""
        print(f"{e.style_key:<25} {e.display_name + v:<35} {e.game:<6} {e.track_type:<12} {e.bpm_approx:<5} {e.key_mood}")
    print(f"\n{len(entries)} track(s) found.")


def _cmd_generate_track(args: argparse.Namespace) -> None:
    """Generate a single full-piece track from a style key or request."""
    from audio_engine.ai.music_library import MusicLibrary, style_for_request
    from audio_engine.ai.radio_playlist import RadioPlaylistGenerator

    lib = MusicLibrary()
    # Resolve style — may be a key or natural language
    all_keys = lib.all_style_keys()
    style_key = args.style if args.style in all_keys else style_for_request(args.style)

    entry = lib.get(style_key)
    display = entry.display_name if entry else style_key
    print(f"Generating full piece: '{display}' (style={style_key}) → {args.output} …")

    # Backend
    if getattr(args, "samples_dir", None):
        backend = "sample"
    elif getattr(args, "ps1", False):
        backend = "ps1"
    else:
        backend = "synth_orchestral"

    gen = RadioPlaylistGenerator(
        sample_rate=args.sample_rate,
        seed=args.seed,
        backend=backend,
        vocal_preset=args.vocal_preset,
    )
    out_path = gen.generate_track(
        style_key=style_key,
        output_path=args.output,
        duration=args.duration,
        fmt=args.format,
        with_vocals=args.with_vocals,
    )
    print(f"Done. Saved to: {out_path}")


def _cmd_generate_radio_playlist(args: argparse.Namespace) -> None:
    """Generate a full FF-radio style playlist of complete pieces."""
    from audio_engine.ai.radio_playlist import RadioPlaylistGenerator

    # Backend
    if getattr(args, "samples_dir", None):
        backend = "sample"
    elif getattr(args, "ps1", False):
        backend = "ps1"
    else:
        backend = "synth_orchestral"

    backend_kwargs = {"samples_dir": args.samples_dir} if getattr(args, "samples_dir", None) else None

    gen = RadioPlaylistGenerator(
        sample_rate=args.sample_rate,
        seed=args.seed,
        backend=backend,
        vocal_preset=args.vocal_preset,
        backend_kwargs=backend_kwargs,
    )

    if args.styles:
        playlist_input: "str | list[str]" = [s.strip() for s in args.styles.split(",") if s.strip()]
    else:
        playlist_input = args.preset

    gen.generate_playlist(
        preset_or_styles=playlist_input,
        output_dir=args.output_dir,
        track_duration=args.track_duration,
        fmt=args.format,
        with_vocals=args.with_vocals,
        force=args.force,
        quiet=args.quiet,
    )


def _cmd_generate_album(args: argparse.Namespace) -> None:
    """Generate a full multi-track album for a given music genre with FF epicness."""
    from audio_engine.ai.radio_playlist import RadioPlaylistGenerator

    # Backend
    if getattr(args, "samples_dir", None):
        backend = "sample"
    elif getattr(args, "ps1", False):
        backend = "ps1"
    else:
        backend = "synth_orchestral"

    backend_kwargs = {"samples_dir": args.samples_dir} if getattr(args, "samples_dir", None) else None

    gen = RadioPlaylistGenerator(
        sample_rate=args.sample_rate,
        seed=args.seed,
        backend=backend,
        vocal_preset=args.vocal_preset,
        backend_kwargs=backend_kwargs,
    )

    gen.generate_album(
        genre=args.genre,
        output_dir=args.output_dir,
        title=args.title,
        track_duration=args.track_duration,
        fmt=args.format,
        with_vocals=args.with_vocals,
        force=args.force,
        quiet=args.quiet,
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


def _cmd_verify_backends(args: argparse.Namespace) -> None:
    """Run deterministic preflight checks on all registered backends and emit a JSON report."""
    import datetime
    import json

    import numpy as np

    import audio_engine.ai.backends as _optional_backends  # noqa: F401
    from audio_engine.ai.backend import BackendRegistry

    sample_rate = args.sample_rate
    smoke = args.smoke
    quiet = args.quiet

    results: list[dict] = []
    all_available = True

    for name in BackendRegistry.available_backends():
        try:
            backend = BackendRegistry.get(name, sample_rate=sample_rate)
            available = backend.is_available()
            reason = backend.availability_reason()
            modalities = list(backend.supported_modalities())
            dep_summary = backend.dependency_summary()
        except Exception as exc:
            results.append({
                "backend": name,
                "available": False,
                "availability_reason": f"instantiation error: {exc}",
                "supported_modalities": [],
                "dependency_summary": "unknown",
                "smoke_run": None,
            })
            all_available = False
            if not quiet:
                print(f"  [error]  {name}: {exc}")
            continue

        smoke_backend = backend
        if smoke and available:
            try:
                smoke_backend = BackendRegistry.get(name, sample_rate=sample_rate, seed=42)
            except TypeError:
                smoke_backend = backend

        smoke_result: dict | None = None
        if smoke and available:
            smoke_result = {"music": None, "sfx": None, "voice": None}
            for modality in modalities:
                try:
                    if modality == "music":
                        audio = smoke_backend.generate_music_audio(
                            style="battle",
                            duration=0.25,
                        )
                        ok = isinstance(audio, np.ndarray) and audio.size > 0
                        smoke_result["music"] = "pass" if ok else "fail: empty output"
                    elif modality == "sfx":
                        audio = smoke_backend.generate_sfx_audio(
                            sfx_type="explosion",
                            duration=0.25,
                        )
                        ok = isinstance(audio, np.ndarray) and audio.size > 0
                        smoke_result["sfx"] = "pass" if ok else "fail: empty output"
                    elif modality == "voice":
                        audio = smoke_backend.generate_voice_audio(text="hello")
                        ok = isinstance(audio, np.ndarray) and audio.size > 0
                        smoke_result["voice"] = "pass" if ok else "fail: empty output"
                except Exception as exc:
                    smoke_result[modality] = f"fail: {exc}"

        record = {
            "backend": name,
            "available": available,
            "availability_reason": reason,
            "supported_modalities": modalities,
            "dependency_summary": dep_summary,
            "smoke_run": smoke_result,
        }
        results.append(record)
        if not available:
            all_available = False

        if not quiet:
            status_label = "available" if available else "unavailable"
            print(f"  [{status_label}]  {name}: {reason}")
            if smoke_result:
                for mod, res in smoke_result.items():
                    if res is not None:
                        print(f"             smoke/{mod}: {res}")

    report = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "sampleRate": sample_rate,
        "smokeRunEnabled": smoke,
        "allAvailable": all_available,
        "backends": results,
    }

    if args.output_report:
        out_path = Path(args.output_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not quiet:
            print(f"\nReport written → {out_path}")
    else:
        print()
        print(json.dumps(report, indent=2))

    if not all_available:
        raise SystemExit(2)


def _cmd_check_licenses(args: argparse.Namespace) -> None:
    """Check installed package licenses against the compliance policy and emit a JSON report."""
    import json as _json
    from pathlib import Path as _Path
    from audio_engine.compliance.license_checker import check_licenses

    policy_path = _Path(args.policy) if args.policy else None
    include_dev = args.include_dev
    all_installed = getattr(args, "all_installed", False)
    quiet = args.quiet

    report = check_licenses(policy_path=policy_path, include_dev=include_dev, all_installed=all_installed)

    if not quiet:
        print(f"Scanned {len(report.packages)} packages using policy: {report.policy_path}")
        print(f"Summary: allow={report.summary.get('allow', 0)}, "
              f"conditional={report.summary.get('conditional', 0)}, "
              f"block={report.summary.get('block', 0)}, "
              f"unknown={report.summary.get('unknown', 0)}")
        if not report.compliant:
            blocked = [p for p in report.packages if p.policy == "block"]
            unknown = [p for p in report.packages if p.policy == "unknown"]
            if blocked:
                print("\nBLOCKED packages (commercial use not permitted):")
                for p in blocked:
                    print(f"  {p.package} {p.version} — {p.spdx_license}: {p.policy_notes}")
            if unknown:
                print("\nUNKNOWN packages (license not verified — treated as block):")
                for p in unknown:
                    print(f"  {p.package} {p.version} — {p.spdx_license}: {p.policy_notes}")
        else:
            print("All packages comply with the license policy.")

    report_dict = report.to_dict()

    if args.output_report:
        out_path = _Path(args.output_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_json.dumps(report_dict, indent=2), encoding="utf-8")
        if not quiet:
            print(f"\nReport written → {out_path}")
    else:
        print()
        print(_json.dumps(report_dict, indent=2))

    if not report.compliant:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    from audio_engine.render.offline_bounce import VALID_PROFILES

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
    gm.add_argument(
        "--ps1",
        action="store_true",
        help="Apply PS1/FF7-era SPU character (bit-crush + SPU reverb). Overrides --backend.",
    )
    gm.add_argument(
        "--orchestral",
        action="store_true",
        help="Use synth-orchestral backend (clean PS2-quality mock-up). Overrides --backend.",
    )
    gm.add_argument(
        "--samples-dir",
        default=None,
        metavar="DIR",
        help=(
            "Path to a samples directory containing .wav files organised by category "
            "(strings/, brass/, choir/, etc.). Enables sample-based remastering on top "
            "of synth_orchestral (or ps1 if --ps1 is also set). Overrides --backend."
        ),
    )
    gm.add_argument(
        "--ps1-reverb",
        default="room",
        choices=["room", "hall", "space", "echo", "pipe", "off"],
        help="SPU reverb mode used with --ps1 (default: room).",
    )
    gm.add_argument(
        "--profile",
        choices=VALID_PROFILES,
        default="game",
        help="Mastering profile preset (default: game).",
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
    gs.add_argument(
        "--ps1",
        action="store_true",
        help="Apply PS1/FF7-era SPU character. Overrides --backend.",
    )
    gs.add_argument(
        "--orchestral",
        action="store_true",
        help="Use synth-orchestral backend. Overrides --backend.",
    )
    gs.add_argument(
        "--samples-dir",
        default=None,
        metavar="DIR",
        help="Path to samples directory for sample-augmented SFX. Overrides --backend.",
    )
    gs.add_argument(
        "--ps1-reverb",
        default="room",
        choices=["room", "hall", "space", "echo", "pipe", "off"],
        help="SPU reverb mode when --ps1 is set (default: room).",
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
    gv.add_argument(
        "--ps1",
        action="store_true",
        help="Apply PS1/FF7-era SPU character to voice. Overrides --backend.",
    )
    gv.add_argument(
        "--orchestral",
        action="store_true",
        help="Use synth-orchestral backend for voice. Overrides --backend.",
    )
    gv.add_argument(
        "--samples-dir",
        default=None,
        metavar="DIR",
        help=(
            "Path to samples directory (no effect on voice audio — voice samples are not "
            "blended; the base backend is still selected by --ps1/--orchestral)."
        ),
    )
    gv.add_argument(
        "--ps1-reverb",
        default="room",
        choices=["room", "hall", "space", "echo", "pipe", "off"],
        help="SPU reverb mode when --ps1 is set (default: room).",
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
        "--check-spectral",
        action="store_true",
        help=(
            "Enable spectral balance as a hard gate: fail if any single frequency band "
            "(low/mid/high) carries more than 90% of total energy. "
            "Spectral data is always recorded in the report regardless of this flag."
        ),
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
        default="unspecified",
        help="Reviewer label written to review-log entries (default: unspecified).",
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
        default="unspecified",
        help="Reviewer label written to review-log entries (default: unspecified).",
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
        default="unspecified",
        help="Reviewer label written to each entry (default: unspecified).",
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
    wrl.add_argument(
        "--from-result",
        help=(
            "Path to a request_batch_result.json written by generate-request-batch. "
            "When provided, entries are sourced from the recorded output paths in the result "
            "file instead of scanning audio directories."
        ),
    )
    wrl.add_argument(
        "--include-skipped",
        action="store_true",
        help="When using --from-result, also include 'skipped' records (default: only 'ok').",
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

    # --- remaster ---
    rm = sub.add_parser(
        "remaster",
        help=(
            "Remaster an existing WAV file by blending in real orchestral samples from a "
            "samples/ directory.  Drop .wav files into category sub-dirs (strings/, brass/, "
            "choir/, piano/, etc.) then run this command."
        ),
    )
    rm.add_argument("--input", "-i", required=True, help="Path to the WAV file to remaster.")
    rm.add_argument("--output", "-o", default="remastered.wav", help="Output file path.")
    rm.add_argument(
        "--samples-dir",
        default="samples/",
        metavar="DIR",
        help="Root samples directory (default: samples/).",
    )
    rm.add_argument(
        "--style",
        default="ff7_overworld",
        help=(
            "Style hint used to select which sample categories to blend "
            "(default: ff7_overworld).  Any music style name is accepted."
        ),
    )
    rm.add_argument(
        "--ps1",
        action="store_true",
        help="Use the PS1 bit-crushed base when blending rather than synth_orchestral.",
    )
    rm.add_argument(
        "--format",
        choices=["wav", "ogg"],
        default="wav",
        help="Output format (default: wav).",
    )
    rm.add_argument(
        "--events-json",
        default=None,
        help=(
            "Optional note-event JSON file for deterministic sample substitution. "
            "Accepted shape: [{'instrument','note','startSeconds','durationSeconds'}]."
        ),
    )
    rm.add_argument("--seed", type=int, default=None, help="Random seed.")

    # --- remaster-batch ---
    rmb = sub.add_parser(
        "remaster-batch",
        help="Deterministically remaster every WAV under an input directory with machine-readable results.",
    )
    rmb.add_argument("--input-dir", "-i", required=True, help="Directory tree containing source WAV files.")
    rmb.add_argument("--output-dir", "-o", required=True, help="Directory tree for remastered WAV outputs.")
    rmb.add_argument(
        "--samples-dir",
        default="samples/",
        metavar="DIR",
        help="Root samples directory (default: samples/).",
    )
    rmb.add_argument(
        "--events-dir",
        default=None,
        metavar="DIR",
        help="Optional directory containing <stem>.events.json files for source WAVs.",
    )
    rmb.add_argument(
        "--style",
        default="ff7_overworld",
        help="Style hint for synth fallback blend (default: ff7_overworld).",
    )
    rmb.add_argument(
        "--report-path",
        default=None,
        help="Optional output path for remaster_batch_result.json.",
    )
    rmb.add_argument("--seed", type=int, default=None, help="Random seed.")
    rmb.add_argument("--quiet", action="store_true", help="Suppress per-file progress output.")

    # --- compose-piece ---
    cp = sub.add_parser(
        "compose-piece",
        help=(
            "Compose a full structured musical piece (intro, verse, chorus, bridge, outro) "
            "with optional sung vocal overlay.  Produces a complete listening experience "
            "similar to 'Eyes on Me' from FF8."
        ),
    )
    cp.add_argument(
        "--style",
        default="ff8_ballad",
        help=(
            "Music style for the piece.  ``ff8_ballad`` is pre-configured for "
            "an 'Eyes on Me'-like result (default: ff8_ballad)."
        ),
    )
    cp.add_argument(
        "--sections",
        default="intro,verse,pre_chorus,chorus,bridge,chorus,outro",
        help=(
            "Comma-separated section names.  Available: "
            "intro, verse, pre_chorus, chorus, bridge, outro "
            "(default: intro,verse,pre_chorus,chorus,bridge,chorus,outro)."
        ),
    )
    cp.add_argument(
        "--with-vocals",
        action="store_true",
        default=True,
        help="Overlay a sung vocal melody line (default: enabled).",
    )
    cp.add_argument(
        "--no-vocals",
        dest="with_vocals",
        action="store_false",
        help="Disable vocal overlay (instrumental only).",
    )
    cp.add_argument(
        "--vocal-preset",
        default="soprano",
        choices=["soprano", "alto", "tenor", "choir_ah"],
        help="Vocal timbre preset (default: soprano).",
    )
    cp.add_argument(
        "--duration", type=float, default=90.0,
        help="Total piece duration in seconds (default: 90).",
    )
    cp.add_argument("--output", "-o", default="piece.wav", help="Output file path.")
    cp.add_argument(
        "--format",
        choices=["wav", "ogg"],
        default="wav",
        help="Output format (default: wav).",
    )
    cp.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")
    cp.add_argument("--seed", type=int, default=None, help="Random seed.")
    cp.add_argument(
        "--ps1",
        action="store_true",
        help="Use PS1 SPU backend for the piece instead of synth_orchestral.",
    )
    cp.add_argument(
        "--orchestral",
        action="store_true",
        help="Use synth_orchestral backend (default when no flag given).",
    )
    cp.add_argument(
        "--samples-dir",
        default=None,
        metavar="DIR",
        help="Path to samples directory for sample-augmented generation.",
    )
    cp.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-section progress messages.",
    )

    # --- list-styles ---
    sub.add_parser("list-styles", help="List available music generation styles.")

    # --- list-instruments ---
    sub.add_parser("list-instruments", help="List available synthesised instruments.")

    # --- list-backends ---
    sub.add_parser("list-backends", help="List available generation backends.")

    # --- verify-backends ---
    vb = sub.add_parser(
        "verify-backends",
        help=(
            "Run deterministic preflight checks on all registered backends and emit a "
            "machine-readable JSON report.  Use --smoke to also run brief generation "
            "smoke tests when a backend is available."
        ),
    )
    vb.add_argument(
        "--output-report", "-o",
        help="Path to write the JSON preflight report (optional; prints to stdout if omitted).",
    )
    vb.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Run a brief (0.25 s) generation smoke test per modality for each available "
            "backend.  Results appear in the report under 'smoke_run'."
        ),
    )
    vb.add_argument(
        "--sample-rate", type=int, default=44100,
        help="Sample rate passed to each backend during instantiation (default: 44100).",
    )
    vb.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-backend progress messages (report is still written/printed).",
    )

    # --- check-licenses ---
    cl = sub.add_parser(
        "check-licenses",
        help=(
            "Check installed package licenses against the compliance policy and emit a "
            "machine-readable JSON report.  Exits 0 when all packages are allow/conditional; "
            "exits 1 when any package is block or unknown."
        ),
    )
    cl.add_argument(
        "--policy", default=None,
        help=(
            "Path to the TOML license policy file.  Defaults to tools/license_policy.toml "
            "in the repository root."
        ),
    )
    cl.add_argument(
        "--output-report", "-o", default=None,
        help="Path to write the JSON compliance report (optional; prints to stdout if omitted).",
    )
    cl.add_argument(
        "--include-dev",
        action="store_true",
        help="Include dev/test packages declared in the dev extra.",
    )
    cl.add_argument(
        "--all-installed",
        action="store_true",
        help=(
            "Scan all packages in the current environment instead of only "
            "those declared in pyproject.toml."
        ),
    )
    cl.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable summary (JSON report is still written/printed).",
    )

    # --- studio ---
    sub.add_parser("studio", help="Launch the local Tkinter Audio Engine Studio.")

    # --- list-music-library ---
    lml = sub.add_parser(
        "list-music-library",
        help="Browse the full Final Fantasy + generic music style catalog.",
    )
    lml.add_argument(
        "--game", default=None,
        help="Filter by game (e.g. ff7, ff8, ff10, ff16, generic).",
    )
    lml.add_argument(
        "--type", default=None, dest="track_type",
        help="Filter by track type (battle, overworld, theme, ballad, ambient, boss, fanfare).",
    )
    lml.add_argument(
        "--search", default=None,
        help="Free-text search query.",
    )
    lml.add_argument(
        "--vocals", action="store_true",
        help="Show only tracks with vocal performance.",
    )
    lml.add_argument(
        "--json", action="store_true", dest="as_json",
        help="Output as JSON instead of human-readable table.",
    )

    # --- generate-track ---
    gt = sub.add_parser(
        "generate-track",
        help=(
            "Generate a single full musical piece from a style key or natural-language "
            "request and export it (intro → verse → chorus → bridge → outro)."
        ),
    )
    gt.add_argument(
        "--style", "-s",
        help=(
            "Style key (e.g. ff7_sad, ff8_ballad, ff10_zanarkand) OR a natural-language "
            "request like 'something sad from FF7' or 'Eyes on Me'."
        ),
        required=True,
    )
    gt.add_argument("--output", "-o", default="track.wav", help="Output file path.")
    gt.add_argument(
        "--duration", type=float, default=60.0,
        help="Target track duration in seconds (default: 60).",
    )
    gt.add_argument(
        "--with-vocals", action="store_true", default=None,
        help="Force vocal overlay (default: auto-detect from catalog).",
    )
    gt.add_argument(
        "--no-vocals", dest="with_vocals", action="store_false",
        help="Disable vocal overlay.",
    )
    gt.add_argument(
        "--vocal-preset", default="soprano",
        choices=["soprano", "alto", "tenor", "choir_ah"],
        help="Vocal timbre preset (default: soprano).",
    )
    gt.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")
    gt.add_argument("--seed", type=int, default=None, help="Random seed.")
    gt.add_argument(
        "--ps1", action="store_true",
        help="Use PS1 SPU backend.",
    )
    gt.add_argument(
        "--orchestral", action="store_true",
        help="Use synth_orchestral backend (default).",
    )
    gt.add_argument(
        "--samples-dir", default=None, metavar="DIR",
        help="Path to samples directory for sample-augmented generation.",
    )
    gt.add_argument(
        "--format", choices=["wav", "ogg"], default="wav",
        help="Output format (default: wav).",
    )

    # --- generate-radio-playlist ---
    grpl = sub.add_parser(
        "generate-radio-playlist",
        help=(
            "Generate a full playlist of complete musical pieces — like FF15's in-game "
            "radio.  Each track is a fully structured piece exported as a WAV/OGG file."
        ),
    )
    grpl.add_argument(
        "--preset", "-p", default="ff_radio",
        choices=list(__import__("audio_engine.ai.radio_playlist",
                                fromlist=["PLAYLIST_PRESETS"]).PLAYLIST_PRESETS.keys()),
        help=(
            "Playlist preset name (default: ff_radio).  "
            "FF presets: ff_radio, ff7_album, ff8_album, battle_mix, emotional_mix, "
            "boss_mix, overworld_mix, vocal_album, modern_ff, classic_ff.  "
            "Genre album presets (all with FF epicness): jazz_album, blues_album, "
            "pop_album, rock_album, electronic_album, metal_album, world_music_album, "
            "ambient_album, acoustic_album, cinematic_album."
        ),
    )
    grpl.add_argument(
        "--styles", default=None,
        help=(
            "Comma-separated list of style keys to use instead of a preset "
            "(e.g. ff7_sad,ff8_ballad,ff10_zanarkand)."
        ),
    )
    grpl.add_argument(
        "--output-dir", "-o", default="output/radio",
        help="Output directory for track files and playlist.json (default: output/radio).",
    )
    grpl.add_argument(
        "--track-duration", type=float, default=60.0,
        help="Target duration per track in seconds (default: 60).",
    )
    grpl.add_argument(
        "--format", choices=["wav", "ogg"], default="wav",
        help="Output format for each track (default: wav).",
    )
    grpl.add_argument(
        "--with-vocals", action="store_true", default=None,
        help="Force vocal overlay on all tracks.",
    )
    grpl.add_argument(
        "--no-vocals", dest="with_vocals", action="store_false",
        help="Disable vocals on all tracks (instrumental only).",
    )
    grpl.add_argument(
        "--vocal-preset", default="soprano",
        choices=["soprano", "alto", "tenor", "choir_ah"],
        help="Vocal timbre preset (default: soprano).",
    )
    grpl.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")
    grpl.add_argument("--seed", type=int, default=None, help="Random seed.")
    grpl.add_argument(
        "--ps1", action="store_true",
        help="Use PS1 SPU backend for all tracks.",
    )
    grpl.add_argument(
        "--orchestral", action="store_true",
        help="Use synth_orchestral backend (default).",
    )
    grpl.add_argument(
        "--samples-dir", default=None, metavar="DIR",
        help="Path to samples directory for sample-augmented generation.",
    )
    grpl.add_argument(
        "--force", action="store_true",
        help="Re-generate tracks even if the output files already exist.",
    )
    grpl.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress messages.",
    )

    # --- generate-album ---
    galb = sub.add_parser(
        "generate-album",
        help=(
            "Generate a complete multi-track album for a given music genre, "
            "each track rendered with Final Fantasy-style orchestral epicness."
        ),
    )
    galb.add_argument(
        "--genre", "-g", required=True,
        help=(
            "Music genre for the album.  Supported: jazz, blues, pop, rock, "
            "electronic, edm, synthwave, metal, world, latin, ambient, acoustic, "
            "folk, country, rnb, soul, cinematic, orchestral."
        ),
    )
    galb.add_argument(
        "--title", default=None,
        help="Album title (default: auto-generated from genre).",
    )
    galb.add_argument(
        "--output-dir", "-o", default="output/album",
        help="Output directory for track files and album.json (default: output/album).",
    )
    galb.add_argument(
        "--track-duration", type=float, default=60.0,
        help="Target duration per track in seconds (default: 60).",
    )
    galb.add_argument(
        "--format", choices=["wav", "ogg"], default="wav",
        help="Output format for each track (default: wav).",
    )
    galb.add_argument(
        "--with-vocals", action="store_true", default=None,
        help="Force vocal overlay on all tracks.",
    )
    galb.add_argument(
        "--no-vocals", dest="with_vocals", action="store_false",
        help="Disable vocals on all tracks (instrumental only).",
    )
    galb.add_argument(
        "--vocal-preset", default="soprano",
        choices=["soprano", "alto", "tenor", "choir_ah"],
        help="Vocal timbre preset (default: soprano).",
    )
    galb.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz.")
    galb.add_argument("--seed", type=int, default=None, help="Random seed.")
    galb.add_argument(
        "--ps1", action="store_true",
        help="Use PS1 SPU backend for all tracks.",
    )
    galb.add_argument(
        "--samples-dir", default=None, metavar="DIR",
        help="Path to samples directory for sample-augmented generation.",
    )
    galb.add_argument(
        "--force", action="store_true",
        help="Re-generate tracks even if output files already exist.",
    )
    galb.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress messages.",
    )

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
    grb.add_argument(
        "--write-provenance", action="store_true",
        help=(
            "Write a .provenance.json sidecar alongside each generated file "
            "(only effective when --request-file is used)."
        ),
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

    # --- export-wav-delivery ---
    ewdp = sub.add_parser(
        "export-wav-delivery",
        help=(
            "Package approved assets into a deterministic commercial WAV delivery. "
            "Reads from <factory-root>/approved/ and writes renamed copies plus "
            "a delivery_manifest.json to <delivery-dir>."
        ),
    )
    ewdp.add_argument(
        "--factory-root", "-f", required=True,
        help="Factory output root directory (must contain an approved/ sub-directory).",
    )
    ewdp.add_argument(
        "--delivery-dir", "-o", required=True,
        help="Destination directory for the delivery package.",
    )
    ewdp.add_argument(
        "--categories", "-c", nargs="+",
        metavar="CATEGORY",
        help="Optional list of category sub-directories to include (e.g. music sfx). "
             "Includes all categories when omitted.",
    )
    ewdp.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file progress messages.",
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
            write_provenance=args.write_provenance,
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


def _cmd_export_wav_delivery(args: argparse.Namespace) -> None:
    """Package approved assets into a deterministic commercial WAV delivery."""
    from audio_engine.integration.export_contract import WavDeliveryPipeline

    quiet = getattr(args, "quiet", False)

    def _progress(msg: str) -> None:
        if not quiet:
            print(f"  {msg}")

    pipeline = WavDeliveryPipeline(progress_callback=_progress)

    categories = args.categories if args.categories else None

    report = pipeline.deliver(
        factory_root=args.factory_root,
        delivery_dir=args.delivery_dir,
        categories=categories,
    )

    s = report["summary"]
    print(
        f"\nWAV delivery: {s['copied']}/{s['total']} files copied"
        f" → {report['deliveryDir']}"
    )
    if not quiet:
        print(f"  Manifest: {report['deliveryDir']}/delivery_manifest.json")


def _cmd_remaster_batch(args: argparse.Namespace) -> None:
    """Run deterministic remaster-batch execution over a WAV directory tree."""
    from audio_engine.integration.asset_pipeline import RemasterBatchPipeline

    quiet = getattr(args, "quiet", False)

    def _progress(msg: str) -> None:
        if not quiet:
            print(msg)

    pipeline = RemasterBatchPipeline(progress_callback=_progress)
    result = pipeline.execute(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        samples_dir=args.samples_dir,
        style=args.style,
        events_dir=args.events_dir,
        report_path=args.report_path,
        seed=args.seed,
    )
    print(result.summary())


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "generate": _cmd_generate,
        "generate-music": _cmd_generate_music,
        "generate-sfx": _cmd_generate_sfx,
        "generate-voice": _cmd_generate_voice,
        "remaster": _cmd_remaster,
        "remaster-batch": _cmd_remaster_batch,
        "compose-piece": _cmd_compose_piece,
        "list-music-library": _cmd_list_music_library,
        "generate-track": _cmd_generate_track,
        "generate-radio-playlist": _cmd_generate_radio_playlist,
        "generate-album": _cmd_generate_album,
        "qa": _cmd_qa,
        "qa-batch": _cmd_qa_batch,
        "approve-draft": _cmd_approve_draft,
        "export-drafts": _cmd_export_drafts,
        "write-review-log": _cmd_write_review_log,
        "sfx": _cmd_sfx,
        "list-styles": _cmd_list_styles,
        "list-instruments": _cmd_list_instruments,
        "list-backends": _cmd_list_backends,
        "verify-backends": _cmd_verify_backends,
        "check-licenses": _cmd_check_licenses,
        "studio": _cmd_studio,
        "generate-request-batch": _cmd_generate_request_batch,
        "generate-plan-batch": _cmd_generate_plan_batch,
        "generate-game-assets": _cmd_generate_game_assets,
        "verify-game-assets": _cmd_verify_game_assets,
        "export-wav-delivery": _cmd_export_wav_delivery,
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
