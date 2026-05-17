"""Loop export helpers."""

from __future__ import annotations

import numpy as np

__all__ = ["bake_crossfade_loop"]


def bake_crossfade_loop(audio: np.ndarray, sample_rate: int, crossfade_ms: float = 500) -> np.ndarray:
    """Blend tail audio into the beginning to reduce loop-point discontinuities."""
    arr = np.asarray(audio, dtype=np.float32).copy()
    crossfade_samples = int(max(0.0, crossfade_ms) * sample_rate / 1000.0)
    if crossfade_samples <= 0:
        return arr
    if arr.shape[0] <= crossfade_samples:
        return arr

    fade = np.linspace(1.0 / crossfade_samples, 1.0, crossfade_samples, dtype=np.float32)
    if arr.ndim == 1:
        arr[:crossfade_samples] = (
            arr[:crossfade_samples] * (1.0 - fade) + arr[-crossfade_samples:] * fade
        )
        return arr

    if arr.ndim == 2:
        fade = fade[:, None]
        arr[:crossfade_samples, :] = (
            arr[:crossfade_samples, :] * (1.0 - fade) + arr[-crossfade_samples:, :] * fade
        )
        return arr

    return arr
