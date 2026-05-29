"""MusicGen backend using local HuggingFace model files."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend
from audio_engine.ai.backends._paths import (
    DEFAULT_AUDIO_FRAME_RATE,
    can_import_module,
    default_model_dir,
    has_complete_model_snapshot,
)


_STYLE_PROMPTS: dict[str, str] = {
    "battle": "epic orchestral battle theme, strings and brass, fast tempo, dramatic, Final Fantasy style",
    "boss": "intense boss battle theme, heavy brass and strings, Phrygian mode, climactic, Final Fantasy style",
    "exploration": "peaceful field exploration theme, piano and flute, JRPG, warm and adventurous",
    "field": "peaceful field exploration theme, piano and flute, JRPG, warm and adventurous",
    "title": "grand orchestral title screen theme, sweeping strings and choir, cinematic JRPG opening",
    "town": "warm and cheerful town theme, acoustic guitar and light orchestra, JRPG village, welcoming",
    "shop": "upbeat shop theme, pizzicato strings and flute, JRPG, lighthearted",
    "inn": "peaceful inn theme, soft piano and acoustic guitar, restful, warm, JRPG",
    "overworld": "epic overworld theme, full orchestra, adventurous, sweeping, Final Fantasy style",
    "dungeon": "dark dungeon theme, low strings and ominous brass, tense, atmospheric, minor key",
    "tension": "tense stealth music, sparse strings, quiet percussion, uneasy, JRPG",
    "sadness": "emotional piano melody, melancholic strings, bittersweet, JRPG emotional scene",
    "ending": "grand orchestral ending theme, full choir and orchestra, emotional resolution, epic",
    "credits": "gentle credits theme, piano and strings, reflective, warm, JRPG",
    "general_orchestral": "professional orchestral composition, full symphony orchestra, cinematic, broadcast quality",
    "general_piano": "solo piano composition, expressive, professional, suitable for streaming and YouTube",
    "general_ambient": "ambient atmospheric music, layered pads and gentle melody, relaxing, suitable for YouTube",
    "general_cinematic": "cinematic orchestral music, epic build, emotional arc, suitable for film and YouTube",
    "ambient": "atmospheric ambient music, slow, ethereal pads, mysterious",
    "menu": "calm main menu theme, piano and strings, JRPG, introspective",
    "victory": "triumphant victory fanfare, brass and strings, major key, celebratory",
}
_MAX_CHUNK_DURATION_SECONDS = 30.0
_MIN_CHUNK_DURATION_SECONDS = 0.1
_STITCH_CROSSFADE_SECONDS = 1.0

# Human-readable labels for each supported model size
MUSICGEN_MODEL_SIZES: dict[str, str] = {
    "small": "musicgen-small",
    "medium": "musicgen-medium",
}


class MusicGenBackend(InferenceBackend):
    """MusicGen backend.  Defaults to the medium model; pass model_size='small' for the
    lighter 300 M-parameter variant which requires less VRAM and loads faster."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        sample_rate: int = 32000,
        seed: int | None = None,
        model_size: str = "medium",
    ) -> None:
        super().__init__(sample_rate=sample_rate)
        self.model_size = model_size if model_size in MUSICGEN_MODEL_SIZES else "medium"
        folder = MUSICGEN_MODEL_SIZES[self.model_size]
        default_path = default_model_dir(folder)
        self.model_path = Path(model_path) if model_path is not None else default_path
        self.seed = seed
        self._fallback = ProceduralBackend(sample_rate=sample_rate, seed=seed)
        self._model_bundle = None

    @property
    def name(self) -> str:
        return "musicgen" if self.model_size == "medium" else f"musicgen-{self.model_size}"

    def is_available(self) -> bool:
        return (
            can_import_module("torch")
            and can_import_module("transformers")
            and has_complete_model_snapshot(self.model_path)
        )

    def dependency_summary(self) -> str:
        folder = MUSICGEN_MODEL_SIZES[self.model_size]
        return (
            f"Requires torch + transformers and local model files at "
            f"{self.model_path} ({folder}). Install with: pip install -e '.[neural]'"
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

            model, processor = self._load_model_bundle()
            config = getattr(model, "config", None)
            audio_encoder = config.audio_encoder if config is not None else None
            frame_rate = audio_encoder.frame_rate if audio_encoder is not None else DEFAULT_AUDIO_FRAME_RATE
            model_sample_rate = int(audio_encoder.sampling_rate) if audio_encoder is not None else self.sample_rate

            text_prompt = _STYLE_PROMPTS.get(style.lower(), f"JRPG game music, {style}")
            if bpm:
                text_prompt = f"{text_prompt}, {int(bpm)} BPM"

            chunk_duration = _MAX_CHUNK_DURATION_SECONDS
            chunk_count = max(1, int(np.ceil(duration / chunk_duration)))
            chunk_lengths = [chunk_duration] * chunk_count
            chunk_lengths[-1] = max(
                _MIN_CHUNK_DURATION_SECONDS,
                duration - (chunk_duration * (chunk_count - 1)),
            )
            chunk_generation_lengths = chunk_lengths.copy()
            if chunk_count > 1:
                for idx in range(1, chunk_count):
                    chunk_generation_lengths[idx] += _STITCH_CROSSFADE_SECONDS

            chunks: list[np.ndarray] = []
            for idx, chunk_len in enumerate(chunk_generation_lengths):
                if self.seed is not None:
                    # Keep deterministic per-chunk output while avoiding identical chunks.
                    torch.manual_seed(self.seed + idx)

                inputs = processor(text=[text_prompt], padding=True, return_tensors="pt")
                max_new_tokens = max(1, int(chunk_len * frame_rate))
                with torch.no_grad():
                    generated = model.generate(**inputs, max_new_tokens=max_new_tokens)

                waveform = getattr(generated, "audio_values", generated)
                if hasattr(waveform, "detach"):
                    waveform = waveform.detach().cpu().numpy()
                audio = np.asarray(waveform[0], dtype=np.float32)
                if model_sample_rate != self.sample_rate:
                    audio = self._resample(audio, source_rate=model_sample_rate, target_rate=self.sample_rate)
                chunks.append(self._ensure_stereo(audio, chunk_len))

            stitched = chunks[0] if len(chunks) == 1 else self._crossfade_stitch(chunks, int(self.sample_rate))
            return self._ensure_stereo(stitched, duration)
        except Exception:
            return self._fallback.generate_music_audio(style=style, duration=duration, bpm=bpm, **kwargs)

    def _load_model_bundle(self):
        if self._model_bundle is None:
            from transformers import AutoProcessor, MusicgenForConditionalGeneration

            model = MusicgenForConditionalGeneration.from_pretrained(
                str(self.model_path),
                local_files_only=True,
            )
            processor = AutoProcessor.from_pretrained(
                str(self.model_path),
                local_files_only=True,
            )
            self._model_bundle = (model, processor)
        return self._model_bundle

    def generate_sfx_audio(
        self,
        sfx_type: str,
        duration: float,
        pitch_hz: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        fallback_kwargs = dict(kwargs)
        fallback_kwargs.setdefault("prompt", sfx_type)
        return self._fallback.generate_sfx_audio(
            sfx_type=sfx_type,
            duration=duration,
            pitch_hz=pitch_hz,
            **fallback_kwargs,
        )

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

    def _crossfade_stitch(self, chunks: list[np.ndarray], crossfade_samples: int) -> np.ndarray:
        stitched = chunks[0].astype(np.float32, copy=True)
        for chunk in chunks[1:]:
            if stitched.size == 0:
                stitched = chunk.astype(np.float32, copy=True)
                continue
            if chunk.size == 0:
                continue

            fade_len = min(crossfade_samples, stitched.shape[0], chunk.shape[0])
            if fade_len <= 0:
                stitched = np.vstack([stitched, chunk])
                continue

            fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)[:, None]
            fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)[:, None]
            cross = stitched[-fade_len:] * fade_out + chunk[:fade_len] * fade_in
            stitched = np.vstack([stitched[:-fade_len], cross, chunk[fade_len:]])

        return stitched.astype(np.float32, copy=False)


class MusicGenSmallBackend(MusicGenBackend):
    """Convenience subclass pre-configured for the MusicGen Small (300 M) model.

    Uses ``models/musicgen-small/`` by default.  Registered as the ``musicgen-small``
    backend, providing a lighter alternative to the default MusicGen Medium backend
    with faster load times and lower VRAM requirements.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        sample_rate: int = 32000,
        seed: int | None = None,
    ) -> None:
        super().__init__(model_path=model_path, sample_rate=sample_rate, seed=seed, model_size="small")
