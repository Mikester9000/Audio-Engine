"""Tests for the Instrument and InstrumentLibrary classes."""

import numpy as np
import pytest

from audio_engine.synthesizer.instrument import Instrument, InstrumentLibrary

SR = 22050


def test_available_instruments_non_empty():
    names = InstrumentLibrary.available()
    assert len(names) > 0


def test_get_known_instrument():
    inst = InstrumentLibrary.get("piano", SR)
    assert isinstance(inst, Instrument)
    assert inst.name == "piano"


def test_get_unknown_raises():
    with pytest.raises(KeyError):
        InstrumentLibrary.get("nonexistent_instrument_xyz", SR)


@pytest.mark.parametrize("name", InstrumentLibrary.available())
def test_instrument_render_shape(name):
    inst = InstrumentLibrary.get(name, SR)
    audio = inst.render(440.0, 0.2)
    assert audio.ndim == 1
    assert len(audio) > 0


@pytest.mark.parametrize("name", InstrumentLibrary.available())
def test_instrument_render_amplitude(name):
    inst = InstrumentLibrary.get(name, SR)
    audio = inst.render(440.0, 0.2)
    # Rendered audio should not exceed 1.0 in absolute value
    assert np.max(np.abs(audio)) <= 1.0 + 1e-5


@pytest.mark.parametrize("name", InstrumentLibrary.available())
def test_instrument_render_dtype(name):
    inst = InstrumentLibrary.get(name, SR)
    audio = inst.render(440.0, 0.2)
    assert audio.dtype == np.float32
