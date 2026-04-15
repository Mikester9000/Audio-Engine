"""Tests for Scale and ScaleLibrary."""

import pytest

from audio_engine.composer.scale import Scale, ScaleLibrary, midi_to_freq


def test_midi_to_freq_a4():
    assert abs(midi_to_freq(69) - 440.0) < 1e-6


def test_midi_to_freq_c4():
    assert abs(midi_to_freq(60) - 261.626) < 0.01


def test_scale_notes_length():
    scale = ScaleLibrary.get("major", "C", 4)
    assert len(scale.notes) == 7


def test_scale_frequencies_positive():
    scale = ScaleLibrary.get("natural_minor", "A", 4)
    for f in scale.frequencies:
        assert f > 0.0


def test_scale_degree_1_is_root():
    scale = ScaleLibrary.get("major", "A", 4)
    assert abs(scale.degree(1) - 440.0) < 1e-6


def test_scale_degree_wraps_octave():
    scale = ScaleLibrary.get("major", "C", 4)
    # Degree 8 should be an octave above degree 1
    assert abs(scale.degree(8) - scale.degree(1) * 2.0) < 0.01


def test_unknown_scale_raises():
    with pytest.raises(KeyError):
        ScaleLibrary.get("nonexistent_scale_xyz")


def test_unknown_root_raises():
    with pytest.raises(ValueError):
        Scale("Z", [0, 2, 4])


def test_available_scales_non_empty():
    assert len(ScaleLibrary.available()) > 0
