"""
Sample-rate conversion (resampling) utility.

Uses scipy's polyphase resampler for high-quality, aliasing-free sample-rate
conversion.  Handles mono and stereo signals transparently.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import resample_poly  # type: ignore[import]
from math import gcd

__all__ = ["resample"]


def resample(
    signal: np.ndarray,
    orig_sr: int,
    target_sr: int,
) -> np.ndarray:
    """Resample *signal* from *orig_sr* to *target_sr*.

    Uses a polyphase filter (anti-aliasing) for quality-preserving
    conversion.  Handles mono (1-D) and stereo (``(N, 2)``) arrays.

    Parameters
    ----------
    signal:
        Float32 audio array, 1-D or shape ``(N, 2)``.
    orig_sr:
        Source sample rate in Hz.
    target_sr:
        Target sample rate in Hz.

    Returns
    -------
    np.ndarray
        Resampled float32 array.

    Example
    -------
    >>> audio_48k = resample(audio_44k, 44100, 48000)
    """
    if orig_sr == target_sr:
        return signal.copy()

    # Reduce up/down ratio by GCD
    common = gcd(orig_sr, target_sr)
    up = target_sr // common
    down = orig_sr // common

    stereo = signal.ndim == 2
    sig_f64 = signal.astype(np.float64)

    if stereo:
        left = resample_poly(sig_f64[:, 0], up, down)
        right = resample_poly(sig_f64[:, 1], up, down)
        result = np.stack([left, right], axis=1)
    else:
        result = resample_poly(sig_f64, up, down)

    return result.astype(np.float32)
