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

            audio = None
            if hasattr(kokoro, "KPipeline"):
                pipeline_cls = kokoro.KPipeline
                try:
                    pipeline = pipeline_cls(model_path=str(self.model_path))
                except TypeError:
                    pipeline = pipeline_cls()
                output = pipeline(text=text, voice=voice_preset, speed=speed)
                audio = self._extract_audio(output)
            elif hasattr(kokoro, "generate"):
                output = kokoro.generate(
                    text=text,
                    voice=voice_preset,
                    speed=speed,
                    model_path=str(self.model_path),
                )
                audio = self._extract_audio(output)

            if audio is None:
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
            if output and isinstance(output[-1], np.ndarray):
                return output[-1]
            if output and hasattr(output[-1], "__array__"):
                return np.asarray(output[-1])
        if isinstance(output, dict):
            for key in ("audio", "wav", "waveform", "samples"):
                if key in output:
                    return np.asarray(output[key])
        if hasattr(output, "audio"):
            return np.asarray(output.audio)
        if hasattr(output, "wav"):
            return np.asarray(output.wav)
        if hasattr(output, "waveform"):
            return np.asarray(output.waveform)
        return None

    def _ensure_mono(self, audio: np.ndarray) -> np.ndarray:
        arr = np.asarray(audio, dtype=np.float32)
        if arr.ndim == 1:
            return arr
        if arr.ndim == 2:
            return np.mean(arr, axis=1 if arr.shape[1] <= 2 else 0).astype(np.float32)
        return arr.reshape(-1).astype(np.float32)
