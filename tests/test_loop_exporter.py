from __future__ import annotations

import numpy as np

from audio_engine.render.loop_exporter import bake_crossfade_loop


def test_crossfade_loop_same_length():
    stereo = np.zeros((44100, 2), dtype=np.float32)
    stereo[:1000] = 1.0
    out = bake_crossfade_loop(stereo, sample_rate=44100, crossfade_ms=500)
    assert out.shape == stereo.shape


def test_crossfade_loop_reduces_loop_discontinuity():
    mono = np.concatenate(
        [np.ones(22050, dtype=np.float32), np.zeros(22050, dtype=np.float32)],
    )
    before = abs(float(mono[0] - mono[-1]))
    out = bake_crossfade_loop(mono, sample_rate=44100, crossfade_ms=500)
    after = abs(float(out[0] - out[-1]))
    assert after < before
