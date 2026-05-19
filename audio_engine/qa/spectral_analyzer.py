"""
Spectral balance and intelligibility analyser for audio QA.

Measures energy distribution across frequency bands (lows / mids / highs) to
detect severely imbalanced mixes, and estimates a basic spectral clarity index
useful as a coarse intelligibility proxy for voice/SFX assets.

Band definitions (approximate, game-audio oriented):
  - Low   : < 250 Hz   – bass/sub content
  - Mid   : 250–4000 Hz – fundamental harmonics, speech/instrument body
  - High  : > 4000 Hz  – air/presence, consonants, transient detail

These checks are *additive* to the existing loudness, peak, and clipping gates.
They do not replace listening review; they surface obvious spectral problems
automatically so review effort can be focused on borderline cases.

Usage
-----
>>> from audio_engine.qa import SpectralAnalyzer
>>> sa = SpectralAnalyzer(sample_rate=44100)
>>> report = sa.analyze(audio)
>>> print(report.summary())
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["SpectralAnalyzer", "SpectralReport"]


@dataclass
class SpectralReport:
    """Result from a spectral balance analysis.

    Attributes
    ----------
    low_ratio:
        Fraction of total spectral energy below *low_cutoff* Hz (0–1).
    mid_ratio:
        Fraction of total spectral energy in the mid band (0–1).
    high_ratio:
        Fraction of total spectral energy above *high_cutoff* Hz (0–1).
    spectral_centroid_hz:
        Frequency-weighted centroid of the power spectrum in Hz.
    high_freq_ratio:
        Ratio of high-frequency energy (> 2 kHz) to total energy.
        High values indicate presence/air; very low values suggest muddy mix.
    spectral_balance_ok:
        ``True`` if none of the bands are severely dominant (no single band
        carries > *max_band_ratio* of total energy, default 0.90).
    intelligibility_ok:
        ``True`` if ``high_freq_ratio`` is above *min_hf_ratio* (default 0.02),
        indicating sufficient high-frequency content for voice/SFX clarity.
    """

    low_ratio: float
    mid_ratio: float
    high_ratio: float
    spectral_centroid_hz: float
    high_freq_ratio: float
    spectral_balance_ok: bool
    intelligibility_ok: bool

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        bal = "OK" if self.spectral_balance_ok else "IMBALANCED"
        intel = "OK" if self.intelligibility_ok else "LOW-HF"
        return (
            f"Spectral {bal} / Intelligibility {intel} – "
            f"L:{self.low_ratio:.2f} M:{self.mid_ratio:.2f} H:{self.high_ratio:.2f} "
            f"centroid:{self.spectral_centroid_hz:.0f} Hz"
        )


class SpectralAnalyzer:
    """Analyse spectral balance and intelligibility of audio.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    low_cutoff:
        Upper frequency of the "low" band in Hz (default 250 Hz).
    high_cutoff:
        Lower frequency of the "high" band in Hz (default 4000 Hz).
    max_band_ratio:
        If any single band carries more than this fraction of total energy,
        :attr:`SpectralReport.spectral_balance_ok` is ``False`` (default 0.90).
    min_hf_ratio:
        Minimum acceptable high-frequency ratio (> 2 kHz / total) for
        :attr:`SpectralReport.intelligibility_ok` to be ``True`` (default 0.02).

    Example
    -------
    >>> sa = SpectralAnalyzer(sample_rate=44100)
    >>> report = sa.analyze(audio)
    >>> print(report.summary())
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        low_cutoff: float = 250.0,
        high_cutoff: float = 4000.0,
        max_band_ratio: float = 0.90,
        min_hf_ratio: float = 0.02,
    ) -> None:
        self.sample_rate = sample_rate
        self.low_cutoff = low_cutoff
        self.high_cutoff = high_cutoff
        self.max_band_ratio = max_band_ratio
        self.min_hf_ratio = min_hf_ratio

    def analyze(self, audio: np.ndarray) -> SpectralReport:
        """Analyse spectral balance of *audio*.

        Parameters
        ----------
        audio:
            Float32 array, 1-D (mono) or ``(N, 2)`` (stereo).

        Returns
        -------
        :class:`SpectralReport`
        """
        # Convert to mono float64
        sig = np.asarray(audio, dtype=np.float64)
        if sig.ndim == 2:
            sig = np.mean(sig, axis=1)

        n = len(sig)
        if n < 2:
            return SpectralReport(
                low_ratio=0.0,
                mid_ratio=0.0,
                high_ratio=0.0,
                spectral_centroid_hz=0.0,
                high_freq_ratio=0.0,
                spectral_balance_ok=True,
                intelligibility_ok=False,
            )

        # Real FFT – use a window to reduce spectral leakage
        window = np.hanning(n)
        fft_vals = np.fft.rfft(sig * window)
        power = np.abs(fft_vals) ** 2

        freqs = np.fft.rfftfreq(n, d=1.0 / self.sample_rate)

        total_power = float(np.sum(power))
        if total_power < 1e-30:
            # Silence – treat as balanced with no high-frequency content
            return SpectralReport(
                low_ratio=0.0,
                mid_ratio=0.0,
                high_ratio=0.0,
                spectral_centroid_hz=0.0,
                high_freq_ratio=0.0,
                spectral_balance_ok=True,
                intelligibility_ok=False,
            )

        # Band energy fractions
        low_mask = freqs < self.low_cutoff
        mid_mask = (freqs >= self.low_cutoff) & (freqs < self.high_cutoff)
        high_mask = freqs >= self.high_cutoff

        low_ratio = float(np.sum(power[low_mask])) / total_power
        mid_ratio = float(np.sum(power[mid_mask])) / total_power
        high_ratio = float(np.sum(power[high_mask])) / total_power

        # Spectral centroid
        centroid = float(np.sum(freqs * power) / total_power)

        # High-frequency ratio (> 2 kHz) for intelligibility proxy
        hf_mask = freqs > 2000.0
        hf_ratio = float(np.sum(power[hf_mask])) / total_power

        # Gate checks
        max_band = max(low_ratio, mid_ratio, high_ratio)
        balance_ok = max_band <= self.max_band_ratio
        intel_ok = hf_ratio >= self.min_hf_ratio

        return SpectralReport(
            low_ratio=round(low_ratio, 4),
            mid_ratio=round(mid_ratio, 4),
            high_ratio=round(high_ratio, 4),
            spectral_centroid_hz=round(centroid, 2),
            high_freq_ratio=round(hf_ratio, 4),
            spectral_balance_ok=balance_ok,
            intelligibility_ok=intel_ok,
        )
