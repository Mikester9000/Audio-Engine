"""Tkinter studio for interactive local generation."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Protocol

from audio_engine.ai.backend import BackendRegistry
from audio_engine.ai.generator import MusicGenerator
from audio_engine.ai.sfx_gen import SFXGen
from audio_engine.ai.sfx_synth import available_sfx_types
from audio_engine.ai.voice_gen import VoiceGen
from audio_engine.ai.voice_synth import VOICE_PRESETS
from audio_engine.render.offline_bounce import VALID_PROFILES

_DEFAULT_SAMPLE_ROOT = "samples"
_FALLBACK_STUDIO_BACKENDS = ["procedural", "sample"]


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


def _set_status(label: _StatusLabel, text: str) -> None:
    label.configure(text=text)
    label.update_idletasks()


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
    examples_root = tk.StringVar(value="assets/examples")
    sample_root = tk.StringVar(value=_DEFAULT_SAMPLE_ROOT)
    sample_base_backend = tk.StringVar(value="synth_orchestral")
    ttk.Label(control_bar, text="Preset file").grid(row=0, column=0, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=preset_path).grid(row=0, column=1, sticky="ew", padx=4)
    ttk.Label(control_bar, text="Examples WAV root").grid(row=1, column=0, sticky="w", padx=4)
    ttk.Entry(control_bar, textvariable=examples_root).grid(row=1, column=1, sticky="ew", padx=4)
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

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    music_tab = ttk.Frame(notebook)
    sfx_tab = ttk.Frame(notebook)
    voice_tab = ttk.Frame(notebook)
    notebook.add(music_tab, text="Music")
    notebook.add(sfx_tab, text="SFX")
    notebook.add(voice_tab, text="Voice")

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

    music_status = ttk.Label(music_tab, text="")
    music_status.grid(row=8, column=0, columnspan=2, sticky="w", padx=8, pady=8)

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
        prompt = style
        out_path = Path(music_out.get())
        out_path.parent.mkdir(parents=True, exist_ok=True)
        from audio_engine.ai.music_gen import MusicGen
        return MusicGen(
            sample_rate=44100,
            backend=_resolve_backend(
                backend_name=music_backend.get(),
                sample_rate=44100,
                seed=seed,
                samples_dir=sample_root.get().strip(),
                sample_base_backend=sample_base_backend.get(),
            ),
            seed=seed,
            mastering_profile=music_profile.get(),
        ).generate_to_file(
            prompt=prompt,
            output_path=out_path,
            duration=duration,
            loopable=True,
            fmt="wav",
        )

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

    ttk.Button(music_tab, text="Generate", command=_generate_music).grid(row=7, column=0, columnspan=2, pady=8)

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

    def _build_current_preset() -> dict[str, object]:
        return {
            "studio": {
                "examplesRoot": examples_root.get(),
                "sampleRoot": sample_root.get(),
                "sampleBaseBackend": sample_base_backend.get(),
            },
            "music": {
                "style": music_style.get(),
                "backend": music_backend.get(),
                "profile": music_profile.get(),
                "bars": int(max(4, _safe_int(str(bars_var.get()), 16))),
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
            music = data.get("music", {})
            if isinstance(music, dict):
                style_value = str(music.get("style", music_style.get()))
                if style_value in MusicGenerator.available_styles():
                    music_style.set(style_value)
                    _refresh_bpm()
                backend_value = str(music.get("backend", music_backend.get()))
                if backend_value in _available_backends_for_modality("music", sample_rate=44100):
                    music_backend.set(backend_value)
                profile_value = str(music.get("profile", music_profile.get()))
                if profile_value in VALID_PROFILES:
                    music_profile.set(profile_value)
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
