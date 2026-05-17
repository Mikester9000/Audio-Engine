"""
Sample-based remaster backend.

Combines real orchestral `.wav` samples from a user-supplied ``samples/``
directory with the synthesised output of a base backend (``synth_orchestral``
by default, or ``ps1`` for the degraded flavour).

Workflow
--------
1. User drops ``.wav`` files into category subdirectories under ``samples/``::

       samples/
       ├── strings/         (violin, cello sections)
       ├── brass/           (french horn, trumpet, trombone)
       ├── choir/           (vowel pads: "aah", "ooh")
       ├── piano/           (piano multi-samples)
       ├── flute/           (woodwind solo/ensemble)
       ├── electric_guitar/ (rhythm/lead guitar)
       ├── percussion/      (orchestral/studio drums)
       └── sfx/             (one-shot SFX samples)

2. Instantiate :class:`SampleBackend`::

       backend = SampleBackend(samples_dir="samples/", sample_rate=44100)

3. Generate audio — samples blend in automatically when available::

       audio = backend.generate_music_audio("ff7_overworld", duration=60.0)

4. For SFX: the sample library tries the ``sfx/`` category first; if no
   samples are found it falls back to the base backend's procedural SFX.

Blend weights
-------------
The mix ratio between synth and sample can be set per-category via
``category_blend_weights``.  Default is 0.65 sample / 0.35 synth, which
gives a noticeably richer sound while preserving the harmonic structure.

Remaster command integration
-----------------------------
:meth:`remaster_file` loads an existing WAV file and blends in samples on
top — this is what the ``audio-engine remaster`` CLI command calls.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend
from audio_engine.samples.sample_library import SampleLibrary

__all__ = ["SampleBackend"]

# Default per-style category blend map:  music style → (category, weight)
# Categories not present in the sample library are silently skipped.
_STYLE_CATEGORY_MAP: dict[str, list[tuple[str, float]]] = {
    "ff7_battle":    [("strings", 0.5), ("brass", 0.6), ("percussion", 0.4)],
    "ff7_overworld": [("strings", 0.6), ("flute", 0.5), ("choir", 0.4)],
    "ff7_boss":      [("brass", 0.6), ("strings", 0.5), ("choir", 0.5), ("electric_guitar", 0.4)],
    "ff7_sad":       [("piano", 0.65), ("strings", 0.55), ("choir", 0.45)],
    "ff7_town":      [("piano", 0.6), ("flute", 0.5), ("strings", 0.4)],
    "ff8_battle":    [("electric_guitar", 0.65), ("brass", 0.5), ("strings", 0.4)],
    "prelude":       [("piano", 0.6)],
    "world_map":     [("strings", 0.65), ("brass", 0.55), ("choir", 0.45)],
    "dungeon":       [("choir", 0.5), ("strings", 0.4)],
    "healing":       [("piano", 0.6), ("flute", 0.5)],
    "tension":       [("strings", 0.6), ("brass", 0.45)],
    # Legacy styles
    "battle":        [("strings", 0.5), ("brass", 0.5), ("percussion", 0.4)],
    "exploration":   [("strings", 0.55), ("flute", 0.45)],
    "ambient":       [("choir", 0.5), ("strings", 0.4)],
    "boss":          [("brass", 0.6), ("strings", 0.5), ("choir", 0.4)],
    "victory":       [("brass", 0.55), ("strings", 0.45)],
    "menu":          [("piano", 0.55), ("strings", 0.4)],
}


class SampleBackend(InferenceBackend):
    """Sample-augmented backend for orchestral remastering.

    Parameters
    ----------
    samples_dir:
        Path to the root samples directory (e.g. ``"samples/"``).
    sample_rate:
        Engine sample rate.
    seed:
        RNG seed for reproducibility.
    base_backend:
        Name of the backend to use for synthesis when samples are absent or
        for blending.  ``"synth_orchestral"`` (default) gives clean
        PS2-quality synthesis; ``"ps1"`` gives the bit-crushed flavour.
    default_blend_weight:
        Fallback blend weight (sample proportion) when a style has no
        specific entry in the category map.
    """

    def __init__(
        self,
        samples_dir: str | Path = "samples/",
        sample_rate: int = 44100,
        seed: int | None = None,
        base_backend: str = "synth_orchestral",
        default_blend_weight: float = 0.65,
    ) -> None:
        super().__init__(sample_rate)
        self._seed = seed
        self._default_weight = float(np.clip(default_blend_weight, 0.0, 1.0))
        self._lib = SampleLibrary(samples_dir, sample_rate=sample_rate)
        self._rng = np.random.default_rng(seed)

        # Build the base backend
        from audio_engine.ai.backend import BackendRegistry
        try:
            self._base: InferenceBackend = BackendRegistry.get(
                base_backend, sample_rate=sample_rate, seed=seed
            )
        except ValueError:
            self._base = ProceduralBackend(sample_rate=sample_rate, seed=seed)

    @property
    def name(self) -> str:
        return f"sample[{self._base.name}]"

    def available_sample_categories(self) -> list[str]:
        """Return sorted list of sample categories with at least one loaded sample."""
        return self._lib.available_categories()

    def dependency_summary(self) -> str:
        cats = self._lib.available_categories()
        if cats:
            return f"sample library ({len(cats)} categories: {', '.join(cats[:5])})"
        return "sample library (no samples loaded — falling back to base backend)"

    def is_available(self) -> bool:
        return True  # Always available; gracefully degrades without samples

    def supported_modalities(self) -> tuple[str, ...]:
        return ("music", "sfx", "voice")

    # ------------------------------------------------------------------
    # InferenceBackend implementation
    # ------------------------------------------------------------------

    def generate_music_audio(
        self,
        style: str,
        duration: float,
        bpm: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate music and blend in matching orchestral samples."""
        audio = self._base.generate_music_audio(style=style, duration=duration, bpm=bpm)

        if not self._lib.available_categories():
            return audio

        category_pairs = _STYLE_CATEGORY_MAP.get(style, [])
        if not category_pairs:
            # Generic blend: try any available orchestral categories
            generic = [("strings", 0.55), ("brass", 0.45), ("choir", 0.40), ("piano", 0.40)]
            category_pairs = [(c, w) for c, w in generic if self._lib.has_category(c)]

        return self._blend_into_audio(audio, category_pairs, duration)

    def generate_sfx_audio(
        self,
        sfx_type: str,
        duration: float,
        pitch_hz: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate SFX — uses ``sfx/`` samples if available, else base backend."""
        audio = self._base.generate_sfx_audio(
            sfx_type=sfx_type, duration=duration, pitch_hz=pitch_hz
        )
        if self._lib.has_category("sfx"):
            return self._lib.blend(
                audio, "sfx",
                sample_weight=self._default_weight,
                duration=duration,
                rng=self._rng,
            )
        return audio

    def generate_voice_audio(
        self,
        text: str,
        voice_preset: str = "narrator",
        speed: float = 1.0,
        **kwargs,
    ) -> np.ndarray:
        """Generate voice — delegates to base backend (voice samples not blended)."""
        return self._base.generate_voice_audio(text=text, voice_preset=voice_preset, speed=speed)

    # ------------------------------------------------------------------
    # Remaster API — usable directly or via the CLI 'remaster' command
    # ------------------------------------------------------------------

    def remaster_audio(
        self,
        audio: np.ndarray,
        style: str = "ff7_overworld",
        duration: float | None = None,
    ) -> np.ndarray:
        """Blend orchestral samples into an existing audio array.

        Parameters
        ----------
        audio:
            Input audio ``(N,)`` mono or ``(N, 2)`` stereo.
        style:
            Style hint used to select which sample categories to blend.
        duration:
            Audio duration override in seconds.

        Returns
        -------
        np.ndarray
            Remastered audio, same shape as input.
        """
        if not self._lib.available_categories():
            return audio

        stereo = audio.ndim == 2
        mono = audio.mean(axis=1) if stereo else audio.astype(np.float32)
        n = len(mono)
        dur = duration or n / self.sample_rate

        category_pairs = _STYLE_CATEGORY_MAP.get(style, [])
        blended = self._blend_mono(mono, category_pairs, dur)

        if stereo:
            return np.stack([blended, blended], axis=1).astype(np.float32)
        return blended

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _blend_into_audio(
        self,
        audio: np.ndarray,
        category_pairs: list[tuple[str, float]],
        duration: float,
    ) -> np.ndarray:
        """Apply sample blending to a stereo or mono audio array."""
        stereo = audio.ndim == 2
        if stereo:
            mono = audio.mean(axis=1)
        else:
            mono = audio.astype(np.float32)

        blended_mono = self._blend_mono(mono, category_pairs, duration)

        if stereo:
            # Light MS widening: keep the blend centred but spread slightly
            w = 0.12
            left  = blended_mono * (1.0 + w)
            right = blended_mono * (1.0 - w)
            return np.stack([left, right], axis=1).astype(np.float32)
        return blended_mono

    def _blend_mono(
        self,
        mono: np.ndarray,
        category_pairs: list[tuple[str, float]],
        duration: float,
    ) -> np.ndarray:
        result = mono.copy().astype(np.float32)
        for category, weight in category_pairs:
            if not self._lib.has_category(category):
                continue
            result = self._lib.blend(
                result,
                category,
                sample_weight=weight,
                duration=duration,
                rng=self._rng,
            )
        return result
