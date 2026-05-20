"""
Pitch-shift helpers for deterministic sample remaster workflows.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = [
    "pitch_ratio_from_midi",
    "pitch_shift_midi",
    "pitch_shift_ratio",
    "pitch_shift_semitones",
    "semitone_ratio",
]


def semitone_ratio(semitones: float) -> float:
    """Return playback-rate ratio for a semitone interval."""
    return float(2.0 ** (float(semitones) / 12.0))


def pitch_ratio_from_midi(source_midi: int, target_midi: int) -> float:
    """Return playback-rate ratio from source note to target note."""
    return semitone_ratio(float(target_midi) - float(source_midi))


def pitch_shift_semitones(audio: np.ndarray, semitones: float) -> np.ndarray:
    """Pitch-shift by semitones while preserving output length."""
    return pitch_shift_ratio(audio, semitone_ratio(semitones))


def pitch_shift_midi(audio: np.ndarray, source_midi: int, target_midi: int) -> np.ndarray:
    """Pitch-shift from source MIDI note to target MIDI note."""
    return pitch_shift_ratio(audio, pitch_ratio_from_midi(source_midi, target_midi))


def pitch_shift_ratio(audio: np.ndarray, ratio: float) -> np.ndarray:
    """Pitch-shift by playback-rate ratio while preserving length."""
    signal = np.asarray(audio, dtype=np.float32)
    if signal.ndim == 2:
        if signal.shape[1] != 2:
            raise ValueError(f"stereo signal must have shape (N, 2), got {signal.shape}")
        left = _pitch_shift_1d(signal[:, 0], ratio)
        right = _pitch_shift_1d(signal[:, 1], ratio)
        return np.column_stack([left, right]).astype(np.float32)
    if signal.ndim != 1:
        raise ValueError(f"audio must be 1-D or stereo (N,2), got shape {signal.shape}")
    return _pitch_shift_1d(signal, ratio)


def _pitch_shift_1d(audio: np.ndarray, ratio: float) -> np.ndarray:
    ratio = float(ratio)
    if not math.isfinite(ratio) or ratio <= 0.0:
        raise ValueError(f"ratio must be a positive finite number, got {ratio!r}")

    if abs(ratio - 1.0) < 1e-6:
        return audio.astype(np.float32, copy=True)

    n = len(audio)
    if n == 0:
        return audio.astype(np.float32, copy=True)

    new_len = max(1, int(n / ratio))
    try:
        from scipy.signal import resample  # type: ignore[import]

        shifted = resample(audio.astype(np.float64), new_len).astype(np.float32)
    except ImportError:
        shifted = np.interp(
            np.linspace(0, n - 1, new_len),
            np.arange(n),
            audio.astype(np.float64),
        ).astype(np.float32)

    if len(shifted) >= n:
        return shifted[:n]
    return np.concatenate([shifted, np.zeros(n - len(shifted), dtype=np.float32)])
