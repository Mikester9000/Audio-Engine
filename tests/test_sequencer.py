"""Tests for the Sequencer class."""

import numpy as np
import pytest

from audio_engine.composer.sequencer import Note, Sequencer
from audio_engine.synthesizer.instrument import InstrumentLibrary

SR = 22050


def _piano(sr: int = SR):
    return InstrumentLibrary.get("piano", sr)


def test_beat_duration():
    seq = Sequencer(bpm=120, sample_rate=SR)
    assert abs(seq.beat_duration - 0.5) < 1e-9


def test_bar_duration_4_4():
    seq = Sequencer(bpm=120, time_signature=4, sample_rate=SR)
    assert abs(seq.bar_duration - 2.0) < 1e-9


def test_add_track_and_note():
    seq = Sequencer(bpm=120, sample_rate=SR)
    seq.add_track("piano", _piano())
    seq.add_note("piano", 440.0, 0.0, 0.5)
    assert len(seq._tracks["piano"].notes) == 1


def test_add_note_unknown_track_raises():
    seq = Sequencer(sample_rate=SR)
    with pytest.raises(KeyError):
        seq.add_note("nonexistent", 440.0, 0.0, 0.5)


def test_render_stereo_shape():
    seq = Sequencer(bpm=120, sample_rate=SR)
    seq.add_track("piano", _piano())
    seq.add_note("piano", 440.0, 0.0, 0.5)
    audio = seq.render()
    assert audio.ndim == 2
    assert audio.shape[1] == 2


def test_render_dtype():
    seq = Sequencer(bpm=120, sample_rate=SR)
    seq.add_track("piano", _piano())
    seq.add_note("piano", 440.0, 0.0, 0.5)
    audio = seq.render()
    assert audio.dtype == np.float32


def test_render_empty():
    seq = Sequencer(sample_rate=SR)
    audio = seq.render()
    assert audio.shape == (0, 2)


def test_render_custom_duration():
    seq = Sequencer(bpm=120, sample_rate=SR)
    seq.add_track("piano", _piano())
    seq.add_note("piano", 440.0, 0.0, 0.3)
    audio = seq.render(duration=2.0)
    assert len(audio) == int(2.0 * SR)


def test_render_amplitude_bounded():
    seq = Sequencer(bpm=120, sample_rate=SR)
    seq.add_track("piano", _piano())
    for i in range(10):
        seq.add_note("piano", 440.0, i * 0.1, 0.1)
    audio = seq.render()
    assert np.max(np.abs(audio)) <= 1.0 + 1e-5


def test_clear_track():
    seq = Sequencer(bpm=120, sample_rate=SR)
    seq.add_track("piano", _piano())
    seq.add_note("piano", 440.0, 0.0, 0.5)
    seq.clear_track("piano")
    assert len(seq._tracks["piano"].notes) == 0


def test_add_notes_bulk():
    seq = Sequencer(bpm=120, sample_rate=SR)
    seq.add_track("piano", _piano())
    notes = [Note(440.0, 0.0, 0.2), Note(880.0, 0.3, 0.2)]
    seq.add_notes("piano", notes)
    assert len(seq._tracks["piano"].notes) == 2
