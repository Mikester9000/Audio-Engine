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
from audio_engine.ai.sfx_gen import SFXGen
from audio_engine.ai.sfx_synth import available_sfx_types
from audio_engine.ai.voice_gen import VoiceGen
from audio_engine.ai.voice_synth import VOICE_PRESETS
from audio_engine.render.offline_bounce import VALID_PROFILES
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
) -> dict[str, list[Path]]:
    catalog: dict[str, list[Path]] = {
        "Music": [],
        "SFX": [],
        "Vocal": [],
        "Examples": [],
    }
    if music_output.exists():
        catalog["Music"].append(music_output)
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


_SYNTH_WAVEFORMS = ["sine", "square", "sawtooth", "triangle", "noise", "bl_sawtooth", "bl_square"]
_SYNTH_FILTER_TYPES = ["none", "lowpass", "highpass", "bandpass"]


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


def launch_studio() -> None:
    import tkinter as tk
    from tkinter import filedialog, ttk

    root = tk.Tk()
    root.title("Audio Engine Studio")
    root.geometry("980x720")
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
    global_status = ttk.Label(control_bar, text="")
    global_status.grid(row=4, column=0, columnspan=12, sticky="w", padx=4, pady=(4, 0))
    control_bar.columnconfigure(1, weight=1)
    control_bar.columnconfigure(7, weight=1)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    music_tab = ttk.Frame(notebook)
    sfx_tab = ttk.Frame(notebook)
    voice_tab = ttk.Frame(notebook)
    synth_tab = ttk.Frame(notebook)
    notebook.add(music_tab, text="Music")
    notebook.add(sfx_tab, text="SFX")
    notebook.add(voice_tab, text="Voice")
    notebook.add(synth_tab, text="Synth Workbench")

    # Music tab
    ttk.Label(music_tab, text="Style").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    music_style = tk.StringVar(value="battle")
    style_box = ttk.Combobox(music_tab, textvariable=music_style, values=MusicGenerator.available_styles(), state="readonly")
    style_box.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

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
    music_status.grid(row=20, column=0, columnspan=2, sticky="w", padx=8, pady=8)

    def _refresh_bpm(*_args: object) -> None:
        style = music_style.get()
        bpm_var.set(str(int(style_metadata.get(style, style_metadata["battle"])["bpm"])))

    style_box.bind("<<ComboboxSelected>>", _refresh_bpm)

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

    ttk.Button(music_tab, text="Generate", command=_generate_music).grid(row=19, column=0, columnspan=2, pady=8)

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

    ttk.Label(sfx_tab, text="Pitch override (Hz)").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    sfx_pitch = tk.StringVar(value="")
    ttk.Entry(sfx_tab, textvariable=sfx_pitch).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Seed").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    sfx_seed = tk.StringVar(value="0")
    ttk.Entry(sfx_tab, textvariable=sfx_seed).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Output path").grid(row=5, column=0, sticky="w", padx=8, pady=6)
    sfx_out = tk.StringVar(value="sfx.wav")
    ttk.Entry(sfx_tab, textvariable=sfx_out).grid(row=5, column=1, sticky="ew", padx=8, pady=6)

    sfx_status = ttk.Label(sfx_tab, text="")
    sfx_status.grid(row=7, column=0, columnspan=2, sticky="w", padx=8, pady=8)

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

    ttk.Button(sfx_tab, text="Generate", command=_generate_sfx).grid(row=6, column=0, columnspan=2, pady=8)

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

    ttk.Label(voice_tab, text="Seed").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    voice_seed = tk.StringVar(value="0")
    ttk.Entry(voice_tab, textvariable=voice_seed).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Output path").grid(row=5, column=0, sticky="w", padx=8, pady=6)
    voice_out = tk.StringVar(value="voice.wav")
    ttk.Entry(voice_tab, textvariable=voice_out).grid(row=5, column=1, sticky="ew", padx=8, pady=6)

    voice_status = ttk.Label(voice_tab, text="")
    voice_status.grid(row=7, column=0, columnspan=2, sticky="w", padx=8, pady=8)

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

    ttk.Button(voice_tab, text="Generate", command=_generate_voice).grid(row=6, column=0, columnspan=2, pady=8)

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

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=2, sticky="ew", padx=8, pady=4)
    ttk.Label(synth_tab, text="— ADSR Envelope —", font=("TkDefaultFont", 9, "bold")).grid(row=_sw_counter[0] - 1, column=0, columnspan=2, pady=2)

    ttk.Label(synth_tab, text="Attack (s)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_attack = tk.DoubleVar(value=0.01)
    ttk.Scale(synth_tab, from_=0.0, to=2.0, variable=synth_attack, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Decay (s)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_decay = tk.DoubleVar(value=0.1)
    ttk.Scale(synth_tab, from_=0.0, to=2.0, variable=synth_decay, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Sustain (0–1)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_sustain = tk.DoubleVar(value=0.7)
    ttk.Scale(synth_tab, from_=0.0, to=1.0, variable=synth_sustain, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Release (s)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_release = tk.DoubleVar(value=0.3)
    ttk.Scale(synth_tab, from_=0.0, to=2.0, variable=synth_release, orient="horizontal").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=2, sticky="ew", padx=8, pady=4)
    ttk.Label(synth_tab, text="— Filter —", font=("TkDefaultFont", 9, "bold")).grid(row=_sw_counter[0] - 1, column=0, columnspan=2, pady=2)

    ttk.Label(synth_tab, text="Filter type").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_filter_type = tk.StringVar(value="none")
    ttk.Combobox(synth_tab, textvariable=synth_filter_type, values=_SYNTH_FILTER_TYPES, state="readonly").grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(synth_tab, text="Cutoff (Hz)").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_cutoff = tk.StringVar(value="2000.0")
    ttk.Entry(synth_tab, textvariable=synth_cutoff).grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Separator(synth_tab, orient="horizontal").grid(row=_sw_row(), column=0, columnspan=2, sticky="ew", padx=8, pady=4)

    ttk.Label(synth_tab, text="Output path").grid(row=_sw_row(), column=0, sticky="w", padx=8, pady=6)
    synth_out = tk.StringVar(value="synth_patch.wav")
    ttk.Entry(synth_tab, textvariable=synth_out).grid(row=_sw_counter[0] - 1, column=1, sticky="ew", padx=8, pady=6)

    synth_status = ttk.Label(synth_tab, text="")
    synth_status.grid(row=_sw_row(), column=0, columnspan=2, sticky="w", padx=8, pady=8)

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
        audio = _build_synth_patch(
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

    def _build_current_preset() -> dict[str, object]:
        return {
            "studio": {
                "examplesRoot": examples_root.get(),
                "sampleRoot": sample_root.get(),
                "sampleBaseBackend": sample_base_backend.get(),
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

    def _refresh_preview_files(*_args: object, select_category: str | None = None) -> None:
        nonlocal preview_catalog
        preview_catalog = _build_preview_catalog(
            music_output=Path(music_out.get()),
            sfx_output=Path(sfx_out.get()),
            voice_output=Path(voice_out.get()),
            examples_root=Path(examples_root.get()),
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
