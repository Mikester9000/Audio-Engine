"""
Instrument – high-level instrument definitions and a built-in library.

Each Instrument wraps an Oscillator, Envelope, Filter, and optional Effects
to produce a named, parametric sound source.  The library ships with
orchestral and synthetic timbres inspired by cinematic RPG soundtracks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.signal import sawtooth as scipy_sawtooth  # type: ignore[import]

from audio_engine.synthesizer.oscillator import Oscillator
from audio_engine.synthesizer.envelope import Envelope
from audio_engine.synthesizer.filter import Filter
from audio_engine.synthesizer.effects import Effects

__all__ = ["Instrument", "InstrumentLibrary"]

_STRINGS_BOW_NOISE_SEED = 11
_BASS_PICK_NOISE_SEED = 21
_PERCUSSION_NOISE_SEED = 5
_FLUTE_BREATH_SEED = 7
_CHOIR_FORMANTS = (700.0, 1220.0, 2600.0)


def _cents_to_ratio(cents: float) -> float:
    return float(2.0 ** (cents / 1200.0))


def _vibrato_phase(freq: float, dur: float, sr: int, rate_hz: float, depth_semitones: float) -> np.ndarray:
    n = max(1, int(dur * sr))
    t = np.arange(n, dtype=np.float64) / sr
    semitone_mod = depth_semitones * np.sin(2.0 * np.pi * rate_hz * t)
    freq_mod = freq * (2.0 ** (semitone_mod / 12.0))
    return 2.0 * np.pi * np.cumsum(freq_mod / sr)


@dataclass
class Instrument:
    """A complete synthesised voice.

    Parameters
    ----------
    name:
        Human-readable label (e.g. ``"violin"``, ``"synth_pad"``).
    oscillator_fn:
        Callable ``(osc, freq, dur) -> np.ndarray``.  Receives an
        :class:`Oscillator` instance so it can use any waveform.
    envelope:
        ADSR envelope applied after oscillator.
    post_process:
        Optional callable ``(signal, effects) -> np.ndarray`` for filtering /
        effects.
    volume:
        Master volume scalar 0–1.
    sample_rate:
        Audio sample rate.
    """

    name: str
    oscillator_fn: Callable[[Oscillator, float, float], np.ndarray]
    envelope: Envelope
    post_process: Callable[[np.ndarray, Effects], np.ndarray] | None = None
    volume: float = 0.8
    sample_rate: int = 44100

    def __post_init__(self) -> None:
        self._osc = Oscillator(self.sample_rate)
        self._fx = Effects(self.sample_rate)

    def render(self, frequency: float, duration: float) -> np.ndarray:
        """Render a single note as a NumPy float32 array.

        Parameters
        ----------
        frequency:
            Pitch in Hz.
        duration:
            Note duration in seconds.
        """
        raw = self.oscillator_fn(self._osc, frequency, duration)
        shaped = self.envelope.apply(raw, duration)
        if self.post_process is not None:
            shaped = self.post_process(shaped, self._fx)
        peak = np.max(np.abs(shaped))
        if peak > 1e-9:
            shaped = shaped / peak
        return (shaped * self.volume).astype(np.float32)


class InstrumentLibrary:
    """Factory that provides pre-built :class:`Instrument` instances.

    All instruments are tuned to produce cinematic, RPG-style timbres
    reminiscent of large-scale orchestral game soundtracks.
    """

    _registry: dict[str, Callable[[], Instrument]] = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """Class decorator to register a factory function."""
        def decorator(fn: Callable) -> Callable:
            cls._registry[name] = fn
            return fn
        return decorator

    @classmethod
    def get(cls, name: str, sample_rate: int = 44100) -> Instrument:
        """Return a new :class:`Instrument` by *name*.

        Raises
        ------
        KeyError
            If *name* is not registered.
        """
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry))
            raise KeyError(f"Unknown instrument '{name}'. Available: {available}")
        return cls._registry[name](sample_rate)

    @classmethod
    def available(cls) -> list[str]:
        """Return a sorted list of registered instrument names."""
        return sorted(cls._registry.keys())


# ---------------------------------------------------------------------------
# Built-in instrument definitions
# ---------------------------------------------------------------------------

@InstrumentLibrary.register("strings")
def _strings(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        phase_c = _vibrato_phase(freq, dur, sr, rate_hz=5.0, depth_semitones=0.5)
        phase_u = _vibrato_phase(freq * _cents_to_ratio(3.0), dur, sr, rate_hz=5.1, depth_semitones=0.45)
        phase_l = _vibrato_phase(freq * _cents_to_ratio(-3.0), dur, sr, rate_hz=4.9, depth_semitones=0.45)
        body = (
            0.46 * scipy_sawtooth(phase_c)
            + 0.30 * scipy_sawtooth(phase_u)
            + 0.24 * scipy_sawtooth(phase_l)
        )
        noise = np.random.default_rng(_STRINGS_BOW_NOISE_SEED).standard_normal(len(body)).astype(np.float32)
        noise = Filter(sr).band_pass(noise, 200.0, 2000.0)
        return body.astype(np.float32) + 0.1 * noise  # -20 dB bow layer

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.low_pass(sig, 6000.0)
        sig = fx.reverb(sig, room_size=0.72, wet=0.25)
        return fx.chorus(sig, rate=0.8, depth=0.004, wet=0.28)

    return Instrument(
        name="strings",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.2, decay=0.25, sustain=0.82, release=0.8, sample_rate=sr),
        post_process=post,
        volume=0.75,
        sample_rate=sr,
    )


@InstrumentLibrary.register("brass")
def _brass(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        base = osc.additive(
            freq, dur,
            [(1, 1.0), (2, 0.85), (3, 0.7), (4, 0.2), (5, 0.1)],
        )
        drive = np.where(np.abs(base) > 0.7, 1.02, 1.0)  # slight growl on loud notes
        return np.tanh(base * drive).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.low_pass(sig, 5000.0)
        return fx.reverb(sig, room_size=0.45, wet=0.18)

    return Instrument(
        name="brass",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.02, decay=0.14, sustain=0.72, release=0.24, sample_rate=sr),
        post_process=post,
        volume=0.8,
        sample_rate=sr,
    )


@InstrumentLibrary.register("piano")
def _piano(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float32) / sr
        harmonic_decay = np.exp(-5.5 * t)
        body = osc.additive(
            freq, dur,
            [(1, 1.0), (2, 0.55), (3, 0.3), (4.03, 0.16), (5.07, 0.08), (7.12, 0.04)],
        )
        click_len = max(1, int(0.005 * sr))
        click = np.zeros(n, dtype=np.float32)
        click[:click_len] = np.exp(-np.linspace(0.0, 6.0, click_len)).astype(np.float32)
        return (body * harmonic_decay + 0.25 * click).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.low_pass(sig, 6000.0)
        return fx.reverb(sig, room_size=0.28, wet=0.12)

    return Instrument(
        name="piano",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.28, sustain=0.0, release=0.22, sample_rate=sr),
        post_process=post,
        volume=0.8,
        sample_rate=sr,
    )


@InstrumentLibrary.register("choir")
def _choir(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        sig = 0.5 * osc.sine(freq * _cents_to_ratio(0.0), dur)
        sig += 0.25 * osc.sine(freq * _cents_to_ratio(8.0), dur)
        sig += 0.25 * osc.sine(freq * _cents_to_ratio(-8.0), dur)
        return sig

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        formants = np.zeros_like(sig)
        for center, bw in zip(_CHOIR_FORMANTS, (120.0, 160.0, 260.0)):
            formants += flt.band_pass(sig, max(80.0, center - bw), center + bw)
        formants = formants / max(1, len(_CHOIR_FORMANTS))
        formants = fx.chorus(formants, rate=0.8, depth=0.006, wet=0.48)
        return fx.reverb(formants, room_size=0.85, wet=0.38)

    return Instrument(
        name="choir",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.3, decay=0.25, sustain=0.78, release=0.9, sample_rate=sr),
        post_process=post,
        volume=0.7,
        sample_rate=sr,
    )


@InstrumentLibrary.register("synth_pad")
def _synth_pad(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return (
            0.34 * osc.sawtooth(freq * _cents_to_ratio(-6.0), dur)
            + 0.34 * osc.sawtooth(freq * _cents_to_ratio(0.0), dur)
            + 0.32 * osc.sawtooth(freq * _cents_to_ratio(6.0), dur)
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        low_start = flt.low_pass(sig, 200.0)
        low_end = flt.low_pass(sig, 8000.0)
        n = len(sig)
        sweep_len = min(n, int(2.0 * sr))
        alpha = np.ones(n, dtype=np.float32)
        alpha[:sweep_len] = np.linspace(0.0, 1.0, sweep_len, dtype=np.float32)
        sig = low_start * (1.0 - alpha) + low_end * alpha
        sig = fx.chorus(sig, rate=0.45, depth=0.008, wet=0.55)
        return fx.reverb(sig, room_size=0.82, wet=0.42)

    return Instrument(
        name="synth_pad",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.35, decay=0.4, sustain=0.85, release=1.2, sample_rate=sr),
        post_process=post,
        volume=0.65,
        sample_rate=sr,
    )


@InstrumentLibrary.register("electric_guitar")
def _electric_guitar(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return osc.fm(freq, freq * 2.0, dur, modulation_index=3.5)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = fx.distortion(sig, drive=3.0, tone=0.6)
        sig = flt.band_pass(sig, 80.0, 5000.0)
        return fx.reverb(sig, room_size=0.3, wet=0.15)

    return Instrument(
        name="electric_guitar",
        oscillator_fn=osc_fn,
        envelope=Envelope.pluck(sr),
        post_process=post,
        volume=0.75,
        sample_rate=sr,
    )


@InstrumentLibrary.register("bass")
def _bass(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        fundamental = osc.sine(freq, dur, amplitude=0.75)
        second = osc.sine(freq * 2.0, dur, amplitude=0.375)  # -6 dB
        pick = np.zeros(n, dtype=np.float32)
        pick_len = max(1, int(0.01 * sr))
        pick_noise = np.random.default_rng(_BASS_PICK_NOISE_SEED).standard_normal(pick_len).astype(np.float32)
        pick[:pick_len] = pick_noise * np.exp(-np.linspace(0.0, 6.0, pick_len))
        return fundamental + second + 0.1 * pick

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.low_pass(sig, 900.0)
        return fx.compress(sig, threshold=0.45, ratio=3.0, makeup_gain=1.05)

    return Instrument(
        name="bass",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.008, decay=0.12, sustain=0.7, release=0.2, sample_rate=sr),
        post_process=post,
        volume=0.85,
        sample_rate=sr,
    )


@InstrumentLibrary.register("percussion")
def _percussion(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float32) / sr
        noise = np.random.default_rng(_PERCUSSION_NOISE_SEED).standard_normal(n).astype(np.float32)
        if freq < 180.0:
            sweep = np.clip(t / 0.05, 0.0, 1.0)
            inst_freq = 200.0 + (60.0 - 200.0) * sweep
            phase = 2.0 * np.pi * np.cumsum(inst_freq / sr)
            kick = np.sin(phase).astype(np.float32) * np.exp(-8.0 * t)
            transient = noise * np.exp(-120.0 * t) * 0.2
            return kick + transient
        snare_tone = np.sin(2.0 * np.pi * 180.0 * t).astype(np.float32) * np.exp(-18.0 * t)
        snare_noise = Filter(sr).band_pass(noise, 1200.0, 7000.0) * np.exp(-25.0 * t)
        return 0.5 * snare_tone + 0.7 * snare_noise

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 60.0)
        return fx.compress(sig, threshold=0.4, ratio=6.0)

    return Instrument(
        name="percussion",
        oscillator_fn=osc_fn,
        envelope=Envelope.percussive(sr),
        post_process=post,
        volume=0.9,
        sample_rate=sr,
    )


@InstrumentLibrary.register("flute")
def _flute(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        phase = _vibrato_phase(freq, dur, sr, rate_hz=4.0, depth_semitones=0.3)
        fundamental = np.sin(phase).astype(np.float32) * 0.85
        second = np.sin(2.0 * phase).astype(np.float32) * 0.21  # -12 dB
        breath = np.random.default_rng(_FLUTE_BREATH_SEED).standard_normal(n).astype(np.float32)
        breath = Filter(sr).band_pass(breath, 2000.0, 8000.0) * 0.063  # -24 dB
        return fundamental + second + breath

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.band_pass(sig, 400.0, 8000.0)
        return fx.reverb(sig, room_size=0.38, wet=0.18)

    return Instrument(
        name="flute",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.1, decay=0.08, sustain=0.85, release=0.28, sample_rate=sr),
        post_process=post,
        volume=0.7,
        sample_rate=sr,
    )


@InstrumentLibrary.register("crystal_synth")
def _crystal_synth(sr: int = 44100) -> Instrument:
    """High-frequency bell/crystal pad found in cinematic scores."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return osc.fm(freq, freq * 3.5, dur, modulation_index=1.5)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        sig = fx.chorus(sig, rate=2.0, depth=0.002, wet=0.3)
        return fx.reverb(sig, room_size=0.9, wet=0.5)

    return Instrument(
        name="crystal_synth",
        oscillator_fn=osc_fn,
        envelope=Envelope.pluck(sr),
        post_process=post,
        volume=0.6,
        sample_rate=sr,
    )


