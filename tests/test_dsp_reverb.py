from __future__ import annotations

import numpy as np

from audio_engine.dsp.reverb import apply_reverb


def test_reverb_same_length():
    mono = np.sin(np.linspace(0, 20, 5000, dtype=np.float32))
    out = apply_reverb(mono, sample_rate=22050, preset="medium_hall", mix=0.25)
    assert out.shape == mono.shape


def test_reverb_presets_do_not_crash():
    mono = np.ones(3000, dtype=np.float32) * 0.1
    for preset in ("small_room", "medium_hall", "large_hall", "cathedral"):
        out = apply_reverb(mono, sample_rate=22050, preset=preset, mix=0.2)
        assert out.shape == mono.shape


def test_reverb_mix_zero_is_dry():
    mono = np.linspace(-1, 1, 1024, dtype=np.float32)
    out = apply_reverb(mono, sample_rate=22050, mix=0.0)
    np.testing.assert_allclose(out, mono, atol=1e-6)
