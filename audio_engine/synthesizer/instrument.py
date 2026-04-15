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

from audio_engine.synthesizer.oscillator import Oscillator
from audio_engine.synthesizer.envelope import Envelope
from audio_engine.synthesizer.filter import Filter
from audio_engine.synthesizer.effects import Effects

__all__ = ["Instrument", "InstrumentLibrary"]


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
        return (
            0.5 * osc.sawtooth(freq, dur)
            + 0.3 * osc.sawtooth(freq * 1.005, dur)   # slight detune → richness
            + 0.2 * osc.sawtooth(freq * 0.995, dur)
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 4000.0)
        sig = fx.reverb(sig, room_size=0.6, wet=0.25)
        return fx.chorus(sig, rate=0.8, depth=0.004, wet=0.3)

    return Instrument(
        name="strings",
        oscillator_fn=osc_fn,
        envelope=Envelope.pad(sr),
        post_process=post,
        volume=0.75,
        sample_rate=sr,
    )


@InstrumentLibrary.register("brass")
def _brass(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return osc.additive(
            freq, dur,
            [(1, 1.0), (2, 0.6), (3, 0.3), (4, 0.15), (5, 0.07)],
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 3500.0)
        return fx.reverb(sig, room_size=0.4, wet=0.2)

    return Instrument(
        name="brass",
        oscillator_fn=osc_fn,
        envelope=Envelope.brass(sr),
        post_process=post,
        volume=0.8,
        sample_rate=sr,
    )


@InstrumentLibrary.register("piano")
def _piano(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return osc.additive(
            freq, dur,
            [(1, 1.0), (2, 0.4), (3, 0.2), (4, 0.1), (5, 0.05), (7, 0.03)],
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 6000.0)
        return fx.reverb(sig, room_size=0.35, wet=0.15)

    return Instrument(
        name="piano",
        oscillator_fn=osc_fn,
        envelope=Envelope.pluck(sr),
        post_process=post,
        volume=0.8,
        sample_rate=sr,
    )


@InstrumentLibrary.register("choir")
def _choir(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        sig = 0.6 * osc.sine(freq, dur)
        sig += 0.2 * osc.sine(freq * 1.003, dur)
        sig += 0.2 * osc.sine(freq * 0.997, dur)
        return sig

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.band_pass(sig, 300.0, 3500.0)
        sig = fx.chorus(sig, rate=1.2, depth=0.005, wet=0.5)
        return fx.reverb(sig, room_size=0.8, wet=0.4)

    return Instrument(
        name="choir",
        oscillator_fn=osc_fn,
        envelope=Envelope.pad(sr),
        post_process=post,
        volume=0.7,
        sample_rate=sr,
    )


@InstrumentLibrary.register("synth_pad")
def _synth_pad(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        return (
            0.4 * osc.triangle(freq, dur)
            + 0.4 * osc.sine(freq * 1.5, dur)   # fifth
            + 0.2 * osc.sawtooth(freq * 2.0, dur)  # octave
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.low_pass(sig, 2000.0)
        sig = fx.chorus(sig, rate=0.5, depth=0.006, wet=0.4)
        return fx.reverb(sig, room_size=0.7, wet=0.35)

    return Instrument(
        name="synth_pad",
        oscillator_fn=osc_fn,
        envelope=Envelope.pad(sr),
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
        return (
            0.6 * osc.sawtooth(freq, dur)
            + 0.4 * osc.square(freq, dur)
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        return flt.low_pass(sig, 600.0)

    return Instrument(
        name="bass",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.01, decay=0.1, sustain=0.6, release=0.1, sample_rate=sr),
        post_process=post,
        volume=0.85,
        sample_rate=sr,
    )


@InstrumentLibrary.register("percussion")
def _percussion(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        # Layered: pitched noise body + sine transient
        body = osc.noise(dur, amplitude=0.7, seed=1)
        tone = osc.sine(freq, dur, amplitude=0.3)
        return body + tone

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
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
        pure = osc.sine(freq, dur, amplitude=0.8)
        breath = osc.noise(dur, amplitude=0.05, seed=7)
        return pure + breath

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.band_pass(sig, 400.0, 8000.0)
        return fx.reverb(sig, room_size=0.4, wet=0.2)

    return Instrument(
        name="flute",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.08, decay=0.05, sustain=0.85, release=0.2, sample_rate=sr),
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
