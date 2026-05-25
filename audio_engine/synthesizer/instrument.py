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
_GUITAR_PICK_NOISE_SEED = 61
_PERCUSSION_NOISE_SEED = 5
_FLUTE_BREATH_SEED = 7
_CHOIR_FORMANTS = (700.0, 1220.0, 2600.0)
_VIOLIN_NOISE_SEED = 31
_TRUMPET_NOISE_SEED = 41
_SYNTH_LEAD_NOISE_SEED = 51
_LEGATO_STRINGS_NOISE_SEED = 71
_NYLON_GUITAR_NOISE_SEED = 81
_SOFT_EP_NOISE_SEED = 91


def _cents_to_ratio(cents: float) -> float:
    return float(2.0 ** (cents / 1200.0))


def _vibrato_phase(freq: float, dur: float, sr: int, rate_hz: float, depth_semitones: float) -> np.ndarray:
    n = max(1, int(dur * sr))
    t = np.arange(n, dtype=np.float64) / sr
    semitone_mod = depth_semitones * np.sin(2.0 * np.pi * rate_hz * t)
    freq_mod = freq * (2.0 ** (semitone_mod / 12.0))
    return 2.0 * np.pi * np.cumsum(freq_mod / sr)


def _bl_saw_from_phase(phase: np.ndarray, freq: float, sr: int) -> np.ndarray:
    """Generate a band-limited sawtooth from a precomputed phase accumulator.

    Uses the same Lanczos-windowed additive synthesis as
    :meth:`Oscillator.bl_sawtooth`, but accepts a time-varying phase track so
    that the oscillator frequency can be modulated sample-by-sample (true pitch
    vibrato / FM rather than amplitude modulation / tremolo).
    """
    nyquist = sr / 2.0
    n_harmonics = min(int(nyquist / max(freq, 1.0)), 40)
    n_harmonics = max(n_harmonics, 1)
    N = float(n_harmonics)
    k = np.arange(1, n_harmonics + 1, dtype=np.float64)
    sigma = np.sinc(k / (N + 1.0))
    coeff = ((-1.0) ** (k + 1) / k) * sigma  # shape: (n_harmonics,)
    # phase shape: (n,);  broadcast to (n_harmonics, n) for vectorised sum
    out = np.sum(coeff[:, None] * np.sin(k[:, None] * phase[None, :]), axis=0)
    out *= 2.0 / np.pi
    peak = np.max(np.abs(out))
    if peak > 1e-9:
        out /= peak
    return out.astype(np.float32)


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
        self._flt = Filter(self.sample_rate)

    def _apply_ps2_realism_voicing(self, signal: np.ndarray) -> np.ndarray:
        """Apply a light global PS2-era realism tint across all instruments."""
        sig = signal.astype(np.float32, copy=False)
        name = self.name.lower()

        # Console-era bandwidth shaping with family-aware top-end.
        sig = self._flt.high_pass(sig, 30.0)
        if any(key in name for key in ("percussion", "timpani", "marimba", "orchestral_hit")):
            top_hz = 9200.0
        elif any(key in name for key in ("guitar", "trumpet", "brass")):
            top_hz = 8600.0
        elif any(key in name for key in ("synth", "celesta", "crystal")):
            top_hz = 9800.0
        else:
            top_hz = 8200.0
        sig = self._flt.warm_low_pass(sig, top_hz)

        # Gentle bus compression + very small room glue.
        sig = self._fx.compress(sig, threshold=0.78, ratio=1.5, makeup_gain=1.015)
        room_wet = 0.02 if "percussion" in name else 0.035
        sig = self._fx.reverb(sig, room_size=0.22, wet=room_wet)
        return np.tanh(sig * 1.05).astype(np.float32)

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
        shaped = self._apply_ps2_realism_voicing(shaped)
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
        # Use band-limited sawtooth ensemble — three detuned voices for natural width
        n = max(1, int(dur * sr))
        rate_hz = 5.0
        t = np.arange(n, dtype=np.float64) / sr
        # Per-voice pitch vibrato via frequency modulation (phase accumulation)
        freq_center = freq * (1.0 + (_cents_to_ratio(0.5) - 1.0) * np.sin(2.0 * np.pi * rate_hz * t))
        freq_upper  = freq * _cents_to_ratio(3.0) * (1.0 + (_cents_to_ratio(0.45) - 1.0) * np.sin(2.0 * np.pi * 5.1 * t))
        freq_lower  = freq * _cents_to_ratio(-3.0) * (1.0 + (_cents_to_ratio(0.45) - 1.0) * np.sin(2.0 * np.pi * 4.9 * t))
        phase_c = 2.0 * np.pi * np.cumsum(freq_center / sr)
        phase_u = 2.0 * np.pi * np.cumsum(freq_upper / sr)
        phase_l = 2.0 * np.pi * np.cumsum(freq_lower / sr)
        body_c = _bl_saw_from_phase(phase_c, freq, sr)
        body_u = _bl_saw_from_phase(phase_u, freq * _cents_to_ratio(3.0), sr)
        body_l = _bl_saw_from_phase(phase_l, freq * _cents_to_ratio(-3.0), sr)
        body = 0.46 * body_c + 0.30 * body_u + 0.24 * body_l
        noise = np.random.default_rng(_STRINGS_BOW_NOISE_SEED).standard_normal(n).astype(np.float32)
        noise = Filter(sr).band_pass(noise, 200.0, 2000.0)
        return body.astype(np.float32) + 0.08 * noise

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.warm_low_pass(sig, 5500.0)
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
        # Band-limited sawtooth with rich harmonic content
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # Lip buzz: slight pitch wobble on attack (simulates embouchure settling)
        # Modulate frequency (phase accumulation) for true pitch variation
        pitch_freq = freq * (1.0 + 0.008 * np.exp(-12.0 * t))
        phase = 2.0 * np.pi * np.cumsum(pitch_freq / sr)
        base = _bl_saw_from_phase(phase, freq, sr)
        # Mild tanh overdrive for brass harmonic saturation (growl on loud notes)
        driven = np.tanh(base.astype(np.float64) * 1.6)
        return driven.astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.resonant_low_pass(sig, 4800.0, resonance=1.4)
        return fx.reverb(sig, room_size=0.45, wet=0.18)

    return Instrument(
        name="brass",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.025, decay=0.14, sustain=0.72, release=0.24, sample_rate=sr),
        post_process=post,
        volume=0.8,
        sample_rate=sr,
    )


