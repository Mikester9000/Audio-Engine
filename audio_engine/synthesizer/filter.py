"""
Filter – low-pass, high-pass, band-pass, and notch filters.

Built on top of scipy.signal's Butterworth IIR filter design so the audio
quality is comparable to professional synthesisers.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt  # type: ignore[import]

__all__ = ["Filter"]

_MAX_DESIGN_CACHE_SIZE = 16


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
        self._design_cache: dict[tuple[str, float], np.ndarray] = {}

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

    def resonant_low_pass(
        self,
        signal: np.ndarray,
        cutoff: float,
        resonance: float = 1.0,
    ) -> np.ndarray:
        """Resonant (Moog-style) low-pass filter with a peak at *cutoff*.

        Parameters
        ----------
        cutoff:
            Cutoff frequency in Hz.
        resonance:
            Q-factor / resonance amount.  Values 0.5–4.0 are useful;
            higher values emphasise the cutoff frequency (PS2-era warmth).
        """
        from scipy.signal import sosfilt, zpk2sos  # type: ignore[import]

        nyq = self.sample_rate / 2.0
        wn = float(np.clip(cutoff / nyq, 1e-4, 0.9999))
        Q = float(np.clip(resonance, 0.1, 20.0))
        # 2-pole peaking LP (state-variable style via biquad)
        # Use a Butterworth LP then boost the cutoff region slightly
        from scipy.signal import butter
        sos = butter(2, wn, btype="low", output="sos")
        out = sosfilt(sos, signal.astype(np.float64))
        if resonance > 1.2:
            # Boost a narrow band around cutoff to create the resonant peak
            bw_hz = max(30.0, cutoff / Q)
            peak_band = self.band_pass(
                signal.astype(np.float32),
                max(20.0, cutoff - bw_hz),
                min(nyq * 0.999, cutoff + bw_hz),
            )
            boost = min((resonance - 1.0) * 0.35, 2.0)
            out = out + boost * peak_band.astype(np.float64)
        return out.astype(np.float32)

    def warm_low_pass(self, signal: np.ndarray, cutoff: float) -> np.ndarray:
        """A gentle 2-pole low-pass with mild saturation for analogue warmth.

        Suitable for softening harsh digital waveforms to a PS2-era character.
        """
        filtered = self.low_pass(signal, cutoff)
        # Mild tanh soft-clip that adds second-harmonic character
        out = np.tanh(filtered.astype(np.float64) * 1.05) / np.tanh(1.05)
        return out.astype(np.float32)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _design(self, btype: str, cutoff: float) -> np.ndarray:
        key = (btype, cutoff)
        cached = self._design_cache.get(key)
        if cached is not None:
            return cached
        nyq = self.sample_rate / 2.0
        normalised = np.clip(cutoff / nyq, 1e-6, 1.0 - 1e-6)
        sos = butter(self.order, normalised, btype=btype, output="sos")
        if len(self._design_cache) >= _MAX_DESIGN_CACHE_SIZE:
            self._design_cache.pop(next(iter(self._design_cache)))
        self._design_cache[key] = sos
        return sos
