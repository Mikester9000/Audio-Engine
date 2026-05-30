"""Tkinter studio for interactive local generation."""

from __future__ import annotations

import functools
import json
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Protocol

from audio_engine.ai.backend import BackendRegistry
from audio_engine.ai.generator import MusicGenerator
from audio_engine.ai.piece_composer import PieceComposer, SECTION_TEMPLATES
from audio_engine.ai.sfx_gen import SFXGen
from audio_engine.ai.sfx_synth import available_sfx_types
from audio_engine.ai.voice_gen import VoiceGen
from audio_engine.ai.voice_synth import VOICE_PRESETS
from audio_engine.render.offline_bounce import VALID_PROFILES, OfflineBounce
from audio_engine.synthesizer.instrument import InstrumentLibrary

_DEFAULT_SAMPLE_ROOT = "samples"
_FALLBACK_STUDIO_BACKENDS = ["procedural", "sample"]
_STYLE_OVERRIDE_LOCK = threading.Lock()


class _StatusLabel(Protocol):
    def configure(self, **kwargs: object) -> object: ...
    def update_idletasks(self) -> object: ...


class _PlaybackHandle(Protocol):
    def stop(self) -> None: ...


class _ProcessPlaybackHandle:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process

    def stop(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()


class _WindowsPlaybackHandle:
    def stop(self) -> None:
        import winsound

        winsound.PlaySound(None, winsound.SND_PURGE)


def _discover_wav_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.wav") if p.is_file())


def _build_preview_catalog(
    *,
    music_output: Path,
    sfx_output: Path,
    voice_output: Path,
    examples_root: Path,
    extra_music_outputs: list[Path] | None = None,
) -> dict[str, list[Path]]:
    catalog: dict[str, list[Path]] = {
        "Music": [],
        "SFX": [],
        "Vocal": [],
        "Examples": [],
    }

    def _append_unique_path(paths: list[Path], candidate: Path) -> None:
        if candidate.exists() and candidate not in paths:
            paths.append(candidate)

    _append_unique_path(catalog["Music"], music_output)
    for extra_path in extra_music_outputs or []:
        _append_unique_path(catalog["Music"], extra_path)
    if sfx_output.exists():
        catalog["SFX"].append(sfx_output)
    if voice_output.exists():
        catalog["Vocal"].append(voice_output)
    catalog["Examples"].extend(_discover_wav_files(examples_root))
    return catalog


@functools.lru_cache(maxsize=8)
def _available_backends_for_modality(modality: str, *, sample_rate: int) -> list[str]:
    try:
        evaluations = BackendRegistry.evaluate_backends(sample_rate=sample_rate, seed=0)
    except Exception:
        return list(_FALLBACK_STUDIO_BACKENDS)
    names = [
        str(entry["name"])
        for entry in evaluations
        if bool(entry.get("available", False))
        and modality in [str(item) for item in entry.get("supported_modalities", [])]
    ]
    if "procedural" not in names:
        names.insert(0, "procedural")
    return sorted(set(names))


def _resolve_backend(
    *,
    backend_name: str,
    sample_rate: int,
    seed: int,
    samples_dir: str,
    sample_base_backend: str,
):
    if backend_name == "sample":
        from audio_engine.ai.sample_backend import SampleBackend

        return SampleBackend(
            samples_dir=samples_dir or _DEFAULT_SAMPLE_ROOT,
            sample_rate=sample_rate,
            seed=seed,
            base_backend=sample_base_backend,
        )
    return BackendRegistry.get(backend_name, sample_rate=sample_rate, seed=seed)


def _start_playback(path: Path) -> _PlaybackHandle:
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    if sys.platform.startswith("win"):
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        return _WindowsPlaybackHandle()
    players: list[list[str]] = []
    if shutil.which("afplay"):
        players.append(["afplay", str(path)])
    if shutil.which("aplay"):
        players.append(["aplay", str(path)])
    if shutil.which("paplay"):
        players.append(["paplay", str(path)])
    if shutil.which("ffplay"):
        players.append(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)])
    for command in players:
        try:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return _ProcessPlaybackHandle(process)
        except OSError:
            continue
    raise RuntimeError("No supported local audio player found (afplay/aplay/paplay/ffplay).")