@InstrumentLibrary.register("piano")
def _piano(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # Three detuned string model per note (typical piano unison behavior).
        detunes_cents = (-2.3, 0.0, 2.5)
        detune_weights = (0.31, 0.42, 0.27)
        partials = ((1.0, 1.0), (2.01, 0.45), (3.03, 0.24), (4.08, 0.14), (5.17, 0.08), (6.32, 0.045))
        string_sum = np.zeros(n, dtype=np.float64)
        for cents, weight in zip(detunes_cents, detune_weights):
            f = freq * _cents_to_ratio(cents)
            partial_sig = np.zeros(n, dtype=np.float64)
            for ratio, amp in partials:
                decay = np.exp(-(2.3 + ratio * 0.55) * t)
                partial_sig += amp * np.sin(2.0 * np.pi * f * ratio * t) * decay
            string_sum += weight * partial_sig

        # Hammer noise + key click transient for recognizable piano attack.
        hammer = np.random.default_rng(_STRINGS_BOW_NOISE_SEED).standard_normal(n).astype(np.float64)
        hammer = Filter(sr).band_pass(hammer.astype(np.float32), 900.0, 7500.0).astype(np.float64)
        hammer *= np.exp(-70.0 * t) * 0.14
        click_len = max(1, int(0.004 * sr))
        key_click = np.zeros(n, dtype=np.float64)
        key_click[:click_len] = 0.8 * np.exp(-np.linspace(0.0, 9.0, click_len))

        # Mild soundboard resonance to retain PS2-era sampled-body character.
        resonance = (
            0.08 * np.sin(2.0 * np.pi * (freq * 0.5) * t)
            + 0.05 * np.sin(2.0 * np.pi * (freq * 1.5) * t)
        ) * np.exp(-4.2 * t)

        return (string_sum + hammer + key_click + resonance).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 38.0)
        sig = flt.warm_low_pass(sig, 6200.0)
        sig = fx.compress(sig, threshold=0.62, ratio=2.2, makeup_gain=1.03)
        return fx.reverb(sig, room_size=0.28, wet=0.12)

    return Instrument(
        name="piano",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.30, sustain=0.0, release=0.25, sample_rate=sr),
        post_process=post,
        volume=0.8,
        sample_rate=sr,
    )


