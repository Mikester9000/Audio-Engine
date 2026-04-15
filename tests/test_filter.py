"""Tests for the Filter class."""

import numpy as np
import pytest

from audio_engine.synthesizer.filter import Filter

SR = 22050
FLT = Filter(sample_rate=SR, order=4)


def _white_noise(n: int = SR) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.standard_normal(n).astype(np.float32)


def _energy_above(signal: np.ndarray, cutoff_hz: float, sr: int = SR) -> float:
    """Fraction of signal energy in frequency bins above *cutoff_hz*."""
    spec = np.abs(np.fft.rfft(signal)) ** 2
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sr)
    above = spec[freqs > cutoff_hz].sum()
    total = spec.sum() + 1e-12
    return float(above / total)


def test_low_pass_attenuates_high_freq():
    noise = _white_noise()
    filtered = FLT.low_pass(noise, cutoff=500.0)
    assert _energy_above(filtered, 2000.0) < _energy_above(noise, 2000.0)


def test_high_pass_attenuates_low_freq():
    noise = _white_noise()
    filtered = FLT.high_pass(noise, cutoff=4000.0)
    # Energy in low bins should drop after high-pass
    def energy_below(sig: np.ndarray, hz: float) -> float:
        spec = np.abs(np.fft.rfft(sig)) ** 2
        freqs = np.fft.rfftfreq(len(sig), 1.0 / SR)
        return float(spec[freqs < hz].sum() / (spec.sum() + 1e-12))

    assert energy_below(filtered, 1000.0) < energy_below(noise, 1000.0)


def test_band_pass_output_length():
    noise = _white_noise(1024)
    out = FLT.band_pass(noise, 300.0, 3000.0)
    assert len(out) == 1024


def test_notch_output_length():
    noise = _white_noise(1024)
    out = FLT.notch(noise, center=1000.0)
    assert len(out) == 1024


def test_low_pass_output_dtype():
    noise = _white_noise(512)
    out = FLT.low_pass(noise, 1000.0)
    assert out.dtype == np.float32
