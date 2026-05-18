"""Tkinter studio for interactive local generation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from audio_engine.ai.generator import MusicGenerator
from audio_engine.ai.sfx_gen import SFXGen
from audio_engine.ai.sfx_synth import available_sfx_types
from audio_engine.ai.voice_gen import VoiceGen
from audio_engine.ai.voice_synth import VOICE_PRESETS


class _StatusLabel(Protocol):
    def configure(self, **kwargs: object) -> object: ...
    def update_idletasks(self) -> object: ...


def _safe_int(value: str, fallback: int) -> int:
    try:
        return int(value.strip())
    except Exception:
        return fallback


def _set_status(label: _StatusLabel, text: str) -> None:
    label.configure(text=text)
    label.update_idletasks()


def launch_studio() -> None:
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Audio Engine Studio")
    root.geometry("760x520")
    style_metadata = MusicGenerator.available_style_metadata()

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

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

    ttk.Label(music_tab, text="BPM").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    bpm_var = tk.StringVar(value=str(int(style_metadata[music_style.get()]["bpm"])))
    bpm_label = ttk.Label(music_tab, textvariable=bpm_var)
    bpm_label.grid(row=1, column=1, sticky="w", padx=8, pady=6)

    ttk.Label(music_tab, text="Bars").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    bars_var = tk.IntVar(value=16)
    bars_spin = ttk.Spinbox(music_tab, from_=4, to=128, textvariable=bars_var)
    bars_spin.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Seed").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    music_seed = tk.StringVar(value="0")
    ttk.Entry(music_tab, textvariable=music_seed).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(music_tab, text="Output path").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    music_out = tk.StringVar(value="music.wav")
    ttk.Entry(music_tab, textvariable=music_out).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    music_status = ttk.Label(music_tab, text="")
    music_status.grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=8)

    def _refresh_bpm(*_args: object) -> None:
        style = music_style.get()
        bpm_var.set(str(int(style_metadata.get(style, style_metadata["battle"])["bpm"])))

    style_box.bind("<<ComboboxSelected>>", _refresh_bpm)

    def _generate_music() -> None:
        try:
            seed = _safe_int(music_seed.get(), 0)
            style = music_style.get()
            bars = max(4, _safe_int(str(bars_var.get()), 16))
            bpm = max(40, _safe_int(bpm_var.get(), 120))
            duration = bars * (60.0 / bpm) * 4.0
            prompt = style
            out_path = Path(music_out.get())
            out_path.parent.mkdir(parents=True, exist_ok=True)
            _set_status(music_status, "Generating music...")
            from audio_engine.ai.music_gen import MusicGen
            MusicGen(sample_rate=44100, backend="procedural", seed=seed).generate_to_file(
                prompt=prompt,
                output_path=out_path,
                duration=duration,
                loopable=True,
                fmt="wav",
            )
            _set_status(music_status, f"Done — saved to {out_path}")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(music_status, f"Error: {exc}")

    ttk.Button(music_tab, text="Generate", command=_generate_music).grid(row=5, column=0, columnspan=2, pady=8)

    # SFX tab
    ttk.Label(sfx_tab, text="Category").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    sfx_type = tk.StringVar(value="explosion")
    ttk.Combobox(sfx_tab, textvariable=sfx_type, values=available_sfx_types(), state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Duration (s)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    sfx_duration = tk.DoubleVar(value=0.8)
    ttk.Scale(sfx_tab, from_=0.05, to=4.0, variable=sfx_duration, orient="horizontal").grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Pitch override (Hz)").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    sfx_pitch = tk.StringVar(value="")
    ttk.Entry(sfx_tab, textvariable=sfx_pitch).grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Seed").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    sfx_seed = tk.StringVar(value="0")
    ttk.Entry(sfx_tab, textvariable=sfx_seed).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(sfx_tab, text="Output path").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    sfx_out = tk.StringVar(value="sfx.wav")
    ttk.Entry(sfx_tab, textvariable=sfx_out).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    sfx_status = ttk.Label(sfx_tab, text="")
    sfx_status.grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=8)

    def _generate_sfx() -> None:
        try:
            seed = _safe_int(sfx_seed.get(), 0)
            pitch = None if not sfx_pitch.get().strip() else float(sfx_pitch.get())
            out_path = Path(sfx_out.get())
            out_path.parent.mkdir(parents=True, exist_ok=True)
            _set_status(sfx_status, "Generating SFX...")
            SFXGen(sample_rate=44100, backend="procedural", seed=seed).generate_to_file(
                prompt=sfx_type.get(),
                output_path=out_path,
                duration=float(sfx_duration.get()),
                pitch_hz=pitch,
            )
            _set_status(sfx_status, f"Done — saved to {out_path}")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(sfx_status, f"Error: {exc}")

    ttk.Button(sfx_tab, text="Generate", command=_generate_sfx).grid(row=5, column=0, columnspan=2, pady=8)

    # Voice tab
    ttk.Label(voice_tab, text="Text").grid(row=0, column=0, sticky="nw", padx=8, pady=6)
    voice_text = tk.Text(voice_tab, width=60, height=8)
    voice_text.insert("1.0", "The hero must find the crystal.")
    voice_text.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Preset").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    voice_preset = tk.StringVar(value="narrator")
    ttk.Combobox(voice_tab, textvariable=voice_preset, values=sorted(VOICE_PRESETS), state="readonly").grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Speed").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    voice_speed = tk.DoubleVar(value=1.0)
    ttk.Scale(voice_tab, from_=0.6, to=2.0, variable=voice_speed, orient="horizontal").grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Seed").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    voice_seed = tk.StringVar(value="0")
    ttk.Entry(voice_tab, textvariable=voice_seed).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    ttk.Label(voice_tab, text="Output path").grid(row=4, column=0, sticky="w", padx=8, pady=6)
    voice_out = tk.StringVar(value="voice.wav")
    ttk.Entry(voice_tab, textvariable=voice_out).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    voice_status = ttk.Label(voice_tab, text="")
    voice_status.grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=8)

    def _generate_voice() -> None:
        try:
            seed = _safe_int(voice_seed.get(), 0)
            text = voice_text.get("1.0", "end").strip()
            out_path = Path(voice_out.get())
            out_path.parent.mkdir(parents=True, exist_ok=True)
            _set_status(voice_status, "Generating voice...")
            VoiceGen(sample_rate=22050, backend="procedural", seed=seed).generate_to_file(
                text=text,
                output_path=out_path,
                voice=voice_preset.get(),
                speed=float(voice_speed.get()),
            )
            _set_status(voice_status, f"Done — saved to {out_path}")
        except Exception as exc:  # pragma: no cover - UI path
            _set_status(voice_status, f"Error: {exc}")

    ttk.Button(voice_tab, text="Generate", command=_generate_voice).grid(row=5, column=0, columnspan=2, pady=8)

    for tab in (music_tab, sfx_tab, voice_tab):
        tab.columnconfigure(1, weight=1)

    root.mainloop()