@InstrumentLibrary.register("choir")
def _choir(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # Ensemble vibrato / pitch detuning via frequency modulation (phase accumulation)
        f1 = freq * (1.0 + 0.003 * np.sin(2.0 * np.pi * 5.2 * t))
        f2 = freq * _cents_to_ratio(5.0) * (1.0 + 0.003 * np.sin(2.0 * np.pi * 5.0 * t + 0.8))
        f3 = freq * _cents_to_ratio(-5.0) * (1.0 + 0.003 * np.sin(2.0 * np.pi * 4.8 * t + 1.6))
        phase1 = 2.0 * np.pi * np.cumsum(f1 / sr)
        phase2 = 2.0 * np.pi * np.cumsum(f2 / sr)
        phase3 = 2.0 * np.pi * np.cumsum(f3 / sr)
        # Glottal source: band-limited sawtooth (good model of vocal folds)
        g1 = _bl_saw_from_phase(phase1, freq, sr).astype(np.float64)
        g2 = _bl_saw_from_phase(phase2, freq * _cents_to_ratio(5.0), sr).astype(np.float64)
        g3 = _bl_saw_from_phase(phase3, freq * _cents_to_ratio(-5.0), sr).astype(np.float64)
        source = 0.5 * g1 + 0.27 * g2 + 0.23 * g3
        return source.astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        # Model vowel formants (approximate "ah" vowel: F1≈700, F2≈1150, F3≈2600)
        formants = np.zeros(len(sig), dtype=np.float64)
        formant_centers = (_CHOIR_FORMANTS[0], _CHOIR_FORMANTS[1], _CHOIR_FORMANTS[2])
        formant_bws = (100.0, 130.0, 220.0)
        formant_amps = (1.0, 0.65, 0.38)
        for center, bw, amp in zip(formant_centers, formant_bws, formant_amps):
            band = flt.band_pass(sig, max(80.0, center - bw), min(center + bw, 8000.0))
            formants += amp * band.astype(np.float64)
        # Breathiness layer
        formants /= sum(formant_amps)
        formants_f32 = formants.astype(np.float32)
        formants_f32 = fx.chorus(formants_f32, rate=0.7, depth=0.006, wet=0.45)
        return fx.reverb(formants_f32, room_size=0.88, wet=0.40)

    return Instrument(
        name="choir",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.32, decay=0.25, sustain=0.78, release=0.95, sample_rate=sr),
        post_process=post,
        volume=0.7,
        sample_rate=sr,
    )


@InstrumentLibrary.register("synth_pad")
def _synth_pad(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        # Band-limited sawtooth supersaw — three detuned voices
        return (
            0.34 * osc.bl_sawtooth(freq * _cents_to_ratio(-7.0), dur)
            + 0.34 * osc.bl_sawtooth(freq, dur)
            + 0.32 * osc.bl_sawtooth(freq * _cents_to_ratio(7.0), dur)
        )

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        # Resonant filter sweep from dark to bright over 2 seconds
        n = len(sig)
        low_start = flt.resonant_low_pass(sig, 350.0, resonance=1.6)
        low_end = flt.resonant_low_pass(sig, 7000.0, resonance=1.2)
        sweep_len = min(n, int(2.0 * sr))
        alpha = np.ones(n, dtype=np.float32)
        alpha[:sweep_len] = np.linspace(0.0, 1.0, sweep_len, dtype=np.float32)
        sig = low_start * (1.0 - alpha) + low_end * alpha
        sig = fx.chorus(sig, rate=0.45, depth=0.009, wet=0.55)
        return fx.reverb(sig, room_size=0.85, wet=0.44)

    return Instrument(
        name="synth_pad",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.38, decay=0.4, sustain=0.85, release=1.2, sample_rate=sr),
        post_process=post,
        volume=0.65,
        sample_rate=sr,
    )


