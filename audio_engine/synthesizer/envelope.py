"""
Envelope – ADSR amplitude shaping.

Applies Attack / Decay / Sustain / Release curves to any audio signal so that
sounds fade in and out naturally rather than clicking.
"""

from __future__ import annotations

import numpy as np

__all__ = ["Envelope"]


class Envelope:
    """ADSR envelope generator.

    Parameters
    ----------
    attack:
        Rise time from 0 → 1 (seconds).
    decay:
        Fall time from 1 → sustain level (seconds).
    sustain:
        Sustain amplitude 0–1 (held for the middle portion of the note).
    release:
        Fall time from sustain → 0 after note-off (seconds).
    sample_rate:
        Samples per second.
    """

    def __init__(
        self,
        attack: float = 0.01,
        decay: float = 0.1,
        sustain: float = 0.7,
        release: float = 0.3,
        sample_rate: int = 44100,
    ) -> None:
        if not (0.0 <= sustain <= 1.0):
            raise ValueError(f"sustain must be between 0 and 1, got {sustain}")
        self.attack = max(attack, 0.0)
        self.decay = max(decay, 0.0)
        self.sustain = sustain
        self.release = max(release, 0.0)
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------

    def apply(self, signal: np.ndarray, duration: float) -> np.ndarray:
        """Apply the ADSR envelope to *signal*.

        The signal is assumed to span exactly *duration* seconds.
        """
        envelope = self._build(duration, len(signal))
        return signal * envelope

    # ------------------------------------------------------------------

    def _build(self, duration: float, num_samples: int) -> np.ndarray:
        """Build the envelope array for *duration* seconds."""
        sr = self.sample_rate
        attack_s = min(int(self.attack * sr), num_samples)
        decay_s = min(int(self.decay * sr), num_samples - attack_s)
        # Reserve samples for release, but never more than what's left after A+D
        remaining_after_ad = num_samples - attack_s - decay_s
        release_s = min(int(self.release * sr), remaining_after_ad)
        sustain_s = max(remaining_after_ad - release_s, 0)

        env = np.zeros(num_samples)

        # Attack: linear rise 0 → 1
        if attack_s > 0:
            env[:attack_s] = np.linspace(0.0, 1.0, attack_s)

        # Decay: linear fall 1 → sustain
        a_end = attack_s + decay_s
        if decay_s > 0:
            env[attack_s:a_end] = np.linspace(1.0, self.sustain, decay_s)

        # Sustain: constant
        s_end = a_end + sustain_s
        env[a_end:s_end] = self.sustain

        # Release: linear fall sustain → 0
        if release_s > 0:
            env[s_end : s_end + release_s] = np.linspace(self.sustain, 0.0, release_s)

        return env

    # ------------------------------------------------------------------
    # Pre-built profiles
    # ------------------------------------------------------------------

    @classmethod
    def percussive(cls, sample_rate: int = 44100) -> "Envelope":
        """Short attack, fast decay, no sustain – suitable for drums/pluck."""
        return cls(attack=0.002, decay=0.05, sustain=0.0, release=0.05, sample_rate=sample_rate)

    @classmethod
    def pad(cls, sample_rate: int = 44100) -> "Envelope":
        """Slow attack, long release – suitable for string/pad sounds."""
        return cls(attack=0.4, decay=0.2, sustain=0.8, release=1.0, sample_rate=sample_rate)

    @classmethod
    def pluck(cls, sample_rate: int = 44100) -> "Envelope":
        """Very fast attack, medium decay – guitar/harp."""
        return cls(attack=0.001, decay=0.3, sustain=0.1, release=0.2, sample_rate=sample_rate)

    @classmethod
    def brass(cls, sample_rate: int = 44100) -> "Envelope":
        """Moderate attack, slight decay, high sustain."""
        return cls(attack=0.05, decay=0.05, sustain=0.9, release=0.15, sample_rate=sample_rate)