def _safe_int(value: str | int, fallback: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return fallback
    try:
        return int(value.strip())
    except ValueError:
        return fallback


def _parse_float_field(value: object, *, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid preset field '{field_name}': expected float") from exc


def _read_studio_preset(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"failed to read preset JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("studio preset must be a JSON object")
    return data


def _write_studio_preset(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _normalize_instrument_choice(value: str, fallback: str) -> str:
    available = set(InstrumentLibrary.available())
    if value in available:
        return value
    return fallback


def _new_file_output_targets(base_name: str, output_dir: str | Path, *, fmt: str = "wav") -> dict[str, str]:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", base_name.strip()).strip("_")
    clean = normalized or "new_asset"
    ext = fmt.lower().strip(".")
    if ext not in {"wav", "ogg"}:
        ext = "wav"
    root = Path(output_dir)
    return {
        "music": str(root / f"{clean}_music.{ext}"),
        "sfx": str(root / f"{clean}_sfx.wav"),
        "voice": str(root / f"{clean}_voice.wav"),
    }


def _build_new_file_template(
    *,
    project_name: str,
    preset_path: str,
    output_targets: dict[str, str],
    preset_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "projectName": project_name.strip() or "new_audio_asset",
        "presetPath": preset_path,
        "outputTargets": output_targets,
        "preset": preset_payload,
    }


def _write_new_file_template(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _set_status(label: _StatusLabel, text: str) -> None:
    label.configure(text=text)
    label.update_idletasks()


def _attach_value_label(
    parent: object,
    variable: object,
    *,
    row: int,
    col: int = 2,
    fmt: str = "{:.2f}",
    width: int = 7,
) -> None:
    """Place a live read-only label beside a slider showing its current value."""
    import tkinter as tk
    from tkinter import ttk

    val_str = tk.StringVar(value=fmt.format(variable.get()))  # type: ignore[attr-defined]
    lbl = ttk.Label(parent, textvariable=val_str, width=width, anchor="w")
    lbl.grid(row=row, column=col, sticky="w", padx=(2, 8))

    def _update(*_args: object) -> None:
        try:
            val_str.set(fmt.format(variable.get()))  # type: ignore[attr-defined]
        except Exception:
            pass

    variable.trace_add("write", _update)  # type: ignore[attr-defined]


def _browse_output_path(path_var: object, *, title: str = "Save As", filetypes: list | None = None) -> None:
    """Open a Save As dialog and write the chosen path into path_var."""
    from tkinter import filedialog

    if filetypes is None:
        filetypes = [("WAV files", "*.wav"), ("OGG files", "*.ogg"), ("All files", "*.*")]
    chosen = filedialog.asksaveasfilename(title=title, filetypes=filetypes)
    if chosen:
        path_var.set(chosen)  # type: ignore[attr-defined]


_SYNTH_WAVEFORMS = ["sine", "square", "sawtooth", "triangle", "noise", "bl_sawtooth", "bl_square"]
_SYNTH_FILTER_TYPES = ["none", "lowpass", "highpass", "bandpass"]
_PC_SECTION_TYPES = list(SECTION_TEMPLATES.keys())  # available section names for Piece Composer
_PC_VOCAL_PRESETS = ["soprano", "alto", "tenor", "choir_ah"]

# Musical note name → frequency (Hz) for instrument browser / synth preview
_NOTE_FREQS: dict[str, float] = {
    "C2": 65.41, "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.00, "A2": 110.00, "B2": 123.47,
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46, "G5": 784.00, "A5": 880.00, "B5": 987.77,
}
_NOTE_NAMES = list(_NOTE_FREQS.keys())
_NOTE_TO_INDEX = {name: idx for idx, name in enumerate(_NOTE_NAMES)}
_INDEX_TO_NOTE = {idx: name for idx, name in enumerate(_NOTE_NAMES)}

_PR_TRACK_TEMPLATES: dict[str, list[dict[str, object]]] = {
    "PS2 Starter Trio": [
        {"name": "Lead", "instrument": "legato_strings_ps2", "role": "melody", "volume": 1.0, "pan": -0.1},
        {"name": "Bass", "instrument": "bass", "role": "bass", "volume": 0.9, "pan": 0.0},
        {"name": "Rhythm", "instrument": "nylon_guitar_ps2", "role": "harmony", "volume": 0.85, "pan": 0.12},
    ],
    "Modern Starter": [
        {"name": "Lead", "instrument": "synth_lead_bright", "role": "melody", "volume": 1.0, "pan": 0.0},
        {"name": "Pad", "instrument": "soft_epiano_ps2", "role": "texture", "volume": 0.8, "pan": -0.15},
        {"name": "Bass", "instrument": "bass", "role": "bass", "volume": 0.9, "pan": 0.0},
    ],
}

_PIECE_SONG_RECIPES: dict[str, dict[str, object]] = {
    "FF8 Ballad Full Song": {
        "style": "ff8_ballad",
        "backend": "synth_orchestral",
        "profile": "ost",
        "duration": 120.0,
        "with_vocals": True,
        "vocal_preset": "soprano",
        "sections": ["intro", "verse", "pre_chorus", "chorus", "verse", "pre_chorus", "chorus", "bridge", "chorus", "outro"],
        "output_stem": "ff8_ballad_full_song",
    },
    "JRPG Adventure Loop": {
        "style": "town",
        "backend": "procedural",
        "profile": "game",
        "duration": 96.0,
        "with_vocals": False,
        "vocal_preset": "soprano",
        "sections": ["intro", "verse", "chorus", "verse", "chorus", "outro"],
        "output_stem": "jrpg_adventure_loop",
    },
    "Boss Battle Suite": {
        "style": "ff7_boss",
        "backend": "full_orchestral",
        "profile": "ost",
        "duration": 110.0,
        "with_vocals": True,
        "vocal_preset": "choir_ah",
        "sections": ["intro", "verse", "chorus", "bridge", "chorus", "chorus", "outro"],
        "output_stem": "boss_battle_suite",
    },
}

_STUDIO_WORKFLOW_PRESETS: dict[str, dict[str, dict[str, object]]] = {
    "Video Game Production": {
        "music": {
            "style": "battle",
            "prompt": "loopable jrpg battle theme for gameplay",
            "backend": "procedural",
            "profile": "game",
            "bars": 16,
            "region": "ruins",
            "adaptiveIntensity": True,
            "format": "ogg",
        },
        "sfx": {
            "category": "footstep",
            "durationSeconds": 0.25,
        },
        "piece": {
            "style": "ff7_boss",
            "backend": "full_orchestral",
            "profile": "ost",
            "durationSeconds": 96.0,
            "withVocals": False,
            "vocalPreset": "choir_ah",
            "format": "ogg",
            "songRecipe": "Boss Battle Suite",
        },
        "studio": {
            "baseName": "game_audio_pack",
        },
    },
    "Professional Music Production": {
        "music": {
            "style": "ff8_ballad",
            "prompt": "commercial release quality emotional orchestral ballad",
            "backend": "full_orchestral",
            "profile": "ost",
            "bars": 32,
            "region": "",
            "adaptiveIntensity": False,
            "format": "wav",
        },
        "sfx": {
            "category": "ui_click",
            "durationSeconds": 0.12,
        },
        "piece": {
            "style": "ff8_ballad",
            "backend": "full_orchestral",
            "profile": "youtube",
            "durationSeconds": 180.0,
            "withVocals": True,
            "vocalPreset": "soprano",
            "format": "wav",
            "songRecipe": "FF8 Ballad Full Song",
        },
        "studio": {
            "baseName": "pro_music_release",
        },
    },
}


def _studio_workflow_preset(goal: str) -> dict[str, dict[str, object]]:
    selected = _STUDIO_WORKFLOW_PRESETS.get(goal)
    if selected is None:
        selected = _STUDIO_WORKFLOW_PRESETS["Video Game Production"]
    return {
        "music": dict(selected["music"]),
        "sfx": dict(selected["sfx"]),
        "piece": dict(selected["piece"]),
        "studio": dict(selected["studio"]),
    }


def _piano_roll_snap_beat(beat: float, snap: float) -> float:
    snap_value = max(0.0, float(snap))
    if snap_value <= 0.0:
        return max(0.0, float(beat))
    return max(0.0, round(float(beat) / snap_value) * snap_value)


def _piano_roll_note_to_index(note: str) -> int:
    return _NOTE_TO_INDEX.get(note, _NOTE_TO_INDEX["A4"])


def _piano_roll_index_to_note(index: int) -> str:
    if index < 0:
        index = 0
    if index >= len(_NOTE_NAMES):
        index = len(_NOTE_NAMES) - 1
    return _INDEX_TO_NOTE[index]


def _piano_roll_clone_note(note: dict[str, object]) -> dict[str, object]:
    return {
        "beat": float(note.get("beat", 0.0)),
        "note": str(note.get("note", "A4")),
        "duration_beats": max(0.05, float(note.get("duration_beats", 1.0))),
        "velocity": min(1.0, max(0.0, float(note.get("velocity", 1.0)))),
    }


def _piano_roll_duplicate_notes(notes: list[dict[str, object]], *, beat_offset: float) -> list[dict[str, object]]:
    clones = [_piano_roll_clone_note(note) for note in notes]
    for note in clones:
        note["beat"] = max(0.0, float(note["beat"]) + float(beat_offset))
    return sorted(clones, key=lambda item: float(item["beat"]))


def _piano_roll_transpose_notes(notes: list[dict[str, object]], *, semitones: int) -> list[dict[str, object]]:
    shifted: list[dict[str, object]] = []
    for note in notes:
        clone = _piano_roll_clone_note(note)
        lane = _piano_roll_note_to_index(str(clone["note"]))
        clone["note"] = _piano_roll_index_to_note(lane + int(semitones))
        shifted.append(clone)
    return shifted


def _piano_roll_nudge_notes(
    notes: list[dict[str, object]],
    *,
    beat_delta: float,
    snap: float | None = None,
) -> list[dict[str, object]]:
    shifted: list[dict[str, object]] = []
    for note in notes:
        clone = _piano_roll_clone_note(note)
        beat = max(0.0, float(clone["beat"]) + float(beat_delta))
        if snap is not None:
            beat = _piano_roll_snap_beat(beat, snap)
        clone["beat"] = beat
        shifted.append(clone)
    return sorted(shifted, key=lambda item: float(item["beat"]))


def _piano_roll_quantize_notes(notes: list[dict[str, object]], *, snap: float) -> list[dict[str, object]]:
    quantized: list[dict[str, object]] = []
    for note in notes:
        clone = _piano_roll_clone_note(note)
        clone["beat"] = _piano_roll_snap_beat(float(clone["beat"]), snap)
        clone["duration_beats"] = max(float(snap), _piano_roll_snap_beat(float(clone["duration_beats"]), snap))
        quantized.append(clone)
    return sorted(quantized, key=lambda item: float(item["beat"]))


def _piano_roll_humanize_notes(
    notes: list[dict[str, object]],
    *,
    timing_amount: float,
    velocity_amount: float,
    seed: int = 0,
) -> list[dict[str, object]]:
    import random

    rng = random.Random(seed)
    humanized: list[dict[str, object]] = []
    for note in notes:
        clone = _piano_roll_clone_note(note)
        beat_shift = rng.uniform(-abs(timing_amount), abs(timing_amount))
        vel_shift = rng.uniform(-abs(velocity_amount), abs(velocity_amount))
        clone["beat"] = max(0.0, float(clone["beat"]) + beat_shift)
        clone["velocity"] = min(1.0, max(0.0, float(clone["velocity"]) + vel_shift))
        humanized.append(clone)
    return sorted(humanized, key=lambda item: float(item["beat"]))


def _clone_piano_roll_tracks(tracks: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    cloned: dict[str, dict[str, object]] = {}
    for track_name, config in tracks.items():
        cloned[track_name] = {
            "instrument": str(config.get("instrument", "piano")),
            "role": str(config.get("role", "harmony")),
            "volume": float(config.get("volume", 1.0)),
            "pan": float(config.get("pan", 0.0)),
            "mute": bool(config.get("mute", False)),
            "solo": bool(config.get("solo", False)),
            "notes": [_piano_roll_clone_note(note) for note in config.get("notes", [])],
        }
    return cloned


def _compose_piece_to_file(
    *,
    style: str,
    sections: list[str],
    with_vocals: bool,
    duration: float,
    backend_name: str,
    vocal_preset: str,
    seed: int,
    output_path: Path,
    mastering_profile: str,
    samples_dir: str,
    sample_base_backend: str,
    fmt: str,
) -> Path:
    """Generate a full multi-section musical piece and write it to *output_path*."""
    backend_kwargs: dict[str, object] | None = None
    if backend_name == "sample":
        backend_kwargs = {
            "samples_dir": samples_dir or _DEFAULT_SAMPLE_ROOT,
            "base_backend": sample_base_backend,
        }
    composer = PieceComposer(
        sample_rate=44100,
        seed=seed,
        backend=backend_name,
        vocal_preset=vocal_preset,
        backend_kwargs=backend_kwargs,
    )
    audio = composer.compose(
        style=style,
        sections=sections,
        with_vocals=with_vocals,
        duration=duration,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bouncer = OfflineBounce(sample_rate=44100, profile=mastering_profile)
    return bouncer.process_and_export(audio, output_path, fmt=fmt)


def _preview_instrument_note(
    instrument_name: str,
    note: str,
    duration: float,
    output_path: Path,
    *,
    sample_rate: int = 44100,
) -> Path:
    """Render a single instrument note and write it as a WAV file."""
    from audio_engine.export.audio_exporter import AudioExporter

    freq = _NOTE_FREQS.get(note, 440.0)
    instr = InstrumentLibrary.get(instrument_name, sample_rate=sample_rate)
    audio = instr.render(freq, duration)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    exporter = AudioExporter(sample_rate=sample_rate)
    return exporter.export(audio, output_path, fmt="wav")


def _save_preview_note_sample(
    *,
    preview_path: Path,
    sample_root: Path,
    instrument_name: str,
    note: str,
) -> Path:
    if not preview_path.exists():
        raise FileNotFoundError(f"Preview file does not exist: {preview_path}")
    safe_instrument = re.sub(r"[^A-Za-z0-9_-]+", "_", instrument_name).strip("_") or "instrument"
    safe_note = re.sub(r"[^A-Za-z0-9#_-]+", "_", note).strip("_") or "A4"
    target_dir = sample_root / safe_instrument
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{safe_note}.wav"
    shutil.copy2(preview_path, target_path)
    return target_path


def _build_synth_patch_ext(
    *,
    waveform: str,
    frequency: float,
    duration: float,
    amplitude: float,
    attack: float,
    decay: float,
    sustain: float,
    release: float,
    filter_type: str,
    filter_cutoff: float,
    filter_q: float,
    detune_cents: float = 0.0,
    waveform2: str = "none",
    osc2_mix: float = 0.0,
    osc2_octave: int = 0,
    lfo_rate: float = 0.0,
    lfo_depth: float = 0.0,
    lfo_target: str = "pitch",
    sample_rate: int = 44100,
) -> "np.ndarray":
    """Extended synth patch builder with detune, dual oscillator and LFO.

    Returns a mono float32 NumPy array normalised to the range [-1, 1].
    """
    import numpy as np
    from audio_engine.synthesizer.oscillator import Oscillator
    from audio_engine.synthesizer.envelope import Envelope
    from audio_engine.synthesizer.filter import Filter

    detune_ratio = 2.0 ** (detune_cents / 1200.0)
    freq1 = frequency * detune_ratio

    osc = Oscillator(sample_rate=sample_rate)

    def _render_wave(wf: str, freq: float, amp: float) -> "np.ndarray":
        wave_fn = getattr(osc, wf, None)
        if wave_fn is None:
            raise ValueError(f"Unknown waveform: {wf!r}")
        if wf == "noise":
            return osc.noise(duration, amp)
        return wave_fn(freq, duration, amp)

    # Primary oscillator
    sig = _render_wave(waveform, freq1, amplitude)

    # Secondary oscillator (mix in if enabled)
    if waveform2 != "none" and osc2_mix > 0.0:
        freq2 = frequency * (2.0 ** osc2_octave)
        sig2 = _render_wave(waveform2, freq2, amplitude)
        sig = sig * (1.0 - osc2_mix) + sig2 * osc2_mix

    # LFO modulation
    n_samples = len(sig)
    if lfo_rate > 0.0 and lfo_depth > 0.0:
        t = np.linspace(0.0, duration, n_samples, endpoint=False)
        lfo = np.sin(2.0 * np.pi * lfo_rate * t) * lfo_depth
        if lfo_target == "amplitude":
            sig = sig * (1.0 + lfo)
        elif lfo_target == "filter":
            # Modulate cutoff; handled below after filter section
            pass  # applied after filter build

    # ADSR envelope
    env = Envelope(
        attack=attack,
        decay=decay,
        sustain=max(0.0, min(1.0, sustain)),
        release=release,
        sample_rate=sample_rate,
    )
    shaped = env.apply(sig, duration)

    # Filter (with optional LFO on cutoff)
    if filter_type != "none":
        cutoff_base = max(20.0, min(filter_cutoff, sample_rate / 2.0 - 1.0))
        filt = Filter(sample_rate=sample_rate)
        if lfo_rate > 0.0 and lfo_depth > 0.0 and lfo_target == "filter":
            # Apply a single static filter at the LFO-modulated midpoint cutoff
            t_mid = duration / 2.0
            lfo_mid = np.sin(2.0 * np.pi * lfo_rate * t_mid) * lfo_depth
            cutoff_base = max(20.0, min(cutoff_base * (1.0 + lfo_mid), sample_rate / 2.0 - 1.0))
        if filter_type == "lowpass":
            shaped = filt.low_pass(shaped, cutoff_base)
        elif filter_type == "highpass":
            shaped = filt.high_pass(shaped, cutoff_base)
        elif filter_type == "bandpass":
            band_low = max(20.0, cutoff_base * 0.5)
            band_high = min(sample_rate / 2.0 - 1.0, cutoff_base * 2.0)
            shaped = filt.band_pass(shaped, band_low, band_high)

    peak = float(np.max(np.abs(shaped)))
    if peak > 1e-9:
        shaped = shaped / peak * min(amplitude, 1.0)

    return shaped.astype(np.float32)


def _build_synth_patch(
    *,
    waveform: str,
    frequency: float,
    duration: float,
    amplitude: float,
    attack: float,
    decay: float,
    sustain: float,
    release: float,
    filter_type: str,
    filter_cutoff: float,
    filter_q: float,
    sample_rate: int = 44100,
) -> "np.ndarray":
    """Build a raw synth sound using oscillator + ADSR + optional filter.

    Returns a mono float32 NumPy array normalised to the range [-1, 1].
    """
    import numpy as np
    from audio_engine.synthesizer.oscillator import Oscillator
    from audio_engine.synthesizer.envelope import Envelope
    from audio_engine.synthesizer.filter import Filter

    osc = Oscillator(sample_rate=sample_rate)
    wave_fn = getattr(osc, waveform, None)
    if wave_fn is None:
        raise ValueError(f"Unknown waveform: {waveform!r}")
    if waveform == "noise":
        raw: np.ndarray = osc.noise(duration, amplitude)
    else:
        raw = wave_fn(frequency, duration, amplitude)

    env = Envelope(
        attack=attack,
        decay=decay,
        sustain=max(0.0, min(1.0, sustain)),
        release=release,
        sample_rate=sample_rate,
    )
    shaped = env.apply(raw, duration)

    if filter_type != "none":
        filt = Filter(sample_rate=sample_rate)
        cutoff = max(20.0, min(filter_cutoff, sample_rate / 2.0 - 1.0))
        if filter_type == "lowpass":
            shaped = filt.low_pass(shaped, cutoff)
        elif filter_type == "highpass":
            shaped = filt.high_pass(shaped, cutoff)
        elif filter_type == "bandpass":
            band_low = max(20.0, cutoff * 0.5)
            band_high = min(sample_rate / 2.0 - 1.0, cutoff * 2.0)
            shaped = filt.band_pass(shaped, band_low, band_high)
        else:
            raise ValueError(f"Unknown filter_type: {filter_type!r}")

    peak = float(np.max(np.abs(shaped)))
    if peak > 1e-9:
        shaped = shaped / peak * min(amplitude, 1.0)

    return shaped.astype(np.float32)


def _export_synth_patch(audio: "np.ndarray", output_path: Path, *, sample_rate: int = 44100) -> Path:
    """Write *audio* as a 16-bit WAV file to *output_path*."""
    from audio_engine.export.audio_exporter import AudioExporter

    output_path.parent.mkdir(parents=True, exist_ok=True)
    exporter = AudioExporter(sample_rate=sample_rate)
    return exporter.export(audio, output_path, fmt="wav")


# ---------------------------------------------------------------------------
# Piano Roll data types — used by the Piano Roll tab and its render helper
# ---------------------------------------------------------------------------

def _render_piano_roll_to_file(
    tracks_data: dict[str, dict],
    *,
    bpm: float,
    time_signature: int,
    output_path: Path,
    mastering_profile: str,
    fmt: str,
    sample_rate: int = 44100,
) -> Path:
    """Render a multi-track piano roll composition to an audio file.

    Parameters
    ----------
    tracks_data:
        Mapping of track name → track config dict with keys:
        ``instrument`` (str), ``pan`` (float), ``volume`` (float),
        ``role`` (str), ``notes`` (list of note dicts with keys
        ``beat``, ``note``, ``duration_beats``, ``velocity``).
    bpm:
        Beats per minute.
    time_signature:
        Beats per bar.
    output_path:
        Destination file path.
    mastering_profile:
        Mastering profile name (passed to :class:`OfflineBounce`).
    fmt:
        Output format ``"wav"`` or ``"ogg"``.
    sample_rate:
        Audio sample rate.
    """
    from audio_engine.composer.sequencer import Sequencer

    seq = Sequencer(bpm=bpm, time_signature=time_signature, sample_rate=sample_rate)
    beat_dur = 60.0 / bpm
    solo_tracks = {
        tname
        for tname, tcfg in tracks_data.items()
        if bool(tcfg.get("solo", False))
    }

    for track_name, tcfg in tracks_data.items():
        if solo_tracks and track_name not in solo_tracks:
            continue
        if not solo_tracks and bool(tcfg.get("mute", False)):
            continue
        instrument = InstrumentLibrary.get(str(tcfg.get("instrument", "piano")), sample_rate=sample_rate)
        seq.add_track(
            name=track_name,
            instrument=instrument,
            pan=float(tcfg.get("pan", 0.0)),
            volume=float(tcfg.get("volume", 1.0)),
            role=str(tcfg.get("role", "harmony")),
        )
        for nd in tcfg.get("notes", []):
            note_name = str(nd.get("note", "A4"))
            freq = _NOTE_FREQS.get(note_name, 440.0)
            onset_sec = float(nd.get("beat", 0.0)) * beat_dur
            dur_sec = max(0.05, float(nd.get("duration_beats", 1.0)) * beat_dur)
            velocity = float(nd.get("velocity", 1.0))
            seq.add_note(track_name, freq, onset_sec, dur_sec, velocity)

    audio = seq.render()
    # Guard against empty render (no notes at all) — produce 0.5 s of silence
    import numpy as _np
    if audio.size == 0:
        audio = _np.zeros((int(sample_rate * 0.5), 2), dtype=_np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bouncer = OfflineBounce(sample_rate=sample_rate, profile=mastering_profile)
    return bouncer.process_and_export(audio, output_path, fmt=fmt)


def launch_studio() -> None:
    import tkinter as tk
    from tkinter import filedialog, ttk

    root = tk.Tk()
    root.title("Audio Engine Studio")
    root.geometry("1100x800")
    style_metadata = MusicGenerator.available_style_metadata()
    last_failed_action: str | None = None
    playback_handle: _PlaybackHandle | None = None
    preview_catalog: dict[str, list[Path]] = {}

    control_bar = ttk.Frame(root)
    control_bar.pack(fill="x", padx=8, pady=6)
    preset_path = tk.StringVar(value="studio_preset.json")
    new_file_path = tk.StringVar(value="studio_new_file.json")
    new_project_name = tk.StringVar(value="new_audio_asset")
    output_dir = tk.StringVar(value="output")
    output_base_name = tk.StringVar(value="new_asset")
    workflow_goal = tk.StringVar(value="Video Game Production")
    examples_root = tk.StringVar(value="assets/examples")
    sample_root = tk.StringVar(value=_DEFAULT_SAMPLE_ROOT)
    sample_base_backend = tk.StringVar(value="synth_orchestral")
    ttk.Label(control_bar, text="Preset file").grid(row=0, column=0, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=preset_path).grid(row=0, column=1, sticky="ew", padx=4)
    ttk.Label(control_bar, text="Examples WAV root").grid(row=1, column=0, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=examples_root).grid(row=1, column=1, sticky="ew", padx=4)
    ttk.Label(control_bar, text="New file JSON").grid(row=0, column=6, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=new_file_path, width=28).grid(row=0, column=7, sticky="ew", padx=4)
    ttk.Label(control_bar, text="Project").grid(row=1, column=6, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=new_project_name, width=28).grid(row=1, column=7, sticky="ew", padx=4)
    ttk.Label(control_bar, text="Output dir").grid(row=2, column=6, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=output_dir, width=28).grid(row=2, column=7, sticky="ew", padx=4)
    ttk.Label(control_bar, text="Base name").grid(row=3, column=6, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=output_base_name, width=28).grid(row=3, column=7, sticky="ew", padx=4)
    ttk.Label(control_bar, text="Sample WAV root").grid(row=2, column=0, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=sample_root).grid(row=2, column=1, sticky="ew", padx=4)
    ttk.Label(control_bar, text="Sample base").grid(row=2, column=2, sticky="w", padx=4)
    ttk.Combobox(
        control_bar,
        textvariable=sample_base_backend,
        values=["synth_orchestral", "ps1", "full_orchestral", "procedural"],
        state="readonly",
        width=18,
    ).grid(row=2, column=3, sticky="w", padx=4)
    ttk.Label(control_bar, text="Workflow goal").grid(row=3, column=0, sticky="w", padx=4)
    ttk.Combobox(
        control_bar,
        textvariable=workflow_goal,
        values=list(_STUDIO_WORKFLOW_PRESETS),
        state="readonly",
    ).grid(row=3, column=1, sticky="ew", padx=4)
    global_status = ttk.Label(control_bar, text="")
    global_status.grid(row=4, column=0, columnspan=12, sticky="w", padx=4, pady=(4, 0))
    control_bar.columnconfigure(1, weight=1)
    control_bar.columnconfigure(7, weight=1)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _make_scrollable_tab(label: str) -> ttk.Frame:
        outer = ttk.Frame(notebook)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(_event: object | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: object) -> None:
            width = getattr(event, "width", None)
            if width is not None:
                canvas.itemconfigure(window_id, width=width)

        def _on_mousewheel(event: object) -> None:
            delta = int(getattr(event, "delta", 0))
            if delta:
                canvas.yview_scroll(int(-delta / 120), "units")
            else:
                button = getattr(event, "num", None)
                if button == 4:
                    canvas.yview_scroll(-1, "units")
                elif button == 5:
                    canvas.yview_scroll(1, "units")

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        notebook.add(outer, text=label)
        return inner

    music_tab = _make_scrollable_tab("Music")
    sfx_tab = _make_scrollable_tab("SFX")
    voice_tab = _make_scrollable_tab("Voice")
    synth_tab = _make_scrollable_tab("Synth Workbench")
    piece_tab = _make_scrollable_tab("Piece Composer")
    instr_tab = _make_scrollable_tab("Instruments")
    piano_roll_outer = ttk.Frame(notebook)
    notebook.add(piano_roll_outer, text="Piano Roll")

    # Music tab
    ttk.Label(music_tab, text="Style").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    music_style = tk.StringVar(value="battle")
    style_box = ttk.Combobox(music_tab, textvariable=music_style, values=MusicGenerator.available_styles(), state="readonly")
    style_box.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    # Style info panel — shows BPM, scale, and instruments for the selected style
    style_info_var = tk.StringVar(value="")
    style_info_lbl = ttk.Label(music_tab, textvariable=style_info_var, justify="left", foreground="#555555")
    style_info_lbl.grid(row=0, column=2, rowspan=4, sticky="nw", padx=(0, 8), pady=6)

    ttk.Label(music_tab, text="Backend").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    music_backend = tk.StringVar(value="procedural")
    ttk.Combobox(
        music_tab,
        textvariable=music_backend,
        values=_available_backends_for_modality("music", sample_rate=44100),
        state="readonly",
    ).grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Mastering profile").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    music_profile = tk.StringVar(value="game")
    ttk.Combobox(
        music_tab,
        textvariable=music_profile,
        values=VALID_PROFILES,
        state="readonly",
    ).grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="BPM").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    bpm_var = tk.StringVar(value=str(int(style_metadata[music_style.get()]["bpm"])))
    bpm_label = ttk.Label(music_tab, textvariable=bpm_var)
    bpm_label.grid(row=3, column=1, sticky="w", padx=8, pady=6)

    ttk.Label(music_tab, text="Bars").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    bars_var = tk.IntVar(value=16)
    bars_spin = ttk.Spinbox(music_tab, from_=4, to=128, textvariable=bars_var)
    bars_spin.grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Seed").grid(row=5, column=0, sticky="w", padx=8, pady=6)
    music_seed = tk.StringVar(value="0")
    ttk.Entry(music_tab, textvariable=music_seed).grid(row=5, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Output path").grid(row=6, column=0, sticky="w", padx=8, pady=6)
    music_out = tk.StringVar(value="music.wav")
    ttk.Entry(music_tab, textvariable=music_out).grid(row=6, column=1, sticky="ew", padx=8, pady=6)
    ttk.Button(
        music_tab,
        text="Browse…",
        command=lambda: _browse_output_path(music_out, title="Save Music As"),
    ).grid(row=6, column=2, padx=(2, 8), pady=6)

    ttk.Label(music_tab, text="Prompt override").grid(row=7, column=0, sticky="w", padx=8, pady=6)
    music_prompt = tk.StringVar(value="")
    ttk.Entry(music_tab, textvariable=music_prompt).grid(row=7, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Output format").grid(row=8, column=0, sticky="w", padx=8, pady=6)
    music_format = tk.StringVar(value="wav")
    ttk.Combobox(music_tab, textvariable=music_format, values=["wav", "ogg"], state="readonly").grid(row=8, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Region hint").grid(row=9, column=0, sticky="w", padx=8, pady=6)
    music_region = tk.StringVar(value="")
    ttk.Combobox(
        music_tab,
        textvariable=music_region,
        values=["", "plains", "forest", "coast", "ruins", "arid"],
        state="readonly",
    ).grid(row=9, column=1, sticky="ew", padx=8, pady=6)

    music_adaptive_intensity = tk.BooleanVar(value=False)
    ttk.Checkbutton(music_tab, text="Adaptive intensity", variable=music_adaptive_intensity).grid(row=10, column=0, columnspan=2, sticky="w", padx=8, pady=4)

    custom_arrangement = tk.BooleanVar(value=False)
    ttk.Checkbutton(music_tab, text="Custom arrangement (procedural backend)", variable=custom_arrangement).grid(row=11, column=0, columnspan=2, sticky="w", padx=8, pady=4)

    instrument_choices = InstrumentLibrary.available()
    ttk.Label(music_tab, text="Lead instrument").grid(row=12, column=0, sticky="w", padx=8, pady=6)
    custom_lead = tk.StringVar(value="strings")
    ttk.Combobox(music_tab, textvariable=custom_lead, values=instrument_choices, state="readonly").grid(row=12, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Counter instrument").grid(row=13, column=0, sticky="w", padx=8, pady=6)
    custom_counter = tk.StringVar(value="flute")
    ttk.Combobox(music_tab, textvariable=custom_counter, values=instrument_choices, state="readonly").grid(row=13, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Pad / accompaniment").grid(row=14, column=0, sticky="w", padx=8, pady=6)
    custom_pad = tk.StringVar(value="synth_pad")
    ttk.Combobox(music_tab, textvariable=custom_pad, values=instrument_choices, state="readonly").grid(row=14, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Chord support").grid(row=15, column=0, sticky="w", padx=8, pady=6)
    custom_chord = tk.StringVar(value="strings")
    ttk.Combobox(music_tab, textvariable=custom_chord, values=instrument_choices, state="readonly").grid(row=15, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Bass instrument").grid(row=16, column=0, sticky="w", padx=8, pady=6)
    custom_bass = tk.StringVar(value="bass")
    ttk.Combobox(music_tab, textvariable=custom_bass, values=instrument_choices, state="readonly").grid(row=16, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Ostinato instrument").grid(row=17, column=0, sticky="w", padx=8, pady=6)
    custom_ostinato = tk.StringVar(value="crystal_synth")
    ttk.Combobox(music_tab, textvariable=custom_ostinato, values=instrument_choices, state="readonly").grid(row=17, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Percussion instrument").grid(row=18, column=0, sticky="w", padx=8, pady=6)
    custom_percussion = tk.StringVar(value="percussion")
    ttk.Combobox(music_tab, textvariable=custom_percussion, values=["", *instrument_choices], state="readonly").grid(row=18, column=1, sticky="ew", padx=8, pady=6)

    music_status = ttk.Label(music_tab, text="")
    music_status.grid(row=20, column=0, columnspan=3, sticky="w", padx=8, pady=8)

    def _refresh_bpm(*_args: object) -> None:
        style = music_style.get()
        meta = style_metadata.get(style, style_metadata["battle"])
        bpm_var.set(str(int(meta["bpm"])))
        scale = meta.get("scale_name", "")
        root = meta.get("root", "")
        instrs = ", ".join(meta.get("instruments", []))
        style_info_var.set(
            f"BPM: {int(meta['bpm'])}  Key: {root} {scale}\nLeads: {instrs}"
        )

    style_box.bind("<<ComboboxSelected>>", _refresh_bpm)
    _refresh_bpm()  # populate style info on startup
    music_tab.columnconfigure(1, weight=1)

    def _run_music_generation() -> Path:
        seed = _safe_int(music_seed.get(), 0)
        style = music_style.get()
        bars = max(4, _safe_int(str(bars_var.get()), 16))
        bpm = max(40, _safe_int(bpm_var.get(), 120))
        duration = bars * (60.0 / bpm) * 4.0
        prompt = music_prompt.get().strip() or style
        out_path = Path(music_out.get())
        out_path.parent.mkdir(parents=True, exist_ok=True)
        from audio_engine.ai.music_gen import MusicGen
        backend_name = music_backend.get()

        def _emit_music(prompt_value: str, *, style_override: str | None = None) -> Path:
            return MusicGen(
                sample_rate=44100,
                backend=_resolve_backend(
                    backend_name=backend_name,
                    sample_rate=44100,
                    seed=seed,
                    samples_dir=sample_root.get().strip(),
                    sample_base_backend=sample_base_backend.get(),
                ),
                seed=seed,
                mastering_profile=music_profile.get(),
            ).generate_to_file(
                prompt=prompt_value,
                output_path=out_path,
                duration=duration,
                loopable=True,
                fmt="ogg" if music_format.get() == "ogg" else "wav",
                region=music_region.get().strip() or None,
                adaptive_intensity=bool(music_adaptive_intensity.get()),
                style_override=style_override,
            )

        if custom_arrangement.get() and backend_name == "procedural":
            from audio_engine.ai import generator as generator_module

            source = generator_module._STYLE_DEFS.get(style)
            if source is None:
                raise ValueError(f"unknown source style for override: {style}")
            lead_fallback = source.instruments[0] if source.instruments else "strings"
            counter_fallback = source.instruments[1] if len(source.instruments) > 1 else lead_fallback
            pad_fallback = source.accompaniment[0] if source.accompaniment else "synth_pad"
            chord_fallback = source.accompaniment[1] if len(source.accompaniment) > 1 else (source.accompaniment[0] if source.accompaniment else "strings")
            percussion_choice = custom_percussion.get().strip()
            percussion_fallback = source.percussion_instrument or "percussion"
            temporary_style_name = f"studio_custom_{style}"
            with _STYLE_OVERRIDE_LOCK:
                generator_module._STYLE_DEFS[temporary_style_name] = generator_module._StyleDef(
                    bpm=float(bpm),
                    scale_name=str(source.scale_name),
                    root=str(source.root),
                    octave=int(source.octave),
                    progression_name=str(source.progression_name),
                    instruments=[
                        _normalize_instrument_choice(custom_lead.get(), lead_fallback),
                        _normalize_instrument_choice(custom_counter.get(), counter_fallback),
                    ],
                    accompaniment=[
                        _normalize_instrument_choice(custom_pad.get(), pad_fallback),
                        _normalize_instrument_choice(custom_chord.get(), chord_fallback),
                    ],
                    bass_instrument=_normalize_instrument_choice(custom_bass.get(), source.bass_instrument),
                    percussion_instrument=(
                        _normalize_instrument_choice(custom_percussion.get(), percussion_fallback)
                        if percussion_choice
                        else None
                    ),
                    melody_pattern=str(source.melody_pattern),
                    chord_pattern=str(source.chord_pattern),
                    bars=int(bars),
                    ostinato_instrument=_normalize_instrument_choice(custom_ostinato.get(), source.ostinato_instrument),
                )
                try:
                    return _emit_music(prompt, style_override=temporary_style_name)
                finally:
                    generator_module._STYLE_DEFS.pop(temporary_style_name, None)

        return _emit_music(prompt)

    def _generate_music() -> None:
        nonlocal last_failed_action
        try:
            _set_status(music_status, "Generating music...")
            out_path = _run_music_generation()
            _set_status(music_status, f"Done — saved to {out_path}")
            _set_status(global_status, "Music generation complete.")
            _refresh_preview_files(select_category="Music")
            if last_failed_action == "music":
                last_failed_action = None
        except Exception as exc:  # pragma: no cover - UI path
            last_failed_action = "music"
            _set_status(music_status, f"Error: {exc}")
            _set_status(global_status, f"Music failed — {exc}")

    ttk.Button(music_tab, text="Generate", command=_generate_music).grid(row=19, column=0, sticky="ew", padx=8, pady=8)
    ttk.Button(
        music_tab,
        text="Play latest",
        command=lambda: _play_output_path(Path(music_out.get()), "Music"),
    ).grid(row=19, column=1, sticky="ew", padx=8, pady=8)

    # SFX tab
    ttk.Label(sfx_tab, text="Category").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    sfx_type = tk.StringVar(value="explosion")
    ttk.Combobox(sfx_tab, textvariable=sfx_type, values=available_sfx_types(), state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Backend").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    sfx_backend = tk.StringVar(value="procedural")
    ttk.Combobox(
        sfx_tab,
        textvariable=sfx_backend,
        values=_available_backends_for_modality("sfx", sample_rate=44100),
        state="readonly",
    ).grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Duration (s)").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    sfx_duration = tk.DoubleVar(value=0.8)
    ttk.Scale(sfx_tab, from_=0.05, to=4.0, variable=sfx_duration, orient="horizontal").grid(row=2, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(sfx_tab, sfx_duration, row=2, fmt="{:.2f}s")

    ttk.Label(sfx_tab, text="Pitch override (Hz)").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    sfx_pitch = tk.StringVar(value="")
    ttk.Entry(sfx_tab, textvariable=sfx_pitch).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Seed").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    sfx_seed = tk.StringVar(value="0")
    ttk.Entry(sfx_tab, textvariable=sfx_seed).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Output path").grid(row=5, column=0, sticky="w", padx=8, pady=6)
    sfx_out = tk.StringVar(value="sfx.wav")
    ttk.Entry(sfx_tab, textvariable=sfx_out).grid(row=5, column=1, sticky="ew", padx=8, pady=6)
    ttk.Button(
        sfx_tab,
        text="Browse…",
        command=lambda: _browse_output_path(sfx_out, title="Save SFX As"),
    ).grid(row=5, column=2, padx=(2, 8), pady=6)

    sfx_status = ttk.Label(sfx_tab, text="")
    sfx_status.grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=8)
    sfx_tab.columnconfigure(1, weight=1)


    def _run_sfx_generation() -> Path:
        seed = _safe_int(sfx_seed.get(), 0)
        pitch = None if not sfx_pitch.get().strip() else float(sfx_pitch.get())
        out_path = Path(sfx_out.get())
        out_path.parent.mkdir(parents=True, exist_ok=True)
        SFXGen(
            sample_rate=44100,
            backend=_resolve_backend(
                backend_name=sfx_backend.get(),
                sample_rate=44100,
                seed=seed,
                samples_dir=sample_root.get().strip(),
                sample_base_backend=sample_base_backend.get(),
            ),
            seed=seed,
        ).generate_to_file(
            prompt=sfx_type.get(),
            output_path=out_path,
            duration=float(sfx_duration.get()),
            pitch_hz=pitch,
        )
        return out_path

    def _generate_sfx() -> None:
        nonlocal last_failed_action
        try:
            _set_status(sfx_status, "Generating SFX...")
            out_path = _run_sfx_generation()
            _set_status(sfx_status, f"Done — saved to {out_path}")
            _set_status(global_status, "SFX generation complete.")
            _refresh_preview_files(select_category="SFX")
            if last_failed_action == "sfx":
                last_failed_action = None
        except Exception as exc:  # pragma: no cover - UI path
            last_failed_action = "sfx"
            _set_status(sfx_status, f"Error: {exc}")
            _set_status(global_status, f"SFX failed — {exc}")

    ttk.Button(sfx_tab, text="Generate", command=_generate_sfx).grid(row=6, column=0, sticky="ew", padx=8, pady=8)
    ttk.Button(
        sfx_tab,
        text="Play latest",
        command=lambda: _play_output_path(Path(sfx_out.get()), "SFX"),
    ).grid(row=6, column=1, sticky="ew", padx=8, pady=8)

    # Voice tab
    ttk.Label(voice_tab, text="Text").grid(row=0, column=0, sticky="nw", padx=8, pady=6)
    voice_text = tk.Text(voice_tab, width=60, height=8)
    voice_text.insert("1.0", "The hero must find the crystal.")
    voice_text.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Backend").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    voice_backend = tk.StringVar(value="procedural")
    ttk.Combobox(
        voice_tab,
        textvariable=voice_backend,
        values=_available_backends_for_modality("voice", sample_rate=22050),
        state="readonly",
    ).grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Preset").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    voice_preset = tk.StringVar(value="narrator")
    ttk.Combobox(voice_tab, textvariable=voice_preset, values=sorted(VOICE_PRESETS), state="readonly").grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Speed").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    voice_speed = tk.DoubleVar(value=1.0)
    ttk.Scale(voice_tab, from_=0.6, to=2.0, variable=voice_speed, orient="horizontal").grid(row=3, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(voice_tab, voice_speed, row=3, fmt="{:.2f}x")

    ttk.Label(voice_tab, text="Seed").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    voice_seed = tk.StringVar(value="0")
    ttk.Entry(voice_tab, textvariable=voice_seed).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Output path").grid(row=5, column=0, sticky="w", padx=8, pady=6)
    voice_out = tk.StringVar(value="voice.wav")
    ttk.Entry(voice_tab, textvariable=voice_out).grid(row=5, column=1, sticky="ew", padx=8, pady=6)
    ttk.Button(
        voice_tab,
        text="Browse…",
        command=lambda: _browse_output_path(voice_out, title="Save Voice As"),
    ).grid(row=5, column=2, padx=(2, 8), pady=6)

    voice_status = ttk.Label(voice_tab, text="")
    voice_status.grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=8)
    voice_tab.columnconfigure(1, weight=1)

    def _run_voice_generation() -> Path:
        seed = _safe_int(voice_seed.get(), 0)
        text = voice_text.get("1.0", "end").strip()
        out_path = Path(voice_out.get())
        out_path.parent.mkdir(parents=True, exist_ok=True)
        VoiceGen(
            sample_rate=22050,
            backend=_resolve_backend(
                backend_name=voice_backend.get(),
                sample_rate=22050,
                seed=seed,
                samples_dir=sample_root.get().strip(),
                sample_base_backend=sample_base_backend.get(),
            ),
            seed=seed,
        ).generate_to_file(
            text=text,
            output_path=out_path,
            voice=voice_preset.get(),
            speed=float(voice_speed.get()),
        )
        return out_path

    def _generate_voice() -> None:
        nonlocal last_failed_action
        try:
            _set_status(voice_status, "Generating voice...")
            out_path = _run_voice_generation()
            _set_status(voice_status, f"Done — saved to {out_path}")
            _set_status(global_status, "Voice generation complete.")
            _refresh_preview_files(select_category="Vocal")
            if last_failed_action == "voice":
                last_failed_action = None
        except Exception as exc:  # pragma: no cover - UI path
            last_failed_action = "voice"
            _set_status(voice_status, f"Error: {exc}")
            _set_status(global_status, f"Voice failed — {exc}")

    ttk.Button(voice_tab, text="Generate", command=_generate_voice).grid(row=6, column=0, sticky="ew", padx=8, pady=8)
    ttk.Button(
        voice_tab,
        text="Play latest",
        command=lambda: _play_output_path(Path(voice_out.get()), "Vocal"),
    ).grid(row=6, column=1, sticky="ew", padx=8, pady=8)

    # ---------------------------------------------------------------------------
    # Synth Workbench tab — manual waveform/ADSR/filter/WAV creation without AI
    # ---------------------------------------------------------------------------
    _sw_counter = [0]

    def _sw_row() -> int:
        r = _sw_counter[0]
        _sw_counter[0] += 1
        return r

    ttk.Label(synth_tab, text="Waveform").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_waveform = tk.StringVar(value="sine")
    ttk.Combobox(synth_tab, textvariable=synth_waveform, values=_SYNTH_WAVEFORMS, state="readonly").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Frequency (Hz)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_freq = tk.StringVar(value="440.0")
    ttk.Entry(synth_tab, textvariable=synth_freq).grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Duration (s)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_dur = tk.StringVar(value="1.0")
    ttk.Entry(synth_tab, textvariable=synth_dur).grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Amplitude (0–1)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_amp = tk.DoubleVar(value=0.8)
    ttk.Scale(synth_tab, from_=0.0, to=1.0, variable=synth_amp, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_amp, row=_sw_counter[0] - 1)

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=3, sticky="ew", padx=8, pady=4)
    ttk.Label(synth_tab, text="— ADSR Envelope —", font=("TkDefaultFont", 9, "bold")).grid(row=_sw_counter[0] - 1, column=0, columnspan=3, pady=2)

    ttk.Label(synth_tab, text="Attack (s)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_attack = tk.DoubleVar(value=0.01)
    ttk.Scale(synth_tab, from_=0.0, to=2.0, variable=synth_attack, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_attack, row=_sw_counter[0] - 1)

    ttk.Label(synth_tab, text="Decay (s)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_decay = tk.DoubleVar(value=0.1)
    ttk.Scale(synth_tab, from_=0.0, to=2.0, variable=synth_decay, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_decay, row=_sw_counter[0] - 1)

    ttk.Label(synth_tab, text="Sustain (0–1)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_sustain = tk.DoubleVar(value=0.7)
    ttk.Scale(synth_tab, from_=0.0, to=1.0, variable=synth_sustain, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_sustain, row=_sw_counter[0] - 1)

    ttk.Label(synth_tab, text="Release (s)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_release = tk.DoubleVar(value=0.3)
    ttk.Scale(synth_tab, from_=0.0, to=2.0, variable=synth_release, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_release, row=_sw_counter[0] - 1)

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=3, sticky="ew", padx=8, pady=4)
    ttk.Label(synth_tab, text="— Filter —", font=("TkDefaultFont", 9, "bold")).grid(row=_sw_counter[0] - 1, column=0, columnspan=3, pady=2)

    ttk.Label(synth_tab, text="Filter type").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_filter_type = tk.StringVar(value="none")
    ttk.Combobox(synth_tab, textvariable=synth_filter_type, values=_SYNTH_FILTER_TYPES, state="readonly").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Cutoff (Hz)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_cutoff = tk.StringVar(value="2000.0")
    ttk.Entry(synth_tab, textvariable=synth_cutoff).grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=3, sticky="ew", padx=8, pady=4)
    ttk.Label(synth_tab, text="— Oscillator 2 —", font=("TkDefaultFont", 9, "bold")).grid(row=_sw_counter[0] - 1, column=0, columnspan=3, pady=2)

    ttk.Label(synth_tab, text="Waveform 2").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_waveform2 = tk.StringVar(value="none")
    ttk.Combobox(synth_tab, textvariable=synth_waveform2, values=["none", *_SYNTH_WAVEFORMS], state="readonly").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Osc 2 mix (0–1)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_osc2_mix = tk.DoubleVar(value=0.0)
    ttk.Scale(synth_tab, from_=0.0, to=1.0, variable=synth_osc2_mix, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_osc2_mix, row=_sw_counter[0] - 1)

    ttk.Label(synth_tab, text="Osc 2 octave").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_osc2_octave = tk.IntVar(value=0)
    ttk.Spinbox(synth_tab, from_=-2, to=2, textvariable=synth_osc2_octave, width=6).grid(row=_sw_counter[0] - 1, column=1, sticky="w", padx=8, pady=6)

    ttk.Label(synth_tab, text="Detune (cents)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_detune = tk.DoubleVar(value=0.0)
    ttk.Scale(synth_tab, from_=-50.0, to=50.0, variable=synth_detune, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_detune, row=_sw_counter[0] - 1, fmt="{:+.1f}¢")

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=3, sticky="ew", padx=8, pady=4)
    ttk.Label(synth_tab, text="— LFO —", font=("TkDefaultFont", 9, "bold")).grid(row=_sw_counter[0] - 1, column=0, columnspan=3, pady=2)

    ttk.Label(synth_tab, text="LFO rate (Hz)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_lfo_rate = tk.DoubleVar(value=0.0)
    ttk.Scale(synth_tab, from_=0.0, to=20.0, variable=synth_lfo_rate, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_lfo_rate, row=_sw_counter[0] - 1, fmt="{:.1f}Hz")

    ttk.Label(synth_tab, text="LFO depth").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_lfo_depth = tk.DoubleVar(value=0.0)
    ttk.Scale(synth_tab, from_=0.0, to=1.0, variable=synth_lfo_depth, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    _attach_value_label(synth_tab, synth_lfo_depth, row=_sw_counter[0] - 1)

    ttk.Label(synth_tab, text="LFO target").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_lfo_target = tk.StringVar(value="pitch")
    ttk.Combobox(synth_tab, textvariable=synth_lfo_target, values=["pitch", "amplitude", "filter"], state="readonly").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=3, sticky="ew", padx=8, pady=4)

    ttk.Label(synth_tab, text="Output path").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_out = tk.StringVar(value="synth_patch.wav")
    ttk.Entry(synth_tab, textvariable=synth_out).grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)
    ttk.Button(
        synth_tab,
        text="Browse…",
        command=lambda: _browse_output_path(synth_out, title="Save Synth Patch As"),
    ).grid(row=_sw_counter[0] - 1, column=2, padx=(2, 8), pady=6)

    synth_status = ttk.Label(synth_tab, text="")
    synth_status.grid(row=_sw_row(), column=0, columnspan=3, sticky="w", padx=8, pady=8)

    synth_tab.columnconfigure(1, weight=1)

    def _run_synth_patch() -> Path:
        try:
            freq = float(synth_freq.get())
        except ValueError:
            freq = 440.0
        try:
            dur = max(0.05, float(synth_dur.get()))
        except ValueError:
            dur = 1.0
        try:
            cutoff = float(synth_cutoff.get())
        except ValueError:
            cutoff = 2000.0
        out_path = Path(synth_out.get())
        audio = _build_synth_patch_ext(
            waveform=synth_waveform.get(),
            frequency=freq,
            duration=dur,
            amplitude=float(synth_amp.get()),
            attack=float(synth_attack.get()),
            decay=float(synth_decay.get()),
            sustain=float(synth_sustain.get()),
            release=float(synth_release.get()),
            filter_type=synth_filter_type.get(),
            filter_cutoff=cutoff,
            filter_q=1.0,
            detune_cents=float(synth_detune.get()),
            waveform2=synth_waveform2.get(),
            osc2_mix=float(synth_osc2_mix.get()),
            osc2_octave=int(synth_osc2_octave.get()),
            lfo_rate=float(synth_lfo_rate.get()),
            lfo_depth=float(synth_lfo_depth.get()),
            lfo_target=synth_lfo_target.get(),
        )
        return _export_synth_patch(audio, out_path)

    def _generate_synth_patch() -> None:
        try:
            _set_status(synth_status, "Building synth patch...")
            out_path = _run_synth_patch()
            _set_status(synth_status, f"Done — saved to {out_path}")
            _set_status(global_status, "Synth patch saved.")
            _refresh_preview_files()
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(synth_status, f"Error: {exc}")
            _set_status(global_status, f"Synth workbench failed — {exc}")

    ttk.Button(synth_tab, text="Generate WAV", command=_generate_synth_patch).grid(row=_sw_row(), column=0, columnspan=2, pady=8)

    # ---------------------------------------------------------------------------
    # Piece Composer tab — create full multi-section musical pieces
    # ---------------------------------------------------------------------------
    _pc_section_list: list[str] = ["intro", "verse", "chorus", "bridge", "chorus", "outro"]

    # Style
    ttk.Label(piece_tab, text="Style").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    pc_style = tk.StringVar(value="ff8_ballad")
    ttk.Combobox(piece_tab, textvariable=pc_style, values=MusicGenerator.available_styles(), state="readonly").grid(row=0, column=1, columnspan=3, sticky="ew", padx=8, pady=6)

    # Backend
    ttk.Label(piece_tab, text="Backend").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    pc_backend = tk.StringVar(value="synth_orchestral")
    ttk.Combobox(
        piece_tab,
        textvariable=pc_backend,
        values=_available_backends_for_modality("music", sample_rate=44100),
        state="readonly",
    ).grid(row=1, column=1, columnspan=3, sticky="ew", padx=8, pady=6)

    # Mastering profile
    ttk.Label(piece_tab, text="Mastering profile").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    pc_profile = tk.StringVar(value="ost")
    ttk.Combobox(piece_tab, textvariable=pc_profile, values=VALID_PROFILES, state="readonly").grid(row=2, column=1, columnspan=3, sticky="ew", padx=8, pady=6)

    # Duration
    ttk.Label(piece_tab, text="Duration (s)").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    pc_duration = tk.StringVar(value="90")
    ttk.Entry(piece_tab, textvariable=pc_duration).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    # Seed
    ttk.Label(piece_tab, text="Seed").grid(row=3, column=2, sticky="w", padx=8, pady=6)
    pc_seed = tk.StringVar(value="0")
    ttk.Entry(piece_tab, textvariable=pc_seed, width=8).grid(row=3, column=3, sticky="ew", padx=8, pady=6)

    # Vocals
    pc_with_vocals = tk.BooleanVar(value=True)
    ttk.Checkbutton(piece_tab, text="With vocals", variable=pc_with_vocals).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=4)

    ttk.Label(piece_tab, text="Vocal preset").grid(row=4, column=2, sticky="w", padx=8, pady=6)
    pc_vocal_preset = tk.StringVar(value="soprano")
    ttk.Combobox(piece_tab, textvariable=pc_vocal_preset, values=_PC_VOCAL_PRESETS, state="readonly", width=12).grid(row=4, column=3, sticky="ew", padx=8, pady=6)

    # Output path and format
    ttk.Label(piece_tab, text="Output path").grid(row=5, column=0, sticky="w", padx=8, pady=6)
    pc_out = tk.StringVar(value="piece.wav")
    ttk.Entry(piece_tab, textvariable=pc_out).grid(row=5, column=1, columnspan=2, sticky="ew", padx=8, pady=6)
    pc_format = tk.StringVar(value="wav")
    ttk.Combobox(piece_tab, textvariable=pc_format, values=["wav", "ogg"], state="readonly", width=6).grid(row=5, column=3, sticky="ew", padx=8, pady=6)

    ttk.Label(piece_tab, text="Song recipe").grid(row=6, column=0, sticky="w", padx=8, pady=6)
    pc_recipe = tk.StringVar(value="FF8 Ballad Full Song")
    ttk.Combobox(
        piece_tab,
        textvariable=pc_recipe,
        values=list(_PIECE_SONG_RECIPES.keys()),
        state="readonly",
    ).grid(row=6, column=1, columnspan=2, sticky="ew", padx=8, pady=6)

    # Section builder (listbox + add/remove/move buttons)
    ttk.Separator(piece_tab, orient="horizontal").grid(row=7, column=0, columnspan=4, sticky="ew", padx=8, pady=4)
    ttk.Label(piece_tab, text="— Sections —", font=("TkDefaultFont", 9, "bold")).grid(row=8, column=0, columnspan=4, pady=2)

    ttk.Label(piece_tab, text="Available").grid(row=9, column=0, sticky="w", padx=8, pady=2)
    ttk.Label(piece_tab, text="Piece order").grid(row=9, column=2, sticky="w", padx=8, pady=2)

    pc_avail_lb = tk.Listbox(piece_tab, height=7, exportselection=False)
    for s in _PC_SECTION_TYPES:
        pc_avail_lb.insert("end", s)
    pc_avail_lb.grid(row=10, column=0, rowspan=4, sticky="nsew", padx=8, pady=4)

    pc_order_lb = tk.Listbox(piece_tab, height=7, exportselection=False)
    for s in _pc_section_list:
        pc_order_lb.insert("end", s)
    pc_order_lb.grid(row=10, column=2, rowspan=4, sticky="nsew", padx=8, pady=4)
    piece_tab.columnconfigure(0, weight=1)
    piece_tab.columnconfigure(2, weight=1)

    def _pc_refresh_order_list() -> None:
        pc_order_lb.delete(0, "end")
        for section_name in _pc_section_list:
            pc_order_lb.insert("end", section_name)

    def _pc_add_section() -> None:
        sel = pc_avail_lb.curselection()
        if not sel:
            return
        sec = pc_avail_lb.get(sel[0])
        _pc_section_list.append(sec)
        _pc_refresh_order_list()

    def _pc_remove_section() -> None:
        sel = pc_order_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(_pc_section_list):
            _pc_section_list.pop(idx)
        _pc_refresh_order_list()

    def _pc_move_up() -> None:
        sel = pc_order_lb.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        _pc_section_list.insert(idx - 1, _pc_section_list.pop(idx))
        _pc_refresh_order_list()
        pc_order_lb.selection_set(idx - 1)

    def _pc_move_down() -> None:
        sel = pc_order_lb.curselection()
        if not sel or sel[0] >= pc_order_lb.size() - 1:
            return
        idx = sel[0]
        _pc_section_list.insert(idx + 1, _pc_section_list.pop(idx))
        _pc_refresh_order_list()
        pc_order_lb.selection_set(idx + 1)

    def _pc_duplicate_section() -> None:
        sel = pc_order_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(_pc_section_list):
            return
        _pc_section_list.insert(idx + 1, _pc_section_list[idx])
        _pc_refresh_order_list()
        pc_order_lb.selection_set(idx + 1)

    def _pc_clear_sections() -> None:
        _pc_section_list.clear()
        _pc_refresh_order_list()

    def _pc_apply_recipe() -> None:
        recipe = _PIECE_SONG_RECIPES.get(pc_recipe.get())
        if recipe is None:
            return
        style_name = str(recipe.get("style", pc_style.get()))
        if style_name in style_metadata:
            pc_style.set(style_name)
        backend_value = str(recipe.get("backend", pc_backend.get()))
        if backend_value in _available_backends_for_modality("music", sample_rate=44100):
            pc_backend.set(backend_value)
        profile_value = str(recipe.get("profile", pc_profile.get()))
        if profile_value in VALID_PROFILES:
            pc_profile.set(profile_value)
        pc_duration.set(str(recipe.get("duration", pc_duration.get())))
        pc_with_vocals.set(bool(recipe.get("with_vocals", pc_with_vocals.get())))
        vocal_value = str(recipe.get("vocal_preset", pc_vocal_preset.get()))
        if vocal_value in _PC_VOCAL_PRESETS:
            pc_vocal_preset.set(vocal_value)
        _pc_section_list[:] = [str(item) for item in recipe.get("sections", _pc_section_list)]
        _pc_refresh_order_list()
        output_stem = str(recipe.get("output_stem", "piece")).strip() or "piece"
        pc_out.set(f"{output_stem}.{pc_format.get()}")
        _set_status(piece_status, f"Loaded song recipe '{pc_recipe.get()}'.")

    btn_col = ttk.Frame(piece_tab)
    btn_col.grid(row=10, column=1, rowspan=4, padx=4, pady=4)
    ttk.Button(btn_col, text="Add →", command=_pc_add_section).pack(fill="x", pady=2)
    ttk.Button(btn_col, text="← Remove", command=_pc_remove_section).pack(fill="x", pady=2)
    ttk.Button(btn_col, text="↑ Up", command=_pc_move_up).pack(fill="x", pady=2)
    ttk.Button(btn_col, text="↓ Down", command=_pc_move_down).pack(fill="x", pady=2)
    ttk.Button(btn_col, text="Duplicate", command=_pc_duplicate_section).pack(fill="x", pady=2)
    ttk.Button(btn_col, text="Clear", command=_pc_clear_sections).pack(fill="x", pady=2)

    recipe_btn_row = ttk.Frame(piece_tab)
    recipe_btn_row.grid(row=14, column=0, columnspan=4, pady=(0, 4))
    ttk.Button(recipe_btn_row, text="Load Song Recipe", command=_pc_apply_recipe).pack(side="left", padx=8)

    ttk.Separator(piece_tab, orient="horizontal").grid(row=15, column=0, columnspan=4, sticky="ew", padx=8, pady=4)

    piece_status = ttk.Label(piece_tab, text="")
    piece_status.grid(row=17, column=0, columnspan=4, sticky="w", padx=8, pady=8)

    def _run_compose_piece() -> Path:
        sections = list(_pc_section_list)
        if not sections:
            raise ValueError("Add at least one section before composing.")
        try:
            dur = float(pc_duration.get())
        except ValueError:
            dur = 90.0
        dur = max(10.0, dur)
        seed = _safe_int(pc_seed.get(), 0)
        out_path = Path(pc_out.get())
        fmt = pc_format.get()
        return _compose_piece_to_file(
            style=pc_style.get(),
            sections=sections,
            with_vocals=bool(pc_with_vocals.get()),
            duration=dur,
            backend_name=pc_backend.get(),
            vocal_preset=pc_vocal_preset.get(),
            seed=seed,
            output_path=out_path,
            mastering_profile=pc_profile.get(),
            samples_dir=sample_root.get().strip(),
            sample_base_backend=sample_base_backend.get(),
            fmt=fmt,
        )

    def _compose_piece_threaded() -> None:
        _set_status(piece_status, "Composing piece — this may take a while...")
        _set_status(global_status, "Piece Composer running...")

        def _worker() -> None:
            try:
                out_path = _run_compose_piece()
                piece_status.configure(text=f"Done — saved to {out_path}")
                global_status.configure(text="Piece Composer complete.")
                _refresh_preview_files(select_category="Music")
            except Exception as exc:  # pragma: no cover - UI path
                piece_status.configure(text=f"Error: {exc}")
                global_status.configure(text=f"Piece Composer failed — {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    btn_row = ttk.Frame(piece_tab)
    btn_row.grid(row=16, column=0, columnspan=4, pady=8)
    ttk.Button(btn_row, text="Compose Piece", command=_compose_piece_threaded).pack(side="left", padx=8)
    ttk.Button(
        btn_row,
        text="Play latest",
        command=lambda: _play_output_path(Path(pc_out.get()), "Music"),
    ).pack(side="left", padx=8)

    # ---------------------------------------------------------------------------
    # Instrument Browser tab — preview every registered instrument
    # ---------------------------------------------------------------------------
    all_instruments = sorted(InstrumentLibrary.available())

    ttk.Label(instr_tab, text="Instrument").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    instr_choice = tk.StringVar(value=all_instruments[0] if all_instruments else "strings")
    ttk.Combobox(instr_tab, textvariable=instr_choice, values=all_instruments, state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(instr_tab, text="Note").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    instr_note = tk.StringVar(value="A4")
    ttk.Combobox(instr_tab, textvariable=instr_note, values=_NOTE_NAMES, state="readonly", width=6).grid(row=1, column=1, sticky="w", padx=8, pady=6)

    ttk.Label(instr_tab, text="Duration (s)").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    instr_dur = tk.DoubleVar(value=1.5)
    ttk.Scale(instr_tab, from_=0.1, to=5.0, variable=instr_dur, orient="horizontal").grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(instr_tab, text="Output path").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    instr_out = tk.StringVar(value="instrument_preview.wav")
    ttk.Entry(instr_tab, textvariable=instr_out).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    instr_status = ttk.Label(instr_tab, text="")
    instr_status.grid(row=5, column=0, columnspan=2, sticky="w", padx=8, pady=8)
    instr_tab.columnconfigure(1, weight=1)

    # Scrollable instrument info panel
    ttk.Separator(instr_tab, orient="horizontal").grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
    ttk.Label(instr_tab, text="Registered instruments", font=("TkDefaultFont", 9, "bold")).grid(row=7, column=0, columnspan=2, pady=2)
    instr_listbox = tk.Listbox(instr_tab, height=10, selectmode="browse")
    for name in all_instruments:
        instr_listbox.insert("end", name)
    instr_listbox.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
    instr_tab.rowconfigure(8, weight=1)

    def _on_instr_listbox_select(_event: object = None) -> None:
        sel = instr_listbox.curselection()
        if sel:
            instr_choice.set(instr_listbox.get(sel[0]))

    instr_listbox.bind("<<ListboxSelect>>", _on_instr_listbox_select)

    def _run_instr_preview() -> Path:
        name = instr_choice.get()
        note = instr_note.get()
        dur = max(0.1, float(instr_dur.get()))
        out_path = Path(instr_out.get())
        return _preview_instrument_note(name, note, dur, out_path)

    def _generate_instr_preview() -> None:
        try:
            _set_status(instr_status, "Rendering instrument note...")
            out_path = _run_instr_preview()
            _set_status(instr_status, f"Done — saved to {out_path}")
            _set_status(global_status, "Instrument preview saved.")
            _refresh_preview_files()
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(instr_status, f"Error: {exc}")
            _set_status(global_status, f"Instrument preview failed — {exc}")

    def _save_instr_preview_to_samples() -> None:
        try:
            target = _save_preview_note_sample(
                preview_path=Path(instr_out.get()),
                sample_root=Path(sample_root.get().strip() or _DEFAULT_SAMPLE_ROOT),
                instrument_name=instr_choice.get(),
                note=instr_note.get(),
            )
            _set_status(instr_status, f"Sample note saved: {target}")
            _set_status(global_status, "Sample note saved.")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(instr_status, f"Save sample failed: {exc}")
            _set_status(global_status, f"Sample note save failed — {exc}")

    btn_row_instr = ttk.Frame(instr_tab)
    btn_row_instr.grid(row=4, column=0, columnspan=2, pady=4)
    ttk.Button(btn_row_instr, text="Preview Note", command=_generate_instr_preview).pack(side="left", padx=8)
    ttk.Button(
        btn_row_instr,
        text="Play latest",
        command=lambda: _play_output_path(Path(instr_out.get()), "Music"),
    ).pack(side="left", padx=8)
    ttk.Button(
        btn_row_instr,
        text="Save as Sample Note",
        command=_save_instr_preview_to_samples,
    ).pack(side="left", padx=8)

    # ---------------------------------------------------------------------------
    # Piano Roll tab — visual grid editing + precise note inspector
    # ---------------------------------------------------------------------------
    _pr_tracks: dict[str, dict] = {}
    _pr_selected_track: list[str | None] = [None]
    _pr_selected_note_index: list[int | None] = [None]
    _TRACK_ROLES = ["melody", "counter", "harmony", "bass", "texture", "percussion"]
    _PR_SNAP_VALUES = {"1 bar": 4.0, "1 beat": 1.0, "1/2": 0.5, "1/4": 0.25, "1/8": 0.125, "1/16": 0.0625}

    pr_top = ttk.Frame(piano_roll_outer)
    pr_top.pack(fill="x", padx=8, pady=6)

    ttk.Label(pr_top, text="BPM").grid(row=0, column=0, sticky="w", padx=4)
    pr_bpm = tk.StringVar(value="120")
    ttk.Entry(pr_top, textvariable=pr_bpm, width=6).grid(row=0, column=1, sticky="w", padx=4)

    ttk.Label(pr_top, text="Time sig").grid(row=0, column=2, sticky="w", padx=4)
    pr_time_sig = tk.IntVar(value=4)
    ttk.Spinbox(pr_top, from_=2, to=12, textvariable=pr_time_sig, width=4).grid(row=0, column=3, sticky="w", padx=4)

    ttk.Label(pr_top, text="Snap").grid(row=0, column=4, sticky="w", padx=4)
    pr_snap = tk.StringVar(value="1/4")
    ttk.Combobox(pr_top, textvariable=pr_snap, values=list(_PR_SNAP_VALUES.keys()), state="readonly", width=8).grid(row=0, column=5, sticky="w", padx=4)

    ttk.Label(pr_top, text="Profile").grid(row=0, column=6, sticky="w", padx=4)
    pr_profile = tk.StringVar(value="ost")
    ttk.Combobox(pr_top, textvariable=pr_profile, values=VALID_PROFILES, state="readonly", width=10).grid(row=0, column=7, sticky="w", padx=4)

    ttk.Label(pr_top, text="Format").grid(row=0, column=8, sticky="w", padx=4)
    pr_format = tk.StringVar(value="wav")
    ttk.Combobox(pr_top, textvariable=pr_format, values=["wav", "ogg"], state="readonly", width=6).grid(row=0, column=9, sticky="w", padx=4)

    ttk.Label(pr_top, text="Output").grid(row=0, column=10, sticky="w", padx=4)
    pr_out = tk.StringVar(value="piano_roll.wav")
    ttk.Entry(pr_top, textvariable=pr_out, width=22).grid(row=0, column=11, sticky="ew", padx=4)
    pr_top.columnconfigure(11, weight=1)

    pr_status = ttk.Label(
        piano_roll_outer,
        text="Canvas workflow: click to place, drag to move/resize, right-click to delete.",
    )
    pr_status.pack(fill="x", padx=8, pady=2)

    pr_pane = ttk.PanedWindow(piano_roll_outer, orient="horizontal")
    pr_pane.pack(fill="both", expand=True, padx=8, pady=4)

    pr_left = ttk.LabelFrame(pr_pane, text="Tracks")
    pr_pane.add(pr_left, weight=1)

    pr_track_tree = ttk.Treeview(
        pr_left,
        columns=("instrument", "role", "vol", "pan", "mute", "solo"),
        show="headings",
        selectmode="browse",
        height=12,
    )
    for col, hdr, w in [
        ("instrument", "Instrument", 120),
        ("role", "Role", 80),
        ("vol", "Vol", 45),
        ("pan", "Pan", 50),
        ("mute", "M", 30),
        ("solo", "S", 30),
    ]:
        pr_track_tree.heading(col, text=hdr)
        pr_track_tree.column(col, width=w, anchor="center")
    pr_track_tree.pack(fill="both", expand=True, padx=4, pady=4)

    pr_template_frame = ttk.Frame(pr_left)
    pr_template_frame.pack(fill="x", padx=4, pady=(0, 4))
    ttk.Label(pr_template_frame, text="Starter tracks").pack(side="left")
    pr_track_template = tk.StringVar(value="PS2 Starter Trio")
    ttk.Combobox(
        pr_template_frame,
        textvariable=pr_track_template,
        values=list(_PR_TRACK_TEMPLATES.keys()),
        state="readonly",
        width=18,
    ).pack(side="left", padx=4)

    pr_track_form = ttk.LabelFrame(pr_left, text="Add / Edit Track")
    pr_track_form.pack(fill="x", padx=4, pady=4)

    ttk.Label(pr_track_form, text="Name").grid(row=0, column=0, sticky="w", padx=4, pady=3)
    pr_tf_name = tk.StringVar(value="Lead")
    ttk.Entry(pr_track_form, textvariable=pr_tf_name, width=12).grid(row=0, column=1, sticky="ew", padx=4, pady=3)

    ttk.Label(pr_track_form, text="Instrument").grid(row=0, column=2, sticky="w", padx=4, pady=3)
    pr_tf_instr = tk.StringVar(value="piano")
    ttk.Combobox(pr_track_form, textvariable=pr_tf_instr, values=sorted(InstrumentLibrary.available()), state="readonly", width=14).grid(row=0, column=3, sticky="ew", padx=4, pady=3)

    ttk.Label(pr_track_form, text="Role").grid(row=1, column=0, sticky="w", padx=4, pady=3)
    pr_tf_role = tk.StringVar(value="melody")
    ttk.Combobox(pr_track_form, textvariable=pr_tf_role, values=_TRACK_ROLES, state="readonly", width=12).grid(row=1, column=1, sticky="ew", padx=4, pady=3)

    ttk.Label(pr_track_form, text="Volume").grid(row=1, column=2, sticky="w", padx=4, pady=3)
    pr_tf_vol = tk.DoubleVar(value=1.0)
    ttk.Scale(pr_track_form, from_=0.0, to=1.0, variable=pr_tf_vol, orient="horizontal", length=80).grid(row=1, column=3, sticky="ew", padx=4, pady=3)

    ttk.Label(pr_track_form, text="Pan").grid(row=2, column=0, sticky="w", padx=4, pady=3)
    pr_tf_pan = tk.DoubleVar(value=0.0)
    ttk.Scale(pr_track_form, from_=-1.0, to=1.0, variable=pr_tf_pan, orient="horizontal", length=80).grid(row=2, column=1, sticky="ew", padx=4, pady=3)
    pr_tf_mute = tk.BooleanVar(value=False)
    pr_tf_solo = tk.BooleanVar(value=False)
    ttk.Checkbutton(pr_track_form, text="Mute", variable=pr_tf_mute).grid(row=2, column=2, sticky="w", padx=4, pady=3)
    ttk.Checkbutton(pr_track_form, text="Solo", variable=pr_tf_solo).grid(row=2, column=3, sticky="w", padx=4, pady=3)
    pr_track_form.columnconfigure(3, weight=1)

    pr_right = ttk.LabelFrame(pr_pane, text="Piano Roll + Inspector")
    pr_pane.add(pr_right, weight=2)

    pr_grid_frame = ttk.Frame(pr_right)
    pr_grid_frame.pack(fill="both", expand=True, padx=4, pady=4)
    pr_canvas = tk.Canvas(pr_grid_frame, bg="#17171c", height=360, highlightthickness=1, highlightbackground="#424254")
    pr_canvas.pack(side="left", fill="both", expand=True)
    pr_canvas_scroll = ttk.Scrollbar(pr_grid_frame, orient="horizontal", command=pr_canvas.xview)
    pr_canvas_scroll.pack(side="bottom", fill="x")
    pr_canvas.configure(xscrollcommand=pr_canvas_scroll.set)

    pr_note_tree = ttk.Treeview(
        pr_right,
        columns=("beat", "note", "dur", "vel"),
        show="headings",
        selectmode="browse",
        height=8,
    )
    for col, hdr, w in [
        ("beat", "Start beat", 80),
        ("note", "Note", 60),
        ("dur", "Duration (beats)", 120),
        ("vel", "Velocity", 70),
    ]:
        pr_note_tree.heading(col, text=hdr)
        pr_note_tree.column(col, width=w, anchor="center")
    pr_note_tree.pack(fill="x", padx=4, pady=4)

    def _pr_snap_value() -> float:
        return float(_PR_SNAP_VALUES.get(pr_snap.get(), 0.25))

    def _pr_note_rect(note: dict[str, object], *, beat_width: float, lane_height: float) -> tuple[float, float, float, float]:
        beat = float(note.get("beat", 0.0))
        dur = max(0.05, float(note.get("duration_beats", 1.0)))
        lane = _piano_roll_note_to_index(str(note.get("note", "A4")))
        y_lane = len(_NOTE_NAMES) - lane - 1
        return (beat * beat_width, y_lane * lane_height, (beat + dur) * beat_width, (y_lane + 1) * lane_height)

    def _pr_refresh_track_tree() -> None:
        pr_track_tree.delete(*pr_track_tree.get_children())
        for tname, tcfg in _pr_tracks.items():
            pr_track_tree.insert(
                "",
                "end",
                iid=tname,
                values=(
                    tcfg.get("instrument", ""),
                    tcfg.get("role", ""),
                    f"{tcfg.get('volume', 1.0):.2f}",
                    f"{tcfg.get('pan', 0.0):+.2f}",
                    "●" if bool(tcfg.get("mute", False)) else "",
                    "●" if bool(tcfg.get("solo", False)) else "",
                ),
            )

    def _pr_refresh_note_tree() -> None:
        pr_note_tree.delete(*pr_note_tree.get_children())
        tname = _pr_selected_track[0]
        if tname is None or tname not in _pr_tracks:
            return
        for i, nd in enumerate(_pr_tracks[tname]["notes"]):
            pr_note_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    f"{float(nd['beat']):.2f}",
                    nd["note"],
                    f"{float(nd['duration_beats']):.2f}",
                    f"{float(nd['velocity']):.2f}",
                ),
            )

    def _pr_refresh_canvas() -> None:
        pr_canvas.delete("all")
        beat_width = 24.0
        lane_height = 18.0
        max_beats = 64
        total_width = beat_width * max_beats
        total_height = lane_height * len(_NOTE_NAMES)
        pr_canvas.configure(scrollregion=(0, 0, total_width, total_height))
        for lane in range(len(_NOTE_NAMES)):
            y = lane * lane_height
            note_name = _piano_roll_index_to_note(len(_NOTE_NAMES) - lane - 1)
            fill = "#1e1e24" if "#" in note_name else "#23232b"
            pr_canvas.create_rectangle(0, y, total_width, y + lane_height, fill=fill, outline="#2d2d39")
            if note_name.endswith("C3") or note_name.endswith("C4") or note_name.endswith("C5"):
                pr_canvas.create_line(0, y, total_width, y, fill="#6e6eb0")
                pr_canvas.create_text(2, y + lane_height * 0.5, text=note_name, fill="#b9b9f6", anchor="w", font=("TkDefaultFont", 8))
        for beat in range(max_beats + 1):
            color = "#65658f" if beat % int(max(1, pr_time_sig.get())) == 0 else "#3c3c4d"
            width = 2 if beat % int(max(1, pr_time_sig.get())) == 0 else 1
            pr_canvas.create_line(beat * beat_width, 0, beat * beat_width, total_height, fill=color, width=width)

        tname = _pr_selected_track[0]
        if not tname or tname not in _pr_tracks:
            return
        notes = _pr_tracks[tname]["notes"]
        for idx, nd in enumerate(notes):
            x1, y1, x2, y2 = _pr_note_rect(nd, beat_width=beat_width, lane_height=lane_height)
            fill = "#42a5f5" if idx != _pr_selected_note_index[0] else "#ffb74d"
            pr_canvas.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1, fill=fill, outline="#101018", tags=(f"note:{idx}", "note"))

    def _pr_unique_track_name(base_name: str) -> str:
        name = base_name
        suffix = 2
        while name in _pr_tracks:
            name = f"{base_name} {suffix}"
            suffix += 1
        return name

    def _pr_add_track() -> None:
        name = pr_tf_name.get().strip()
        if not name:
            _set_status(pr_status, "Track name cannot be empty.")
            return
        if name in _pr_tracks:
            name = _pr_unique_track_name(name)
        _pr_tracks[name] = {
            "instrument": pr_tf_instr.get(),
            "role": pr_tf_role.get(),
            "volume": float(pr_tf_vol.get()),
            "pan": float(pr_tf_pan.get()),
            "mute": bool(pr_tf_mute.get()),
            "solo": bool(pr_tf_solo.get()),
            "notes": [],
        }
        _pr_selected_track[0] = name
        _pr_refresh_track_tree()
        _pr_refresh_note_tree()
        _pr_refresh_canvas()
        _set_status(pr_status, f"Track '{name}' added.")

    def _pr_apply_template() -> None:
        template = _PR_TRACK_TEMPLATES.get(pr_track_template.get(), [])
        if not template:
            return
        for item in template:
            name = _pr_unique_track_name(str(item.get("name", "Track")))
            _pr_tracks[name] = {
                "instrument": str(item.get("instrument", "piano")),
                "role": str(item.get("role", "harmony")),
                "volume": float(item.get("volume", 1.0)),
                "pan": float(item.get("pan", 0.0)),
                "mute": False,
                "solo": False,
                "notes": [],
            }
        _pr_refresh_track_tree()
        _set_status(pr_status, f"Added starter tracks from '{pr_track_template.get()}'.")

    def _pr_update_track() -> None:
        tname = _pr_selected_track[0]
        if not tname or tname not in _pr_tracks:
            _set_status(pr_status, "Select a track to update.")
            return
        track = _pr_tracks[tname]
        track["instrument"] = pr_tf_instr.get()
        track["role"] = pr_tf_role.get()
        track["volume"] = float(pr_tf_vol.get())
        track["pan"] = float(pr_tf_pan.get())
        track["mute"] = bool(pr_tf_mute.get())
        track["solo"] = bool(pr_tf_solo.get())
        _pr_refresh_track_tree()
        _set_status(pr_status, f"Track '{tname}' updated.")

    def _pr_remove_track() -> None:
        sel = pr_track_tree.selection()
        if not sel:
            _set_status(pr_status, "Select a track to remove.")
            return
        name = sel[0]
        _pr_tracks.pop(name, None)
        if _pr_selected_track[0] == name:
            _pr_selected_track[0] = None
        _pr_selected_note_index[0] = None
        _pr_refresh_track_tree()
        _pr_refresh_note_tree()
        _pr_refresh_canvas()
        _set_status(pr_status, f"Track '{name}' removed.")

    def _pr_on_track_select(_event: object = None) -> None:
        sel = pr_track_tree.selection()
        if not sel:
            return
        _pr_selected_track[0] = sel[0]
        _pr_selected_note_index[0] = None
        track = _pr_tracks.get(sel[0], {})
        pr_tf_name.set(sel[0])
        pr_tf_instr.set(str(track.get("instrument", "piano")))
        pr_tf_role.set(str(track.get("role", "melody")))
        pr_tf_vol.set(float(track.get("volume", 1.0)))
        pr_tf_pan.set(float(track.get("pan", 0.0)))
        pr_tf_mute.set(bool(track.get("mute", False)))
        pr_tf_solo.set(bool(track.get("solo", False)))
        _pr_refresh_note_tree()
        _pr_refresh_canvas()

    pr_track_tree.bind("<<TreeviewSelect>>", _pr_on_track_select)

    pr_track_btns = ttk.Frame(pr_left)
    pr_track_btns.pack(fill="x", padx=4, pady=4)
    ttk.Button(pr_track_btns, text="Add Track", command=_pr_add_track).pack(side="left", padx=2)
    ttk.Button(pr_track_btns, text="Update", command=_pr_update_track).pack(side="left", padx=2)
    ttk.Button(pr_track_btns, text="Remove", command=_pr_remove_track).pack(side="left", padx=2)
    ttk.Button(pr_track_btns, text="Add Starter Tracks", command=_pr_apply_template).pack(side="left", padx=2)

    pr_note_form = ttk.LabelFrame(pr_right, text="Selected note / precise values")
    pr_note_form.pack(fill="x", padx=4, pady=4)

    ttk.Label(pr_note_form, text="Start beat").grid(row=0, column=0, sticky="w", padx=4, pady=3)
    pr_nf_beat = tk.DoubleVar(value=0.0)
    ttk.Spinbox(pr_note_form, from_=0.0, to=256.0, increment=0.25, textvariable=pr_nf_beat, width=8).grid(row=0, column=1, sticky="ew", padx=4, pady=3)

    ttk.Label(pr_note_form, text="Note").grid(row=0, column=2, sticky="w", padx=4, pady=3)
    pr_nf_note = tk.StringVar(value="C4")
    ttk.Combobox(pr_note_form, textvariable=pr_nf_note, values=_NOTE_NAMES, state="readonly", width=6).grid(row=0, column=3, sticky="ew", padx=4, pady=3)

    ttk.Label(pr_note_form, text="Duration").grid(row=1, column=0, sticky="w", padx=4, pady=3)
    pr_nf_dur = tk.DoubleVar(value=1.0)
    ttk.Spinbox(pr_note_form, from_=0.05, to=64.0, increment=0.25, textvariable=pr_nf_dur, width=8).grid(row=1, column=1, sticky="ew", padx=4, pady=3)

    ttk.Label(pr_note_form, text="Velocity").grid(row=1, column=2, sticky="w", padx=4, pady=3)
    pr_nf_vel = tk.DoubleVar(value=1.0)
    ttk.Scale(pr_note_form, from_=0.0, to=1.0, variable=pr_nf_vel, orient="horizontal", length=100).grid(row=1, column=3, sticky="ew", padx=4, pady=3)
    pr_note_form.columnconfigure(1, weight=1)
    pr_note_form.columnconfigure(3, weight=1)

    def _pr_add_note() -> None:
        tname = _pr_selected_track[0]
        if not tname or tname not in _pr_tracks:
            _set_status(pr_status, "Select a track first.")
            return
        beat = _piano_roll_snap_beat(float(pr_nf_beat.get()), _pr_snap_value())
        dur = max(_pr_snap_value(), float(pr_nf_dur.get()))
        nd = {
            "beat": beat,
            "note": pr_nf_note.get(),
            "duration_beats": dur,
            "velocity": float(pr_nf_vel.get()),
        }
        notes = _pr_tracks[tname]["notes"]
        notes.append(nd)
        notes.sort(key=lambda item: float(item["beat"]))
        _pr_refresh_note_tree()
        _pr_refresh_canvas()
        pr_nf_beat.set(beat + dur)
        _set_status(pr_status, f"Note {nd['note']} added at beat {beat:.2f}.")

    def _pr_edit_note() -> None:
        tname = _pr_selected_track[0]
        idx = _pr_selected_note_index[0]
        if not tname or tname not in _pr_tracks or idx is None:
            _set_status(pr_status, "Select a note first.")
            return
        notes = _pr_tracks[tname]["notes"]
        if idx >= len(notes):
            return
        notes[idx] = {
            "beat": _piano_roll_snap_beat(float(pr_nf_beat.get()), _pr_snap_value()),
            "note": pr_nf_note.get(),
            "duration_beats": max(0.05, float(pr_nf_dur.get())),
            "velocity": float(pr_nf_vel.get()),
        }
        notes.sort(key=lambda item: float(item["beat"]))
        _pr_refresh_note_tree()
        _pr_refresh_canvas()

    def _pr_remove_note() -> None:
        tname = _pr_selected_track[0]
        idx = _pr_selected_note_index[0]
        if not tname or tname not in _pr_tracks or idx is None:
            _set_status(pr_status, "Select a note to remove.")
            return
        notes = _pr_tracks[tname]["notes"]
        if idx < len(notes):
            removed = notes.pop(idx)
            _pr_selected_note_index[0] = None
            _pr_refresh_note_tree()
            _pr_refresh_canvas()
            _set_status(pr_status, f"Removed note {removed['note']} at beat {float(removed['beat']):.2f}.")

    def _pr_select_note_index(idx: int | None) -> None:
        _pr_selected_note_index[0] = idx
        tname = _pr_selected_track[0]
        if idx is None or not tname or tname not in _pr_tracks:
            return
        notes = _pr_tracks[tname]["notes"]
        if idx >= len(notes):
            return
        nd = notes[idx]
        pr_nf_beat.set(float(nd["beat"]))
        pr_nf_note.set(str(nd["note"]))
        pr_nf_dur.set(float(nd["duration_beats"]))
        pr_nf_vel.set(float(nd["velocity"]))
        if pr_note_tree.exists(str(idx)):
            pr_note_tree.selection_set(str(idx))

    def _pr_load_note_to_form(_event: object = None) -> None:
        sel = pr_note_tree.selection()
        if not sel:
            return
        _pr_select_note_index(int(sel[0]))
        _pr_refresh_canvas()

    pr_note_tree.bind("<<TreeviewSelect>>", _pr_load_note_to_form)

    pr_drag_state: dict[str, object] = {"active": False}

    def _pr_pick_note_at(x: float, y: float) -> int | None:
        item = pr_canvas.find_withtag("current")
        if item:
            tags = pr_canvas.gettags(item[0])
            for tag in tags:
                if tag.startswith("note:"):
                    try:
                        return int(tag.split(":", 1)[1])
                    except ValueError:
                        return None
        return None

    def _pr_canvas_to_note(x: float, y: float) -> tuple[float, str]:
        beat_width = 24.0
        lane_height = 18.0
        beat = _piano_roll_snap_beat(float(pr_canvas.canvasx(x)) / beat_width, _pr_snap_value())
        lane = int(float(pr_canvas.canvasy(y)) / lane_height)
        note = _piano_roll_index_to_note(len(_NOTE_NAMES) - lane - 1)
        return beat, note

    def _pr_on_canvas_press(event: object) -> None:
        if _pr_selected_track[0] is None:
            _set_status(pr_status, "Select a track first.")
            return
        x = float(getattr(event, "x", 0.0))
        y = float(getattr(event, "y", 0.0))
        idx = _pr_pick_note_at(x, y)
        if idx is None:
            beat, note = _pr_canvas_to_note(x, y)
            pr_nf_beat.set(beat)
            pr_nf_note.set(note)
            pr_nf_dur.set(max(_pr_snap_value(), float(pr_nf_dur.get())))
            _pr_add_note()
            return
        _pr_select_note_index(idx)
        tname = _pr_selected_track[0]
        if not tname or tname not in _pr_tracks:
            return
        note = _pr_tracks[tname]["notes"][idx]
        beat_width = 24.0
        x1, _, x2, _ = _pr_note_rect(note, beat_width=beat_width, lane_height=18.0)
        edge_resize = float(pr_canvas.canvasx(x)) >= (x2 - 8.0)
        pr_drag_state.update(
            {
                "active": True,
                "idx": idx,
                "mode": "resize" if edge_resize else "move",
                "start_x": float(pr_canvas.canvasx(x)),
                "start_y": float(pr_canvas.canvasy(y)),
                "start_beat": float(note["beat"]),
                "start_note": str(note["note"]),
                "start_dur": float(note["duration_beats"]),
            }
        )
        _pr_refresh_canvas()

    def _pr_on_canvas_drag(event: object) -> None:
        if not bool(pr_drag_state.get("active")):
            return
        tname = _pr_selected_track[0]
        idx = pr_drag_state.get("idx")
        if not tname or tname not in _pr_tracks or not isinstance(idx, int):
            return
        notes = _pr_tracks[tname]["notes"]
        if idx >= len(notes):
            return
        beat_width = 24.0
        lane_height = 18.0
        start_x = float(pr_drag_state.get("start_x", 0.0))
        start_y = float(pr_drag_state.get("start_y", 0.0))
        dx_beats = (float(pr_canvas.canvasx(float(getattr(event, "x", 0.0)))) - start_x) / beat_width
        dy_lanes = int((float(pr_canvas.canvasy(float(getattr(event, "y", 0.0)))) - start_y) / lane_height)
        mode = str(pr_drag_state.get("mode", "move"))
        if mode == "resize":
            notes[idx]["duration_beats"] = max(
                _pr_snap_value(),
                _piano_roll_snap_beat(float(pr_drag_state.get("start_dur", 1.0)) + dx_beats, _pr_snap_value()),
            )
        else:
            notes[idx]["beat"] = _piano_roll_snap_beat(float(pr_drag_state.get("start_beat", 0.0)) + dx_beats, _pr_snap_value())
            lane = _piano_roll_note_to_index(str(pr_drag_state.get("start_note", "A4"))) - dy_lanes
            notes[idx]["note"] = _piano_roll_index_to_note(lane)
        _pr_select_note_index(idx)
        _pr_refresh_note_tree()
        _pr_refresh_canvas()

    def _pr_on_canvas_release(_event: object = None) -> None:
        if bool(pr_drag_state.get("active")):
            pr_drag_state["active"] = False
            tname = _pr_selected_track[0]
            if tname and tname in _pr_tracks:
                _pr_tracks[tname]["notes"].sort(key=lambda item: float(item["beat"]))
                _pr_refresh_note_tree()
                _pr_refresh_canvas()

    def _pr_on_canvas_delete(event: object) -> None:
        idx = _pr_pick_note_at(float(getattr(event, "x", 0.0)), float(getattr(event, "y", 0.0)))
        if idx is None:
            return
        _pr_select_note_index(idx)
        _pr_remove_note()

    pr_canvas.bind("<Button-1>", _pr_on_canvas_press)
    pr_canvas.bind("<B1-Motion>", _pr_on_canvas_drag)
    pr_canvas.bind("<ButtonRelease-1>", _pr_on_canvas_release)
    pr_canvas.bind("<Button-3>", _pr_on_canvas_delete)

    pr_tools = ttk.Frame(pr_right)
    pr_tools.pack(fill="x", padx=4, pady=2)
    pr_transpose = tk.IntVar(value=12)
    pr_nudge = tk.DoubleVar(value=0.25)
    ttk.Label(pr_tools, text="Transpose").pack(side="left", padx=(0, 2))
    ttk.Spinbox(pr_tools, from_=-24, to=24, textvariable=pr_transpose, width=5).pack(side="left")
    ttk.Label(pr_tools, text="Nudge").pack(side="left", padx=(8, 2))
    ttk.Spinbox(pr_tools, from_=-4.0, to=4.0, increment=0.125, textvariable=pr_nudge, width=6).pack(side="left")

    def _pr_apply_notes_edit(fn: object, status_label: str) -> None:
        tname = _pr_selected_track[0]
        if not tname or tname not in _pr_tracks:
            _set_status(pr_status, "Select a track first.")
            return
        notes = _pr_tracks[tname]["notes"]
        _pr_tracks[tname]["notes"] = fn(notes)
        _pr_refresh_note_tree()
        _pr_refresh_canvas()
        _set_status(pr_status, status_label)

    ttk.Button(
        pr_tools,
        text="Quantize",
        command=lambda: _pr_apply_notes_edit(lambda notes: _piano_roll_quantize_notes(notes, snap=_pr_snap_value()), "Track quantized."),
    ).pack(side="left", padx=4)
    ttk.Button(
        pr_tools,
        text="Duplicate Bar",
        command=lambda: _pr_apply_notes_edit(
            lambda notes: sorted(notes + _piano_roll_duplicate_notes(notes, beat_offset=float(pr_time_sig.get())), key=lambda item: float(item["beat"])),
            "Bar duplicated.",
        ),
    ).pack(side="left", padx=4)
    ttk.Button(
        pr_tools,
        text="Transpose",
        command=lambda: _pr_apply_notes_edit(lambda notes: _piano_roll_transpose_notes(notes, semitones=int(pr_transpose.get())), "Track transposed."),
    ).pack(side="left", padx=4)
    ttk.Button(
        pr_tools,
        text="Nudge",
        command=lambda: _pr_apply_notes_edit(lambda notes: _piano_roll_nudge_notes(notes, beat_delta=float(pr_nudge.get()), snap=_pr_snap_value()), "Track nudged."),
    ).pack(side="left", padx=4)
    ttk.Button(
        pr_tools,
        text="Humanize",
        command=lambda: _pr_apply_notes_edit(
            lambda notes: _piano_roll_humanize_notes(notes, timing_amount=_pr_snap_value() * 0.2, velocity_amount=0.08, seed=_safe_int(music_seed.get(), 0)),
            "Track humanized.",
        ),
    ).pack(side="left", padx=4)

    pr_note_btns = ttk.Frame(pr_right)
    pr_note_btns.pack(fill="x", padx=4, pady=4)
    ttk.Button(pr_note_btns, text="Add Note", command=_pr_add_note).pack(side="left", padx=4)
    ttk.Button(pr_note_btns, text="Update Selected", command=_pr_edit_note).pack(side="left", padx=4)
    ttk.Button(pr_note_btns, text="Remove Note", command=_pr_remove_note).pack(side="left", padx=4)
    ttk.Button(
        pr_note_btns,
        text="Preview Note",
        command=lambda: _play_output_path(
            _preview_instrument_note(
                _pr_tracks.get(_pr_selected_track[0] or "", {}).get("instrument", "piano"),
                pr_nf_note.get(),
                0.35,
                Path("piano_roll_note_preview.wav"),
            ),
            "Music",
        ),
    ).pack(side="left", padx=4)
    _pr_refresh_canvas()

    # -- Save / Load composition JSON --
    pr_json_path = tk.StringVar(value="piano_roll.json")
    pr_io_frame = ttk.Frame(piano_roll_outer)
    pr_io_frame.pack(fill="x", padx=8, pady=2)

    ttk.Label(pr_io_frame, text="Composition JSON").pack(side="left", padx=4)
    ttk.Entry(pr_io_frame, textvariable=pr_json_path, width=30).pack(side="left", padx=4)

    def _pr_save_json() -> None:
        path = Path(pr_json_path.get())
        payload = {
            "bpm": _safe_int(pr_bpm.get(), 120),
            "time_signature": int(pr_time_sig.get()),
            "tracks": _pr_tracks,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        _set_status(pr_status, f"Saved composition to {path}.")

    def _pr_load_json() -> None:
        path = Path(pr_json_path.get())
        if not path.exists():
            _set_status(pr_status, f"File not found: {path}")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _set_status(pr_status, f"Load failed: {exc}")
            return
        pr_bpm.set(str(data.get("bpm", 120)))
        pr_time_sig.set(int(data.get("time_signature", 4)))
        _pr_tracks.clear()
        for tname, tcfg in data.get("tracks", {}).items():
            _pr_tracks[tname] = {
                "instrument": str(tcfg.get("instrument", "piano")),
                "role": str(tcfg.get("role", "harmony")),
                "volume": float(tcfg.get("volume", 1.0)),
                "pan": float(tcfg.get("pan", 0.0)),
                "mute": bool(tcfg.get("mute", False)),
                "solo": bool(tcfg.get("solo", False)),
                "notes": [_piano_roll_clone_note(note) for note in tcfg.get("notes", [])],
            }
        _pr_selected_track[0] = None
        _pr_selected_note_index[0] = None
        _pr_refresh_track_tree()
        _pr_refresh_note_tree()
        _pr_refresh_canvas()
        _set_status(pr_status, f"Loaded composition from {path}.")

    ttk.Button(pr_io_frame, text="Save JSON", command=_pr_save_json).pack(side="left", padx=4)
    ttk.Button(pr_io_frame, text="Load JSON", command=_pr_load_json).pack(side="left", padx=4)

    # -- Render button --
    pr_render_frame = ttk.Frame(piano_roll_outer)
    pr_render_frame.pack(fill="x", padx=8, pady=4)

    def _pr_render_threaded() -> None:
        if not _pr_tracks:
            _set_status(pr_status, "No tracks — add a track and some notes first.")
            return
        total_notes = sum(len(tc["notes"]) for tc in _pr_tracks.values())
        if total_notes == 0:
            _set_status(pr_status, "No notes — add notes before rendering.")
            return
        _set_status(pr_status, "Rendering piano roll...")
        _set_status(global_status, "Piano Roll rendering...")

        def _worker() -> None:
            try:
                bpm = max(20.0, float(_safe_int(pr_bpm.get(), 120)))
                out = Path(pr_out.get())
                result = _render_piano_roll_to_file(
                    dict(_pr_tracks),
                    bpm=bpm,
                    time_signature=int(pr_time_sig.get()),
                    output_path=out,
                    mastering_profile=pr_profile.get(),
                    fmt=pr_format.get(),
                )
                pr_status.configure(text=f"Done — saved to {result}")
                global_status.configure(text="Piano Roll render complete.")
                _refresh_preview_files(select_category="Music")
            except Exception as exc:  # pragma: no cover - UI path
                pr_status.configure(text=f"Render error: {exc}")
                global_status.configure(text=f"Piano Roll failed — {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    ttk.Button(pr_render_frame, text="Render to Audio", command=_pr_render_threaded).pack(side="left", padx=8)
    ttk.Button(
        pr_render_frame,
        text="Play latest",
        command=lambda: _play_output_path(Path(pr_out.get()), "Music"),
    ).pack(side="left", padx=8)

    def _build_current_preset() -> dict[str, object]:
        return {
            "studio": {
                "examplesRoot": examples_root.get(),
                "sampleRoot": sample_root.get(),
                "sampleBaseBackend": sample_base_backend.get(),
                "workflowGoal": workflow_goal.get(),
                "newFilePath": new_file_path.get(),
                "newProjectName": new_project_name.get(),
                "outputDir": output_dir.get(),
                "outputBaseName": output_base_name.get(),
            },
            "music": {
                "style": music_style.get(),
                "prompt": music_prompt.get(),
                "backend": music_backend.get(),
                "profile": music_profile.get(),
                "bars": int(max(4, _safe_int(str(bars_var.get()), 16))),
                "region": music_region.get(),
                "adaptiveIntensity": bool(music_adaptive_intensity.get()),
                "format": music_format.get(),
                "customArrangement": bool(custom_arrangement.get()),
                "leadInstrument": custom_lead.get(),
                "counterInstrument": custom_counter.get(),
                "padInstrument": custom_pad.get(),
                "chordInstrument": custom_chord.get(),
                "bassInstrument": custom_bass.get(),
                "ostinatoInstrument": custom_ostinato.get(),
                "percussionInstrument": custom_percussion.get(),
                "seed": music_seed.get(),
                "outputPath": music_out.get(),
            },
            "sfx": {
                "category": sfx_type.get(),
                "backend": sfx_backend.get(),
                "durationSeconds": float(sfx_duration.get()),
                "pitchHz": sfx_pitch.get(),
                "seed": sfx_seed.get(),
                "outputPath": sfx_out.get(),
            },
            "voice": {
                "text": voice_text.get("1.0", "end").strip(),
                "backend": voice_backend.get(),
                "preset": voice_preset.get(),
                "speed": float(voice_speed.get()),
                "seed": voice_seed.get(),
                "outputPath": voice_out.get(),
            },
            "piece": {
                "style": pc_style.get(),
                "backend": pc_backend.get(),
                "profile": pc_profile.get(),
                "durationSeconds": max(10.0, _parse_float_field(pc_duration.get() or 90.0, field_name="piece.durationSeconds")),
                "seed": pc_seed.get(),
                "withVocals": bool(pc_with_vocals.get()),
                "vocalPreset": pc_vocal_preset.get(),
                "outputPath": pc_out.get(),
                "format": pc_format.get(),
                "songRecipe": pc_recipe.get(),
                "sections": list(_pc_section_list),
            },
            "pianoRoll": {
                "bpm": _safe_int(pr_bpm.get(), 120),
                "timeSignature": int(pr_time_sig.get()),
                "snap": pr_snap.get(),
                "profile": pr_profile.get(),
                "format": pr_format.get(),
                "outputPath": pr_out.get(),
                "jsonPath": pr_json_path.get(),
                "tracks": _clone_piano_roll_tracks(_pr_tracks),
            },
        }

    def _save_preset() -> None:
        try:
            path = Path(preset_path.get())
            _write_studio_preset(path, _build_current_preset())
            _set_status(global_status, f"Preset saved: {path}")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(global_status, f"Preset save failed — {exc}")

    def _load_preset() -> None:
        try:
            path = Path(preset_path.get())
            data = _read_studio_preset(path)
            studio = data.get("studio", {})
            if isinstance(studio, dict):
                examples_root.set(str(studio.get("examplesRoot", examples_root.get())))
                sample_root.set(str(studio.get("sampleRoot", sample_root.get())))
                sample_base = str(studio.get("sampleBaseBackend", sample_base_backend.get()))
                if sample_base in {"synth_orchestral", "ps1", "full_orchestral", "procedural"}:
                    sample_base_backend.set(sample_base)
                workflow_value = str(studio.get("workflowGoal", workflow_goal.get()))
                if workflow_value in _STUDIO_WORKFLOW_PRESETS:
                    workflow_goal.set(workflow_value)
                new_file_path.set(str(studio.get("newFilePath", new_file_path.get())))
                new_project_name.set(str(studio.get("newProjectName", new_project_name.get())))
                output_dir.set(str(studio.get("outputDir", output_dir.get())))
                output_base_name.set(str(studio.get("outputBaseName", output_base_name.get())))
            music = data.get("music", {})
            if isinstance(music, dict):
                style_value = str(music.get("style", music_style.get()))
                if style_value in MusicGenerator.available_styles():
                    music_style.set(style_value)
                    _refresh_bpm()
                music_prompt.set(str(music.get("prompt", music_prompt.get())))
                backend_value = str(music.get("backend", music_backend.get()))
                if backend_value in _available_backends_for_modality("music", sample_rate=44100):
                    music_backend.set(backend_value)
                profile_value = str(music.get("profile", music_profile.get()))
                if profile_value in VALID_PROFILES:
                    music_profile.set(profile_value)
                region_value = str(music.get("region", music_region.get()))
                if region_value in {"", "plains", "forest", "coast", "ruins", "arid"}:
                    music_region.set(region_value)
                format_value = str(music.get("format", music_format.get())).lower()
                if format_value in {"wav", "ogg"}:
                    music_format.set(format_value)
                custom_arrangement.set(bool(music.get("customArrangement", custom_arrangement.get())))
                custom_lead.set(_normalize_instrument_choice(str(music.get("leadInstrument", custom_lead.get())), custom_lead.get()))
                custom_counter.set(_normalize_instrument_choice(str(music.get("counterInstrument", custom_counter.get())), custom_counter.get()))
                custom_pad.set(_normalize_instrument_choice(str(music.get("padInstrument", custom_pad.get())), custom_pad.get()))
                custom_chord.set(_normalize_instrument_choice(str(music.get("chordInstrument", custom_chord.get())), custom_chord.get()))
                custom_bass.set(_normalize_instrument_choice(str(music.get("bassInstrument", custom_bass.get())), custom_bass.get()))
                custom_ostinato.set(_normalize_instrument_choice(str(music.get("ostinatoInstrument", custom_ostinato.get())), custom_ostinato.get()))
                percussion_value = str(music.get("percussionInstrument", custom_percussion.get()))
                if percussion_value:
                    percussion_value = _normalize_instrument_choice(percussion_value, custom_percussion.get())
                custom_percussion.set(percussion_value)
                music_adaptive_intensity.set(bool(music.get("adaptiveIntensity", music_adaptive_intensity.get())))
                bars_raw = music.get("bars", bars_var.get())
                bars_value = _safe_int(str(bars_raw), int(bars_var.get()))
                bars_var.set(max(4, bars_value))
                music_seed.set(str(music.get("seed", music_seed.get())))
                music_out.set(str(music.get("outputPath", music_out.get())))

            sfx = data.get("sfx", {})
            if isinstance(sfx, dict):
                sfx_value = str(sfx.get("category", sfx_type.get()))
                if sfx_value in available_sfx_types():
                    sfx_type.set(sfx_value)
                sfx_backend_value = str(sfx.get("backend", sfx_backend.get()))
                if sfx_backend_value in _available_backends_for_modality("sfx", sample_rate=44100):
                    sfx_backend.set(sfx_backend_value)
                sfx_duration_value = _parse_float_field(
                    sfx.get("durationSeconds", sfx_duration.get()),
                    field_name="sfx.durationSeconds",
                )
                sfx_duration.set(sfx_duration_value)
                sfx_pitch.set(str(sfx.get("pitchHz", sfx_pitch.get())))
                sfx_seed.set(str(sfx.get("seed", sfx_seed.get())))
                sfx_out.set(str(sfx.get("outputPath", sfx_out.get())))

            voice = data.get("voice", {})
            if isinstance(voice, dict):
                voice_text.delete("1.0", "end")
                voice_text.insert("1.0", str(voice.get("text", "")))
                voice_backend_value = str(voice.get("backend", voice_backend.get()))
                if voice_backend_value in _available_backends_for_modality("voice", sample_rate=22050):
                    voice_backend.set(voice_backend_value)
                preset_value = str(voice.get("preset", voice_preset.get()))
                if preset_value in VOICE_PRESETS:
                    voice_preset.set(preset_value)
                voice_speed_value = _parse_float_field(
                    voice.get("speed", voice_speed.get()),
                    field_name="voice.speed",
                )
                voice_speed.set(voice_speed_value)
                voice_seed.set(str(voice.get("seed", voice_seed.get())))
                voice_out.set(str(voice.get("outputPath", voice_out.get())))

            piece = data.get("piece", {})
            if isinstance(piece, dict):
                style_value = str(piece.get("style", pc_style.get()))
                if style_value in MusicGenerator.available_styles():
                    pc_style.set(style_value)
                backend_value = str(piece.get("backend", pc_backend.get()))
                if backend_value in _available_backends_for_modality("music", sample_rate=44100):
                    pc_backend.set(backend_value)
                profile_value = str(piece.get("profile", pc_profile.get()))
                if profile_value in VALID_PROFILES:
                    pc_profile.set(profile_value)
                pc_duration.set(str(piece.get("durationSeconds", pc_duration.get())))
                pc_seed.set(str(piece.get("seed", pc_seed.get())))
                pc_with_vocals.set(bool(piece.get("withVocals", pc_with_vocals.get())))
                vocal_value = str(piece.get("vocalPreset", pc_vocal_preset.get()))
                if vocal_value in _PC_VOCAL_PRESETS:
                    pc_vocal_preset.set(vocal_value)
                format_value = str(piece.get("format", pc_format.get())).lower()
                if format_value in {"wav", "ogg"}:
                    pc_format.set(format_value)
                pc_out.set(str(piece.get("outputPath", pc_out.get())))
                recipe_value = str(piece.get("songRecipe", pc_recipe.get()))
                if recipe_value in _PIECE_SONG_RECIPES:
                    pc_recipe.set(recipe_value)
                _pc_section_list[:] = [str(item) for item in piece.get("sections", _pc_section_list)]
                _pc_refresh_order_list()

            piano_roll = data.get("pianoRoll", {})
            if isinstance(piano_roll, dict):
                pr_bpm.set(str(piano_roll.get("bpm", pr_bpm.get())))
                pr_time_sig.set(int(piano_roll.get("timeSignature", pr_time_sig.get())))
                snap_value = str(piano_roll.get("snap", pr_snap.get()))
                if snap_value in _PR_SNAP_VALUES:
                    pr_snap.set(snap_value)
                profile_value = str(piano_roll.get("profile", pr_profile.get()))
                if profile_value in VALID_PROFILES:
                    pr_profile.set(profile_value)
                format_value = str(piano_roll.get("format", pr_format.get())).lower()
                if format_value in {"wav", "ogg"}:
                    pr_format.set(format_value)
                pr_out.set(str(piano_roll.get("outputPath", pr_out.get())))
                pr_json_path.set(str(piano_roll.get("jsonPath", pr_json_path.get())))
                _pr_tracks.clear()
                tracks_value = piano_roll.get("tracks", {})
                if isinstance(tracks_value, dict):
                    _pr_tracks.update(_clone_piano_roll_tracks(tracks_value))
                _pr_selected_track[0] = next(iter(_pr_tracks), None)
                _pr_selected_note_index[0] = None
                _pr_refresh_track_tree()
                _pr_refresh_note_tree()
                _pr_refresh_canvas()

            _set_status(global_status, f"Preset loaded: {path}")
            _refresh_preview_files()
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(global_status, f"Preset load failed — {exc}")

    def _apply_new_file_targets() -> None:
        targets = _new_file_output_targets(
            output_base_name.get(),
            output_dir.get(),
            fmt=music_format.get(),
        )
        music_out.set(targets["music"])
        sfx_out.set(targets["sfx"])
        voice_out.set(targets["voice"])
        _set_status(global_status, f"New file targets applied for '{output_base_name.get().strip() or 'new_asset'}'.")
        _refresh_preview_files()

    def _write_new_file() -> None:
        try:
            targets = _new_file_output_targets(
                output_base_name.get(),
                output_dir.get(),
                fmt=music_format.get(),
            )
            payload = _build_new_file_template(
                project_name=new_project_name.get(),
                preset_path=preset_path.get(),
                output_targets=targets,
                preset_payload=_build_current_preset(),
            )
            path = Path(new_file_path.get())
            _write_new_file_template(path, payload)
            _set_status(global_status, f"New file template saved: {path}")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(global_status, f"New file template failed — {exc}")

    def _apply_workflow_goal() -> None:
        try:
            preset = _studio_workflow_preset(workflow_goal.get())
            music = preset["music"]
            sfx = preset["sfx"]
            piece = preset["piece"]
            studio = preset["studio"]

            style_value = str(music.get("style", music_style.get()))
            if style_value in MusicGenerator.available_styles():
                music_style.set(style_value)
                _refresh_bpm()
            prompt_value = str(music.get("prompt", music_prompt.get()))
            music_prompt.set(prompt_value)
            music_backend_value = str(music.get("backend", music_backend.get()))
            if music_backend_value in _available_backends_for_modality("music", sample_rate=44100):
                music_backend.set(music_backend_value)
            music_profile_value = str(music.get("profile", music_profile.get()))
            if music_profile_value in VALID_PROFILES:
                music_profile.set(music_profile_value)
            music_region_value = str(music.get("region", music_region.get()))
            if music_region_value in {"", "plains", "forest", "coast", "ruins", "arid"}:
                music_region.set(music_region_value)
            music_format_value = str(music.get("format", music_format.get())).lower()
            if music_format_value in {"wav", "ogg"}:
                music_format.set(music_format_value)
            custom_arrangement.set(False)
            bars_var.set(max(4, _safe_int(str(music.get("bars", bars_var.get())), int(bars_var.get()))))
            music_adaptive_intensity.set(bool(music.get("adaptiveIntensity", music_adaptive_intensity.get())))

            sfx_value = str(sfx.get("category", sfx_type.get()))
            if sfx_value in available_sfx_types():
                sfx_type.set(sfx_value)
            sfx_duration.set(max(0.05, _parse_float_field(sfx.get("durationSeconds", sfx_duration.get()), field_name="sfx.durationSeconds")))

            piece_style = str(piece.get("style", pc_style.get()))
            if piece_style in MusicGenerator.available_styles():
                pc_style.set(piece_style)
            piece_backend = str(piece.get("backend", pc_backend.get()))
            if piece_backend in _available_backends_for_modality("music", sample_rate=44100):
                pc_backend.set(piece_backend)
            piece_profile = str(piece.get("profile", pc_profile.get()))
            if piece_profile in VALID_PROFILES:
                pc_profile.set(piece_profile)
            pc_duration.set(str(max(10.0, _parse_float_field(piece.get("durationSeconds", pc_duration.get()), field_name="piece.durationSeconds"))))
            pc_with_vocals.set(bool(piece.get("withVocals", pc_with_vocals.get())))
            piece_vocal = str(piece.get("vocalPreset", pc_vocal_preset.get()))
            if piece_vocal in _PC_VOCAL_PRESETS:
                pc_vocal_preset.set(piece_vocal)
            piece_format = str(piece.get("format", pc_format.get())).lower()
            if piece_format in {"wav", "ogg"}:
                pc_format.set(piece_format)
            piece_recipe = str(piece.get("songRecipe", pc_recipe.get()))
            if piece_recipe in _PIECE_SONG_RECIPES:
                pc_recipe.set(piece_recipe)

            base_name = str(studio.get("baseName", output_base_name.get())).strip()
            if base_name:
                output_base_name.set(base_name)
            _apply_new_file_targets()
            pc_out.set(str(Path(output_dir.get()) / f"{output_base_name.get().strip() or 'new_asset'}_piece.{pc_format.get()}"))
            _set_status(global_status, f"Applied workflow goal: {workflow_goal.get()}")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(global_status, f"Workflow goal apply failed — {exc}")

    def _generate_all() -> None:
        nonlocal last_failed_action
        failures: list[str] = []
        _set_status(global_status, "Running batch generation (music + sfx + voice)...")
        for name, runner, status_label in (
            ("music", _run_music_generation, music_status),
            ("sfx", _run_sfx_generation, sfx_status),
            ("voice", _run_voice_generation, voice_status),
        ):
            try:
                _set_status(status_label, f"Generating {name}...")
                out_path = runner()
                _set_status(status_label, f"Done — saved to {out_path}")
            except Exception as exc:  # pragma: no cover - UI path
                failures.append(f"{name}: {exc}")
                last_failed_action = name
                _set_status(status_label, f"Error: {exc}")
        if failures:
            _set_status(global_status, "Batch completed with errors — " + "; ".join(failures))
        else:
            last_failed_action = None
            _set_status(global_status, "Batch completed successfully.")
        _refresh_preview_files()

    def _retry_last_error() -> None:
        if last_failed_action == "music":
            _generate_music()
            return
        if last_failed_action == "sfx":
            _generate_sfx()
            return
        if last_failed_action == "voice":
            _generate_voice()
            return
        _set_status(global_status, "No failed action to retry.")

    # Preview panel (play/stop + category/file selection)
    preview_frame = ttk.LabelFrame(root, text="Preview")
    preview_frame.pack(fill="x", padx=8, pady=(0, 8))
    preview_category = tk.StringVar(value="Music")
    preview_file = tk.StringVar(value="")
    ttk.Label(preview_frame, text="Category").grid(row=0, column=0, padx=6, pady=6, sticky="w")
    category_box = ttk.Combobox(
        preview_frame,
        textvariable=preview_category,
        values=["Music", "SFX", "Vocal", "Examples"],
        state="readonly",
        width=14,
    )
    category_box.grid(row=0, column=1, padx=6, pady=6, sticky="w")
    ttk.Label(preview_frame, text="File").grid(row=0, column=2, padx=6, pady=6, sticky="w")
    file_box = ttk.Combobox(preview_frame, textvariable=preview_file, values=[], state="readonly")
    file_box.grid(row=0, column=3, padx=6, pady=6, sticky="ew")
    preview_frame.columnconfigure(3, weight=1)

    def _stop_playback() -> None:
        nonlocal playback_handle
        if playback_handle is not None:
            playback_handle.stop()
            playback_handle = None

    def _play_output_path(output_path: Path, category: str) -> None:
        path = output_path.expanduser()
        if not path.exists():
            _set_status(global_status, f"File not found for preview: {path}")
            return
        _refresh_preview_files(select_category=category)
        preview_file.set(str(path))
        _play_selected()

    def _refresh_preview_files(*_args: object, select_category: str | None = None) -> None:
        nonlocal preview_catalog
        preview_catalog = _build_preview_catalog(
            music_output=Path(music_out.get()),
            sfx_output=Path(sfx_out.get()),
            voice_output=Path(voice_out.get()),
            examples_root=Path(examples_root.get()),
            extra_music_outputs=[
                Path(pc_out.get()),
                Path(pr_out.get()),
                Path(instr_out.get()),
                Path(synth_out.get()),
            ],
        )
        if select_category is not None and select_category in preview_catalog:
            preview_category.set(select_category)
        files = [str(path) for path in preview_catalog.get(preview_category.get(), [])]
        file_box.configure(values=files)
        if files:
            preview_file.set(files[0])
        else:
            preview_file.set("")

    def _play_selected() -> None:
        nonlocal playback_handle
        selected = preview_file.get().strip()
        if not selected:
            _set_status(global_status, "No file selected for preview.")
            return
        try:
            _stop_playback()
            playback_handle = _start_playback(Path(selected))
            _set_status(global_status, f"Playing: {selected}")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(global_status, f"Playback failed — {exc}")

    def _stop_selected() -> None:
        _stop_playback()
        _set_status(global_status, "Playback stopped.")

    def _browse_example_root() -> None:
        selected = filedialog.askdirectory(initialdir=examples_root.get() or ".")
        if selected:
            examples_root.set(selected)
            _refresh_preview_files(select_category="Examples")

    ttk.Button(control_bar, text="Save Preset", command=_save_preset).grid(row=0, column=2, padx=4)
    ttk.Button(control_bar, text="Load Preset", command=_load_preset).grid(row=0, column=3, padx=4)
    ttk.Button(control_bar, text="Generate All", command=_generate_all).grid(row=0, column=4, padx=4)
    ttk.Button(control_bar, text="Retry Last Error", command=_retry_last_error).grid(row=0, column=5, padx=4)
    ttk.Button(control_bar, text="Browse Examples", command=_browse_example_root).grid(row=1, column=2, padx=4)
    ttk.Button(control_bar, text="Refresh Preview Files", command=_refresh_preview_files).grid(row=1, column=3, padx=4)
    ttk.Button(control_bar, text="New File Targets", command=_apply_new_file_targets).grid(row=1, column=4, padx=4)
    ttk.Button(control_bar, text="Write New File JSON", command=_write_new_file).grid(row=1, column=5, padx=4)
    ttk.Button(control_bar, text="Apply Workflow Goal", command=_apply_workflow_goal).grid(row=3, column=2, padx=4, sticky="w")

    ttk.Button(preview_frame, text="Play", command=_play_selected).grid(row=0, column=4, padx=6, pady=6)
    ttk.Button(preview_frame, text="Stop", command=_stop_selected).grid(row=0, column=5, padx=6, pady=6)

    category_box.bind("<<ComboboxSelected>>", _refresh_preview_files)
    _refresh_preview_files(select_category="Music")

    def _on_close() -> None:
        _stop_playback()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    for tab in (music_tab, sfx_tab, voice_tab):
        tab.columnconfigure(1, weight=1)

    root.mainloop()
