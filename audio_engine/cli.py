"""
Command-line interface for the Audio Engine.

Usage examples
--------------
Generate a battle track (WAV):
    audio-engine generate --style battle --bars 8 --output battle.wav

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audio-engine",
        description="Audio Engine for Game Engine for Teaching – produce music and SFX.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- generate ---
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

    # --- sfx ---
    sfx = sub.add_parser("sfx", help="Render a quick sound effect.")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "generate": _cmd_generate,
        "sfx": _cmd_sfx,
        "list-styles": _cmd_list_styles,
        "list-instruments": _cmd_list_instruments,
    }

    handler = dispatch.get(args.command)
    if handler is None:  # pragma: no cover
        parser.print_help()
        return 1

    try:
        handler(args)
        return 0
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover – surface unexpected errors
        print(f"Unexpected error: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())
