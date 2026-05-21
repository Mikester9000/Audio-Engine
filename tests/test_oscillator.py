"""Tests for the Oscillator class."""

import numpy as np
import pytest

from audio_engine.synthesizer.oscillator import Oscillator

SR = 22050
OSC = Oscillator(sample_rate=SR)


def test_sine_length():
    sig = OSC.sine(440.0, 1.0)
    assert len(sig) == SR


def test_sine_amplitude():
    sig = OSC.sine(440.0, 1.0, amplitude=0.5)
    assert np.max(np.abs(sig)) <= 0.5 + 1e-6


def test_square_length():
    sig = OSC.square(440.0, 0.5)
    assert len(sig) == SR // 2


def test_sawtooth_length():
    sig = OSC.sawtooth(220.0, 0.25)
    assert len(sig) == SR // 4


def test_triangle_length():
    sig = OSC.triangle(110.0, 2.0)
    assert len(sig) == 2 * SR


def test_noise_length():
    sig = OSC.noise(1.0)
    assert len(sig) == SR


def test_noise_deterministic():
    a = OSC.noise(0.5, seed=42)
    b = OSC.noise(0.5, seed=42)
    np.testing.assert_array_equal(a, b)


def test_additive_normalised():
    harmonics = [(1, 1.0), (2, 0.5), (3, 0.25)]
    sig = OSC.additive(440.0, 0.5, harmonics, amplitude=0.8)
    assert np.max(np.abs(sig)) <= 0.8 + 1e-6


def test_fm_length():
    sig = OSC.fm(440.0, 880.0, 1.0)
    assert len(sig) == SR


def test_pulse_alias():
    p = OSC.pulse(440.0, 0.5, pulse_width=0.25)
    q = OSC.square(440.0, 0.5, duty_cycle=0.25)
    np.testing.assert_array_almost_equal(p, q)


# ------------------------------------------------------------------
# Band-limited oscillator tests
# ------------------------------------------------------------------

def _energy_above(sig: np.ndarray, cutoff_hz: float, sr: int = SR) -> float:
    """Fraction of signal energy in frequency bins above *cutoff_hz*."""
    spec = np.abs(np.fft.rfft(sig)) ** 2
    freqs = np.fft.rfftfreq(len(sig), 1.0 / sr)
    above = spec[freqs > cutoff_hz].sum()
    total = spec.sum() + 1e-12
    return float(above / total)


def test_bl_sawtooth_length():
    sig = OSC.bl_sawtooth(440.0, 1.0)
    assert len(sig) == SR


def test_bl_sawtooth_dtype():
    sig = OSC.bl_sawtooth(440.0, 1.0)
    assert sig.dtype == np.float32


def test_bl_sawtooth_peak_normalised():
    sig = OSC.bl_sawtooth(440.0, 1.0, amplitude=0.8)
    assert np.max(np.abs(sig)) <= 0.8 + 1e-6


def test_bl_sawtooth_alias_suppression():
    """BL sawtooth should have less high-frequency energy than the raw scipy version."""
    raw = OSC.sawtooth(440.0, 1.0)
    bl = OSC.bl_sawtooth(440.0, 1.0)
    assert _energy_above(bl, 8000.0) < _energy_above(raw, 8000.0)


def test_bl_square_length():
    sig = OSC.bl_square(440.0, 1.0)
    assert len(sig) == SR


def test_bl_square_dtype():
    sig = OSC.bl_square(440.0, 1.0)
    assert sig.dtype == np.float32


def test_bl_square_peak_normalised():
    sig = OSC.bl_square(440.0, 1.0, amplitude=0.7)
    assert np.max(np.abs(sig)) <= 0.7 + 1e-6


def test_bl_square_alias_suppression():
    """BL square should have less high-frequency energy than the raw square."""
    raw = OSC.square(440.0, 1.0)
    bl = OSC.bl_square(440.0, 1.0)
    assert _energy_above(bl, 8000.0) < _energy_above(raw, 8000.0)


def test_bl_triangle_length():
    sig = OSC.bl_triangle(440.0, 1.0)
    assert len(sig) == SR


def test_bl_triangle_dtype():
    sig = OSC.bl_triangle(440.0, 1.0)
    assert sig.dtype == np.float32


def test_bl_triangle_peak_normalised():
    sig = OSC.bl_triangle(440.0, 1.0, amplitude=0.6)
    assert np.max(np.abs(sig)) <= 0.6 + 1e-6


def test_bl_triangle_alias_suppression():
    """BL triangle should have less high-frequency energy than the raw triangle."""
    raw = OSC.triangle(440.0, 1.0)
    bl = OSC.bl_triangle(440.0, 1.0)
    assert _energy_above(bl, 8000.0) < _energy_above(raw, 8000.0)