@InstrumentLibrary.register("electric_guitar")
def _electric_guitar(sr: int = 44100) -> Instrument:
    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        fm = osc.fm(freq, freq * 2.0, dur, modulation_index=3.2).astype(np.float64)
        saw = osc.bl_sawtooth(freq, dur).astype(np.float64) * 0.25
        pick = np.random.default_rng(_GUITAR_PICK_NOISE_SEED).standard_normal(n).astype(np.float32)
        pick = Filter(sr).band_pass(pick, 1600.0, 7800.0).astype(np.float64)
        pick *= np.exp(-55.0 * t) * 0.18
        return (fm + saw + pick).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = fx.distortion(sig, drive=3.2, tone=0.58)
        sig = flt.high_pass(sig, 90.0)
        sig = flt.low_pass(sig, 5200.0)
        sig = flt.band_pass(sig, 130.0, 4200.0)  # cabinet-like narrowing
        sig = fx.compress(sig, threshold=0.58, ratio=3.2, makeup_gain=1.08)
        return fx.reverb(sig, room_size=0.24, wet=0.09)

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
        # Band-limited sawtooth for warm bass without aliasing buzz
        fundamental = osc.bl_sawtooth(freq, dur) * 0.72
        second = osc.sine(freq * 2.0, dur, amplitude=0.28)
        pick = np.zeros(n, dtype=np.float32)
        pick_len = max(1, int(0.008 * sr))
        pick_noise = np.random.default_rng(_BASS_PICK_NOISE_SEED).standard_normal(pick_len).astype(np.float32)
        pick[:pick_len] = pick_noise * np.exp(-np.linspace(0.0, 6.0, pick_len))
        return fundamental + second + 0.08 * pick

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.resonant_low_pass(sig, 800.0, resonance=1.3)
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
    Modelled here with a band-limited sawtooth ensemble + gentle low-pass + chorus.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        s1 = osc.bl_sawtooth(freq, dur) * 0.55
        s2 = osc.bl_sawtooth(freq * 1.007, dur) * 0.28   # detune
        s3 = osc.bl_sawtooth(freq * 0.994, dur) * 0.17   # detune low
        return s1 + s2 + s3

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr)
        sig = flt.warm_low_pass(sig, 3600.0)   # compressed bandwidth of ADPCM
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

    Uses a band-limited sawtooth + square blend for the mid-punch character of
    the PS1 bass samples.  Filter sweeps to 600 Hz to stay out of the melody.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        saw = osc.bl_sawtooth(freq, dur) * 0.65
        sq  = osc.bl_square(freq, dur, duty_cycle=0.45) * 0.35
        return saw + sq

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        from audio_engine.synthesizer.filter import Filter
        flt = Filter(sr, order=8)  # high-order LP keeps bass energy strictly below 500 Hz
        sig = flt.low_pass(sig, 500.0)
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
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        fm = osc.fm(freq, freq * 2.0, dur, modulation_index=3.8).astype(np.float64)
        sq = osc.bl_square(freq, dur, duty_cycle=0.48).astype(np.float64) * 0.3
        pick = np.random.default_rng(_GUITAR_PICK_NOISE_SEED + 2).standard_normal(n).astype(np.float32)
        pick = Filter(sr).band_pass(pick, 2200.0, 8500.0).astype(np.float64)
        pick *= np.exp(-65.0 * t) * 0.22
        return (fm + sq + pick).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = fx.distortion(sig, drive=6.0, tone=0.65)
        sig = flt.band_pass(sig, 100.0, 5500.0)
        sig = flt.resonant_low_pass(sig, 4700.0, resonance=1.25)
        sig = fx.compress(sig, threshold=0.45, ratio=5.0, makeup_gain=1.15)
        return fx.reverb(sig, room_size=0.2, wet=0.08)

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

