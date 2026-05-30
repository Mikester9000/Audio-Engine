"""Kokoro backend for local voice generation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend
from audio_engine.ai.backends._paths import can_import_module, default_model_dir, has_complete_model_snapshot


class KokoroBackend(InferenceBackend):
    def __init__(
        self,
        model_path: str | Path | None = None,
        sample_rate: int = 22050,
        seed: int | None = None,
    ) -> None:
        super().__init__(sample_rate=sample_rate)
        default_path = default_model_dir("kokoro")
        self.model_path = Path(model_path) if model_path is not None else default_path
        self.seed = seed
        self._fallback = ProceduralBackend(sample_rate=sample_rate, seed=seed)

    @property
    def name(self) -> str:
        return "kokoro"

    def is_available(self) -> bool:
        return (
            can_import_module("kokoro")
            and has_complete_model_snapshot(self.model_path)
        )

    def dependency_summary(self) -> str:
        return (
            "Requires kokoro package and local model files at "
            f"{self.model_path}. Install with: pip install -e '.[neural]'"
        )

    def generate_music_audio(
        self,
        style: str,
        duration: float,
        bpm: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        return self._fallback.generate_music_audio(style=style, duration=duration, bpm=bpm, **kwargs)

    def generate_sfx_audio(
        self,
        sfx_type: str,
        duration: float,
        pitch_hz: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        return self._fallback.generate_sfx_audio(sfx_type=sfx_type, duration=duration, pitch_hz=pitch_hz, **kwargs)

    def generate_voice_audio(
        self,
        text: str,
        voice_preset: str = "narrator",
        speed: float = 1.0,
        **kwargs,
    ) -> np.ndarray:
        if not self.is_available():
            return self._fallback.generate_voice_audio(text=text, voice_preset=voice_preset, speed=speed, **kwargs)

        try:
            import kokoro

            os.environ.setdefault("KOKORO_MODEL_PATH", str(self.model_path))

            audio: np.ndarray | None = None
            output: Any = None

            if hasattr(kokoro, "generate"):
                output = kokoro.generate(
                    text=text,
                    voice=voice_preset,
                    speed=speed,
                    model_path=str(self.model_path),
                )
                audio = self._extract_audio(output)

            elif hasattr(kokoro, "KPipeline"):
                try:
                    pipeline = kokoro.KPipeline(model_path=str(self.model_path))
                except TypeError:
                    pipeline = kokoro.KPipeline()
                output = pipeline(text=text, voice=voice_preset, speed=speed)
                audio = self._extract_iterable_audio(output)
                if audio is None and output is not None:
                    audio = self._extract_audio(output)

            if audio is None:
                audio = self._extract_audio(output)

            if audio is None or audio.size == 0:
                return self._fallback.generate_voice_audio(text=text, voice_preset=voice_preset, speed=speed, **kwargs)

            return self._ensure_mono(audio)
        except Exception:
            return self._fallback.generate_voice_audio(text=text, voice_preset=voice_preset, speed=speed, **kwargs)

    def _extract_audio(self, output: Any) -> np.ndarray | None:
        if output is None:
            return None
        if isinstance(output, np.ndarray):
            return output
        if isinstance(output, (list, tuple)):
            for candidate in output:
                if isinstance(candidate, np.ndarray):
                    return candidate.astype(np.float32, copy=False)
                if hasattr(candidate, "__array__"):
                    arr = np.asarray(candidate, dtype=np.float32)
                    if arr.ndim >= 1 and arr.size > 1:
                        return arr
        if isinstance(output, dict):
            for key in ("audio", "wav", "waveform", "samples"):
                if key in output:
                    return np.asarray(output[key], dtype=np.float32)
        if hasattr(output, "audio"):
            return np.asarray(output.audio, dtype=np.float32)
        if hasattr(output, "wav"):
            return np.asarray(output.wav, dtype=np.float32)
        if hasattr(output, "waveform"):
            return np.asarray(output.waveform, dtype=np.float32)
        return None

    def _extract_iterable_audio(self, output: Any) -> np.ndarray | None:
        if isinstance(output, (str, bytes, dict, np.ndarray)):
            return None
        if not hasattr(output, "__iter__"):
            return None
        chunks: list[np.ndarray] = []
        for item in output:
            chunk = self._extract_audio(item)
            if chunk is not None and chunk.size > 0:
                chunks.append(chunk)
        if not chunks:
            return None
        return np.concatenate(chunks, axis=0).astype(np.float32)

    def _ensure_mono(self, audio: np.ndarray) -> np.ndarray:
        arr = np.asarray(audio, dtype=np.float32)
        if arr.ndim == 1:
            return arr
        if arr.ndim == 2:
            return np.mean(arr, axis=1 if arr.shape[1] <= 2 else 0).astype(np.float32)
        return arr.reshape(-1).astype(np.float32)
