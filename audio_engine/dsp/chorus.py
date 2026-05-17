"""Stereo chorus effect."""

from __future__ import annotations

import numpy as np

__all__ = ["apply_chorus"]


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


def apply_chorus(
    audio: np.ndarray,
    sample_rate: int,
    depth: float = 0.003,
    rate: float = 0.5,
    mix: float = 0.3,
) -> np.ndarray:
    """Apply a 3-voice modulated-delay stereo chorus."""
    mix = float(np.clip(mix, 0.0, 1.0))
    if mix <= 0.0:
        return _as_stereo(audio)

    stereo = _as_stereo(audio)
    n = stereo.shape[0]
    t = np.arange(n, dtype=np.float32) / float(sample_rate)
    base_delays = np.array([0.015, 0.020, 0.025], dtype=np.float32)
    phases = np.array([0.0, np.pi * 0.7, np.pi * 1.4], dtype=np.float32)
    pans = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
    dry = stereo.astype(np.float64)
    wet = np.zeros_like(dry)

    mono = np.mean(dry, axis=1)
    for base_delay, phase, pan in zip(base_delays, phases, pans):
        delay_sec = base_delay + (depth * np.sin(2.0 * np.pi * rate * t + phase))
        delay_samples = np.clip((delay_sec * sample_rate).astype(np.int32), 1, n - 1)
        idx = np.arange(n) - delay_samples
        idx[idx < 0] = 0
        delayed = mono[idx]
        left_gain = (1.0 - pan) * 0.5
        right_gain = (1.0 + pan) * 0.5
        wet[:, 0] += delayed * left_gain
        wet[:, 1] += delayed * right_gain

    wet /= 3.0
    out = (1.0 - mix) * dry + mix * wet
    return np.clip(out, -1.0, 1.0).astype(np.float32)
