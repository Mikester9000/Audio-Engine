"""
Vocal melody synthesizer — formant-based sung vowel tones.

Produces a sung melodic line from a sequence of
``(frequency_hz, duration_s, vowel)`` notes using the same formant resonance
model as :mod:`audio_engine.ai.voice_synth`, adapted for musical pitch with:

* Exact pitch control via a sine-carrier at the specified frequency.
* Vibrato (LFO pitch modulation at 5.5 Hz, ±1.5 semitones depth).
* Soft legato crossfade between consecutive notes.
* Breathiness layer for an airy vocal texture.

This is intentionally *not* a text-to-speech synthesizer — it generates a
wordless melodic hum / vowel line suitable for integrating under or alongside
an instrumental arrangement (think "Eyes on Me" orchestral vocal, FF choir
pads, etc.).

Usage
-----
>>> synth = VocalMelodySynth(sample_rate=44100, voice_preset="soprano")
>>> melody = [
...     (440.0, 1.5, "ah"),   # A4 for 1.5 s on "ah" vowel
...     (493.9, 1.0, "oh"),   # B4 for 1.0 s on "oh" vowel
...     (523.3, 2.0, "ah"),   # C5 for 2.0 s on "ah" vowel
... ]
>>> audio = synth.synthesize(melody)
"""

from __future__ import annotations

from typing import Literal

import numpy as np

__all__ = ["VocalMelodySynth", "VOCAL_PRESETS"]

VocalPreset = Literal["soprano", "alto", "tenor", "choir_ah"]

# ---------------------------------------------------------------------------
# Vowel formant tables (F1, F2 in Hz)
# Approximate values from Peterson & Barney (1952)
# ---------------------------------------------------------------------------

_VOWEL_FORMANTS: dict[str, tuple[float, float]] = {
    "ah":  (800.0,  1200.0),   # "father" vowel — most open
    "oh":  (500.0,   900.0),   # "boat"
    "ee":  (300.0,  2300.0),   # "see"
    "oo":  (300.0,   900.0),   # "moon"
    "eh":  (600.0,  1700.0),   # "bed"
    "mm":  (280.0,  1100.0),   # closed hum
    "hm":  (300.0,   900.0),   # nasal hum
}

_DEFAULT_VOWEL = "ah"


class _VocalPreset:
    __slots__ = ("vibrato_depth_semitones", "breathiness", "jitter", "volume")

    def __init__(
        self,
        vibrato_depth_semitones: float,
        breathiness: float,
        jitter: float,
        volume: float,
    ) -> None:
        self.vibrato_depth_semitones = vibrato_depth_semitones
        self.breathiness = breathiness
        self.jitter = jitter
        self.volume = volume


VOCAL_PRESETS: dict[str, _VocalPreset] = {
    "soprano":  _VocalPreset(vibrato_depth_semitones=1.2, breathiness=0.08, jitter=0.003, volume=0.85),
    "alto":     _VocalPreset(vibrato_depth_semitones=0.9, breathiness=0.06, jitter=0.004, volume=0.82),
    "tenor":    _VocalPreset(vibrato_depth_semitones=1.0, breathiness=0.07, jitter=0.004, volume=0.80),
    "choir_ah": _VocalPreset(vibrato_depth_semitones=0.6, breathiness=0.04, jitter=0.002, volume=0.75),
}


