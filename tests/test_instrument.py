"""Tests for the Instrument and InstrumentLibrary classes."""

import numpy as np
import pytest

from audio_engine.synthesizer.instrument import Instrument, InstrumentLibrary

SR = 22050


def _rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(signal.astype(np.float64)))))


def _band_energy(signal: np.ndarray, sr: int, low_hz: float, high_hz: float) -> float:
    if len(signal) == 0:
        return 0.0
    spectrum = np.fft.rfft(signal.astype(np.float64))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / sr)
    mask = (freqs >= low_hz) & (freqs < high_hz)
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs(spectrum[mask])))


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


def test_piano_transient_decay_profile():
    piano = InstrumentLibrary.get("piano", SR)
    audio = piano.render(440.0, 0.8)
    early = audio[: int(0.04 * SR)]
    late = audio[int(0.45 * SR) : int(0.75 * SR)]
    assert _rms(early) > _rms(late) * 1.9


def test_acoustic_guitar_pick_brightness_falls_after_attack():
    guitar = InstrumentLibrary.get("acoustic_guitar", SR)
    audio = guitar.render(220.0, 0.8)
    attack = audio[: int(0.06 * SR)]
    body = audio[int(0.18 * SR) : int(0.38 * SR)]
    attack_high = _band_energy(attack, SR, 2500.0, 8500.0)
    body_high = _band_energy(body, SR, 2500.0, 8500.0)
    assert attack_high > body_high * 1.4


def test_ff8_guitar_has_midrange_presence_over_sub_bass():
    ff8_guitar = InstrumentLibrary.get("ff8_electric_guitar", SR)
    audio = ff8_guitar.render(196.0, 0.5)
    mid = _band_energy(audio, SR, 650.0, 3600.0)
    sub = _band_energy(audio, SR, 20.0, 120.0)
    assert mid > sub * 3.0