# ---------------------------------------------------------------------------
# FF7 / FF8-era PS1 SPU instrument timbres
# Designed to approximate the Nobuo Uematsu / PS1 ADPCM sample character.
# ---------------------------------------------------------------------------

@InstrumentLibrary.register("ff7_lead")
def _ff7_lead(sr: int = 44100) -> Instrument:
    """Bright crystal lead — the iconic FF7 melody instrument.

    Approximates the crystalline sine-wave lead heard in tracks such as
    Aerith's Theme and Main Theme of FFVII.  Uses sine + triangle mix for a
    clean but slightly warm tone, with light FM for subtle harmonic movement.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        # Slightly detuned sines for natural ensemble width
        primary  = osc.sine(freq, dur, amplitude=0.70)
        upper    = osc.sine(freq * 2.0, dur, amplitude=0.18)   # octave
        tri      = osc.triangle(freq, dur, amplitude=0.12)
        return primary + upper + tri

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 7000.0)
        sig = fx.chorus(sig, rate=0.6, depth=0.002, wet=0.15)
        return fx.reverb(sig, room_size=0.45, wet=0.22)

    return Instrument(
        name="ff7_lead",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.01, decay=0.08, sustain=0.85, release=0.25, sample_rate=sr),
        post_process=post,
        volume=0.78,
        sample_rate=sr,
    )


@InstrumentLibrary.register("ff7_strings")
def _ff7_strings(sr: int = 44100) -> Instrument:
    """Warm-but-synthetic string ensemble — FF7/FF8 SPU string character.

    The PS1 ADPCM strings had a compressed, slightly nasal quality.
    Modelled here with a sawtooth ensemble + gentle low-pass + chorus.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        s1 = osc.sawtooth(freq, dur, amplitude=0.55)
        s2 = osc.sawtooth(freq * 1.007, dur, amplitude=0.28)   # detune
        s3 = osc.sawtooth(freq * 0.994, dur, amplitude=0.17)   # detune low
        return s1 + s2 + s3

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 3800.0)       # compressed bandwidth of ADPCM
        sig = fx.chorus(sig, rate=0.9, depth=0.005, wet=0.35)
        return fx.reverb(sig, room_size=0.55, wet=0.30)

    return Instrument(
        name="ff7_strings",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.18, decay=0.15, sustain=0.80, release=0.55, sample_rate=sr),
        post_process=post,
        volume=0.72,
        sample_rate=sr,
    )


