"""Tests for the Instrument and InstrumentLibrary classes."""

import numpy as np
import pytest

from audio_engine.synthesizer.instrument import Instrument, InstrumentLibrary

SR = 22050
_LEGATO_BLOOM_RATIO_MIN = 1.15
_NYLON_ATTACK_HIGH_RATIO_MIN = 1.3
_SOFT_EP_ATTACK_BRIGHTNESS_RATIO_MIN = 1.05
_SYNTH_PAD_WARMTH_RATIO_MIN = 1.15
_CRYSTAL_ATTACK_SPARKLE_RATIO_MIN = 1.2
_LEAD_TO_PAD_PRESENCE_RATIO_MIN = 1.15


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


def test_legato_strings_ps2_has_bow_bloom_after_attack():
    inst = InstrumentLibrary.get("legato_strings_ps2", SR)
    audio = inst.render(329.63, 0.9)
    early = _rms(audio[: int(0.05 * SR)])
    bloom = _rms(audio[int(0.15 * SR) : int(0.35 * SR)])
    assert bloom > early * _LEGATO_BLOOM_RATIO_MIN


def test_nylon_guitar_ps2_attack_brightness_falls_into_body():
    inst = InstrumentLibrary.get("nylon_guitar_ps2", SR)
    audio = inst.render(196.0, 0.85)
    attack = audio[: int(0.06 * SR)]
    body = audio[int(0.20 * SR) : int(0.42 * SR)]
    attack_high = _band_energy(attack, SR, 1400.0, 6000.0)
    body_high = _band_energy(body, SR, 1400.0, 6000.0)
    assert attack_high > body_high * _NYLON_ATTACK_HIGH_RATIO_MIN


def test_soft_epiano_ps2_has_tine_attack_presence():
    inst = InstrumentLibrary.get("soft_epiano_ps2", SR)
    audio = inst.render(261.63, 0.8)
    attack = audio[: int(0.05 * SR)]
    tail = audio[int(0.25 * SR) : int(0.45 * SR)]
    attack_presence = _band_energy(attack, SR, 4200.0, 9000.0)
    tail_presence = _band_energy(tail, SR, 4200.0, 9000.0)
    attack_low = _band_energy(attack, SR, 200.0, 1200.0)
    tail_low = _band_energy(tail, SR, 200.0, 1200.0)
    assert (attack_presence / max(attack_low, 1e-9)) > (
        tail_presence / max(tail_low, 1e-9)
    ) * _SOFT_EP_ATTACK_BRIGHTNESS_RATIO_MIN


def test_synth_pad_has_warm_body_over_high_air():
    inst = InstrumentLibrary.get("synth_pad", SR)
    audio = inst.render(220.0, 1.0)
    body = _band_energy(audio, SR, 140.0, 1600.0)
    air = _band_energy(audio, SR, 4200.0, 9000.0)
    assert body > air * _SYNTH_PAD_WARMTH_RATIO_MIN


def test_crystal_synth_has_attack_sparkle():
    inst = InstrumentLibrary.get("crystal_synth", SR)
    audio = inst.render(523.25, 0.9)
    attack = audio[: int(0.12 * SR)]
    tail = audio[int(0.34 * SR) : int(0.56 * SR)]
    attack_air = _band_energy(attack, SR, 3200.0, 9800.0)
    tail_air = _band_energy(tail, SR, 3200.0, 9800.0)
    assert attack_air > tail_air * _CRYSTAL_ATTACK_SPARKLE_RATIO_MIN


def test_synth_lead_has_more_presence_than_synth_pad():
    lead = InstrumentLibrary.get("synth_lead_bright", SR).render(220.0, 0.8)
    pad = InstrumentLibrary.get("synth_pad", SR).render(220.0, 0.8)
    lead_presence = _band_energy(lead, SR, 900.0, 3600.0)
    lead_low = _band_energy(lead, SR, 120.0, 600.0)
    pad_presence = _band_energy(pad, SR, 900.0, 3600.0)
    pad_low = _band_energy(pad, SR, 120.0, 600.0)
    assert (lead_presence / max(lead_low, 1e-9)) > (
        pad_presence / max(pad_low, 1e-9)
    ) * _LEAD_TO_PAD_PRESENCE_RATIO_MIN
