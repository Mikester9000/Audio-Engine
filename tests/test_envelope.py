"""Tests for the Envelope class."""

import numpy as np
import pytest

from audio_engine.synthesizer.envelope import Envelope

SR = 22050


def _make_signal(duration: float, sr: int = SR) -> np.ndarray:
    return np.ones(int(duration * sr), dtype=np.float32)


def test_apply_length():
    env = Envelope(sample_rate=SR)
    sig = _make_signal(1.0)
    out = env.apply(sig, 1.0)
    assert len(out) == len(sig)


def test_apply_starts_at_zero():
    env = Envelope(attack=0.1, sample_rate=SR)
    sig = _make_signal(1.0)
    out = env.apply(sig, 1.0)
    assert out[0] < 0.05


def test_apply_ends_at_zero():
    env = Envelope(release=0.2, sample_rate=SR)
    sig = _make_signal(1.0)
    out = env.apply(sig, 1.0)
    assert out[-1] < 0.05


def test_sustain_range():
    env = Envelope(attack=0.01, decay=0.01, sustain=0.5, release=0.01, sample_rate=SR)
    sig = _make_signal(1.0)
    out = env.apply(sig, 1.0)
    # In the sustain region the value should be close to 0.5
    mid = len(out) // 2
    assert 0.4 < out[mid] < 0.6


def test_invalid_sustain():
    with pytest.raises(ValueError):
        Envelope(sustain=1.5)


def test_percussive_factory():
    env = Envelope.percussive(SR)
    assert env.sustain == 0.0


def test_pad_factory():
    env = Envelope.pad(SR)
    assert env.attack > 0.3


def test_pluck_factory():
    env = Envelope.pluck(SR)
    assert env.attack < 0.01


def test_brass_factory():
    env = Envelope.brass(SR)
    assert env.sustain > 0.8