@InstrumentLibrary.register("ff7_bass")
def _ff7_bass(sr: int = 44100) -> Instrument:
    """Punchy melodic bass — Uematsu's bass lines are rhythmically active.

    Uses a sawtooth + square blend for the mid-punch character of the PS1
    bass samples.  Filter sweeps to 600 Hz to stay out of the way of melody.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        saw = osc.sawtooth(freq, dur, amplitude=0.65)
        sq  = osc.square(freq, dur, amplitude=0.35, duty_cycle=0.45)
        return saw + sq

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 650.0)
        return fx.compress(sig, threshold=0.5, ratio=3.0, makeup_gain=1.1)

    return Instrument(
        name="ff7_bass",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.008, decay=0.12, sustain=0.60, release=0.12, sample_rate=sr),
        post_process=post,
        volume=0.88,
        sample_rate=sr,
    )


@InstrumentLibrary.register("ff7_electric_guitar")
def _ff7_electric_guitar(sr: int = 44100) -> Instrument:
    """Driven electric guitar — as heard in FF7 boss battle tracks.

    The FF7 electric guitar sample had a middy crunch character — not as
    saturated as metal, but clearly distorted.  FM + soft-clip models this.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return osc.fm(freq, freq * 1.5, dur, modulation_index=2.8)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = fx.distortion(sig, drive=4.0, tone=0.55)
        sig = flt.band_pass(sig, 120.0, 4500.0)
        sig = fx.reverb(sig, room_size=0.28, wet=0.12)
        return sig

    return Instrument(
        name="ff7_electric_guitar",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.005, decay=0.2, sustain=0.55, release=0.18, sample_rate=sr),
        post_process=post,
        volume=0.72,
        sample_rate=sr,
    )


