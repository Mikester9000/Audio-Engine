"""
Sequencer – assembles Notes into a multi-track audio buffer.

The sequencer is the central timeline editor.  Each track holds an
instrument and a list of Note events; ``render()`` mixes them into a
single mono or stereo NumPy array.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np

from audio_engine.synthesizer.instrument import Instrument

__all__ = ["Note", "Sequencer"]


class Note(NamedTuple):
    """A single note event on the timeline.

    Attributes
    ----------
    frequency:
        Pitch in Hz.
    onset:
        Start time in seconds from the beginning of the sequence.
    duration:
        Note duration in seconds.
    velocity:
        Loudness 0–1 (scales the rendered amplitude).
    """

    frequency: float
    onset: float
    duration: float
    velocity: float = 1.0


@dataclass
class _Track:
    instrument: Instrument
    notes: list[Note] = field(default_factory=list)
    pan: float = 0.0   # -1 = full left, 0 = centre, 1 = full right
    volume: float = 1.0


class Sequencer:
    """Multi-track audio sequencer.

    Parameters
    ----------
    bpm:
        Beats per minute (default 120).
    time_signature:
        Number of beats per bar (default 4).
    sample_rate:
        Audio sample rate in Hz (default 44 100).
    """

    def __init__(
        self,
        bpm: float = 120.0,
        time_signature: int = 4,
        sample_rate: int = 44100,
    ) -> None:
        self.bpm = bpm
        self.time_signature = time_signature
        self.sample_rate = sample_rate
        self._tracks: dict[str, _Track] = {}

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def add_track(
        self,
        name: str,
        instrument: Instrument,
        pan: float = 0.0,
        volume: float = 1.0,
    ) -> None:
        """Add a named track with the given *instrument*."""
        self._tracks[name] = _Track(instrument=instrument, pan=pan, volume=volume)

    def add_note(
        self,
        track_name: str,
        frequency: float,
        onset: float,
        duration: float,
        velocity: float = 1.0,
    ) -> None:
        """Schedule a note on *track_name*.

        Parameters
        ----------
        track_name:
            Must match a track added via :meth:`add_track`.
        frequency:
            Pitch in Hz.
        onset:
            Start time in seconds.
        duration:
            Duration in seconds.
        velocity:
            Amplitude scalar 0–1.
        """
        if track_name not in self._tracks:
            raise KeyError(f"Track '{track_name}' not found")
        self._tracks[track_name].notes.append(Note(frequency, onset, duration, velocity))

    def add_notes(self, track_name: str, notes: list[Note]) -> None:
        """Bulk-add a list of :class:`Note` objects to *track_name*."""
        for note in notes:
            self.add_note(track_name, note.frequency, note.onset, note.duration, note.velocity)

    def clear_track(self, track_name: str) -> None:
        """Remove all notes from *track_name*."""
        if track_name in self._tracks:
            self._tracks[track_name].notes.clear()

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------

    @property
    def beat_duration(self) -> float:
        """Duration of one beat in seconds."""
        return 60.0 / self.bpm

    @property
    def bar_duration(self) -> float:
        """Duration of one bar in seconds."""
        return self.beat_duration * self.time_signature

    def beats_to_seconds(self, beats: float) -> float:
        """Convert *beats* to seconds."""
        return beats * self.beat_duration

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, duration: float | None = None) -> np.ndarray:
        """Mix all tracks into a stereo float32 NumPy array of shape ``(N, 2)``.

        Parameters
        ----------
        duration:
            Total output length in seconds.  Defaults to the latest note end
            time across all tracks.
        """
        if duration is None:
            duration = self._total_duration()
        if duration <= 0:
            return np.zeros((0, 2), dtype=np.float32)

        total_samples = int(duration * self.sample_rate)
        mix_left = np.zeros(total_samples, dtype=np.float64)
        mix_right = np.zeros(total_samples, dtype=np.float64)

        for track in self._tracks.values():
            for note in track.notes:
                note_samples = int(note.duration * self.sample_rate)
                if note_samples <= 0:
                    continue
                rendered = track.instrument.render(note.frequency, note.duration)
                rendered = rendered * note.velocity * track.volume

                onset_sample = int(note.onset * self.sample_rate)
                end_sample = onset_sample + len(rendered)
                if onset_sample >= total_samples:
                    continue
                end_sample = min(end_sample, total_samples)
                chunk = rendered[: end_sample - onset_sample]

                # Pan law: constant power
                pan = np.clip(track.pan, -1.0, 1.0)
                left_gain = np.cos((pan + 1.0) * np.pi / 4.0)
                right_gain = np.sin((pan + 1.0) * np.pi / 4.0)
                mix_left[onset_sample:end_sample] += left_gain * chunk
                mix_right[onset_sample:end_sample] += right_gain * chunk

        # Stack stereo
        stereo = np.column_stack([mix_left, mix_right]).astype(np.float32)
        # Master normalise
        peak = np.max(np.abs(stereo))
        if peak > 1.0:
            stereo /= peak
        return stereo

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _total_duration(self) -> float:
        max_end = 0.0
        for track in self._tracks.values():
            for note in track.notes:
                max_end = max(max_end, note.onset + note.duration)
        return max_end