_OBOE_NOISE_SEED = 37
_CLARINET_NOISE_SEED = 41
_HARP_NOISE_SEED = 53
_TIMPANI_NOISE_SEED = 67


@InstrumentLibrary.register("oboe")
def _oboe(sr: int = 44100) -> Instrument:
    """Nasal, double-reed woodwind — the characteristic voice of the oboe.

    Uses FM synthesis with a sawtooth carrier and narrow bandpass filtering
    to create the oboe's distinctive "nasal" resonance peak around 1 kHz.
    """

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        # Slight vibrato on the carrier via frequency modulation (phase accumulation)
        t = np.arange(n, dtype=np.float64) / sr
        carrier_freq = freq * (1.0 + 0.004 * np.sin(2.0 * np.pi * 5.5 * t))
        phase = 2.0 * np.pi * np.cumsum(carrier_freq / sr)
        carrier = _bl_saw_from_phase(phase, freq, sr).astype(np.float64)
        # Add weak reed buzz via high-frequency FM modulation
        mod_phase = 2.0 * np.pi * freq * 2.0 * np.arange(n, dtype=np.float64) / sr
        buzz = (0.18 * np.sin(mod_phase + 1.6 * np.sin(mod_phase * 0.5))).astype(np.float32)
        # Seeded reed-breath noise (filtered white noise simulating air through the reed)
        breath = np.random.default_rng(_OBOE_NOISE_SEED).standard_normal(n).astype(np.float32)
        breath = Filter(sr).band_pass(breath, 400.0, 2500.0)
        return (carrier.astype(np.float32) + buzz + 0.06 * breath)

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
        tones = h1 + h3 + h5 + h7
        # Seeded air-column breath noise (low-amplitude, narrow-band — the clarinet "hiss")
        n = len(h1)
        air = np.random.default_rng(_CLARINET_NOISE_SEED).standard_normal(n).astype(np.float32)
        air = Filter(sr).band_pass(air, 250.0, 1500.0)
        return tones + 0.05 * air

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
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        # Pitch vibrato via frequency modulation (phase accumulation)
        freq_center = freq * (1.0 + 0.003 * np.sin(2.0 * np.pi * 4.5 * t))
        freq_upper  = freq * _cents_to_ratio(4.0) * (1.0 + 0.003 * np.sin(2.0 * np.pi * 4.6 * t + 0.5))
        freq_lower  = freq * _cents_to_ratio(-4.0) * (1.0 + 0.003 * np.sin(2.0 * np.pi * 4.4 * t + 1.0))
        phase_c = 2.0 * np.pi * np.cumsum(freq_center / sr)
        phase_u = 2.0 * np.pi * np.cumsum(freq_upper / sr)
        phase_l = 2.0 * np.pi * np.cumsum(freq_lower / sr)
        body_c = _bl_saw_from_phase(phase_c, freq, sr).astype(np.float64)
        body_u = _bl_saw_from_phase(phase_u, freq * _cents_to_ratio(4.0), sr).astype(np.float64)
        body_l = _bl_saw_from_phase(phase_l, freq * _cents_to_ratio(-4.0), sr).astype(np.float64)
        body = 0.55 * body_c + 0.25 * body_u + 0.20 * body_l
        noise = np.random.default_rng(_STRINGS_BOW_NOISE_SEED + 3).standard_normal(n).astype(np.float32)
        noise = Filter(sr).band_pass(noise, 100.0, 1200.0)
        return body.astype(np.float32) + 0.07 * noise

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.warm_low_pass(sig, 3800.0)
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
        # Seeded fingernail pluck transient (bright, very fast-decaying noise burst)
        pluck_noise = np.random.default_rng(_HARP_NOISE_SEED).standard_normal(n).astype(np.float32)
        pluck_noise = Filter(sr).band_pass(pluck_noise, 1000.0, 8000.0)
        pluck_noise *= np.exp(-50.0 * t).astype(np.float32)
        return carrier + second + 0.10 * pluck_noise

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


