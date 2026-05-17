"""MusicGen backend using local HuggingFace model files."""

from __future__ import annotations

from importlib import util as importlib_util
from pathlib import Path

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend
from audio_engine.ai.backends._paths import default_model_dir


_STYLE_PROMPTS: dict[str, str] = {
    "battle": "epic orchestral battle theme, strings and brass, fast tempo, dramatic, Final Fantasy style",
    "boss": "intense boss battle theme, heavy brass and strings, Phrygian mode, climactic, Final Fantasy style",
    "exploration": "peaceful field exploration theme, piano and flute, JRPG, warm and adventurous",
    "field": "peaceful field exploration theme, piano and flute, JRPG, warm and adventurous",
    "town": "cheerful town theme, light orchestra, JRPG, welcoming",
    "dungeon": "dark dungeon ambience, low strings and drones, mysterious and tense",
    "ambient": "atmospheric ambient music, slow, ethereal pads, mysterious",
    "menu": "calm main menu theme, piano and strings, JRPG, introspective",
    "victory": "triumphant victory fanfare, brass and strings, major key, celebratory",
}


class MusicGenBackend(InferenceBackend):
    def __init__(
        self,
        model_path: str | Path | None = None,
        sample_rate: int = 32000,
        seed: int | None = None,
    ) -> None:
        super().__init__(sample_rate=sample_rate)
        default_path = default_model_dir("musicgen-small")
        self.model_path = Path(model_path) if model_path is not None else default_path
        self.seed = seed
        self._fallback = ProceduralBackend(sample_rate=sample_rate, seed=seed)

    @property
    def name(self) -> str:
        return "musicgen"

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
        if not self.is_available():
            return self._fallback.generate_music_audio(style=style, duration=duration, bpm=bpm, **kwargs)

        try:
            import torch
            from transformers import AutoProcessor, MusicgenForConditionalGeneration

            model = MusicgenForConditionalGeneration.from_pretrained(
                str(self.model_path),
                local_files_only=True,
            )
            processor = AutoProcessor.from_pretrained(
                str(self.model_path),
                local_files_only=True,
            )

            if self.seed is not None:
                torch.manual_seed(self.seed)

            text_prompt = _STYLE_PROMPTS.get(style.lower(), f"JRPG game music, {style}")
            if bpm:
                text_prompt = f"{text_prompt}, {int(bpm)} BPM"

            inputs = processor(text=[text_prompt], padding=True, return_tensors="pt")
            config = getattr(model, "config", None)
            audio_encoder = getattr(config, "audio_encoder", None)
            frame_rate = getattr(audio_encoder, "frame_rate", 50)
            max_new_tokens = max(1, int(duration * frame_rate))

            with torch.no_grad():
                generated = model.generate(**inputs, max_new_tokens=max_new_tokens)

            waveform = getattr(generated, "audio_values", generated)
            if hasattr(waveform, "detach"):
                waveform = waveform.detach().cpu().numpy()
            audio = np.asarray(waveform[0], dtype=np.float32)
            model_sample_rate = int(getattr(audio_encoder, "sampling_rate", self.sample_rate))
            if model_sample_rate != self.sample_rate:
                audio = self._resample(audio, source_rate=model_sample_rate, target_rate=self.sample_rate)
            return self._ensure_stereo(audio, duration)
        except Exception:
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
        return self._fallback.generate_voice_audio(text=text, voice_preset=voice_preset, speed=speed, **kwargs)

    def _ensure_stereo(self, audio: np.ndarray, duration: float) -> np.ndarray:
        if audio.ndim == 1:
            stereo = np.stack([audio, audio], axis=1)
        elif audio.ndim == 2 and audio.shape[0] == 2 and audio.shape[1] != 2:
            stereo = audio.T
        elif audio.ndim == 2 and audio.shape[1] == 2:
            stereo = audio
        else:
            flat = audio.reshape(-1)
            stereo = np.stack([flat, flat], axis=1)

        target_samples = max(1, int(duration * self.sample_rate))
        if stereo.shape[0] > target_samples:
            stereo = stereo[:target_samples]
        elif stereo.shape[0] < target_samples:
            pad = np.zeros((target_samples - stereo.shape[0], 2), dtype=np.float32)
            stereo = np.vstack([stereo, pad])

        return stereo.astype(np.float32, copy=False)

    def _resample(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        if source_rate == target_rate:
            return audio
        from scipy.signal import resample

        target_len = max(1, int(round(audio.shape[0] * target_rate / source_rate)))
        return resample(audio, target_len).astype(np.float32)