@InstrumentLibrary.register("ff8_electric_guitar")
def _ff8_electric_guitar(sr: int = 44100) -> Instrument:
    """Aggressive rock guitar — FF8 battle / "The Man with the Machine Gun" style.

    FF8 pushed the electric guitar much harder than FF7 — more saturation,
    higher presence.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        fm  = osc.fm(freq, freq * 2.0, dur, modulation_index=3.8)
        sq  = osc.square(freq, dur, amplitude=0.3, duty_cycle=0.48)
        return fm + sq

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = fx.distortion(sig, drive=6.0, tone=0.65)
        sig = flt.band_pass(sig, 100.0, 5500.0)
        sig = fx.compress(sig, threshold=0.45, ratio=5.0, makeup_gain=1.15)
        return fx.reverb(sig, room_size=0.22, wet=0.10)

    return Instrument(
        name="ff8_electric_guitar",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.004, decay=0.15, sustain=0.65, release=0.15, sample_rate=sr),
        post_process=post,
        volume=0.80,
        sample_rate=sr,
    )


@InstrumentLibrary.register("harpsichord")
def _harpsichord(sr: int = 44100) -> Instrument:
    """Harpsichord / clavier — for prelude-style arpeggios and baroque textures.

    Sharp pluck with rich harmonics, fast decay.  Characteristic of the
    ancient keyboard sounds sampled into many PS1 RPG soundtracks.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return osc.additive(
            freq, dur,
            [(1, 1.0), (2, 0.8), (3, 0.5), (4, 0.3), (5, 0.15), (6, 0.07)],
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.high_pass(sig, 80.0)
        return fx.reverb(sig, room_size=0.25, wet=0.12)

    return Instrument(
        name="harpsichord",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.18, sustain=0.0, release=0.12, sample_rate=sr),
        post_process=post,
        volume=0.75,
        sample_rate=sr,
    )


