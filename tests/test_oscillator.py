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
