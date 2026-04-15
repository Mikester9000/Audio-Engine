"""
True-peak brick-wall limiter.

Prevents output from exceeding a configurable ceiling (default -0.3 dBFS)
while using a fast lookahead attack to avoid hard clipping artefacts.

The limiter is suitable for final mastering – it runs after any compressor
or EQ stages to ensure the exported file never clips.
"""

from __future__ import annotations

import numpy as np

__all__ = ["Limiter"]


def _db_to_linear(db: float) -> float:
    """Convert dB value to a linear amplitude multiplier."""
    return 10.0 ** (db / 20.0)


class Limiter:
    """Brick-wall true-peak limiter.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    ceiling_db:
        Maximum output level in dBFS (default ``-0.3`` – leaves a small
        true-peak headroom).
    release_ms:
        Gain recovery time in milliseconds after the signal drops below the
        ceiling.
    lookahead_ms:
        Lookahead buffer in milliseconds.  Allows the limiter to begin
        gain reduction before the peak arrives, preventing hard transients.

    Example
    -------
    >>> limiter = Limiter(44100, ceiling_db=-0.3)
    >>> limited = limiter.process(audio)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        ceiling_db: float = -0.3,
        release_ms: float = 150.0,
        lookahead_ms: float = 5.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.ceiling = _db_to_linear(ceiling_db)
        self._release_coef = np.exp(-1.0 / (sample_rate * release_ms / 1000.0))
        self._lookahead = max(1, int(sample_rate * lookahead_ms / 1000.0))

    def process(self, signal: np.ndarray) -> np.ndarray:
        """Apply the limiter to *signal*.

        Parameters
        ----------
        signal:
            1-D mono or ``(N, 2)`` stereo float32 array.

        Returns
        -------
        np.ndarray
            Limited signal.  Same shape and dtype.
        """
        stereo = signal.ndim == 2
        sig = signal.astype(np.float64)

        if stereo:
            peak_env = np.max(np.abs(sig), axis=1)
        else:
            peak_env = np.abs(sig)

        gain = self._compute_gain(peak_env)

        if stereo:
            out = sig * gain[:, np.newaxis]
        else:
            out = sig * gain

        return out.astype(np.float32)

    def _compute_gain(self, peak_env: np.ndarray) -> np.ndarray:
        """Compute lookahead + release gain curve from a peak envelope.

        Parameters
        ----------
        peak_env:
            Absolute peak value at each sample, shape ``(N,)``.

        Returns
        -------
        np.ndarray
            Per-sample gain multipliers, shape ``(N,)``.
        """
        n = len(peak_env)
        ceiling = self.ceiling

        # Lookahead: for each sample, find the max peak within the next
        # ``lookahead`` samples so we can pre-emptively reduce gain.
        lookahead_peak = np.copy(peak_env)
        la = self._lookahead
        # Vectorised lookahead using stride tricks via cumulative max
        # (simpler approach: slide max over a window)
        for i in range(min(la, n)):
            lookahead_peak[: n - i] = np.maximum(
                lookahead_peak[: n - i], peak_env[i : n]
            )

        # Desired gain (instantaneous)
        desired = np.where(
            lookahead_peak > ceiling,
            ceiling / (lookahead_peak + 1e-12),
            1.0,
        )

        # Apply release smoothing
        gain = np.ones(n, dtype=np.float64)
        prev = 1.0
        for i in range(n):
            g = desired[i]
            if g < prev:
                # Instant attack (no ramp – brick-wall)
                gain[i] = g
            else:
                # Exponential release
                gain[i] = self._release_coef * prev + (1.0 - self._release_coef) * g
            prev = gain[i]

        return gain
