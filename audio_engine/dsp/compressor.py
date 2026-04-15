"""
Dynamic range compressor with attack/release envelope.

Implements a feed-forward RMS compressor with configurable:
- Threshold (dBFS)
- Compression ratio
- Attack and release time constants
- Knee width (soft knee)
- Make-up gain

This is a sample-accurate compressor that tracks the signal envelope using
a first-order IIR smoother, giving natural-sounding gain reduction.
"""

from __future__ import annotations

import numpy as np

__all__ = ["Compressor"]


def _db_to_linear(db: float) -> float:
    """Convert dB value to linear amplitude."""
    return 10.0 ** (db / 20.0)


def _linear_to_db(linear: float | np.ndarray) -> float | np.ndarray:
    """Convert linear amplitude to dB (safe – avoids log(0))."""
    return 20.0 * np.log10(np.maximum(np.abs(linear), 1e-9))


class Compressor:
    """Feed-forward dynamic range compressor.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    threshold_db:
        Level above which compression begins, in dBFS (e.g. ``-18.0``).
    ratio:
        Compression ratio, e.g. ``4.0`` for 4:1.
    attack_ms:
        Attack time in milliseconds – how quickly gain reduction ramps up.
    release_ms:
        Release time in milliseconds – how quickly gain reduction recovers.
    knee_db:
        Soft-knee width in dB.  ``0`` = hard knee.  ``6`` = gentle onset.
    makeup_gain_db:
        Additional make-up gain in dB applied after compression.

    Example
    -------
    >>> comp = Compressor(44100, threshold_db=-18.0, ratio=4.0)
    >>> output = comp.process(audio)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        threshold_db: float = -18.0,
        ratio: float = 4.0,
        attack_ms: float = 10.0,
        release_ms: float = 100.0,
        knee_db: float = 6.0,
        makeup_gain_db: float = 0.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.threshold_db = threshold_db
        self.ratio = ratio
        self.knee_db = knee_db
        self.makeup_gain_db = makeup_gain_db

        # Convert time constants to per-sample coefficients
        self._attack_coef = np.exp(-1.0 / (sample_rate * attack_ms / 1000.0))
        self._release_coef = np.exp(-1.0 / (sample_rate * release_ms / 1000.0))
        self._makeup_linear = _db_to_linear(makeup_gain_db)

    def process(self, signal: np.ndarray) -> np.ndarray:
        """Apply dynamic range compression to *signal*.

        Parameters
        ----------
        signal:
            1-D mono or ``(N, 2)`` stereo float32 array.

        Returns
        -------
        np.ndarray
            Compressed signal, same shape and dtype.
        """
        stereo = signal.ndim == 2
        sig = signal.astype(np.float64)

        if stereo:
            # Use the louder channel to drive the sidechain (sum-to-mono)
            sidechain = np.mean(np.abs(sig), axis=1)
            gain = self._compute_gain(sidechain)
            out = sig * gain[:, np.newaxis] * self._makeup_linear
        else:
            gain = self._compute_gain(np.abs(sig))
            out = sig * gain * self._makeup_linear

        return out.astype(np.float32)

    def _compute_gain(self, envelope_input: np.ndarray) -> np.ndarray:
        """Compute per-sample gain reduction from an envelope signal.

        Parameters
        ----------
        envelope_input:
            Absolute value (or RMS) of the sidechain signal, shape ``(N,)``.

        Returns
        -------
        np.ndarray
            Gain multipliers, shape ``(N,)``.
        """
        n = len(envelope_input)
        level_db = _linear_to_db(envelope_input)

        # Compute desired gain reduction (in dB) using soft-knee
        half_knee = self.knee_db / 2.0
        gain_reduction_db = np.zeros(n, dtype=np.float64)

        for i in range(n):
            x = level_db[i]
            overshoot = x - self.threshold_db

            if self.knee_db > 0 and overshoot > -half_knee and overshoot < half_knee:
                # Soft-knee region – blend smoothly into compression
                t = (overshoot + half_knee) / self.knee_db
                eff_ratio = 1.0 + (self.ratio - 1.0) * t
                gain_reduction_db[i] = overshoot * (1.0 - 1.0 / eff_ratio) * t
            elif overshoot > half_knee:
                # Above threshold (and knee)
                gain_reduction_db[i] = overshoot * (1.0 - 1.0 / self.ratio)
            # else: below threshold – no compression (gain_reduction stays 0)

        # Convert desired GR to linear gain multipliers
        desired_gain = _db_to_linear(-gain_reduction_db)

        # Smooth with attack/release envelope
        smoothed_gain = np.ones(n, dtype=np.float64)
        prev = 1.0
        for i in range(n):
            g = desired_gain[i]
            if g < prev:
                coef = self._attack_coef
            else:
                coef = self._release_coef
            smoothed_gain[i] = coef * prev + (1.0 - coef) * g
            prev = smoothed_gain[i]

        return smoothed_gain