@InstrumentLibrary.register("violin_solo")
def _violin_solo(sr: int = 44100) -> Instrument:
    """Expressive solo violin with narrow vibrato and bow-noise edge."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        phase = _vibrato_phase(freq, dur, sr, rate_hz=6.1, depth_semitones=0.09)
        body = _bl_saw_from_phase(phase, freq, sr)
        n = len(body)
        t = np.arange(n, dtype=np.float64) / sr
        harmonic = np.sin(phase * 2.0).astype(np.float32) * np.exp(-0.18 * t).astype(np.float32) * 0.12
        bow_noise = np.random.default_rng(_VIOLIN_NOISE_SEED).standard_normal(n).astype(np.float32)
        bow_noise = Filter(sr).band_pass(bow_noise, 900.0, 5200.0) * 0.07
        bow_transient = np.random.default_rng(_VIOLIN_NOISE_SEED + 1).standard_normal(n).astype(np.float32)
        bow_transient = Filter(sr).band_pass(bow_transient, 1400.0, 6800.0)
        bow_transient = bow_transient * np.exp(-16.0 * t).astype(np.float32) * 0.09
        return (0.86 * body + harmonic + bow_noise + bow_transient).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 140.0)
        sig = flt.band_pass(sig, 180.0, 7600.0)
        sig = fx.compress(sig, threshold=0.64, ratio=2.4, makeup_gain=1.05)
        return fx.reverb(sig, room_size=0.40, wet=0.15)

    return Instrument(
        name="violin_solo",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.018, decay=0.16, sustain=0.72, release=0.24, sample_rate=sr),
        post_process=post,
        volume=0.80,
        sample_rate=sr,
    )


@InstrumentLibrary.register("trumpet")
def _trumpet(sr: int = 44100) -> Instrument:
    """Bright trumpet lead with brassy buzz and controlled bite."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        scoop = 1.0 + 0.035 * np.exp(-18.0 * t)
        phase = 2.0 * np.pi * np.cumsum((freq * scoop) / sr)
        base = _bl_saw_from_phase(phase, freq, sr)
        buzz = np.sin(phase * 2.0).astype(np.float32) * 0.22
        edge = np.sin(phase * 3.0).astype(np.float32) * 0.10
        breath = np.random.default_rng(_TRUMPET_NOISE_SEED).standard_normal(n).astype(np.float32)
        breath = Filter(sr).band_pass(breath, 1200.0, 7000.0) * 0.04
        return (0.70 * base + buzz + edge + breath).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 180.0)
        sig = flt.band_pass(sig, 240.0, 7600.0)
        sig = fx.compress(sig, threshold=0.57, ratio=3.0, makeup_gain=1.08)
        return fx.reverb(sig, room_size=0.35, wet=0.12)

    return Instrument(
        name="trumpet",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.01, decay=0.11, sustain=0.66, release=0.16, sample_rate=sr),
        post_process=post,
        volume=0.82,
        sample_rate=sr,
    )