@InstrumentLibrary.register("orchestral_hit")
def _orchestral_hit(sr: int = 44100) -> Instrument:
    """Orchestral stab — short dramatic chord hit used in climactic moments.

    Combines brass, strings, and a transient noise burst for the classic
    "orchestral hit" one-shot found throughout PS1/PS2 RPG soundtracks.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        brass  = osc.additive(freq, dur, [(1, 1.0), (2, 0.5), (3, 0.25)])
        noise  = osc.noise(dur, amplitude=0.15, seed=99)
        return brass + noise

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 6000.0)
        sig = fx.compress(sig, threshold=0.4, ratio=4.0, makeup_gain=1.2)
        return fx.reverb(sig, room_size=0.7, wet=0.35)

    return Instrument(
        name="orchestral_hit",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.002, decay=0.25, sustain=0.0, release=0.30, sample_rate=sr),
        post_process=post,
        volume=0.85,
        sample_rate=sr,
    )


# ---------------------------------------------------------------------------
# Full-orchestra section instruments — distinct timbres for rich multi-section
# orchestral arrangements.  Each uses a unique synthesis technique to ensure
# clear tonal separation from the instruments above.
# ---------------------------------------------------------------------------

_TIMPANI_NOISE_SEED = 67


@InstrumentLibrary.register("oboe")
def _oboe(sr: int = 44100) -> Instrument:
    """Nasal, double-reed woodwind — the characteristic voice of the oboe.

    Uses FM synthesis with a sawtooth carrier and narrow bandpass filtering
    to create the oboe's distinctive "nasal" resonance peak around 1 kHz.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        # Slight vibrato on the carrier
        phase = _vibrato_phase(freq, dur, sr, rate_hz=5.5, depth_semitones=0.25)
        carrier = scipy_sawtooth(phase).astype(np.float32)
        # Add weak reed buzz via high-frequency FM modulation
        mod_phase = 2.0 * np.pi * freq * 2.0 * np.arange(n, dtype=np.float64) / sr
        buzz = (0.18 * np.sin(mod_phase + 1.6 * np.sin(mod_phase * 0.5))).astype(np.float32)
        return carrier + buzz

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        # Oboe resonance peak ~1–1.5 kHz, cut harsh highs
        sig = flt.band_pass(sig, 600.0, 3500.0)
        sig = fx.reverb(sig, room_size=0.32, wet=0.14)
        return sig

    return Instrument(
        name="oboe",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.04, decay=0.06, sustain=0.88, release=0.22, sample_rate=sr),
        post_process=post,
        volume=0.68,
        sample_rate=sr,
    )


