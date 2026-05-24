"""
High-level music generation interface.

:class:`MusicGen` wraps an :class:`~audio_engine.ai.backend.InferenceBackend`
and exposes a simple API for generating music tracks from text prompts or
style presets.  It handles prompt parsing, generation, optional mastering,
and file export.

Usage
-----
>>> from audio_engine.ai import MusicGen
>>> gen = MusicGen(sample_rate=44100)
>>> audio = gen.generate("epic orchestral battle, 140 BPM, loopable")
>>> gen.generate_to_file("battle theme", "battle.wav", duration=60.0, loopable=True)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

import numpy as np

from audio_engine.ai.backend import InferenceBackend, BackendRegistry
from audio_engine.ai.prompt import PromptParser, MusicPlan
from audio_engine.export.audio_exporter import AudioExporter
from audio_engine.render.loop_exporter import bake_crossfade_loop

__all__ = ["MusicGen"]

_REGION_PROMPT_HINTS: dict[str, str] = {
    "plains": "wide open plains travel identity with clear heroic momentum",
    "forest": "layered forest canopy texture with woodwind shimmer",
    "coast": "coastal breeze texture with airy harmonic space",
    "ruins": "ancient ruins atmosphere with mystery and reverent tension",
    "arid": "arid frontier tone with sparse rhythmic pulse",
}
_CALM_LAYER_GAIN = 0.82
_INTENSE_LAYER_GAIN = 1.18
_ADAPTIVE_INTENSITY_GAIN = 1.08
_REGION_STYLE_OVERRIDES: dict[str, str] = {
    "plains": "exploration_plains",
    "forest": "exploration_forest",
    "coast": "exploration_coast",
    "arid": "exploration_arid",
}


class MusicGen:
    """High-level music generation with prompt parsing and export.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    backend:
        Backend name or :class:`~audio_engine.ai.backend.InferenceBackend`
        instance.  Defaults to ``"procedural"`` (built-in synthesiser).
    seed:
        Random seed for reproducibility.
    apply_mastering:
        If ``True``, run the generated audio through the
        :class:`~audio_engine.render.OfflineBounce` mastering pipeline
        before returning/exporting.

    Example
    -------
    >>> gen = MusicGen(sample_rate=44100, seed=42)
    >>> audio = gen.generate("calm ambient exploration 90 BPM")
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        backend: str | InferenceBackend = "procedural",
        seed: int | None = None,
        apply_mastering: bool = True,
        mastering_profile: str = "game",
        region_prompt_hints: dict[str, str] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.apply_mastering = apply_mastering
        self.mastering_profile = mastering_profile
        self._region_prompt_hints = dict(_REGION_PROMPT_HINTS)
        if region_prompt_hints:
            self._region_prompt_hints.update(region_prompt_hints)
        self._parser = PromptParser()
        self._exporter = AudioExporter(sample_rate=sample_rate)

        if isinstance(backend, str):
            self._backend = BackendRegistry.get(backend, sample_rate=sample_rate, seed=seed)
        else:
            self._backend = backend
        self._seed = seed

    def generate(
        self,
        prompt: str,
        duration: float = 30.0,
        loopable: bool = False,
        region: str | None = None,
        adaptive_intensity: bool = False,
        style_override: str | None = None,
    ) -> np.ndarray:
        """Generate a music track from a text prompt.

        Parameters
        ----------
        prompt:
            Natural-language description, e.g.
            ``"dark orchestral boss theme 160 BPM"``.
        duration:
            Target duration in seconds.
        loopable:
            If ``True``, attempt to make the output loop seamlessly.

        Returns
        -------
        np.ndarray
            Stereo float32 array ``(N, 2)``.
        """
        shaped_prompt = self._prompt_with_region(prompt, region)
        plan = self._parser.parse_music(shaped_prompt, duration=duration)
        if style_override:
            plan.style = style_override.strip() or plan.style
        if loopable:
            plan.loopable = True
        return self._generate_from_plan(
            plan,
            region=region,
            adaptive_intensity=adaptive_intensity,
        )

    def generate_from_plan(
        self,
        plan: MusicPlan,
        region: str | None = None,
        adaptive_intensity: bool = False,
    ) -> np.ndarray:
        """Generate music from a pre-built :class:`~audio_engine.ai.prompt.MusicPlan`.

        Parameters
        ----------
        plan:
            Generation plan with style, BPM, duration, etc.

        Returns
        -------
        np.ndarray
            Stereo float32 array ``(N, 2)``.
        """
        shaped_prompt = self._prompt_with_region(plan.prompt, region)
        return self._generate_from_plan(
            plan,
            region=region,
            adaptive_intensity=adaptive_intensity,
            prompt_override=shaped_prompt,
        )

    def generate_to_file(
        self,
        prompt: str,
        output_path: str | Path,
        duration: float = 30.0,
        loopable: bool = False,
        fmt: Literal["wav", "ogg"] = "wav",
        region: str | None = None,
        adaptive_intensity: bool = False,
        layer_output_dir: str | Path | None = None,
        style_override: str | None = None,
    ) -> Path:
        """Generate music and save to *output_path*.

        Parameters
        ----------
        prompt:
            Natural-language description.
        output_path:
            Output file path.
        duration:
            Target duration in seconds.
        loopable:
            Whether to embed loop-point metadata (WAV only).
        fmt:
            Output format: ``"wav"`` or ``"ogg"``.

        Returns
        -------
        Path
            Written file path.
        """
        audio = self.generate(
            prompt,
            duration=duration,
            loopable=loopable,
            region=region,
            adaptive_intensity=adaptive_intensity,
            style_override=style_override,
        )
        if loopable:
            audio = bake_crossfade_loop(audio, self.sample_rate, crossfade_ms=500)
        path = self._exporter.export(audio, output_path, fmt=fmt)

        if loopable and fmt == "wav":
            # Embed loop points at 0 → last sample
            total_samples = audio.shape[0]
            self._exporter.write_loop_points(path, 0, total_samples - 1)

        if layer_output_dir is not None:
            self._export_adaptive_layers(
                audio=audio,
                output_path=path,
                layer_output_dir=layer_output_dir,
                region=region,
                adaptive_intensity=adaptive_intensity,
            )

        return path

    def _generate_from_plan(
        self,
        plan: MusicPlan,
        region: str | None = None,
        adaptive_intensity: bool = False,
        prompt_override: str | None = None,
    ) -> np.ndarray:
        """Internal: execute the plan and optionally master the result."""
        style = self._style_with_region(plan.style, region)
        prompt = plan.prompt if prompt_override is None else prompt_override
        audio = self._backend.generate_music_audio(
            style=style,
            duration=plan.duration,
            bpm=plan.bpm,
            prompt=prompt,
            adaptive_intensity=adaptive_intensity,
        )
        if adaptive_intensity:
            audio = np.clip(audio * _ADAPTIVE_INTENSITY_GAIN, -1.0, 1.0).astype(np.float32)

        if self.apply_mastering:
            audio = self._master(audio)

        return audio

    def _master(self, audio: np.ndarray) -> np.ndarray:
        """Apply a lightweight mastering pass."""
        from audio_engine.render.offline_bounce import OfflineBounce

        bounce = OfflineBounce(
            sample_rate=self.sample_rate,
            apply_master_eq=True,
            apply_compression=True,
            profile=self.mastering_profile,
        )
        return bounce.process(audio)

    def _prompt_with_region(self, prompt: str, region: str | None) -> str:
        if not region:
            return prompt
        hint = self._region_prompt_hints.get(region.lower())
        if not hint:
            return prompt
        return f"{prompt}, {hint}"

    def _style_with_region(self, style: str, region: str | None) -> str:
        if style != "exploration" or not region:
            return style
        return _REGION_STYLE_OVERRIDES.get(region.lower(), style)

    def _export_adaptive_layers(
        self,
        audio: np.ndarray,
        output_path: Path,
        layer_output_dir: str | Path,
        region: str | None,
        adaptive_intensity: bool,
    ) -> None:
        layer_dir = Path(layer_output_dir)
        layer_dir.mkdir(parents=True, exist_ok=True)
        stem = output_path.stem
        base_path = layer_dir / f"{stem}_layer_base.wav"
        calm_path = layer_dir / f"{stem}_layer_calm.wav"
        intense_path = layer_dir / f"{stem}_layer_intense.wav"

        calm_audio = np.clip(audio * _CALM_LAYER_GAIN, -1.0, 1.0).astype(np.float32)
        intense_audio = np.clip(audio * _INTENSE_LAYER_GAIN, -1.0, 1.0).astype(np.float32)

        self._exporter.export(audio, base_path, fmt="wav")
        self._exporter.export(calm_audio, calm_path, fmt="wav")
        self._exporter.export(intense_audio, intense_path, fmt="wav")

        main_mix_path = Path(os.path.relpath(output_path, start=layer_dir))
        metadata = {
            "mainMixPath": str(main_mix_path),
            "region": region,
            "adaptiveIntensityEnabled": bool(adaptive_intensity),
            "layers": [
                {"name": "base", "path": str(base_path.relative_to(layer_dir))},
                {"name": "calm", "path": str(calm_path.relative_to(layer_dir))},
                {"name": "intense", "path": str(intense_path.relative_to(layer_dir))},
            ],
            "seed": self._seed,
        }
        (layer_dir / f"{stem}_layers.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