@InstrumentLibrary.register("acoustic_guitar")
def _acoustic_guitar(sr: int = 44100) -> Instrument:
    """Nylon/steel hybrid pluck suited for folk and festival styles."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        fundamental = np.sin(2.0 * np.pi * freq * t) * np.exp(-4.8 * t)
        second = 0.33 * np.sin(2.0 * np.pi * (freq * 2.0) * t) * np.exp(-8.0 * t)
        third = 0.20 * np.sin(2.0 * np.pi * (freq * 3.01) * t) * np.exp(-10.5 * t)
        fourth = 0.10 * np.sin(2.0 * np.pi * (freq * 4.18) * t) * np.exp(-13.5 * t)
        body = (fundamental + second + third + fourth).astype(np.float32)

        # Acoustic body resonances (air + wood cavity) for guitar identity.
        resonance = (
            0.09 * np.sin(2.0 * np.pi * 110.0 * t)
            + 0.07 * np.sin(2.0 * np.pi * 220.0 * t)
            + 0.05 * np.sin(2.0 * np.pi * 440.0 * t)
        ) * np.exp(-6.4 * t)

        pick = np.random.default_rng(_GUITAR_PICK_NOISE_SEED).standard_normal(n).astype(np.float32)
        pick = Filter(sr).band_pass(pick, 1400.0, 9200.0) * np.exp(-52.0 * t).astype(np.float32) * 0.28
        fret = np.random.default_rng(_GUITAR_PICK_NOISE_SEED + 1).standard_normal(n).astype(np.float32)
        fret = Filter(sr).band_pass(fret, 2800.0, 10000.0) * np.exp(-88.0 * t).astype(np.float32) * 0.06
        return (body + resonance.astype(np.float32) + pick + fret).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 75.0)
        sig = flt.warm_low_pass(sig, 7600.0)
        sig = flt.band_pass(sig, 90.0, 6200.0)
        sig = fx.compress(sig, threshold=0.66, ratio=2.2, makeup_gain=1.03)
        return fx.reverb(sig, room_size=0.22, wet=0.10)

    return Instrument(
        name="acoustic_guitar",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.24, sustain=0.0, release=0.22, sample_rate=sr),
        post_process=post,
        volume=0.77,
        sample_rate=sr,
    )


@InstrumentLibrary.register("legato_strings_ps2")
def _legato_strings_ps2(sr: int = 44100) -> Instrument:
    """Lush legato strings with soft bow attack (PS2-era orchestral color)."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        base_phase = _vibrato_phase(freq, dur, sr, rate_hz=5.2, depth_semitones=0.07)
        upper_phase = _vibrato_phase(freq * _cents_to_ratio(4.0), dur, sr, rate_hz=5.4, depth_semitones=0.06)
        lower_phase = _vibrato_phase(freq * _cents_to_ratio(-4.0), dur, sr, rate_hz=5.0, depth_semitones=0.06)

        body = (
            0.58 * _bl_saw_from_phase(base_phase, freq, sr)
            + 0.24 * _bl_saw_from_phase(upper_phase, freq * _cents_to_ratio(4.0), sr)
            + 0.18 * _bl_saw_from_phase(lower_phase, freq * _cents_to_ratio(-4.0), sr)
        ).astype(np.float32)

        bow = np.random.default_rng(_LEGATO_STRINGS_NOISE_SEED).standard_normal(n).astype(np.float32)
        bow = Filter(sr).band_pass(bow, 280.0, 3200.0) * 0.06
        bloom = (1.0 - np.exp(-5.5 * t)).astype(np.float32)
        return (body * bloom + bow).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 120.0)
        sig = flt.warm_low_pass(sig, 5400.0)
        sig = fx.chorus(sig, depth=0.0018, rate=0.62, wet=0.16)
        sig = fx.compress(sig, threshold=0.63, ratio=2.4, makeup_gain=1.05)
        return fx.reverb(sig, room_size=0.55, wet=0.19)

    return Instrument(
        name="legato_strings_ps2",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.032, decay=0.18, sustain=0.75, release=0.34, sample_rate=sr),
        post_process=post,
        volume=0.80,
        sample_rate=sr,
    )


