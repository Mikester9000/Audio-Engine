"""Deterministic procedural voice synthesis with phoneme-class shaping.

Public interface:
    synthesise_voice(text, voice_preset=\"narrator\", speed=1.0, sample_rate=22050, seed=None)
        -> mono float32 NumPy array

The implementation stays fully offline and uses:
- multi-stage glottal excitation (with jitter + sub-harmonics),
- voiced/unvoiced phoneme segmentation,
- plosive/fricative transient/noise layers,
- sentence-level pitch arcs and per-segment envelopes.
"""

from __future__ import annotations

import re
import zlib
from typing import NamedTuple

import numpy as np

__all__ = ["synthesise_voice", "VOICE_PRESETS"]


class _VoicePreset(NamedTuple):
    f0: float
    formant_shifts: tuple[float, float, float]
    jitter: float
    breathiness: float


VOICE_PRESETS: dict[str, _VoicePreset] = {
    "narrator": _VoicePreset(f0=120.0, formant_shifts=(1.0, 1.0, 1.0), jitter=0.012, breathiness=0.05),
    "hero": _VoicePreset(f0=112.0, formant_shifts=(1.05, 0.95, 0.98), jitter=0.015, breathiness=0.04),
    "villain": _VoicePreset(f0=90.0, formant_shifts=(0.9, 1.08, 1.05), jitter=0.02, breathiness=0.08),
    "announcer": _VoicePreset(f0=135.0, formant_shifts=(1.08, 1.0, 0.95), jitter=0.008, breathiness=0.025),
    "npc": _VoicePreset(f0=150.0, formant_shifts=(1.15, 1.05, 1.0), jitter=0.028, breathiness=0.1),
}

# Per-vowel formant frequencies (F1, F2, F3) in Hz for adult average voice
# Source: standard phonetics reference values
_VOWEL_FORMANTS: dict[str, tuple[float, float, float]] = {
    "a": (800.0, 1200.0, 2600.0),  # "ah" as in "father"
    "e": (400.0, 2000.0, 2800.0),  # "eh" as in "bed"
    "i": (280.0, 2700.0, 3200.0),  # "ee" as in "see"
    "o": (450.0, 800.0, 2500.0),   # "oh" as in "go"
    "u": (310.0, 870.0, 2400.0),   # "oo" as in "moon"
    "y": (390.0, 2000.0, 2700.0),  # "y" treated as /ɪ/
}
_BASE_FORMANTS = np.array([700.0, 1220.0, 2600.0], dtype=np.float64)  # fallback neutral
_SUBHARMONIC_PHASE_OFFSET = 0.33
_NOISE_BAND_MIN = 0.001  # Avoid zero-width/zero-frequency band edges during normalization.
_NOISE_BAND_MAX = 0.949  # Leave room for the minimum high-edge spacing below Nyquist.
_NOISE_BAND_MIN_WIDTH = 0.05  # Keep a stable minimum normalized band-pass width for low sample rates.
_VOCAL_HP_CUTOFF_HZ = 40.0
_VOCAL_LP_CUTOFF_HZ = 9800.0
_PRESENCE_BAND_LO_HZ = 1200.0
_PRESENCE_BAND_HI_HZ = 4200.0
_DEESS_BAND_LO_HZ = 5200.0
_DEESS_BAND_HI_HZ = 9800.0
_PRESENCE_LIFT_GAIN = 0.10
_DEESS_ATTENUATION = 0.35
_SATURATION_DRIVE = 1.25
_REFLECTION_DELAY_1_S = 0.011
_REFLECTION_DELAY_2_S = 0.019
_REFLECTION_GAIN_1 = 0.12
_REFLECTION_GAIN_2 = 0.08
_POST_MIN_NORMALIZED_FREQ = 0.001
_POST_MAX_NORMALIZED_FREQ = 0.99
_POST_PRESENCE_MIN_NORMALIZED = 0.01
_POST_PRESENCE_MAX_NORMALIZED = 0.97
_POST_DEESS_MIN_NORMALIZED = 0.02
_POST_DEESS_MAX_NORMALIZED = 0.99
_DEESS_WINDOW_SECONDS = 0.004
_DEESS_WINDOW_MIN_SAMPLES = 8

_VOWELS = set("aeiouy")
_PLOSIVES = set("pbtdkg")
_FRICATIVES = set("sfzxv")
_SH_SET = {"sh", "ch"}


