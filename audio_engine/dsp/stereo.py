"""Stereo imaging helpers."""

from __future__ import annotations

import numpy as np

__all__ = ["apply_haas", "apply_mid_side_width"]


def _as_stereo(audio: np.ndarray) -> np.ndarray:
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 1:
        return np.stack([arr, arr], axis=1)
    if arr.ndim == 2 and arr.shape[1] == 2:
        return arr
    if arr.ndim == 2 and arr.shape[0] == 2:
        return arr.T
    flat = arr.reshape(-1)
    return np.stack([flat, flat], axis=1)


def apply_haas(audio: np.ndarray, sample_rate: int, delay_ms: float = 15.0) -> np.ndarray:
    """Create stereo width by delaying right channel slightly."""
    stereo = _as_stereo(audio).copy()
    delay_samples = int(max(0.0, delay_ms) * sample_rate / 1000.0)
    if delay_samples <= 0 or delay_samples >= stereo.shape[0]:
        return stereo
    stereo[delay_samples:, 1] = stereo[:-delay_samples, 1]
    stereo[:delay_samples, 1] = 0.0
    return stereo.astype(np.float32, copy=False)


def apply_mid_side_width(audio: np.ndarray, width: float = 1.2) -> np.ndarray:
    """Adjust stereo width using M/S matrix."""
    stereo = _as_stereo(audio)
    if np.isclose(width, 1.0):
        return stereo.astype(np.float32, copy=False)

    left = stereo[:, 0].astype(np.float64)
    right = stereo[:, 1].astype(np.float64)
    mid = 0.5 * (left + right)
    side = 0.5 * (left - right) * float(width)
    out_left = mid + side
    out_right = mid - side
    out = np.stack([out_left, out_right], axis=1)
    return np.clip(out, -1.0, 1.0).astype(np.float32)
