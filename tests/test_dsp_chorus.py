from __future__ import annotations

import numpy as np

from audio_engine.dsp.chorus import apply_chorus


def test_chorus_returns_stereo_with_same_length():
    mono = np.ones(4000, dtype=np.float32) * 0.1
    out = apply_chorus(mono, sample_rate=22050, mix=0.4)
    assert out.ndim == 2
    assert out.shape[0] == mono.shape[0]
    assert out.shape[1] == 2


def test_chorus_mix_zero_returns_dry_stereo():
    mono = np.linspace(-0.5, 0.5, 2048, dtype=np.float32)
    out = apply_chorus(mono, sample_rate=22050, mix=0.0)
    expected = np.stack([mono, mono], axis=1)
    np.testing.assert_allclose(out, expected, atol=1e-6)
