"""
Deterministic remaster pipeline with sample substitution and synth fallback.
"""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from audio_engine.ai.sample_backend import SampleBackend
from audio_engine.dsp import pitch_shift_ratio, resample
from audio_engine.export.audio_exporter import AudioExporter
from audio_engine.integration.sample_library import OrchestralSampleLibrary

__all__ = ["RemasterEvent", "RemasterPipeline"]


@dataclass(frozen=True)
class RemasterEvent:
    """A single note event used for sample substitution."""

    instrument: str
    note: str
    start_seconds: float
    duration_seconds: float
    velocity: float = 1.0


class RemasterPipeline:
    """Remaster mono/stereo WAV content using deterministic sample overlays."""

    def __init__(
        self,
        sample_rate: int = 44100,
        seed: int | None = None,
        base_backend: str = "synth_orchestral",
    ) -> None:
        self.sample_rate = sample_rate
        self.seed = seed
        self.base_backend = base_backend

    def remaster(
        self,
        audio: np.ndarray,
        *,
        style: str = "ff7_overworld",
        samples_dir: str | Path = "samples/",
        events: list[RemasterEvent] | None = None,
    ) -> np.ndarray:
        """Remaster an audio array with sample overlays and synth fallback."""
        samples_root = Path(samples_dir)
        backend = SampleBackend(
            samples_dir=samples_root,
            sample_rate=self.sample_rate,
            seed=self.seed,
            base_backend=self.base_backend,
        )

        duration = (audio.shape[0] if audio.ndim == 2 else len(audio)) / float(self.sample_rate)
        base = backend.remaster_audio(audio, style=style, duration=duration).astype(np.float32)

        if not events:
            return base

        orchestral_root = samples_root / "orchestral"
        if not orchestral_root.exists():
            orchestral_root = samples_root
        scanner = OrchestralSampleLibrary(orchestral_root)
        if not scanner.available_instruments():
            return base

        mono = base.mean(axis=1) if base.ndim == 2 else base.copy()
        overlay = np.zeros_like(mono, dtype=np.float32)

        for event in events:
            if event.duration_seconds <= 0.0 or event.start_seconds < 0.0:
                continue
            match = scanner.resolve_nearest(event.instrument, event.note)
            if match is None:
                continue
            sample = self._load_wav_mono(match.source.path, target_sr=self.sample_rate)
            if sample.size == 0:
                continue
            shifted = pitch_shift_ratio(sample, match.pitch_ratio)
            target_n = max(1, int(event.duration_seconds * self.sample_rate))
            if shifted.size < target_n:
                reps = target_n // shifted.size + 1
                shifted = np.tile(shifted, reps)
            segment = shifted[:target_n] * float(np.clip(event.velocity, 0.0, 1.5))
            start = int(event.start_seconds * self.sample_rate)
            if start >= len(overlay):
                continue
            end = min(len(overlay), start + len(segment))
            overlay[start:end] += segment[: end - start]

        if not np.any(np.abs(overlay) > 0.0):
            return base

        combined = (0.8 * mono + 0.2 * overlay).astype(np.float32)
        peak = float(np.max(np.abs(combined))) if combined.size else 0.0
        if peak > 1.0:
            combined = combined / peak

        if base.ndim == 2:
            return np.column_stack([combined, combined]).astype(np.float32)
        return combined.astype(np.float32)

    def remaster_file(
        self,
        input_path: str | Path,
        output_path: str | Path,
        *,
        style: str = "ff7_overworld",
        samples_dir: str | Path = "samples/",
        events_json: str | Path | None = None,
        fmt: str = "wav",
    ) -> Path:
        """Load an input WAV, remaster it, and export to disk."""
        audio, sr = self._load_wav_any(input_path)
        events = self._load_events(events_json) if events_json else []
        previous_sr = self.sample_rate
        self.sample_rate = sr
        try:
            remastered = self.remaster(
                audio,
                style=style,
                samples_dir=samples_dir,
                events=events,
            )
        finally:
            self.sample_rate = previous_sr
        exporter = AudioExporter(sample_rate=sr)
        return exporter.export(remastered, output_path, fmt=fmt)  # type: ignore[arg-type]

    @staticmethod
    def _load_events(events_json: str | Path) -> list[RemasterEvent]:
        path = Path(events_json)
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_events = payload.get("events", payload) if isinstance(payload, dict) else payload
        if not isinstance(raw_events, list):
            raise ValueError(f"events JSON must be a list or object with 'events': {path}")

        parsed: list[RemasterEvent] = []
        for entry in raw_events:
            if not isinstance(entry, dict):
                continue
            parsed.append(
                RemasterEvent(
                    instrument=str(entry.get("instrument", "")).strip(),
                    note=str(entry.get("note", "C4")).strip(),
                    start_seconds=float(entry.get("startSeconds", 0.0)),
                    duration_seconds=float(entry.get("durationSeconds", 0.0)),
                    velocity=float(entry.get("velocity", 1.0)),
                )
            )
        return parsed

    @staticmethod
    def _load_wav_mono(path: Path, *, target_sr: int) -> np.ndarray:
        audio, sr = RemasterPipeline._load_wav_any(path)
        mono = audio.mean(axis=1) if audio.ndim == 2 else audio
        if sr != target_sr:
            mono = resample(mono.astype(np.float32), orig_sr=sr, target_sr=target_sr)
        return mono.astype(np.float32)

    @staticmethod
    def _load_wav_any(path: str | Path) -> tuple[np.ndarray, int]:
        p = Path(path)
        with wave.open(str(p), "rb") as wf:
            n_channels = wf.getnchannels()
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            sampwidth = wf.getsampwidth()
            raw = wf.readframes(n_frames)

        if sampwidth == 1:
            arr = np.frombuffer(raw, dtype=np.int8).astype(np.float32) / 128.0
        elif sampwidth == 2:
            arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            arr = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0

        if n_channels > 1:
            arr = arr.reshape(-1, n_channels)
        return arr.astype(np.float32), sr
