"""
AudioEngine – the top-level façade for the Audio Engine.

This class provides a unified, beginner-friendly interface that orchestrates
the synthesizer, AI composer, exporter, and the new post-processing pipeline.
It is the recommended entry-point for integration with a Game Engine.

For more direct control, use the sub-module classes:
- :class:`~audio_engine.ai.MusicGen` – prompt-driven music generation
- :class:`~audio_engine.ai.SFXGen` – prompt-driven SFX generation
- :class:`~audio_engine.ai.VoiceGen` – local text-to-speech
- :class:`~audio_engine.render.OfflineBounce` – mastering / loudness normalisation
- :class:`~audio_engine.qa.LoudnessMeter` – EBU R128 loudness measurement

Example usage
-------------
>>> from audio_engine import AudioEngine
>>> engine = AudioEngine()

# Generate a 30-second battle track and save it
>>> engine.generate_track("battle", bars=8, output_path="battle.wav")

# Generate from a natural-language prompt
>>> engine.generate_music("dark ambient dungeon loop 90 BPM", output_path="dungeon.wav", loopable=True)

# Generate a sound effect
>>> engine.generate_sfx_from_prompt("laser zap", output_path="laser.wav")

# Synthesise voice
>>> engine.generate_voice("Level complete!", voice="announcer", output_path="level_done.wav")

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
    """Unified Audio Engine façade.

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
        self._seed = seed
        self._generator = MusicGenerator(sample_rate=sample_rate, seed=seed)
        self._exporter = AudioExporter(sample_rate=sample_rate, bit_depth=bit_depth)

    # ------------------------------------------------------------------
    # AI track generation (legacy style-based API)
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
    # Prompt-driven AI generation (new pipeline)
    # ------------------------------------------------------------------

    def generate_music(
        self,
        prompt: str,
        duration: float = 30.0,
        loopable: bool = False,
        output_path: str | Path | None = None,
        fmt: Literal["wav", "ogg"] = "wav",
    ) -> np.ndarray:
        """Generate music from a natural-language prompt.

        This uses the full AI pipeline: prompt parsing → procedural
        generation → mastering (EQ + compression + limiting + loudness
        normalisation).

        Parameters
        ----------
        prompt:
            Free-form description, e.g.
            ``"epic orchestral battle theme 140 BPM loopable"``.
        duration:
            Target duration in seconds.
        loopable:
            If ``True``, embed loop-point metadata in the exported WAV.
        output_path:
            If supplied, save the audio to this path.
        fmt:
            Output format: ``"wav"`` or ``"ogg"``.

        Returns
        -------
        np.ndarray
            Stereo float32 array ``(N, 2)``.
        """
        from audio_engine.ai.music_gen import MusicGen

        gen = MusicGen(sample_rate=self.sample_rate, seed=self._seed)
        audio = gen.generate(prompt, duration=duration, loopable=loopable)

        if output_path is not None:
            path = gen.generate_to_file(
                prompt, output_path, duration=duration, loopable=loopable, fmt=fmt
            )
        return audio

    def generate_sfx_from_prompt(
        self,
        prompt: str,
        duration: float = 1.0,
        pitch_hz: float | None = None,
        output_path: str | Path | None = None,
    ) -> np.ndarray:
        """Generate a sound effect from a natural-language prompt.

        Parameters
        ----------
        prompt:
            Description, e.g. ``"explosion impact 1.5 seconds"``.
        duration:
            Default duration in seconds.
        pitch_hz:
            Optional base pitch in Hz.
        output_path:
            If supplied, save the audio to this WAV path.

        Returns
        -------
        np.ndarray
            Mono float32 audio array.
        """
        from audio_engine.ai.sfx_gen import SFXGen

        gen = SFXGen(sample_rate=self.sample_rate, seed=self._seed)
        audio = gen.generate(prompt, duration=duration, pitch_hz=pitch_hz)

        if output_path is not None:
            self._exporter.export(audio, output_path, fmt="wav")
        return audio

    def generate_voice(
        self,
        text: str,
        voice: str = "narrator",
        speed: float = 1.0,
        output_path: str | Path | None = None,
    ) -> np.ndarray:
        """Synthesise speech from *text* using local TTS.

        Parameters
        ----------
        text:
            The text to speak.
        voice:
            Voice preset: ``"narrator"``, ``"hero"``, ``"villain"``,
            ``"announcer"``, or ``"npc"``.
        speed:
            Speech rate multiplier (1.0 = normal).
        output_path:
            If supplied, save the audio to this WAV path.

        Returns
        -------
        np.ndarray
            Mono float32 audio array.
        """
        from audio_engine.ai.voice_gen import VoiceGen

        gen = VoiceGen(sample_rate=22050, seed=self._seed)
        audio = gen.generate(text, voice=voice, speed=speed)

        if output_path is not None:
            voice_exporter = AudioExporter(sample_rate=22050, bit_depth=self._exporter.bit_depth)
            voice_exporter.export(audio, output_path, fmt="wav")
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

    @staticmethod
    def available_voices() -> list[str]:
        """Return the list of available voice presets."""
        from audio_engine.ai.voice_synth import VOICE_PRESETS

        return sorted(VOICE_PRESETS)

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
