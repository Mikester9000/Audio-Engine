"""Tests for the Effects class."""

import numpy as np
import pytest

from audio_engine.synthesizer.effects import Effects

SR = 22050
FX = Effects(sample_rate=SR)


def _sine(freq: float = 440.0, duration: float = 0.5) -> np.ndarray:
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def test_reverb_output_length():
    sig = _sine()
    out = FX.reverb(sig, room_size=0.3, wet=0.3)
    assert len(out) == len(sig)


def test_reverb_dtype():
    out = FX.reverb(_sine())
    assert out.dtype == np.float32


def test_delay_output_length():
    sig = _sine()
    out = FX.delay(sig, delay_time=0.1, feedback=0.3)
    assert len(out) == len(sig)


def test_chorus_output_length():
    sig = _sine()
    out = FX.chorus(sig, rate=1.0, depth=0.002)
    assert len(out) == len(sig)


def test_distortion_clips_within_range():
    sig = _sine()
    out = FX.distortion(sig, drive=10.0)
    assert np.max(np.abs(out)) <= 1.0 + 1e-5


def test_compress_reduces_peak():
    rng = np.random.default_rng(5)
    loud = rng.standard_normal(SR).astype(np.float32)
    loud /= np.max(np.abs(loud))
    compressed = FX.compress(loud, threshold=0.3, ratio=8.0)
    assert np.max(np.abs(compressed)) < np.max(np.abs(loud)) + 0.1


def test_normalise():
    sig = _sine() * 0.1
    out = FX.normalise(sig, target=0.9)
    assert abs(np.max(np.abs(out)) - 0.9) < 1e-4


def test_normalise_silent():
    silent = np.zeros(512, dtype=np.float32)
    out = FX.normalise(silent)
    np.testing.assert_array_equal(out, silent)
