"""AudioGen backend using local HuggingFace model files."""

from __future__ import annotations

from importlib import util as importlib_util
from pathlib import Path

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend


_SFX_PROMPTS: dict[str, str] = {
    "explosion": "large explosion with deep rumble and debris",
    "footstep": "single footstep on stone floor",
    "click": "short UI click sound",
    "beep": "clean electronic beep",
    "hit": "sharp combat hit impact",
    "impact": "hard impact thud with transient",
    "whoosh": "fast airy whoosh pass-by",
    "laser": "retro sci-fi laser shot",
    "coin": "coin pickup chime",
    "pickup": "item pickup jingle",
    "jump": "arcade jump sound",
    "magic": "magical spell cast sparkle",
    "spell": "magical spell cast sparkle",
    "fire": "burst of fire ignition",
    "water": "water splash",
    "wind": "gust of wind",
    "ping": "notification ping",
    "alert": "short alert ping",
}


class AudioGenBackend(InferenceBackend):
    def __init__(
        self,
        model_path: str | Path | None = None,
        sample_rate: int = 16000,
        seed: int | None = None,
    ) -> None:
        super().__init__(sample_rate=sample_rate)
        default_path = Path(__file__).resolve().parents[3] / "models" / "audiogen-medium"
        self.model_path = Path(model_path) if model_path is not None else default_path
        self.seed = seed
        self._fallback = ProceduralBackend(sample_rate=sample_rate, seed=seed)

    @property
    def name(self) -> str:
        return "audiogen"

    def is_available(self) -> bool:
        return (
            importlib_util.find_spec("torch") is not None
            and importlib_util.find_spec("transformers") is not None
            and self.model_path.exists()
            and self.model_path.is_dir()
        )

    def dependency_summary(self) -> str:
        return (
            "Requires torch + transformers and local model files at "
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
        if not self.is_available():
            return self._fallback.generate_sfx_audio(sfx_type=sfx_type, duration=duration, pitch_hz=pitch_hz, **kwargs)

        try:
            import torch
            from transformers import AutoModelForTextToWaveform, AutoProcessor

            model = AutoModelForTextToWaveform.from_pretrained(
                str(self.model_path),
                local_files_only=True,
            )
            processor = AutoProcessor.from_pretrained(
                str(self.model_path),
                local_files_only=True,
            )

            if self.seed is not None:
                torch.manual_seed(self.seed)

            prompt = _SFX_PROMPTS.get(sfx_type.lower(), f"game sound effect: {sfx_type}")
            inputs = processor(text=[prompt], padding=True, return_tensors="pt")
            frame_rate = getattr(getattr(model.config, "audio_encoder", None), "frame_rate", 50)
            max_new_tokens = max(1, int(duration * frame_rate))

            with torch.no_grad():
                generated = model.generate(**inputs, max_new_tokens=max_new_tokens)

            waveform = getattr(generated, "audio_values", generated)
            if hasattr(waveform, "detach"):
                waveform = waveform.detach().cpu().numpy()
            audio = np.asarray(waveform[0], dtype=np.float32)
            model_sample_rate = int(
                getattr(
                    getattr(model.config, "audio_encoder", None),
                    "sampling_rate",
                    self.sample_rate,
                )
            )
            if model_sample_rate != self.sample_rate:
                audio = self._resample(audio, source_rate=model_sample_rate, target_rate=self.sample_rate)
            return self._ensure_mono(audio, duration)
        except Exception:
            return self._fallback.generate_sfx_audio(sfx_type=sfx_type, duration=duration, pitch_hz=pitch_hz, **kwargs)

    def generate_voice_audio(
        self,
        text: str,
        voice_preset: str = "narrator",
        speed: float = 1.0,
        **kwargs,
    ) -> np.ndarray:
        return self._fallback.generate_voice_audio(text=text, voice_preset=voice_preset, speed=speed, **kwargs)

    def _ensure_mono(self, audio: np.ndarray, duration: float) -> np.ndarray:
        if audio.ndim == 1:
            mono = audio
        elif audio.ndim == 2:
            mono = np.mean(audio, axis=0 if audio.shape[0] <= 2 else 1)
        else:
            mono = audio.reshape(-1)

        target_samples = max(1, int(duration * self.sample_rate))
        if mono.shape[0] > target_samples:
            mono = mono[:target_samples]
        elif mono.shape[0] < target_samples:
            mono = np.pad(mono, (0, target_samples - mono.shape[0]))

        return mono.astype(np.float32, copy=False)

    def _resample(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        if source_rate == target_rate:
            return audio
        from scipy.signal import resample

        target_len = max(1, int(round(audio.shape[0] * target_rate / source_rate)))
        return resample(audio, target_len).astype(np.float32)
