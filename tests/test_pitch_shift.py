from __future__ import annotations

import numpy as np

from audio_engine.dsp.pitch_shift import (
    pitch_ratio_from_midi,
    pitch_shift_ratio,
    pitch_shift_semitones,
    semitone_ratio,
)


def _tone(sr: int = 22050, seconds: float = 0.2, hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False)
    return np.sin(2.0 * np.pi * hz * t).astype(np.float32)


def test_semitone_ratio_and_midi_ratio_match():
    assert np.isclose(semitone_ratio(12.0), 2.0)
    assert np.isclose(pitch_ratio_from_midi(60, 72), 2.0)


def test_pitch_shift_ratio_preserves_length_for_mono():
    audio = _tone()
    shifted = pitch_shift_ratio(audio, ratio=1.25)
    assert shifted.shape == audio.shape
    assert shifted.dtype == np.float32
    assert not np.allclose(audio, shifted, atol=1e-4)


def test_pitch_shift_ratio_preserves_stereo_shape():
    mono = _tone()
    stereo = np.column_stack([mono, mono])
    shifted = pitch_shift_ratio(stereo, ratio=0.75)
    assert shifted.shape == stereo.shape
    assert shifted.dtype == np.float32


def test_pitch_shift_semitones_identity():
    audio = _tone()
    shifted = pitch_shift_semitones(audio, semitones=0.0)
    np.testing.assert_allclose(audio, shifted)