class VocalMelodySynth:
    """Formant-based sung vowel melody synthesizer.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    voice_preset:
        One of ``"soprano"``, ``"alto"``, ``"tenor"``, ``"choir_ah"``.
    vibrato_rate_hz:
        LFO frequency for vibrato (default 5.5 Hz — typical classical vibrato).
    legato_ms:
        Cross-fade length in milliseconds between consecutive notes
        (default 30 ms).
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        voice_preset: VocalPreset = "soprano",
        vibrato_rate_hz: float = 5.5,
        legato_ms: float = 30.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.vibrato_rate_hz = vibrato_rate_hz
        self.legato_samples = max(1, int(legato_ms * sample_rate / 1000.0))
        preset_key = voice_preset if voice_preset in VOCAL_PRESETS else "soprano"
        self._preset = VOCAL_PRESETS[preset_key]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(
        self,
        notes: list[tuple[float, float, str]],
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """Synthesize a melodic vocal line.

        Parameters
        ----------
        notes:
            List of ``(frequency_hz, duration_s, vowel)`` tuples.
            *vowel* must be one of: ``ah``, ``oh``, ``ee``, ``oo``,
            ``eh``, ``mm``, ``hm``.
        rng:
            Optional RNG for reproducible breathiness noise.

        Returns
        -------
        np.ndarray
            Mono float32 audio.
        """
        if rng is None:
            rng = np.random.default_rng(0)

        segments: list[np.ndarray] = []
        for freq, dur, vowel in notes:
            segment = self._synthesize_note(freq, dur, vowel, rng)
            segments.append(segment)

        if not segments:
            return np.zeros(0, dtype=np.float32)

        return self._join_with_legato(segments)

    def synthesize_ah_melody(
        self,
        freqs: list[float],
        durations: list[float],
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """Convenience wrapper: synthesize all notes on 'ah' vowel."""
        notes = [(f, d, "ah") for f, d in zip(freqs, durations)]
        return self.synthesize(notes, rng=rng)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _synthesize_note(
        self,
        freq: float,
        duration: float,
        vowel: str,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Synthesize a single sustained vocal note."""
        sr = self.sample_rate
        n = max(1, int(duration * sr))
        t = np.arange(n, dtype=np.float64) / sr
        preset = self._preset

        # Vibrato: pitch-modulated carrier
        vibrato_freq_ratio = 2.0 ** (preset.vibrato_depth_semitones / 12.0)
        # LFO depth in Hz, only ramps in after onset (natural vibrato delay)
        lfo_env = np.clip((t - 0.15) / 0.20, 0.0, 1.0)  # fades in at 150 ms
        vibrato_cents = (vibrato_freq_ratio - 1.0) * freq * np.sin(
            2.0 * np.pi * self.vibrato_rate_hz * t
        ) * lfo_env
        # Slight random pitch jitter
        jitter = preset.jitter * rng.standard_normal(n)
        inst_freq = freq + vibrato_cents + jitter * freq

        # Carrier phase integration
        phase = np.cumsum(2.0 * np.pi * inst_freq / sr)
        carrier = np.sin(phase)

        # Formant colouring via two resonance band-pass filters
        formant_sig = self._apply_formants(carrier.astype(np.float32), vowel)

        # Breathiness: band-limited noise (air rushing through vocal cords)
        breath_noise = rng.standard_normal(n).astype(np.float32)
        breath_noise = self._hpf(breath_noise, 3000.0)
        breath_noise *= preset.breathiness

        # Mix carrier + breath
        mixed = formant_sig + breath_noise

        # ADSR envelope — slow attack/release for legato feel
        env = self._build_vocal_env(n, sr, duration)
        result = (mixed * env * preset.volume).astype(np.float32)

        # Normalise to avoid clipping
        peak = np.max(np.abs(result))
        if peak > 1e-9:
            result = result / peak * 0.80
        return result

    def _apply_formants(self, signal: np.ndarray, vowel: str) -> np.ndarray:
        """Apply two resonant band-pass filters for vowel formants."""
        f1, f2 = _VOWEL_FORMANTS.get(vowel, _VOWEL_FORMANTS[_DEFAULT_VOWEL])
        try:
            from scipy.signal import butter, sosfilt  # type: ignore[import]
            sr = self.sample_rate
            nyq = sr / 2.0

            def _bp(sig: np.ndarray, fc: float, bw: float = 200.0) -> np.ndarray:
                lo = max(30.0, fc - bw / 2.0) / nyq
                hi = min(nyq - 1.0, fc + bw / 2.0) / nyq
                if hi <= lo:
                    return sig
                sos = butter(2, [lo, hi], btype="band", output="sos")
                return sosfilt(sos, signal.astype(np.float64)).astype(np.float32)

            f1_sig = _bp(signal, f1, bw=300.0) * 1.0
            f2_sig = _bp(signal, f2, bw=250.0) * 0.7
            # Keep a little of the fundamental
            mixed = 0.4 * signal + 0.45 * f1_sig + 0.15 * f2_sig
        except ImportError:
            mixed = signal  # scipy unavailable: return uncoloured carrier

        return mixed.astype(np.float32)

    def _hpf(self, signal: np.ndarray, cutoff: float) -> np.ndarray:
        """Single-pole high-pass for breath noise."""
        try:
            from scipy.signal import butter, sosfilt  # type: ignore[import]
            nyq = self.sample_rate / 2.0
            sos = butter(2, cutoff / nyq, btype="high", output="sos")
            return sosfilt(sos, signal.astype(np.float64)).astype(np.float32)
        except ImportError:
            return signal

    def _build_vocal_env(self, n: int, sr: int, duration: float) -> np.ndarray:
        """ADSR envelope tuned for sustained singing."""
        attack_n  = min(int(0.05 * sr), n)         # 50 ms attack
        release_n = min(int(0.12 * sr), max(0, n - attack_n))
        sustain_n = n - attack_n - release_n

        env = np.zeros(n, dtype=np.float32)
        if attack_n > 0:
            env[:attack_n] = np.linspace(0.0, 1.0, attack_n)
        if sustain_n > 0:
            env[attack_n:attack_n + sustain_n] = 1.0
        if release_n > 0:
            env[attack_n + sustain_n:] = np.linspace(1.0, 0.0, release_n)
        return env

    def _join_with_legato(self, segments: list[np.ndarray]) -> np.ndarray:
        """Concatenate segments with short overlap-add crossfade for legato."""
        if len(segments) == 1:
            return segments[0]

        xfade = self.legato_samples
        result_parts = [segments[0]]

        for seg in segments[1:]:
            prev = result_parts[-1]
            if len(prev) >= xfade and len(seg) >= xfade:
                # Overlap: fade out end of prev, fade in start of seg
                fade_out = np.linspace(1.0, 0.0, xfade, dtype=np.float32)
                fade_in  = np.linspace(0.0, 1.0, xfade, dtype=np.float32)
                blended = prev[-xfade:] * fade_out + seg[:xfade] * fade_in
                result_parts[-1] = np.concatenate([prev[:-xfade], blended])
                result_parts.append(seg[xfade:])
            else:
                result_parts.append(seg)

        return np.concatenate(result_parts).astype(np.float32)
