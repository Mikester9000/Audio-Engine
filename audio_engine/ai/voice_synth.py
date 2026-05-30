"""Deterministic procedural voice synthesis with phoneme-class shaping.

Public interface:
    synthesise_voice(text, voice_preset=\"narrator\", speed=1.0, sample_rate=22050, seed=None)
        -> mono float32 NumPy array

The implementation stays fully offline and uses:
- multi-stage glottal excitation (with jitter + sub-harmonics),
- voiced/unvoiced phoneme segmentation with per-class durations,
- per-vowel formant frequencies for distinct vowel quality,
- plosive burst + aspiration modelling,
- fricative spectral shaping per phoneme,
- nasal formant resonance for /m/, /n/,
- word-boundary pauses for intelligibility,
- sentence-level pitch arcs and per-segment envelopes,
- presence-lift, de-essing, saturation, and early-reflection post-processing.

For the best intelligibility, install the kokoro neural TTS backend
(pip install -e ".[neural]") and select 'kokoro' in the Voice tab backend
dropdown.  The procedural synth here is a zero-dependency fallback.
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
    "narrator": _VoicePreset(f0=120.0, formant_shifts=(1.0, 1.0, 1.0), jitter=0.012, breathiness=0.04),
    "hero": _VoicePreset(f0=112.0, formant_shifts=(1.05, 0.95, 0.98), jitter=0.015, breathiness=0.03),
    "villain": _VoicePreset(f0=90.0, formant_shifts=(0.9, 1.08, 1.05), jitter=0.02, breathiness=0.06),
    "announcer": _VoicePreset(f0=135.0, formant_shifts=(1.08, 1.0, 0.95), jitter=0.008, breathiness=0.02),
    "npc": _VoicePreset(f0=150.0, formant_shifts=(1.15, 1.05, 1.0), jitter=0.028, breathiness=0.08),
}

# Per-vowel formant frequencies (F1, F2, F3) in Hz — standard phonetics reference values
_VOWEL_FORMANTS: dict[str, tuple[float, float, float]] = {
    "a": (800.0, 1200.0, 2600.0),   # "ah" as in "father"
    "e": (400.0, 2000.0, 2800.0),   # "eh" as in "bed"
    "i": (280.0, 2700.0, 3200.0),   # "ee" as in "see"
    "o": (450.0, 800.0, 2500.0),    # "oh" as in "go"
    "u": (310.0, 870.0, 2400.0),    # "oo" as in "moon"
    "y": (390.0, 2000.0, 2700.0),   # "y" treated as /ɪ/
}
_BASE_FORMANTS = np.array([700.0, 1220.0, 2600.0], dtype=np.float64)  # neutral vowel fallback

# Fricative spectral shapes: (lo_hz, hi_hz, gain)
_FRICATIVE_BANDS: dict[str, tuple[float, float, float]] = {
    "s": (4500.0, 9000.0, 1.0),
    "z": (4000.0, 8500.0, 0.85),
    "f": (1800.0, 7000.0, 0.8),
    "v": (1600.0, 6500.0, 0.7),
    "x": (4000.0, 9000.0, 0.9),   # /x/ as in "loch"
    "sh": (2500.0, 8000.0, 1.0),
    "ch": (3000.0, 8500.0, 0.95),
}

_SUBHARMONIC_PHASE_OFFSET = 0.33
_NOISE_BAND_MIN = 0.001
_NOISE_BAND_MAX = 0.949
_NOISE_BAND_MIN_WIDTH = 0.05
_VOCAL_HP_CUTOFF_HZ = 40.0
_VOCAL_LP_CUTOFF_HZ = 8000.0
_PRESENCE_BAND_LO_HZ = 1000.0
_PRESENCE_BAND_HI_HZ = 5000.0
_DEESS_BAND_LO_HZ = 5500.0
_DEESS_BAND_HI_HZ = 9000.0
_PRESENCE_LIFT_GAIN = 0.15
_DEESS_ATTENUATION = 0.30
_SATURATION_DRIVE = 1.15
_REFLECTION_DELAY_1_S = 0.011
_REFLECTION_DELAY_2_S = 0.019
_REFLECTION_GAIN_1 = 0.10
_REFLECTION_GAIN_2 = 0.07
_POST_MIN_NORMALIZED_FREQ = 0.001
_POST_MAX_NORMALIZED_FREQ = 0.99
_DEESS_WINDOW_SECONDS = 0.004
_DEESS_WINDOW_MIN_SAMPLES = 8
_DEESS_ENVELOPE_EPSILON = 1e-9

_VOWELS = set("aeiouy")
_PLOSIVES = set("pbtdkg")
_FRICATIVES = set("sfzxv")
_NASALS = set("mn")
_APPROXIMANTS = set("rl")
_SH_SET = {"sh", "ch"}

# A word-boundary token inserted between words
_WORD_BOUNDARY = "__WB__"


def _stable_seed(text: str, seed: int | None) -> int:
    crc = zlib.crc32(text.encode("utf-8"))
    return ((seed or 0) & 0x7FFFFFFF) ^ (crc & 0x7FFFFFFF)


def _tokenise(text: str) -> list[str]:
    """Split text into phoneme tokens with explicit word-boundary markers."""
    words_and_punct = re.findall(r"[a-zA-Z]+|[?.!,;:]", text.lower())
    tokens: list[str] = []
    prev_was_word = False
    for item in words_and_punct:
        if item in {"?", ".", "!", ",", ";", ":"}:
            prev_was_word = False
            tokens.append(item)
            continue
        # Insert word boundary pause between words
        if prev_was_word:
            tokens.append(_WORD_BOUNDARY)
        prev_was_word = True
        # Split word into phoneme tokens (digraphs first)
        i = 0
        while i < len(item):
            if i + 1 < len(item) and item[i : i + 2] in _SH_SET:
                tokens.append(item[i : i + 2])
                i += 2
            else:
                tokens.append(item[i])
                i += 1
    return tokens


def _segment_duration(token: str, speed: float) -> float:
    """Return the target duration of a phoneme in seconds at the given speed."""
    speed = max(speed, 0.5)
    # Sentence-ending pauses
    if token in {".", "!", "?"}:
        return 0.14 / speed
    # Mid-sentence pauses
    if token in {",", ";", ":"}:
        return 0.08 / speed
    # Word-boundary breath/gap
    if token == _WORD_BOUNDARY:
        return 0.055 / speed
    # Vowels — longest phonemes for intelligibility
    if token in _VOWELS:
        return 0.145 / speed
    # Affricates / digraphs (sh, ch)
    if token in _SH_SET:
        return 0.11 / speed
    # Fricatives
    if token in _FRICATIVES:
        return 0.10 / speed
    # Nasals and liquids
    if token in _NASALS or token in _APPROXIMANTS:
        return 0.09 / speed
    # Plosives
    if token in _PLOSIVES:
        return 0.075 / speed
    # Default consonant (h, w, j, q, etc.)
    return 0.08 / speed


def _sentence_pitch_arc(tokens: list[str], question: bool) -> np.ndarray:
    spoken = [
        t for t in tokens
        if t not in {".", "!", "?", ",", ";", ":", _WORD_BOUNDARY}
    ]
    if not spoken:
        return np.array([1.0], dtype=np.float64)
    n = len(spoken)
    if question:
        # Questions end on an upswing
        return np.concatenate([
            np.linspace(1.0, 0.97, max(1, n * 3 // 4), dtype=np.float64),
            np.linspace(0.97, 1.10, max(1, n - n * 3 // 4), dtype=np.float64),
        ])[:n]
    # Statements: slight fall with a small reset between clauses
    return np.linspace(1.07, 0.93, n, dtype=np.float64)


def _glottal_excitation(f0: float, duration: float, sr: int, jitter: float, rng: np.random.Generator) -> np.ndarray:
    """Band-limited glottal source with micro-vibrato and pitch jitter."""
    n = max(1, int(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    micro = 1.0 + 0.010 * np.sin(2.0 * np.pi * 5.8 * t + rng.uniform(0, 2 * np.pi))
    irregular = 1.0 + jitter * rng.normal(0.0, 0.5, n)
    f_track = np.clip(f0 * micro * irregular, 40.0, sr / 3.0)
    phase = 2.0 * np.pi * np.cumsum(f_track / sr)

    nyquist = sr / 2.0
    n_harmonics = min(int(nyquist / max(f0, 1.0)), 40)
    glottal = np.zeros(n, dtype=np.float64)
    for k in range(1, n_harmonics + 1):
        glottal += (1.0 / k) * np.sin(k * phase)
    glottal += 0.22 * np.sin(0.5 * phase + _SUBHARMONIC_PHASE_OFFSET)
    return glottal.astype(np.float32)


def _formant_filter(
    signal: np.ndarray,
    shifts: tuple[float, float, float],
    sr: int,
    base_formants: np.ndarray | None = None,
) -> np.ndarray:
    """Apply three formant bandpass filters to a glottal source signal."""
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    if base_formants is None:
        base_formants = _BASE_FORMANTS

    sig = signal.astype(np.float64)
    out = np.zeros_like(sig)
    # Wider bandwidths improve clarity; spectral tilt from F1 → F3
    bw_values = (110.0, 150.0, 200.0)
    amp_values = (1.0, 0.80, 0.50)
    for base, shift, bw, amp in zip(base_formants, shifts, bw_values, amp_values):
        center = float(base * shift)
        lo = max(60.0, center - bw)
        hi = min(sr / 2.0 - 10.0, center + bw)
        if hi <= lo:
            continue
        sos = butter(2, [lo / (sr / 2.0), hi / (sr / 2.0)], btype="band", output="sos")
        out += amp * sosfilt(sos, sig)
    return out.astype(np.float32)


def _nasal_formant(signal: np.ndarray, sr: int) -> np.ndarray:
    """Add nasal murmur resonance around 250 Hz for /m/ and /n/."""
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    nyq = sr / 2.0
    lo = max(0.001, 200.0 / nyq)
    hi = min(0.999, 350.0 / nyq)
    if hi <= lo:
        return signal
    sos = butter(2, [lo, hi], btype="band", output="sos")
    murmur = sosfilt(sos, signal.astype(np.float64)).astype(np.float32)
    return signal + 0.6 * murmur


def _noise_layer(
    duration: float,
    sr: int,
    rng: np.random.Generator,
    lo: float,
    hi: float,
    *,
    n_samples: int | None = None,
) -> np.ndarray:
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    n = n_samples if n_samples is not None else max(1, int(duration * sr))
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


def _segment_env(n: int, *, attack_frac: float = 0.12, release_frac: float = 0.20) -> np.ndarray:
    if n <= 1:
        return np.ones(max(1, n), dtype=np.float32)
    a = max(1, int(attack_frac * n))
    r = max(1, int(release_frac * n))
    s = max(0, n - a - r)
    return np.concatenate([
        np.linspace(0.0, 1.0, a, dtype=np.float32),
        np.ones(s, dtype=np.float32),
        np.linspace(1.0, 0.0, r, dtype=np.float32),
    ])[:n]


def _studio_vocal_post(signal: np.ndarray, sr: int) -> np.ndarray:
    """Deterministic vocal post-processing: cleanup, presence lift, de-essing, saturation."""
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    if len(signal) == 0:
        return signal.astype(np.float32)

    sig = signal.astype(np.float64)
    sig -= float(np.mean(sig))

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

    # Presence lift — boost the 1–5 kHz speech intelligibility band
    lo = max(_PRESENCE_BAND_LO_HZ / (sr / 2.0), 0.01)
    hi = min(_PRESENCE_BAND_HI_HZ / (sr / 2.0), 0.97)
    if hi > lo:
        presence = sosfilt(butter(2, [lo, hi], btype="bandpass", output="sos"), sig)
        sig = sig + _PRESENCE_LIFT_GAIN * presence

    # De-essing
    s_lo = max(_DEESS_BAND_LO_HZ / (sr / 2.0), 0.02)
    s_hi = min(_DEESS_BAND_HI_HZ / (sr / 2.0), 0.99)
    if s_hi > s_lo:
        sib = sosfilt(butter(2, [s_lo, s_hi], btype="bandpass", output="sos"), sig)
        window_size = max(_DEESS_WINDOW_MIN_SAMPLES, int(_DEESS_WINDOW_SECONDS * sr))
        env = np.convolve(np.abs(sib), np.ones(window_size) / window_size, mode="same")
        env = env / (np.max(env) + _DEESS_ENVELOPE_EPSILON)
        sig = sig - sib * (_DEESS_ATTENUATION * env)

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
    """Synthesize deterministic speech-like audio from text.

    This is a zero-dependency procedural fallback.  For genuinely intelligible
    speech install ``pip install -e ".[neural]"`` and choose the ``kokoro``
    backend in the Voice tab.
    """
    if not text:
        return np.zeros(int(0.4 * sample_rate), dtype=np.float32)

    preset = VOICE_PRESETS.get(voice_preset, VOICE_PRESETS["narrator"])
    rng = np.random.default_rng(_stable_seed(text + voice_preset, seed))

    tokens = _tokenise(text)
    question = text.strip().endswith("?")
    pitch_arc = _sentence_pitch_arc(tokens, question)

    pieces: list[np.ndarray] = []
    voiced_index = 0

    for token in tokens:
        duration = _segment_duration(token, speed)
        n = max(1, int(duration * sample_rate))

        # --- Silence tokens ---
        if token in {".", "!", "?", ",", ";", ":", _WORD_BOUNDARY}:
            pieces.append(np.zeros(n, dtype=np.float32))
            continue

        arc_mul = pitch_arc[min(voiced_index, len(pitch_arc) - 1)]
        voiced_index += 1
        base_f0 = preset.f0 * arc_mul

        # ------------------------------------------------------------------
        # Vowels — glottal source + per-vowel formant filter
        # ------------------------------------------------------------------
        if token in _VOWELS:
            voiced = _glottal_excitation(base_f0, duration, sample_rate, preset.jitter, rng)
            vowel_bases = np.array(
                _VOWEL_FORMANTS.get(token, tuple(_BASE_FORMANTS.tolist())),
                dtype=np.float64,
            )
            segment = _formant_filter(voiced, preset.formant_shifts, sample_rate, vowel_bases)
            # Slight amplitude modulation for naturalness
            shimmer = 1.0 + 0.025 * np.sin(
                2.0 * np.pi * 10.0 * np.arange(n) / sample_rate
                + rng.uniform(0, 2 * np.pi)
            )
            env = _segment_env(n, attack_frac=0.08, release_frac=0.15)
            segment = (segment[:n] * shimmer.astype(np.float32) * env).astype(np.float32)

        # ------------------------------------------------------------------
        # Affricates / digraphs (sh, ch)
        # ------------------------------------------------------------------
        elif token in _SH_SET:
            lo, hi, gain = _FRICATIVE_BANDS.get(token, (2500.0, 8000.0, 1.0))
            noise = _noise_layer(duration, sample_rate, rng, lo, hi) * gain
            # Leading voiced onset blended in
            voiced_onset_dur = duration * 0.25
            voiced_onset = _glottal_excitation(base_f0 * 0.85, voiced_onset_dur, sample_rate, preset.jitter, rng)
            onset_n = voiced_onset.shape[0]
            segment = noise.copy()
            if onset_n <= n:
                segment[:onset_n] += 0.25 * voiced_onset * np.linspace(1.0, 0.0, onset_n, dtype=np.float32)
            env = _segment_env(n, attack_frac=0.15, release_frac=0.25)
            segment = (segment[:n] * env).astype(np.float32)

        # ------------------------------------------------------------------
        # Fricatives (s, z, f, v, x)
        # ------------------------------------------------------------------
        elif token in _FRICATIVES:
            lo, hi, gain = _FRICATIVE_BANDS.get(token, (3000.0, 9000.0, 1.0))
            segment = _noise_layer(duration, sample_rate, rng, lo, hi) * gain
            # Voiced fricatives (z, v) add a quiet voiced component
            if token in {"z", "v"}:
                voiced = _glottal_excitation(base_f0 * 0.8, duration, sample_rate, preset.jitter, rng)
                formant_voice = _formant_filter(voiced, preset.formant_shifts, sample_rate)
                segment = (segment[:n] + 0.35 * formant_voice[:n]).astype(np.float32)
            env = _segment_env(n, attack_frac=0.10, release_frac=0.20)
            segment = (segment[:n] * env).astype(np.float32)

        # ------------------------------------------------------------------
        # Nasals (m, n) — voiced with nasal formant resonance
        # ------------------------------------------------------------------
        elif token in _NASALS:
            voiced = _glottal_excitation(base_f0, duration, sample_rate, preset.jitter * 0.6, rng)
            nasal_bases = np.array([250.0, 1000.0, 2200.0], dtype=np.float64)
            segment = _formant_filter(voiced, preset.formant_shifts, sample_rate, nasal_bases)
            segment = _nasal_formant(segment, sample_rate)
            env = _segment_env(n, attack_frac=0.10, release_frac=0.20)
            segment = (segment[:n] * env).astype(np.float32)

        # ------------------------------------------------------------------
        # Approximants (r, l) — voiced with neutral/liquid formant shaping
        # ------------------------------------------------------------------
        elif token in _APPROXIMANTS:
            voiced = _glottal_excitation(base_f0 * 0.95, duration, sample_rate, preset.jitter * 0.65, rng)
            # /r/ raises F3; /l/ has lower F2
            if token == "r":
                liquid_bases = np.array([420.0, 1100.0, 1800.0], dtype=np.float64)
            else:
                liquid_bases = np.array([380.0, 800.0, 2600.0], dtype=np.float64)
            segment = _formant_filter(voiced, preset.formant_shifts, sample_rate, liquid_bases)
            env = _segment_env(n, attack_frac=0.12, release_frac=0.18)
            segment = (segment[:n] * env).astype(np.float32)

        # ------------------------------------------------------------------
        # Plosives (p, b, t, d, k, g) — silence closure + burst + aspiration
        # ------------------------------------------------------------------
        elif token in _PLOSIVES:
            segment = np.zeros(n, dtype=np.float32)
            # Voiced plosives (/b/, /d/, /g/) have brief voiced pre-voicing
            if token in {"b", "d", "g"}:
                prevoice_n = max(1, int(0.02 * sample_rate))
                prevoice = _glottal_excitation(base_f0, prevoice_n / sample_rate, sample_rate, preset.jitter, rng)
                prevoice *= np.linspace(0.3, 0.0, prevoice_n, dtype=np.float32)
                copy_n = min(prevoice_n, n)
                segment[:copy_n] += prevoice[:copy_n]
            # Burst transient
            burst_n = max(2, int(0.006 * sample_rate))
            burst = np.linspace(0.9, 0.0, min(burst_n, n), dtype=np.float32)
            burst_start = min(max(0, n - burst_n), n)
            segment[burst_start:] = np.maximum(segment[burst_start:], burst[:n - burst_start])
            # Aspiration noise after burst (unvoiced plosives /p/, /t/, /k/)
            if token in {"p", "t", "k"}:
                asp_n = max(1, int(0.03 * sample_rate))
                asp = _noise_layer(asp_n / sample_rate, sample_rate, rng, 2000.0, 8000.0) * 0.5
                seg_space = n - burst_start
                copy_asp = min(asp_n, seg_space, len(asp))
                if copy_asp > 0 and burst_start + copy_asp <= n:
                    segment[burst_start:burst_start + copy_asp] += asp[:copy_asp]

        # ------------------------------------------------------------------
        # Remaining consonants (h, w, j, q, c …)
        # ------------------------------------------------------------------
        else:
            if token == "h":
                # /h/ is glottal fricative
                segment = _noise_layer(duration, sample_rate, rng, 200.0, 5000.0) * 0.6
                voiced = _glottal_excitation(base_f0 * 0.7, duration, sample_rate, preset.jitter, rng)
                segment = (segment[:n] + 0.2 * voiced[:n]).astype(np.float32)
            elif token == "w":
                # /w/ — labio-velar approximant: low F1 and F2
                voiced = _glottal_excitation(base_f0, duration, sample_rate, preset.jitter, rng)
                w_bases = np.array([310.0, 610.0, 2200.0], dtype=np.float64)
                segment = _formant_filter(voiced, preset.formant_shifts, sample_rate, w_bases)
            else:
                # Generic: blend voiced + wideband noise
                voiced = _glottal_excitation(base_f0 * 0.85, duration, sample_rate, preset.jitter, rng)
                noise = _noise_layer(duration, sample_rate, rng, 400.0, 6000.0) * 0.5
                segment = (_formant_filter(voiced, preset.formant_shifts, sample_rate)[:n] * 0.55
                           + noise[:n]).astype(np.float32)
            env = _segment_env(n, attack_frac=0.10, release_frac=0.20)
            segment = (segment[:n] * env).astype(np.float32)

        stress = 0.80 + 0.20 * rng.random()
        pieces.append((segment[:n] * stress).astype(np.float32))

    if not pieces:
        return np.zeros(int(0.4 * sample_rate), dtype=np.float32)

    voice = np.concatenate(pieces).astype(np.float32)

    # Light breathiness layer over the full signal
    # Light breathiness layer — request exactly len(voice) samples to avoid shape mismatch
    breath = _noise_layer(0.0, sample_rate, rng, 250.0, 5000.0, n_samples=len(voice))
    voice = voice + preset.breathiness * 0.20 * breath

    voice = _studio_vocal_post(voice, sample_rate)

    # Short fade-in / fade-out to avoid clicks
    fade = min(int(0.008 * sample_rate), len(voice) // 4)
    if fade > 0:
        voice[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
        voice[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)

    # Normalise to -6 dBFS
    peak = float(np.max(np.abs(voice)))
    if peak > 1e-9:
        target = 10.0 ** (-6.0 / 20.0)
        voice = (voice / peak * target).astype(np.float32)
    return voice