@InstrumentLibrary.register("clarinet")
def _clarinet(sr: int = 44100) -> Instrument:
    """Hollow, liquid woodwind — the characteristic sound of the clarinet.

    Clarinets have a strong odd-harmonic series (like a stopped pipe), which
    gives them their distinctive hollow quality.  Modelled using additive
    synthesis with only odd harmonics.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        # Odd-harmonic additive series: 1, 3, 5, 7 with decreasing amplitude
        phase0 = _vibrato_phase(freq, dur, sr, rate_hz=4.8, depth_semitones=0.2)
        h1 = np.sin(phase0).astype(np.float32) * 0.70
        h3 = np.sin(3.0 * phase0).astype(np.float32) * 0.30
        h5 = np.sin(5.0 * phase0).astype(np.float32) * 0.14
        h7 = np.sin(7.0 * phase0).astype(np.float32) * 0.06
        return h1 + h3 + h5 + h7

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.low_pass(sig, 4500.0)
        sig = flt.high_pass(sig, 250.0)
        sig = fx.reverb(sig, room_size=0.28, wet=0.12)
        return sig

    return Instrument(
        name="clarinet",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.06, decay=0.05, sustain=0.90, release=0.20, sample_rate=sr),
        post_process=post,
        volume=0.72,
        sample_rate=sr,
    )


@InstrumentLibrary.register("french_horn")
def _french_horn(sr: int = 44100) -> Instrument:
    """Warm, mellow brass — the lyrical voice of the French horn.

    Distinct from the brighter ``brass`` instrument: softer onset, narrow
    harmonic series with emphasis on the fundamental and a gentle mellow
    character.  Modelled using additive synthesis with a smooth onset.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        # Fewer harmonics than trumpet, gentle amplitude envelope per harmonic
        sig = osc.additive(
            freq, dur,
            [(1, 1.0), (2, 0.58), (3, 0.34), (4, 0.14), (5, 0.06)],
        )
        # Soft tanh saturation for a slightly warm, organic character
        return np.tanh(sig * 1.2).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.low_pass(sig, 3500.0)
        sig = fx.reverb(sig, room_size=0.60, wet=0.24)
        return sig

    return Instrument(
        name="french_horn",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.08, decay=0.18, sustain=0.74, release=0.36, sample_rate=sr),
        post_process=post,
        volume=0.78,
        sample_rate=sr,
    )


