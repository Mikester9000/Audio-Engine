"""
Filter – low-pass, high-pass, band-pass, and notch filters.

Built on top of scipy.signal's Butterworth IIR filter design so the audio
quality is comparable to professional synthesisers.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt  # type: ignore[import]

__all__ = ["Filter"]


class Filter:
    """Stateless biquad-style filter bank.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    order:
        Butterworth filter order (higher → steeper roll-off, more CPU).
    """

    def __init__(self, sample_rate: int = 44100, order: int = 4) -> None:
        self.sample_rate = sample_rate
        self.order = order

    # ------------------------------------------------------------------
    # Public filter methods
    # ------------------------------------------------------------------

    def low_pass(self, signal: np.ndarray, cutoff: float) -> np.ndarray:
        """Remove frequencies above *cutoff* Hz."""
        sos = self._design("low", cutoff)
        return sosfilt(sos, signal).astype(np.float32)

    def high_pass(self, signal: np.ndarray, cutoff: float) -> np.ndarray:
        """Remove frequencies below *cutoff* Hz."""
        sos = self._design("high", cutoff)
        return sosfilt(sos, signal).astype(np.float32)

    def band_pass(self, signal: np.ndarray, low: float, high: float) -> np.ndarray:
        """Keep only frequencies between *low* and *high* Hz."""
        nyq = self.sample_rate / 2.0
        low_n = max(low / nyq, 1e-6)
        high_n = min(high / nyq, 1.0 - 1e-6)
        sos = butter(self.order, [low_n, high_n], btype="bandpass", output="sos")
        return sosfilt(sos, signal).astype(np.float32)

    def notch(self, signal: np.ndarray, center: float, bandwidth: float = 50.0) -> np.ndarray:
        """Attenuate a narrow band of frequencies around *center* Hz."""
        low = center - bandwidth / 2.0
        high = center + bandwidth / 2.0
        return signal - self.band_pass(signal, max(low, 1.0), high)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _design(self, btype: str, cutoff: float) -> np.ndarray:
        nyq = self.sample_rate / 2.0
        normalised = np.clip(cutoff / nyq, 1e-6, 1.0 - 1e-6)
        return butter(self.order, normalised, btype=btype, output="sos")