def _stable_seed(text: str, seed: int | None) -> int:
    crc = zlib.crc32(text.encode("utf-8"))
    return ((seed or 0) & 0x7FFFFFFF) ^ (crc & 0x7FFFFFFF)


def _tokenise(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z]+|[?.!,;:]", text.lower())
    tokens: list[str] = []
    for token in raw:
        if token in {"?", ".", "!", ",", ";", ":"}:
            tokens.append(token)
            continue
        i = 0
        while i < len(token):
            if i + 1 < len(token) and token[i : i + 2] in _SH_SET:
                tokens.append(token[i : i + 2])
                i += 2
            else:
                tokens.append(token[i])
                i += 1
    return tokens


def _segment_duration(token: str, speed: float) -> float:
    speed = max(speed, 0.5)
    if token in {".", "!", "?"}:
        return 0.09 / speed
    if token in {",", ";", ":"}:
        return 0.05 / speed
    if token in _VOWELS:
        return 0.08 / speed
    if token in _SH_SET:
        return 0.07 / speed
    return 0.045 / speed


def _sentence_pitch_arc(tokens: list[str], question: bool) -> np.ndarray:
    spoken = [t for t in tokens if t not in {".", "!", "?", ",", ";", ":"}]
    if not spoken:
        return np.array([1.0], dtype=np.float64)
    n = len(spoken)
    if question:
        return np.linspace(0.95, 1.09, n, dtype=np.float64)
    return np.linspace(1.06, 0.94, n, dtype=np.float64)