@InstrumentLibrary.register("nylon_guitar_ps2")
def _nylon_guitar_ps2(sr: int = 44100) -> Instrument:
    """Warm fingerstyle nylon guitar with woody body resonance."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr

        fundamental = np.sin(2.0 * np.pi * freq * t) * np.exp(-4.5 * t)
        second = 0.27 * np.sin(2.0 * np.pi * (freq * 2.0) * t) * np.exp(-6.8 * t)
        third = 0.17 * np.sin(2.0 * np.pi * (freq * 3.0) * t) * np.exp(-8.4 * t)
        body = (fundamental + second + third).astype(np.float32)

        # Body air/wood resonances tuned lower than steel/acoustic variant.
        resonances = (
            0.10 * np.sin(2.0 * np.pi * 95.0 * t)
            + 0.08 * np.sin(2.0 * np.pi * 185.0 * t)
            + 0.06 * np.sin(2.0 * np.pi * 370.0 * t)
        ) * np.exp(-5.8 * t)

        finger = np.random.default_rng(_NYLON_GUITAR_NOISE_SEED).standard_normal(n).astype(np.float32)
        finger = Filter(sr).band_pass(finger, 900.0, 5600.0) * np.exp(-42.0 * t).astype(np.float32) * 0.20
        return (body + resonances.astype(np.float32) + finger).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 70.0)
        sig = flt.warm_low_pass(sig, 6100.0)
        sig = fx.compress(sig, threshold=0.68, ratio=2.0, makeup_gain=1.02)
        return fx.reverb(sig, room_size=0.24, wet=0.11)

    return Instrument(
        name="nylon_guitar_ps2",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.001, decay=0.22, sustain=0.0, release=0.26, sample_rate=sr),
        post_process=post,
        volume=0.76,
        sample_rate=sr,
    )


@InstrumentLibrary.register("soft_epiano_ps2")
def _soft_epiano_ps2(sr: int = 44100) -> Instrument:
    """Soft electric piano with bell-tine attack and warm sustain."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        phase = 2.0 * np.pi * np.cumsum(freq * (1.0 + 0.004 * np.sin(2.0 * np.pi * 5.0 * t)) / sr)
        tine = np.sin(phase * 2.0).astype(np.float32) * np.exp(-16.0 * t).astype(np.float32) * 0.30
        body = 0.64 * _bl_saw_from_phase(phase, freq, sr)
        sub = 0.10 * np.sin(phase * 0.5).astype(np.float32)
        air = np.random.default_rng(_SOFT_EP_NOISE_SEED).standard_normal(n).astype(np.float32)
        air = Filter(sr).band_pass(air, 1800.0, 7600.0) * np.exp(-38.0 * t).astype(np.float32) * 0.035
        return (body + tine + sub + air).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 95.0)
        sig = flt.warm_low_pass(sig, 6800.0)
        sig = fx.chorus(sig, depth=0.0010, rate=0.85, wet=0.13)
        sig = fx.compress(sig, threshold=0.64, ratio=2.3, makeup_gain=1.04)
        return fx.reverb(sig, room_size=0.28, wet=0.12)

    return Instrument(
        name="soft_epiano_ps2",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.008, decay=0.18, sustain=0.58, release=0.2, sample_rate=sr),
        post_process=post,
        volume=0.78,
        sample_rate=sr,
    )


@InstrumentLibrary.register("synth_lead_bright")
def _synth_lead_bright(sr: int = 44100) -> Instrument:
    """Modern bright synth lead for electronic and sci-fi styles."""

    def osc_fn(osc: Oscillator, freq: float, dur: float) -> np.ndarray:
        n = max(1, int(dur * sr))
        t = np.arange(n, dtype=np.float64) / sr
        glide = freq * (1.0 + 0.08 * np.exp(-9.0 * t))
        phase = 2.0 * np.pi * np.cumsum(glide / sr)
        saw = _bl_saw_from_phase(phase, freq, sr)
        pulse = np.sign(np.sin(phase * 0.5)).astype(np.float32) * 0.25
        air = np.random.default_rng(_SYNTH_LEAD_NOISE_SEED).standard_normal(n).astype(np.float32)
        air = Filter(sr).band_pass(air, 3000.0, 11000.0) * 0.04
        return (0.85 * saw + pulse + air).astype(np.float32)

    def post(sig: np.ndarray, fx: Effects) -> np.ndarray:
        flt = Filter(sr)
        sig = flt.high_pass(sig, 240.0)
        sig = flt.resonant_low_pass(sig, 4800.0, resonance=1.35)
        sig = fx.chorus(sig, depth=0.0009, rate=0.75, wet=0.14)
        sig = fx.compress(sig, threshold=0.56, ratio=3.0, makeup_gain=1.08)
        return fx.reverb(sig, room_size=0.3, wet=0.1)

    return Instrument(
        name="synth_lead_bright",
        oscillator_fn=osc_fn,
        envelope=Envelope(attack=0.005, decay=0.08, sustain=0.64, release=0.12, sample_rate=sr),
        post_process=post,
        volume=0.79,
        sample_rate=sr,
    )