@InstrumentLibrary.register("cello")
def _cello(sr: int = 44100) -> Instrument:
    """Deep, resonant bowed string — the cello.

    Similar synthesis approach to ``strings`` but tuned to the cello's
    lower register: more fundamental weight, slower bow attack, and a
    richer low-mid resonance.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        phase_c = _vibrato_phase(freq, dur, sr, rate_hz=4.5, depth_semitones=0.55)
        phase_u = _vibrato_phase(freq * _cents_to_ratio(4.0), dur, sr, rate_hz=4.6, depth_semitones=0.5)
        phase_l = _vibrato_phase(freq * _cents_to_ratio(-4.0), dur, sr, rate_hz=4.4, depth_semitones=0.5)
        # Heavier fundamental than the strings section, less of the upper detune
        body = (
            0.55 * scipy_sawtooth(phase_c)
            + 0.25 * scipy_sawtooth(phase_u)
            + 0.20 * scipy_sawtooth(phase_l)
        )
        noise = np.random.default_rng(_STRINGS_BOW_NOISE_SEED + 3).standard_normal(len(body)).astype(np.float32)
        noise = Filter(sr).band_pass(noise, 100.0, 1200.0)
        return body.astype(np.float32) + 0.08 * noise

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.low_pass(sig, 4000.0)
        sig = flt.high_pass(sig, 55.0)
        sig = fx.reverb(sig, room_size=0.68, wet=0.22)
        return fx.chorus(sig, rate=0.6, depth=0.003, wet=0.20)

    return Instrument(
        name="cello",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.28, decay=0.30, sustain=0.80, release=0.90, sample_rate=sr),
        post_process=post,
        volume=0.80,
        sample_rate=sr,
    )


@InstrumentLibrary.register("harp")
def _harp(sr: int = 44100) -> Instrument:
    """Plucked, bright-decaying harp — the ethereal orchestral harp.

    Uses FM synthesis with a fast exponential decay to produce the harp's
    characteristic bright pluck that blossoms into a warm resonance.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # FM pluck: carrier + modulator that decays quickly
        mod_decay = np.exp(-18.0 * t)
        mod_signal = 2.5 * mod_decay * np.sin(2.0 * np.pi * freq * 2.0 * t)
        carrier = np.sin(2.0 * np.pi * freq * t + mod_signal).astype(np.float32)
        # Add a little string resonance via second harmonic
        second = (0.22 * np.sin(2.0 * np.pi * freq * 2.0 * t) * np.exp(-12.0 * t)).astype(np.float32)
        return carrier + second

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 80.0)
        sig = flt.low_pass(sig, 8000.0)
        sig = fx.reverb(sig, room_size=0.55, wet=0.30)
        return sig

    return Instrument(
        name="harp",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.35, sustain=0.0, release=0.45, sample_rate=sr),
        post_process=post,
        volume=0.72,
        sample_rate=sr,
    )