def _glottal_excitation(f0: float, duration: float, sr: int, jitter: float, rng: np.random.Generator) -> np.ndarray:
    """Synthesise a realistic glottal source signal.

    Uses a band-limited sawtooth (additive harmonics up to Nyquist) with
    pitch jitter and vibrato modulation for natural vocal variation.  The
    band-limited approach avoids the aliasing that made earlier versions of
    this function sound harsh and buzzy.
    """
    n = max(1, int(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    # Micro-vibrato (6 Hz, small depth) + jitter (random cycle-to-cycle irregularity)
    micro = 1.0 + 0.012 * np.sin(2.0 * np.pi * 6.1 * t + rng.uniform(0, 2 * np.pi))
    irregular = 1.0 + jitter * rng.normal(0.0, 0.55, n)
    f_track = np.clip(f0 * micro * irregular, 40.0, sr / 3.0)
    phase = 2.0 * np.pi * np.cumsum(f_track / sr)

    # Band-limited glottal source: sum harmonics up to Nyquist
    nyquist = sr / 2.0
    n_harmonics = min(int(nyquist / max(f0, 1.0)), 40)  # cap at 40 for speed
    glottal = np.zeros(n, dtype=np.float64)
    for k in range(1, n_harmonics + 1):
        # Glottal spectral tilt: 1/k amplitude (natural roll-off of vocal source)
        amp = 1.0 / k
        glottal += amp * np.sin(k * phase)
    # Sub-harmonic gives the "chest register" richness
    glottal += 0.28 * np.sin(0.5 * phase + _SUBHARMONIC_PHASE_OFFSET)
    return glottal.astype(np.float32)


def _formant_filter(
    signal: np.ndarray,
    shifts: tuple[float, float, float],
    sr: int,
    base_formants: np.ndarray | None = None,
) -> np.ndarray:
    """Apply formant bandpass filters to a glottal source.

    Parameters
    ----------
    signal:
        Glottal source signal.
    shifts:
        Per-formant frequency scaling factors from the voice preset.
    sr:
        Sample rate.
    base_formants:
        Base formant frequencies (F1, F2, F3) in Hz.  Uses the neutral
        defaults if not provided.  Pass vowel-specific values for more
        realistic vowel quality.
    """
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    if base_formants is None:
        base_formants = _BASE_FORMANTS

    sig = signal.astype(np.float64)
    out = np.zeros_like(sig)
    bw_values = (95.0, 130.0, 170.0)
    amp_values = (1.0, 0.85, 0.55)  # F1 loudest, F3 softer — realistic spectral tilt
    for base, shift, bw, amp in zip(base_formants, shifts, bw_values, amp_values):
        center = float(base * shift)
        lo = max(60.0, center - bw)
        hi = min(sr / 2.0 - 10.0, center + bw)
        if hi <= lo:
            continue
        sos = butter(2, [lo / (sr / 2.0), hi / (sr / 2.0)], btype="band", output="sos")
        out += amp * sosfilt(sos, sig)
    return out.astype(np.float32)


def _noise_layer(duration: float, sr: int, rng: np.random.Generator, lo: float, hi: float) -> np.ndarray:
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    n = max(1, int(duration * sr))
    raw = rng.standard_normal(n).astype(np.float64)
    nyq = sr / 2.0
    if nyq <= 0.0 or hi <= 0.0 or lo >= nyq:
        return raw.astype(np.float32)
    lo_n = float(np.clip(lo / nyq, _NOISE_BAND_MIN, _NOISE_BAND_MAX))
    hi_n = float(np.clip(hi / nyq, lo_n + _NOISE_BAND_MIN_WIDTH, 0.999))
    if hi_n <= lo_n:
        return raw.astype(np.float32)
    sos = butter(3, [lo_n, hi_n], btype="band", output="sos")
    return sosfilt(sos, raw).astype(np.float32)


def _segment_env(n: int) -> np.ndarray:
    if n <= 1:
        return np.ones(max(1, n), dtype=np.float32)
    a = max(1, int(0.2 * n))
    r = max(1, int(0.25 * n))
    s = max(0, n - a - r)
    return np.concatenate(
        [
            np.linspace(0.0, 1.0, a, dtype=np.float32),
            np.ones(s, dtype=np.float32),
            np.linspace(1.0, 0.0, r, dtype=np.float32),
        ]
    )[:n]


def _studio_vocal_post(signal: np.ndarray, sr: int) -> np.ndarray:
    """Apply deterministic vocal post-processing polish.

    Parameters
    ----------
    signal:
        Mono float audio array to process.
    sr:
        Sample rate in Hz.

    Returns
    -------
    np.ndarray
        Mono float32 audio after a fixed processing chain:
        high/low-pass cleanup, presence lift, de-essing, mild saturation,
        and short early reflections.
    """
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    if len(signal) == 0:
        return signal.astype(np.float32)

    sig = signal.astype(np.float64)
    sig -= float(np.mean(sig))

    # Cleanup low rumble and harsh top-end.
    hp = butter(
        2,
        max(_VOCAL_HP_CUTOFF_HZ / (sr / 2.0), _POST_MIN_NORMALIZED_FREQ),
        btype="highpass",
        output="sos",
    )
    lp = butter(
        2,
        min(_VOCAL_LP_CUTOFF_HZ / (sr / 2.0), _POST_MAX_NORMALIZED_FREQ),
        btype="lowpass",
        output="sos",
    )
    sig = sosfilt(hp, sig)
    sig = sosfilt(lp, sig)

    # Presence lift for intelligibility.
    lo = max(_PRESENCE_BAND_LO_HZ / (sr / 2.0), _POST_PRESENCE_MIN_NORMALIZED)
    hi = min(_PRESENCE_BAND_HI_HZ / (sr / 2.0), _POST_PRESENCE_MAX_NORMALIZED)
    if hi > lo:
        presence = sosfilt(butter(2, [lo, hi], btype="bandpass", output="sos"), sig)
        sig = sig + _PRESENCE_LIFT_GAIN * presence

    # De-ess: dynamic attenuation of high-band spikes.
    s_lo = max(_DEESS_BAND_LO_HZ / (sr / 2.0), _POST_DEESS_MIN_NORMALIZED)
    s_hi = min(_DEESS_BAND_HI_HZ / (sr / 2.0), _POST_DEESS_MAX_NORMALIZED)
    if s_hi > s_lo:
        sib = sosfilt(butter(2, [s_lo, s_hi], btype="bandpass", output="sos"), sig)
        window_size = max(_DEESS_WINDOW_MIN_SAMPLES, int(_DEESS_WINDOW_SECONDS * sr))
        env = np.convolve(np.abs(sib), np.ones(window_size) / window_size, mode="same")
        env = env / (float(np.max(env)) + 1e-9)
        sig = sig - sib * (_DEESS_ATTENUATION * env)

    # Gentle non-linear smoothing + short room reflections.
    sig = np.tanh(sig * _SATURATION_DRIVE)
    d1 = max(1, int(_REFLECTION_DELAY_1_S * sr))
    d2 = max(1, int(_REFLECTION_DELAY_2_S * sr))
    refl = np.zeros_like(sig)
    if len(sig) > d1:
        refl[d1:] += _REFLECTION_GAIN_1 * sig[:-d1]
    if len(sig) > d2:
        refl[d2:] += _REFLECTION_GAIN_2 * sig[:-d2]
    sig = sig + refl
    return np.clip(sig, -1.0, 1.0).astype(np.float32)


def synthesise_voice(
    text: str,
    voice_preset: str = "narrator",
    speed: float = 1.0,
    sample_rate: int = 22050,
    seed: int | None = None,
) -> np.ndarray:
    """Synthesize deterministic speech-like audio from text."""
    if not text:
        return np.zeros(int(0.4 * sample_rate), dtype=np.float32)

    preset = VOICE_PRESETS.get(voice_preset, VOICE_PRESETS["narrator"])
    rng = np.random.default_rng(_stable_seed(text + voice_preset, seed))

    tokens = _tokenise(text)
    spoken_tokens = [t for t in tokens if t not in {".", "!", "?", ",", ";", ":"}]
    question = text.strip().endswith("?")
    pitch_arc = _sentence_pitch_arc(tokens, question)

    pieces: list[np.ndarray] = []
    voiced_index = 0
    for token in tokens:
        duration = _segment_duration(token, speed)
        n = max(1, int(duration * sample_rate))

        if token in {".", "!", "?", ",", ";", ":"}:
            pieces.append(np.zeros(n, dtype=np.float32))
            continue

        arc_mul = pitch_arc[min(voiced_index, len(pitch_arc) - 1)]
        voiced_index += 1
        base_f0 = preset.f0 * arc_mul

        if token in _VOWELS:
            voiced = _glottal_excitation(base_f0, duration, sample_rate, preset.jitter, rng)
            # Use per-vowel formant frequencies for more distinct vowel quality
            vowel_bases = np.array(
                _VOWEL_FORMANTS.get(token, tuple(_BASE_FORMANTS.tolist())),
                dtype=np.float64,
            )
            segment = _formant_filter(voiced, preset.formant_shifts, sample_rate, vowel_bases)
            shimmer = 0.03 * np.sin(2.0 * np.pi * 12.0 * np.arange(n) / sample_rate + rng.uniform(0, 2 * np.pi))
            segment = segment[:n] * (1.0 + shimmer.astype(np.float32))
        else:
            if token in _FRICATIVES or token in _SH_SET:
                lo, hi = (2800.0, 11000.0) if token != "f" else (1800.0, 7000.0)
                segment = _noise_layer(duration, sample_rate, rng, lo, hi)
            else:
                segment = _noise_layer(duration, sample_rate, rng, 300.0, 6000.0) * 0.45

            if token in _PLOSIVES:
                click_n = max(1, int(0.004 * sample_rate))
                click = np.zeros(n, dtype=np.float32)
                click[:click_n] = np.linspace(1.0, 0.0, click_n, dtype=np.float32)
                segment = segment + click

            if token in {"r", "l", "m", "n"}:
                voiced = _glottal_excitation(base_f0 * 0.9, duration, sample_rate, preset.jitter * 0.7, rng)
                segment = segment + 0.3 * _formant_filter(voiced, preset.formant_shifts, sample_rate)[:n]

        env = _segment_env(n)
        stress = 0.75 + 0.25 * rng.random()
        pieces.append((segment[:n] * env * stress).astype(np.float32))

    if not pieces:
        return np.zeros(int(0.4 * sample_rate), dtype=np.float32)

    voice = np.concatenate(pieces).astype(np.float32)
    breath = _noise_layer((len(voice) + 1) / sample_rate, sample_rate, rng, 250.0, 6000.0)[: len(voice)]
    micro_amp = 1.0 + 0.025 * np.sin(2.0 * np.pi * 3.5 * np.arange(len(voice)) / sample_rate)
    voice = (voice * micro_amp.astype(np.float32)) + preset.breathiness * 0.25 * breath
    voice = _studio_vocal_post(voice, sample_rate)

    fade = min(int(0.01 * sample_rate), len(voice) // 4)
    if fade > 0:
        voice[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
        voice[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)

    peak = float(np.max(np.abs(voice)))
    if peak > 1e-9:
        target = 10.0 ** (-6.0 / 20.0)
        voice = (voice / peak * target).astype(np.float32)
    return voice
