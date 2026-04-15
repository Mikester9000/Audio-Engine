"""Tests for Chord and ChordProgression."""

import pytest

from audio_engine.composer.chord import Chord, ChordProgression
from audio_engine.composer.scale import ScaleLibrary


def test_chord_major_intervals():
    c = Chord(60, "major")
    assert c.intervals == [0, 4, 7]


def test_chord_minor_intervals():
    c = Chord(60, "minor")
    assert c.intervals == [0, 3, 7]


def test_chord_midi_notes():
    c = Chord(60, "major")
    assert c.midi_notes == [60, 64, 67]


def test_chord_frequencies_positive():
    c = Chord(69, "major7")
    for f in c.frequencies:
        assert f > 0.0


def test_unknown_quality_raises():
    with pytest.raises(ValueError):
        Chord(60, "nonexistent_quality")


def test_chord_progression_chords():
    scale = ScaleLibrary.get("major", "C", 4)
    prog = ChordProgression(scale, "I_IV_V_I")
    chords = prog.chords
    assert len(chords) == 4


def test_chord_progression_custom():
    scale = ScaleLibrary.get("natural_minor", "A", 4)
    prog = ChordProgression(scale, chords=[(1, "minor"), (4, "minor")])
    assert len(prog.chords) == 2


def test_unknown_progression_raises():
    scale = ScaleLibrary.get("major", "C")
    with pytest.raises(KeyError):
        ChordProgression(scale, "nonexistent_progression_xyz")


def test_no_progression_or_chords_raises():
    scale = ScaleLibrary.get("major", "C")
    with pytest.raises(ValueError):
        ChordProgression(scale)


def test_available_progressions_non_empty():
    assert len(ChordProgression.available()) > 0
