"""
Noise dithering for quantisation error shaping.

When reducing bit depth (e.g. from float32 to 16-bit PCM), quantisation
introduces periodic distortion (quantisation noise).  Dithering adds a very
small amount of shaped noise *before* quantisation so that the error becomes
random (spectrally flat or high-frequency shaped) rather than harmonic.

This module implements Triangular Probability Density Function (TPDF) dither,
which is the preferred dither type for audio because its error is completely
uncorrelated with the signal.

Reference: S. P. Lipshitz, J. Vanderkooy, R. A. Wannamaker,
           "Minimally audible noise shaping", JAES 1991.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

__all__ = ["dither"]

DitherType = Literal["tpdf", "rpdf", "none"]


def dither(
    signal: np.ndarray,
    bit_depth: int = 16,
    dither_type: DitherType = "tpdf",
    seed: int | None = None,
) -> np.ndarray:
    """Apply noise dithering before bit-depth quantisation.

    The signal is expected to be normalised to ``[-1, 1]`` (float32).
    After dithering, the signal is still in float32 – the caller is
    responsible for the final integer conversion.

    Parameters
    ----------
    signal:
        Float32 audio, 1-D or ``(N, 2)``.
    bit_depth:
        Target bit depth (default 16).  Used to scale the dither amplitude
        correctly to ±1 LSB.
    dither_type:
        ``"tpdf"`` (default) – triangular PDF (sum of two uniform random
        variables); ``"rpdf"`` – rectangular PDF (single uniform); ``"none"``
        – no dither (pass-through).
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    np.ndarray
        Dithered float32 signal, same shape as input.

    Example
    -------
    >>> dithered = dither(audio, bit_depth=16)
    """
    if dither_type == "none":
        return signal.copy()

    rng = np.random.default_rng(seed)

    # 1 LSB in float32 at the given bit depth
    lsb = 2.0 / (2 ** bit_depth)

    if dither_type == "tpdf":
        # TPDF = sum of two uniform (−0.5, 0.5) distributions → triangle
        noise = (rng.random(signal.shape) - 0.5) + (rng.random(signal.shape) - 0.5)
    elif dither_type == "rpdf":
        noise = rng.random(signal.shape) - 0.5
    else:
        raise ValueError(f"Unknown dither_type '{dither_type}'")

    return (signal.astype(np.float64) + noise * lsb).astype(np.float32)
