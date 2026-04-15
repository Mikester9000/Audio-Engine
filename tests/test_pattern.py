"""Tests for RhythmPattern."""

import pytest

from audio_engine.composer.pattern import RhythmPattern


def test_four_on_floor_beats():
    p = RhythmPattern.four_on_the_floor()
    assert len(p.beats) == 4


def test_note_durations_sum_to_bar():
    p = RhythmPattern.eighth_notes()
    bar_dur = 2.0
    durations = p.note_durations(bar_dur)
    total = sum(d for _, d in durations)
    assert abs(total - bar_dur) < 1e-6


def test_note_durations_onsets_in_range():
    p = RhythmPattern.syncopated()
    bar_dur = 1.5
    for onset, dur in p.note_durations(bar_dur):
        assert 0.0 <= onset < bar_dur
        assert dur > 0.0


def test_empty_pattern_returns_empty_durations():
    p = RhythmPattern([])
    assert p.note_durations(1.0) == []


def test_ambient_single_beat():
    p = RhythmPattern.ambient()
    assert len(p.beats) == 1
    assert p.beats[0] == 0.0


def test_battle_pattern_has_hits():
    p = RhythmPattern.battle()
    assert len(p.beats) >= 4


def test_half_notes_has_two_beats():
    p = RhythmPattern.half_notes()
    assert len(p.beats) == 2


def test_deduplication():
    p = RhythmPattern([0.0, 0.0, 0.5, 0.5])
    assert len(p.beats) == 2
