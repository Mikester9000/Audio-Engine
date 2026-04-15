"""
AudioEngine – the top-level façade for the Audio Engine for Teaching.

This class provides a unified, beginner-friendly interface that orchestrates
the synthesizer, AI composer, and exporter.  It is the recommended
entry-point for integration with a Game Engine for Teaching.

Example usage
-------------
>>> from audio_engine import AudioEngine
>>> engine = AudioEngine()

# Generate a 30-second battle track and save it
>>> engine.generate_track("battle", bars=8, output_path="battle.wav")

# Render a custom note sequence
>>> from audio_engine.composer import Sequencer, Note
>>> from audio_engine.synthesizer import InstrumentLibrary
>>> seq = Sequencer(bpm=120)
>>> seq.add_track("piano", InstrumentLibrary.get("piano"))
>>> seq.add_note("piano", 440.0, onset=0.0, duration=0.5)
>>> audio = seq.render()
>>> engine.export(audio, "my_note.wav")
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np

from audio_engine.ai.generator import MusicGenerator, TrackStyle
from audio_engine.export.audio_exporter import AudioExporter
from audio_engine.composer.sequencer import Sequencer, Note
from audio_engine.synthesizer.instrument import InstrumentLibrary

__all__ = ["AudioEngine"]


class AudioEngine:
    """Unified Audio Engine for Game Engine for Teaching.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz (default 44 100 Hz – CD quality).
    bit_depth:
        Bit depth for exported WAV files: 16 (default) or 32.
    seed:
        Random seed for reproducible AI generation.  ``None`` = random.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        bit_depth: Literal[16, 32] = 16,
        seed: int | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self._generator = MusicGenerator(sample_rate=sample_rate, seed=seed)
        self._exporter = AudioExporter(sample_rate=sample_rate, bit_depth=bit_depth)

    # ------------------------------------------------------------------
    # AI track generation
    # ------------------------------------------------------------------

    def generate_track(
        self,
        style: TrackStyle = "battle",
        bars: int | None = None,
        output_path: str | Path | None = None,
        fmt: Literal["wav", "ogg"] = "wav",
    ) -> np.ndarray:
        """Generate a complete music track using the AI composer.

        Parameters
        ----------
        style:
            Musical style – one of ``"battle"``, ``"exploration"``,
            ``"ambient"``, ``"boss"``, ``"victory"``, ``"menu"``.
        bars:
            Number of bars to generate (``None`` → style default).
        output_path:
            If supplied, the audio is also saved to this file.
        fmt:
            Output format: ``"wav"`` (default) or ``"ogg"``.

        Returns
        -------
        np.ndarray
            Stereo float32 array with shape ``(N, 2)``.
        """
        audio = self._generator.generate_audio(style=style, bars=bars)
        if output_path is not None:
            self._exporter.export(audio, output_path, fmt=fmt)
        return audio

    # ------------------------------------------------------------------
    # Custom sequencer access
    # ------------------------------------------------------------------

    def create_sequencer(self, bpm: float = 120.0, time_signature: int = 4) -> Sequencer:
        """Create a blank :class:`~audio_engine.composer.Sequencer`.

        Parameters
        ----------
        bpm:
            Beats per minute.
        time_signature:
            Beats per bar.
        """
        return Sequencer(bpm=bpm, time_signature=time_signature, sample_rate=self.sample_rate)

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def export(
        self,
        audio: np.ndarray,
        path: str | Path,
        fmt: Literal["wav", "ogg"] = "wav",
        loop_start: int | None = None,
        loop_end: int | None = None,
    ) -> Path:
        """Export a NumPy audio array to a file.

        Parameters
        ----------
        audio:
            1-D (mono) or ``(N, 2)`` (stereo) float32 array.
        path:
            Output file path.
        fmt:
            File format: ``"wav"`` (default) or ``"ogg"``.
        loop_start:
            If given, embed game-engine loop-point metadata (WAV only).
        loop_end:
            Loop end in samples (required if *loop_start* is set).

        Returns
        -------
        Path
            Path of the written file.
        """
        out_path = self._exporter.export(audio, path, fmt=fmt)
        if loop_start is not None:
            if loop_end is None:
                raise ValueError("loop_end must be provided when loop_start is set")
            if fmt != "wav":
                raise ValueError("Loop-point metadata is only supported for WAV files")
            self._exporter.write_loop_points(out_path, loop_start, loop_end)
        return out_path

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def available_styles() -> list[str]:
        """Return the list of available AI music generation styles."""
        return MusicGenerator.available_styles()

    @staticmethod
    def available_instruments() -> list[str]:
        """Return the list of available synthesised instruments."""
        return InstrumentLibrary.available()

    # ------------------------------------------------------------------
    # Render a chord/arpeggio from scratch (quick SFX helper)
    # ------------------------------------------------------------------

    def render_sfx(
        self,
        instrument_name: str,
        frequencies: list[float],
        duration: float = 0.5,
        overlap: bool = False,
    ) -> np.ndarray:
        """Render a simple sound effect by stacking or sequencing notes.

        Parameters
        ----------
        instrument_name:
            Instrument to use (see :meth:`available_instruments`).
        frequencies:
            List of pitches in Hz.
        duration:
            Duration of each note in seconds.
        overlap:
            If ``True``, all notes are rendered simultaneously (chord).
            If ``False``, notes are played in sequence (arpeggio).

        Returns
        -------
        np.ndarray
            Mono float32 array.
        """
        inst = InstrumentLibrary.get(instrument_name, self.sample_rate)
        if overlap:
            total_samples = int(duration * self.sample_rate)
            mix = np.zeros(total_samples, dtype=np.float32)
            for freq in frequencies:
                rendered = inst.render(freq, duration)
                length = min(len(rendered), total_samples)
                mix[:length] += rendered[:length]
            peak = np.max(np.abs(mix))
            if peak > 1.0:
                mix /= peak
            return mix
        else:
            parts: list[np.ndarray] = [inst.render(f, duration) for f in frequencies]
            return np.concatenate(parts)