@InstrumentLibrary.register("celesta")
def _celesta(sr: int = 44100) -> Instrument:
    """Sparkly, bell-like keyboard — the celesta.

    Pure-sine additive synthesis with slightly inharmonic upper partials
    (like a real celesta's metal bars) and fast exponential decay.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # Slightly inharmonic partials — celesta bar modes are ~2.76, 5.4, 8.9...
        fundamental = np.sin(2.0 * np.pi * freq * t) * np.exp(-5.0 * t)
        h2 = 0.38 * np.sin(2.0 * np.pi * freq * 2.76 * t) * np.exp(-8.0 * t)
        h3 = 0.14 * np.sin(2.0 * np.pi * freq * 5.40 * t) * np.exp(-14.0 * t)
        return (fundamental + h2 + h3).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 200.0)
        sig = fx.reverb(sig, room_size=0.70, wet=0.38)
        return sig

    return Instrument(
        name="celesta",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.22, sustain=0.0, release=0.30, sample_rate=sr),
        post_process=post,
        volume=0.65,
        sample_rate=sr,
    )


@InstrumentLibrary.register("timpani")
def _timpani(sr: int = 44100) -> Instrument:
    """Tonal orchestral kettledrum — the timpani.

    Combines an inharmonic membrane resonance (pitch sweep on attack)
    with a tunable fundamental tone to produce the timpani's characteristic
    boom.  The fundamental is clearly pitched unlike a regular bass drum.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # Pitch glide: starts ~30% above target and settles in ~80 ms
        freq_envelope = freq * (1.0 + 0.30 * np.exp(-25.0 * t))
        phase = 2.0 * np.pi * np.cumsum(freq_envelope / sr)
        fundamental = np.sin(phase).astype(np.float32) * np.exp(-4.5 * t).astype(np.float32)
        # Inharmonic partials of a circular membrane: ~1.59, 2.14, 2.65 times fundamental
        p2 = (0.35 * np.sin(1.59 * phase) * np.exp(-7.0 * t)).astype(np.float32)
        p3 = (0.18 * np.sin(2.14 * phase) * np.exp(-10.0 * t)).astype(np.float32)
        # Beater impact noise burst
        noise = np.random.default_rng(_TIMPANI_NOISE_SEED).standard_normal(n).astype(np.float32)
        transient = Filter(sr).band_pass(noise, 200.0, 5000.0) * np.exp(-80.0 * t).astype(np.float32) * 0.4
        return fundamental + p2 + p3 + transient

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 40.0)
        sig = flt.low_pass(sig, 5000.0)
        sig = fx.compress(sig, threshold=0.5, ratio=4.0, makeup_gain=1.1)
        return fx.reverb(sig, room_size=0.55, wet=0.20)

    return Instrument(
        name="timpani",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.002, decay=0.50, sustain=0.0, release=0.60, sample_rate=sr),
        post_process=post,
        volume=0.90,
        sample_rate=sr,
    )


@InstrumentLibrary.register("marimba")
def _marimba(sr: int = 44100) -> Instrument:
    """Warm wooden mallet percussion — the marimba.

    Sine-heavy additive synthesis with a wooden attack transient and fast
    decay, producing the characteristic warm-but-woody marimba tone.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # Marimba bar: fundamental + ~4th harmonic (slightly inharmonic)
        fundamental = np.sin(2.0 * np.pi * freq * t) * np.exp(-6.5 * t)
        fourth = 0.28 * np.sin(2.0 * np.pi * freq * 3.98 * t) * np.exp(-14.0 * t)
        # Brief mallet click transient
        click_len = max(1, int(0.004 * sr))
        click = np.zeros(n, dtype=np.float64)
        click[:click_len] = 0.5 * np.exp(-np.linspace(0.0, 8.0, click_len))
        return (fundamental + fourth + click).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.band_pass(sig, 150.0, 6000.0)
        return fx.reverb(sig, room_size=0.35, wet=0.16)

    return Instrument(
        name="marimba",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.30, sustain=0.0, release=0.25, sample_rate=sr),
        post_process=post,
        volume=0.76,
        sample_rate=sr,
    )
