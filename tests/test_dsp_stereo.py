from __future__ import annotations

import numpy as np

from audio_engine.dsp.stereo import apply_haas, apply_mid_side_width


def test_haas_returns_stereo():
    mono = np.ones(3000, dtype=np.float32) * 0.2
    out = apply_haas(mono, sample_rate=22050, delay_ms=15.0)
    assert out.ndim == 2
    assert out.shape == (mono.shape[0], 2)


def test_mid_side_width_identity_at_one():
    stereo = np.stack(
        [np.linspace(-1, 1, 2048, dtype=np.float32), np.linspace(1, -1, 2048, dtype=np.float32)],
        axis=1,
    )
    out = apply_mid_side_width(stereo, width=1.0)
    np.testing.assert_allclose(out, stereo, atol=1e-6)


def test_mid_side_width_above_one_widens():
    t = np.linspace(0, 1, 2048, dtype=np.float32)
    stereo = np.stack([t, t * 0.8], axis=1)
    before = np.mean(np.abs(stereo[:, 0] - stereo[:, 1]))
    out = apply_mid_side_width(stereo, width=1.5)
    after = np.mean(np.abs(out[:, 0] - out[:, 1]))
    assert after > before
