"""Procedural SFX synthesizer with distinct per-category recipes.

Supported families include explosion, footstep, hit/impact, whoosh/swing,
laser, coin/pickup, jump, magic + elemental spells, heal/cure, summon,
save/level-up/game-over cues, sword/slash, and UI click/confirm/cancel.

Extension pattern:
1) add a `_sfx_<name>(duration, pitch_hz, sr, rng)` function,
2) register aliases in `_SFX_FUNCTIONS`.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

__all__ = ["synthesise_sfx", "available_sfx_types"]

_NORMALIZED_MIN_EDGE = 1e-4
_NORMALIZED_MAX_EDGE = 0.999


def _normalized_band(lo: float, hi: float, sr: int, min_width: float = 0.02) -> tuple[float, float] | None:
    """Normalize a frequency band to Nyquist-relative edges or return None when out of range."""
    nyq = sr / 2.0
    if nyq <= 0.0 or hi <= 0.0 or lo >= nyq:
        return None
    low = float(np.clip(lo / nyq, _NORMALIZED_MIN_EDGE, _NORMALIZED_MAX_EDGE - min_width))
    high = float(np.clip(hi / nyq, low + min_width, _NORMALIZED_MAX_EDGE))
    if high <= low:
        return None
    return low, high


def _sine(freq: float, duration: float, sr: int, amp: float = 1.0, phase: float = 0.0) -> np.ndarray:
    n = max(1, int(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    return (amp * np.sin(2.0 * np.pi * freq * t + phase)).astype(np.float32)


def _square(freq: float, duration: float, sr: int, amp: float = 1.0) -> np.ndarray:
    sig = _sine(freq, duration, sr, amp=1.0)
    return (amp * np.sign(sig + 1e-8)).astype(np.float32)


def _exp_env(n: int, decay: float) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n, dtype=np.float64)
    return np.exp(-decay * t).astype(np.float32)


def _adsr(n: int, sr: int, attack_ms: float, decay_ms: float, sustain: float, release_ms: float) -> np.ndarray:
    a = max(1, int(sr * attack_ms / 1000.0))
    d = max(1, int(sr * decay_ms / 1000.0))
    r = max(1, int(sr * release_ms / 1000.0))
    s = max(0, n - a - d - r)
    env = np.zeros(n, dtype=np.float32)
    env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    env[a : a + d] = np.linspace(1.0, sustain, d, dtype=np.float32)
    env[a + d : a + d + s] = sustain
    env[a + d + s :] = np.linspace(sustain, 0.0, n - (a + d + s), dtype=np.float32)
    return env


def _band_noise(n: int, lo: float, hi: float, sr: int, rng: np.random.Generator) -> np.ndarray:
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    raw = rng.standard_normal(n).astype(np.float64)
    band = _normalized_band(lo, hi, sr)
    if band is None:
        return raw.astype(np.float32)
    low, high = band
    sos = butter(4, [low, high], btype="band", output="sos")
    return sosfilt(sos, raw).astype(np.float32)


def _moving_band_noise(
    n: int,
    start_hz: float,
    end_hz: float,
    bandwidth: float,
    sr: int,
    rng: np.random.Generator,
) -> np.ndarray:
    from scipy.signal import butter, sosfilt  # type: ignore[import]

    steps = 8
    segment_len = max(1, n // steps)
    segments: list[np.ndarray] = []
    centers = np.linspace(start_hz, end_hz, steps)
    for c in centers:
        lo = max(80.0, c - bandwidth / 2.0)
        hi = min(sr / 2.0 - 50.0, c + bandwidth / 2.0)
        raw = rng.standard_normal(segment_len).astype(np.float64)
        band = _normalized_band(lo, hi, sr, min_width=0.04)
        if band is None:
            segments.append(raw.astype(np.float32))
            continue
        sos = butter(2, list(band), btype="band", output="sos")
        segments.append(sosfilt(sos, raw).astype(np.float32))
    out = np.concatenate(segments)
    if len(out) < n:
        out = np.pad(out, (0, n - len(out)))
    return out[:n]


def _reverb(signal: np.ndarray, sr: int, room_seconds: float, decay: float, seed: int) -> np.ndarray:
    from scipy.signal import fftconvolve  # type: ignore[import]

    n_ir = max(64, int(room_seconds * sr))
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n_ir).astype(np.float64)
    ir *= np.exp(-np.linspace(0.0, decay, n_ir))
    ir /= np.sum(np.abs(ir)) + 1e-9
    wet = fftconvolve(signal.astype(np.float64), ir, mode="full")[: len(signal)]
    return wet.astype(np.float32)


def _freq_sweep(start_hz: float, end_hz: float, duration: float, sr: int, exp: bool = False) -> np.ndarray:
    n = max(1, int(duration * sr))
    if exp:
        freqs = np.geomspace(max(1.0, start_hz), max(1.0, end_hz), n)
    else:
        freqs = np.linspace(start_hz, end_hz, n)
    phase = 2.0 * np.pi * np.cumsum(freqs / sr)
    return np.sin(phase).astype(np.float32)


def _sfx_explosion(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.7)
    n = int(d * sr)
    sweep = _freq_sweep(80.0, 30.0, d, sr)
    low = _band_noise(n, 30.0, 120.0, sr, rng)
    mid = _band_noise(n, 120.0, 900.0, sr, rng)
    high = _band_noise(n, 900.0, 3500.0, sr, rng)
    env = _exp_env(n, decay=4.0)
    dry = (0.5 * sweep + 0.25 * low + 0.18 * mid + 0.07 * high) * env
    wet = _reverb(
        dry.astype(np.float32),
        sr,
        room_seconds=1.8,
        decay=5.5,
        seed=int(rng.integers(0, 2**31 - 1)),
    )
    return (0.6 * dry + 0.4 * wet).astype(np.float32)


def _sfx_footstep(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.12)
    n = int(d * sr)
    body = _sine(120.0, d, sr)
    body_env = _adsr(n, sr, attack_ms=1.0, decay_ms=35.0, sustain=0.0, release_ms=45.0)
    material = _band_noise(n, 180.0, 2400.0, sr, rng)
    noise_env = _adsr(n, sr, attack_ms=0.5, decay_ms=20.0, sustain=0.0, release_ms=35.0)
    dry = 0.7 * body[:n] * body_env + 0.45 * material * noise_env
    rev = _reverb(
        dry.astype(np.float32),
        sr,
        room_seconds=0.18,
        decay=3.0,
        seed=int(rng.integers(0, 2**31 - 1)),
    )
    return (0.88 * dry + 0.12 * rev).astype(np.float32)


def _sfx_hit(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.2)
    n = int(d * sr)
    base = pitch_hz or 190.0
    partials = [1.0, 1.41, 1.93, 2.65]
    tone = np.zeros(n, dtype=np.float32)
    for p in partials:
        drop = _freq_sweep(base * p, max(55.0, base * p * 0.6), d, sr)
        tone += (0.3 / p) * drop[:n]
    transient_n = max(1, int(0.03 * sr))
    transient = _band_noise(transient_n, 1200.0, 10000.0, sr, rng)
    burst = np.zeros(n, dtype=np.float32)
    burst[:transient_n] = transient * _exp_env(transient_n, 15.0)
    env = _adsr(n, sr, attack_ms=1.0, decay_ms=60.0, sustain=0.0, release_ms=80.0)
    ring = _sine(2600.0, d, sr, amp=0.28) * _exp_env(n, 7.5)
    return (tone + burst) * env + ring[:n]


def _sfx_whoosh(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.25)
    n = int(d * sr)
    sweep = _moving_band_noise(n, 400.0, 7500.0, bandwidth=1700.0, sr=sr, rng=rng)
    bow = np.sin(np.linspace(0.0, np.pi, n, dtype=np.float64)).astype(np.float32)
    return (sweep * bow).astype(np.float32)


def _sfx_laser(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.18)
    n = int(d * sr)
    sweep = _freq_sweep(2000.0, 400.0, d, sr, exp=True)
    sq = _square(900.0, d, sr, amp=0.22)
    env = _exp_env(n, decay=6.0)
    return (0.78 * sweep[:n] + 0.22 * sq[:n]) * env


def _sfx_coin(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.2)
    n = int(d * sr)
    base = pitch_hz or 1047.0
    t = np.arange(n, dtype=np.float64) / sr
    primary = np.sin(2.0 * np.pi * base * t)
    second = 0.55 * np.sin(2.0 * np.pi * (base * 1.5) * t)
    sparkle = np.zeros(n, dtype=np.float64)
    for i, ratio in enumerate((2.0, 2.5, 3.0, 3.5)):
        start = min(n - 1, int((0.008 * i) * sr))
        seg = n - start
        if seg <= 0:
            continue
        tt = np.arange(seg, dtype=np.float64) / sr
        sparkle[start:] += 0.15 * np.sin(2.0 * np.pi * base * ratio * tt)
    env = _exp_env(n, decay=10.0)
    return ((primary + second + sparkle) * env).astype(np.float32)


def _sfx_jump(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.22)
    n = int(d * sr)
    glide = _freq_sweep(200.0, 600.0, d, sr)
    noise = _band_noise(n, 1000.0, 7000.0, sr, rng)
    transient = np.zeros(n, dtype=np.float32)
    transient_n = max(1, int(0.02 * sr))
    transient[:transient_n] = noise[:transient_n] * _exp_env(transient_n, 18.0)
    env = _adsr(n, sr, attack_ms=2.0, decay_ms=70.0, sustain=0.0, release_ms=80.0)
    return (glide[:n] * env + 0.2 * transient).astype(np.float32)


def _sfx_magic(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.6)
    n = int(d * sr)
    base = pitch_hz or 620.0
    t = np.arange(n, dtype=np.float64) / sr
    sig = np.zeros(n, dtype=np.float64)
    for _ in range(rng.integers(4, 7)):
        detune = rng.uniform(-0.025, 0.025)
        ratio = rng.choice([1.0, 1.5, 2.0, 2.5, 3.0])
        sig += np.sin(2.0 * np.pi * (base * ratio * (1 + detune)) * t + rng.uniform(0, 2 * np.pi))
    sig /= max(1, np.max(np.abs(sig)))
    flutter = 1.0 + 0.12 * np.sin(2.0 * np.pi * 11.0 * t + rng.uniform(0, 2 * np.pi))
    env = _adsr(n, sr, attack_ms=20.0, decay_ms=180.0, sustain=0.42, release_ms=260.0)
    dry = (sig * flutter * env).astype(np.float32)
    wet = _reverb(dry, sr, room_seconds=1.4, decay=4.8, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.6 * dry + 0.4 * wet).astype(np.float32)


def _sfx_spell_fire(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.7)
    n = int(d * sr)
    roar = _band_noise(n, 60.0, 500.0, sr, rng)
    crackle = _band_noise(n, 3000.0, 10000.0, sr, rng)
    transient = _band_noise(n, 800.0, 2500.0, sr, rng)
    attack = np.zeros(n, dtype=np.float32)
    attack_n = max(1, int(0.06 * sr))
    attack[:attack_n] = transient[:attack_n] * _exp_env(attack_n, 10.0)
    env = _adsr(n, sr, attack_ms=10.0, decay_ms=90.0, sustain=0.45, release_ms=220.0)
    return (0.62 * roar + 0.28 * crackle + 0.25 * attack) * env


def _sfx_spell_ice(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.6)
    n = int(d * sr)
    base = pitch_hz or 1800.0
    t = np.arange(n, dtype=np.float64) / sr
    partials = np.zeros(n, dtype=np.float64)
    for ratio in (1.0, 1.37, 1.91, 2.73):
        partials += 0.22 * np.sin(2.0 * np.pi * base * ratio * t + rng.uniform(0, 2 * np.pi))
    crackle = _band_noise(n, 3500.0, 12000.0, sr, rng) * 0.22
    env = _adsr(n, sr, attack_ms=3.0, decay_ms=80.0, sustain=0.28, release_ms=180.0)
    dry = (partials + crackle) * env
    cold = _reverb(
        dry.astype(np.float32),
        sr,
        room_seconds=0.9,
        decay=4.3,
        seed=int(rng.integers(0, 2**31 - 1)),
    )
    return (0.72 * dry + 0.28 * cold).astype(np.float32)


def _sfx_spell_thunder(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.7)
    n = int(d * sr)
    crack_n = max(1, int(0.05 * sr))
    crack = _band_noise(crack_n, 300.0, 16000.0, sr, rng) * _exp_env(crack_n, 24.0)
    out = np.zeros(n, dtype=np.float32)
    out[:crack_n] += crack
    rumble = _band_noise(n, 30.0, 200.0, sr, rng)
    rumble_env = _adsr(n, sr, attack_ms=12.0, decay_ms=90.0, sustain=0.3, release_ms=250.0)
    out += 0.7 * rumble * rumble_env
    echo_delay = int(0.11 * sr)
    if echo_delay < n:
        out[echo_delay:] += 0.22 * out[:-echo_delay]
    return out


def _sfx_cure(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.7)
    n = int(d * sr)
    base = pitch_hz or 660.0
    notes = [base, base * 1.25, base * 1.5]
    out = np.zeros(n, dtype=np.float32)
    for i, note in enumerate(notes):
        delay = int((0.15 * i) * sr)
        seg = n - delay
        if seg <= 0:
            continue
        t = np.arange(seg, dtype=np.float64) / sr
        bell = (
            0.75 * np.sin(2.0 * np.pi * note * t)
            + 0.22 * np.sin(2.0 * np.pi * note * 2.0 * t)
            + 0.12 * np.sin(2.0 * np.pi * note * 3.0 * t)
        )
        env = _exp_env(seg, decay=6.5)
        out[delay:] += (bell * env * 0.4).astype(np.float32)
    shimmer = _band_noise(n, 4500.0, 11000.0, sr, rng) * 0.08
    wet = _reverb(
        out + shimmer,
        sr,
        room_seconds=1.2,
        decay=4.4,
        seed=int(rng.integers(0, 2**31 - 1)),
    )
    return (0.6 * out + 0.4 * wet).astype(np.float32)


def _sfx_summon(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 1.0)
    n = int(d * sr)
    bass = _sine(55.0, d, sr)
    bass_env = _exp_env(n, decay=3.0)
    swell = _band_noise(n, 300.0, 5000.0, sr, rng)
    rise = np.linspace(0.0, 1.0, n, dtype=np.float32)
    shimmer = _band_noise(n, 4000.0, 12000.0, sr, rng)
    return (0.58 * bass[:n] * bass_env + 0.32 * swell * rise + 0.16 * shimmer * rise).astype(np.float32)


def _sfx_limit_break(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.8)
    n = int(d * sr)
    rise = _freq_sweep(70.0, 1700.0, d, sr, exp=True)
    surge = _band_noise(n, 200.0, 9000.0, sr, rng) * np.linspace(0.0, 1.0, n, dtype=np.float32)
    return (0.65 * rise[:n] + 0.45 * surge).astype(np.float32)


def _sfx_save_point(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = pitch_hz or 523.25
    notes = [base, base * 1.25, base * 1.5, base * 2.0]
    note_dur = max(0.12, max(duration, 0.48) / 4.0)
    parts: list[np.ndarray] = []
    for f in notes:
        n = int(note_dur * sr)
        t = np.arange(n, dtype=np.float64) / sr
        note = (
            0.65 * np.sin(2.0 * np.pi * f * t)
            + 0.23 * np.sin(2.0 * np.pi * 2 * f * t)
            + 0.12 * np.sin(2.0 * np.pi * 3 * f * t)
        )
        parts.append((note * _exp_env(n, 8.0)).astype(np.float32))
    return np.concatenate(parts).astype(np.float32)


def _sfx_level_up(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = pitch_hz or 523.25
    ratios = [1.0, 1.1225, 1.2599, 1.3348, 1.4983, 1.6818, 2.0]
    note_dur = max(0.06, max(duration, 0.5) / len(ratios))
    parts: list[np.ndarray] = []
    for i, r in enumerate(ratios):
        n = int(note_dur * sr)
        t = np.arange(n, dtype=np.float64) / sr
        f = base * r
        tone = np.sin(2.0 * np.pi * f * t) + 0.25 * np.sin(2.0 * np.pi * 2 * f * t)
        sparkle = 0.08 * np.sin(2.0 * np.pi * (f * 3.5) * t + i * 0.4)
        parts.append(((tone + sparkle) * _exp_env(n, 11.0)).astype(np.float32))
    return np.concatenate(parts).astype(np.float32)


def _sfx_game_over(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = pitch_hz or 440.0
    ratios = [1.0, 0.84, 0.67, 0.5]
    note_dur = max(0.14, max(duration, 0.55) / len(ratios))
    parts: list[np.ndarray] = []
    for r in ratios:
        n = int(note_dur * sr)
        t = np.arange(n, dtype=np.float64) / sr
        f = base * r
        tone = 0.7 * np.sin(2.0 * np.pi * f * t) + 0.2 * np.sin(2.0 * np.pi * 1.5 * f * t)
        parts.append((tone * _adsr(n, sr, 3.0, 50.0, 0.22, 90.0)).astype(np.float32))
    return np.concatenate(parts).astype(np.float32)


def _sfx_sword(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.3)
    n = int(d * sr)
    whoosh = _moving_band_noise(n, 2500.0, 9000.0, bandwidth=2200.0, sr=sr, rng=rng)
    whoosh *= np.sin(np.linspace(0.0, np.pi, n, dtype=np.float64)).astype(np.float32)
    ring_d = max(0.08, d * 0.35)
    ring_n = int(ring_d * sr)
    ring_t = np.arange(ring_n, dtype=np.float64) / sr
    ring = (
        0.5 * np.sin(2.0 * np.pi * 2400.0 * ring_t)
        + 0.3 * np.sin(2.0 * np.pi * 3700.0 * ring_t)
        + 0.2 * np.sin(2.0 * np.pi * 5100.0 * ring_t)
    )
    ring *= _exp_env(ring_n, 18.0)
    out = whoosh.astype(np.float32)
    start = max(0, n - ring_n)
    out[start : start + ring_n] += ring[: n - start].astype(np.float32)
    return out


def _sfx_parry(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.24)
    n = int(d * sr)
    clang = _sfx_sword(d, pitch_hz, sr, rng)[:n]
    body = np.zeros(n, dtype=np.float32)
    transient_n = max(1, int(0.018 * sr))
    transient = _band_noise(transient_n, 1400.0, 10000.0, sr, rng) * _exp_env(transient_n, 24.0)
    body[:transient_n] = transient
    # Use high inharmonic partials plus a short low thunk so parries read as
    # bright metal-on-metal impacts while still carrying enough energy for QA.
    ring = (
        0.34 * _sine(1750.0, d, sr)
        + 0.22 * _sine(2630.0, d, sr, phase=np.pi / 7.0)
        + 0.12 * _sine(3890.0, d, sr, phase=np.pi / 5.0)
    )[:n]
    ring *= _exp_env(n, 12.0)
    low_impact = _sine(pitch_hz or 320.0, d, sr, amp=0.16)[:n] * _exp_env(n, 16.0)
    return (0.52 * clang + body + ring + low_impact).astype(np.float32)


def _sfx_ui_click(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    d = max(duration, 0.03)
    n = int(d * sr)
    tone = _sine(pitch_hz or 800.0, d, sr)
    noise = _band_noise(n, 2500.0, 10000.0, sr, rng)
    env = _exp_env(n, 18.0)
    return (0.75 * tone[:n] + 0.25 * noise) * env


def _sfx_confirm(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    note_d = max(0.06, max(duration, 0.16) / 2.0)
    first = _sine(800.0, note_d, sr) * _exp_env(int(note_d * sr), 10.0)
    second = _sine(1200.0, note_d, sr) * _exp_env(int(note_d * sr), 10.0)
    return np.concatenate([first, second]).astype(np.float32)


def _sfx_cancel(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    note_d = max(0.06, max(duration, 0.16) / 2.0)
    first = _sine(1200.0, note_d, sr) * _exp_env(int(note_d * sr), 10.0)
    second = _sine(800.0, note_d, sr) * _exp_env(int(note_d * sr), 10.0)
    return np.concatenate([first, second]).astype(np.float32)


def _sfx_generic(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    return _sfx_ui_click(max(duration, 0.08), pitch_hz or 900.0, sr, rng)


# ---------------------------------------------------------------------------
# Additional distinct SFX recipes added for PS2-era quality and semantic match
# ---------------------------------------------------------------------------

def _sfx_water(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Running/flowing water — layered low-frequency burble with splash transients."""
    d = max(duration, 0.6)
    n = int(d * sr)
    # Continuous flow: pink-ish low-mid noise
    flow = _band_noise(n, 200.0, 2400.0, sr, rng) * 0.55
    # Gurgle: amplitude modulated with a slow random LFO
    lfo_rate = rng.uniform(3.5, 7.0)
    t = np.arange(n, dtype=np.float64) / sr
    gurgle_mod = 0.5 + 0.5 * np.abs(np.sin(2.0 * np.pi * lfo_rate * t))
    # Splash transients: random short bursts of high-frequency noise
    splashes = np.zeros(n, dtype=np.float32)
    n_splashes = max(2, int(d * 4))
    for _ in range(n_splashes):
        pos = int(rng.integers(0, max(1, n - int(0.05 * sr))))
        splash_len = max(1, int(rng.uniform(0.01, 0.05) * sr))
        s = _band_noise(splash_len, 1500.0, 8000.0, sr, rng) * _exp_env(splash_len, 12.0)
        end = min(pos + splash_len, n)
        splashes[pos:end] += (s[:end - pos] * rng.uniform(0.2, 0.6)).astype(np.float32)
    dry = (flow * gurgle_mod.astype(np.float32) + splashes).astype(np.float32)
    wet = _reverb(dry, sr, room_seconds=0.35, decay=3.5, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.75 * dry + 0.25 * wet).astype(np.float32)


def _sfx_wind(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Ambient wind — slowly modulated band-pass noise with howl resonances."""
    d = max(duration, 0.8)
    n = int(d * sr)
    t = np.arange(n, dtype=np.float64) / sr
    # Main wind body: broadband mid-low noise with amplitude swell
    body = _band_noise(n, 120.0, 3500.0, sr, rng)
    swell_period = rng.uniform(1.5, 3.5)
    swell = 0.55 + 0.45 * np.sin(2.0 * np.pi * t / swell_period + rng.uniform(0, 2 * np.pi))
    # Howl: a narrow resonance that sweeps slowly in pitch
    howl_freq = rng.uniform(280.0, 800.0)
    howl = np.zeros(n, dtype=np.float64)
    steps = 6
    for i in range(steps):
        seg = n // steps
        offset = i * seg
        f = howl_freq * (1.0 + 0.18 * np.sin(i * 1.1))
        end = min(offset + seg, n)
        seg_t = np.arange(end - offset, dtype=np.float64) / sr
        howl[offset:end] = 0.18 * np.sin(2.0 * np.pi * f * seg_t)
    high_whistle = _band_noise(n, 4000.0, 9000.0, sr, rng) * 0.12
    dry = (body * swell.astype(np.float32) + howl.astype(np.float32) + high_whistle).astype(np.float32)
    wet = _reverb(dry, sr, room_seconds=0.9, decay=4.0, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.65 * dry + 0.35 * wet).astype(np.float32)


def _sfx_arrow(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Bow/arrow shot — bowstring release + fast whoosh + optional impact."""
    d = max(duration, 0.35)
    n = int(d * sr)
    # Bowstring snap: brief low-frequency thunk
    snap_n = max(1, int(0.025 * sr))
    snap_t = np.arange(snap_n, dtype=np.float64) / sr
    snap = (0.7 * np.sin(2.0 * np.pi * 180.0 * snap_t) + 0.3 * np.sin(2.0 * np.pi * 420.0 * snap_t))
    snap *= _exp_env(snap_n, 30.0)
    # Arrow whoosh: tight high-frequency noise rising then falling
    whoosh = _moving_band_noise(n, 3500.0, 12000.0, bandwidth=1800.0, sr=sr, rng=rng)
    arc = np.concatenate([
        np.linspace(0.1, 1.0, n // 3, dtype=np.float32),
        np.linspace(1.0, 0.3, n - n // 3, dtype=np.float32),
    ])
    whoosh *= arc
    out = np.zeros(n, dtype=np.float32)
    out[:snap_n] = snap.astype(np.float32)
    out += 0.6 * whoosh
    return out


def _sfx_door(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Wooden door creak and close — low creak + thud impact."""
    d = max(duration, 0.5)
    n = int(d * sr)
    # Creak: short swept tone (wood friction)
    creak_d = min(0.35, d * 0.6)
    creak_n = int(creak_d * sr)
    creak_start = rng.uniform(100.0, 280.0)
    creak_end = rng.uniform(60.0, creak_start * 0.7)
    creak_t = np.arange(creak_n, dtype=np.float64) / sr
    creak_freq = np.linspace(creak_start, creak_end, creak_n)
    creak_phase = 2.0 * np.pi * np.cumsum(creak_freq / sr)
    creak = np.sin(creak_phase).astype(np.float32) * 0.5
    creak_noise = _band_noise(creak_n, 200.0, 4000.0, sr, rng) * 0.35
    creak_env = np.sin(np.linspace(0.0, np.pi, creak_n, dtype=np.float32))
    creak = (creak + creak_noise) * creak_env
    # Door thud: low impact at the end
    thud_n = max(1, int(0.12 * sr))
    thud_t = np.arange(thud_n, dtype=np.float64) / sr
    thud = (
        0.65 * np.sin(2.0 * np.pi * 80.0 * thud_t) + 0.25 * np.sin(2.0 * np.pi * 150.0 * thud_t)
    ).astype(np.float32)
    thud *= _exp_env(thud_n, 12.0)
    thud_noise = _band_noise(thud_n, 150.0, 2000.0, sr, rng) * 0.35 * _exp_env(thud_n, 18.0)
    out = np.zeros(n, dtype=np.float32)
    out[:creak_n] = creak.astype(np.float32)
    thud_start = max(0, n - thud_n)
    out[thud_start:thud_start + thud_n] += (thud + thud_noise).astype(np.float32)
    return out


def _sfx_glass_break(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Glass shattering — sharp crack + cascading high-frequency tinkle."""
    d = max(duration, 0.6)
    n = int(d * sr)
    # Initial crack: very brief broadband burst
    crack_n = max(1, int(0.012 * sr))
    crack = _band_noise(crack_n, 2000.0, 16000.0, sr, rng) * _exp_env(crack_n, 40.0)
    out = np.zeros(n, dtype=np.float32)
    out[:crack_n] = crack
    # Cascading shards: many random high-frequency tones with fast decay
    n_shards = rng.integers(8, 20)
    for _ in range(int(n_shards)):
        f = rng.uniform(1500.0, 6000.0)
        onset = int(rng.uniform(0.005, 0.08) * sr)
        shard_n = max(1, int(rng.uniform(0.04, 0.2) * sr))
        if onset + shard_n > n:
            continue
        t = np.arange(shard_n, dtype=np.float64) / sr
        tone = np.sin(2.0 * np.pi * f * t).astype(np.float32)
        env = _exp_env(shard_n, rng.uniform(8.0, 25.0))
        amp = float(rng.uniform(0.1, 0.45))
        out[onset:onset + shard_n] += (tone * env * amp).astype(np.float32)
    # High shimmer tail
    shimmer = _band_noise(n, 3000.0, 12000.0, sr, rng) * np.exp(-6.0 * np.arange(n, dtype=np.float64) / sr).astype(np.float32) * 0.25
    out += shimmer
    return out


def _sfx_heartbeat(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Heartbeat — two-beat pulse pattern (lub-dub) repeated to fill duration."""
    d = max(duration, 0.5)
    n = int(d * sr)
    bpm = float(pitch_hz) if pitch_hz else 72.0
    beat_period = 60.0 / bpm
    out = np.zeros(n, dtype=np.float32)
    pos = 0
    while pos < n:
        # lub (first heart sound)
        for beat_offset, freq, amp in [(0, 55.0, 0.9), (int(0.15 * sr), 45.0, 0.55)]:
            pulse_n = max(1, int(0.12 * sr))
            if pos + beat_offset + pulse_n > n:
                break
            pulse_t = np.arange(pulse_n, dtype=np.float64) / sr
            pulse = (np.sin(2.0 * np.pi * freq * pulse_t) * amp).astype(np.float32)
            pulse_env = _adsr(pulse_n, sr, attack_ms=3.0, decay_ms=40.0, sustain=0.0, release_ms=60.0)
            start = pos + beat_offset
            end = min(start + pulse_n, n)
            out[start:end] += (pulse * pulse_env)[:end - start]
        pos += int(beat_period * sr)
    return out


def _sfx_footstep_stone(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Stone/hard surface footstep — harder, more resonant than default."""
    d = max(duration, 0.12)
    n = int(d * sr)
    body = _sine(95.0, d, sr)
    body_env = _adsr(n, sr, attack_ms=1.0, decay_ms=22.0, sustain=0.0, release_ms=35.0)
    stone = _band_noise(n, 300.0, 5000.0, sr, rng)
    stone_env = _adsr(n, sr, attack_ms=0.3, decay_ms=15.0, sustain=0.0, release_ms=25.0)
    # Short metallic ring from stone contact
    ring = _sine(1400.0, d, sr, amp=0.18) * _exp_env(n, 22.0)
    dry = 0.55 * body[:n] * body_env + 0.35 * stone * stone_env + ring[:n]
    rev = _reverb(dry.astype(np.float32), sr, room_seconds=0.25, decay=4.0, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.82 * dry + 0.18 * rev).astype(np.float32)


def _sfx_footstep_grass(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Grass footstep — soft, rustling, mostly noise."""
    d = max(duration, 0.12)
    n = int(d * sr)
    rustle = _band_noise(n, 800.0, 6000.0, sr, rng)
    rustle_env = _adsr(n, sr, attack_ms=2.0, decay_ms=30.0, sustain=0.0, release_ms=55.0)
    body = _sine(90.0, d, sr) * 0.3
    body_env = _adsr(n, sr, attack_ms=1.0, decay_ms=20.0, sustain=0.0, release_ms=30.0)
    return (0.65 * rustle * rustle_env + 0.35 * body[:n] * body_env).astype(np.float32)


def _sfx_footstep_dirt(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Dirt footstep — dry crunch with muted low thump."""
    d = max(duration, 0.12)
    n = int(d * sr)
    crunch = _band_noise(n, 250.0, 2800.0, sr, rng)
    crunch_env = _adsr(n, sr, attack_ms=0.7, decay_ms=22.0, sustain=0.0, release_ms=30.0)
    thump = _sine(85.0, d, sr, amp=0.35)
    thump_env = _adsr(n, sr, attack_ms=1.0, decay_ms=18.0, sustain=0.0, release_ms=26.0)
    return (0.58 * crunch * crunch_env + 0.42 * thump[:n] * thump_env).astype(np.float32)


def _sfx_footstep_wood(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Wood footstep — resonant knock with short creak."""
    d = max(duration, 0.12)
    n = int(d * sr)
    knock = _sine(220.0, d, sr, amp=0.55) * _exp_env(n, 16.0)
    creak = _band_noise(n, 400.0, 2200.0, sr, rng)
    creak_env = _adsr(n, sr, attack_ms=1.0, decay_ms=30.0, sustain=0.0, release_ms=36.0)
    return (0.62 * knock[:n] + 0.38 * creak * creak_env).astype(np.float32)


def _sfx_footstep_metal(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Metal footstep — bright clank with ringing overtone."""
    d = max(duration, 0.12)
    n = int(d * sr)
    clank_noise = _band_noise(n, 700.0, 7000.0, sr, rng)
    clank_env = _adsr(n, sr, attack_ms=0.3, decay_ms=18.0, sustain=0.0, release_ms=24.0)
    ring = (
        _sine(1300.0, d, sr, amp=0.3)
        + _sine(2200.0, d, sr, amp=0.16)
    ) * _exp_env(n, 20.0)
    dry = (0.55 * clank_noise * clank_env + 0.45 * ring[:n]).astype(np.float32)
    rev = _reverb(dry, sr, room_seconds=0.18, decay=3.5, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.85 * dry + 0.15 * rev).astype(np.float32)


def _sfx_footstep_water(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Shallow water footstep — splash transient with watery tail."""
    d = max(duration, 0.16)
    n = int(d * sr)
    splash = _band_noise(n, 500.0, 9000.0, sr, rng)
    splash_env = _adsr(n, sr, attack_ms=0.5, decay_ms=28.0, sustain=0.0, release_ms=45.0)
    body = _band_noise(n, 80.0, 600.0, sr, rng)
    body_env = _adsr(n, sr, attack_ms=2.0, decay_ms=38.0, sustain=0.0, release_ms=55.0)
    return (0.58 * splash * splash_env + 0.42 * body * body_env).astype(np.float32)


def _sfx_dodge_evade(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Dodge/evade cue — fast directional whoosh."""
    d = max(duration, 0.18)
    n = int(d * sr)
    sweep = _freq_sweep(600.0, 220.0, d, sr)
    hiss = _moving_band_noise(n, 1800.0, 600.0, bandwidth=1300.0, sr=sr, rng=rng)
    env = np.sin(np.linspace(0.0, np.pi, n, dtype=np.float64)).astype(np.float32)
    return (0.45 * sweep[:n] * env + 0.55 * hiss * env).astype(np.float32)


def _sfx_damage_taken(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Damage taken cue — short body thud + breathy noise."""
    d = max(duration, 0.22)
    n = int(d * sr)
    thud = _sine(95.0, d, sr, amp=0.7) * _exp_env(n, 12.0)
    grit = _band_noise(n, 300.0, 3000.0, sr, rng) * _exp_env(n, 18.0)
    return (0.62 * thud[:n] + 0.38 * grit).astype(np.float32)


def _sfx_critical_hit(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Critical hit cue — impact base with bright splash."""
    base = _sfx_hit(max(duration, 0.35), pitch_hz, sr, rng)
    n = len(base)
    sparkle = _band_noise(n, 3000.0, 12000.0, sr, rng) * _exp_env(n, 26.0) * 0.28
    ring = (_sine(2800.0, n / sr, sr, amp=0.2) * _exp_env(n, 14.0))[:n]
    return (base + sparkle + ring).astype(np.float32)


def _sfx_spell_holy(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Holy/light spell — ascending chimes with warm hall tail."""
    d = max(duration, 0.75)
    n = int(d * sr)
    base = pitch_hz or 740.0
    t = np.arange(n, dtype=np.float64) / sr
    chord = (
        0.42 * np.sin(2.0 * np.pi * base * t)
        + 0.28 * np.sin(2.0 * np.pi * base * 1.5 * t)
        + 0.20 * np.sin(2.0 * np.pi * base * 2.0 * t)
    )
    rise = np.linspace(0.6, 1.2, n, dtype=np.float64)
    shimmer = _band_noise(n, 2500.0, 10000.0, sr, rng) * 0.18
    env = _adsr(n, sr, attack_ms=15.0, decay_ms=120.0, sustain=0.40, release_ms=260.0)
    dry = ((chord * rise).astype(np.float32) + shimmer) * env
    wet = _reverb(dry.astype(np.float32), sr, room_seconds=1.3, decay=4.6, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.58 * dry + 0.42 * wet).astype(np.float32)


def _sfx_spell_buff_shield(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Buff/shield cue — upward shimmer and gentle protective ring."""
    d = max(duration, 0.6)
    n = int(d * sr)
    rise = _freq_sweep(260.0, 960.0, d, sr)
    shimmer = _band_noise(n, 1800.0, 9000.0, sr, rng)
    env = _adsr(n, sr, attack_ms=20.0, decay_ms=100.0, sustain=0.35, release_ms=220.0)
    ring = _sine(1200.0, d, sr, amp=0.22) * _exp_env(n, 10.0)
    return (0.45 * rise[:n] * env + 0.35 * shimmer * env + 0.20 * ring[:n]).astype(np.float32)


def _sfx_spell_debuff_poison(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Debuff/poison cue — descending unstable hiss with low gurgle."""
    d = max(duration, 0.65)
    n = int(d * sr)
    hiss = _moving_band_noise(n, 5000.0, 900.0, bandwidth=2200.0, sr=sr, rng=rng)
    gurgle = _band_noise(n, 120.0, 700.0, sr, rng)
    env = _adsr(n, sr, attack_ms=8.0, decay_ms=110.0, sustain=0.42, release_ms=250.0)
    return (0.6 * hiss * env + 0.4 * gurgle * env).astype(np.float32)


def _sfx_chest_open(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Chest open cue — hinge creak and latch click."""
    d = max(duration, 0.5)
    n = int(d * sr)
    creak = _moving_band_noise(n, 180.0, 520.0, bandwidth=260.0, sr=sr, rng=rng)
    creak_env = _adsr(n, sr, attack_ms=10.0, decay_ms=180.0, sustain=0.0, release_ms=160.0)
    click_n = max(1, int(0.03 * sr))
    click = _band_noise(click_n, 1200.0, 9000.0, sr, rng) * _exp_env(click_n, 35.0)
    out = (creak * creak_env).astype(np.float32)
    out[:click_n] += click.astype(np.float32)
    return out


def _sfx_dialogue_blip(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Dialogue blip — very short text-advance tick."""
    d = max(0.05, min(max(duration, 0.07), 0.12))
    n = int(d * sr)
    tone = _sine(pitch_hz or 700.0, d, sr, amp=0.55)
    noise = _band_noise(n, 1500.0, 6000.0, sr, rng) * 0.22
    env = _exp_env(n, 40.0)
    return (tone[:n] * env + noise * env).astype(np.float32)


def _sfx_transition_whoosh(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Transition whoosh — broad sweep for scene/battle transitions."""
    d = max(duration, 0.6)
    n = int(d * sr)
    sweep = _moving_band_noise(n, 2200.0, 260.0, bandwidth=1900.0, sr=sr, rng=rng)
    low = _freq_sweep(320.0, 120.0, d, sr)
    env = np.sin(np.linspace(0.0, np.pi, n, dtype=np.float64)).astype(np.float32)
    dry = (0.7 * sweep * env + 0.3 * low[:n] * env).astype(np.float32)
    wet = _reverb(dry, sr, room_seconds=0.6, decay=3.6, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.75 * dry + 0.25 * wet).astype(np.float32)


def _sfx_summon_charge(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Summon charge cue — long magical build-up."""
    d = max(duration, 2.0)
    n = int(d * sr)
    base = pitch_hz or 180.0
    t = np.arange(n, dtype=np.float64) / sr
    rise = np.linspace(0.9, 2.8, n, dtype=np.float64)
    body = np.sin(2.0 * np.pi * base * rise * t)
    choirish = np.sin(2.0 * np.pi * (base * 2.0) * t + 0.6) * 0.45
    noise = _moving_band_noise(n, 600.0, 4200.0, bandwidth=2600.0, sr=sr, rng=rng) * 0.24
    env = np.linspace(0.08, 1.0, n, dtype=np.float64).astype(np.float32)
    dry = ((body + choirish).astype(np.float32) * env + noise.astype(np.float32) * env).astype(np.float32)
    wet = _reverb(dry, sr, room_seconds=2.2, decay=6.4, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.52 * dry + 0.48 * wet).astype(np.float32)


def _sfx_menu_navigate(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """UI menu navigation — crisp, short, distinct from confirm/cancel."""
    d = max(duration, 0.06)
    n = int(d * sr)
    base = pitch_hz or 1050.0
    # Slightly pitched click with a short decay
    tone = _sine(base, d, sr, amp=0.6) + _sine(base * 1.5, d, sr, amp=0.25)
    env = _exp_env(n, 28.0)
    return (tone[:n] * env).astype(np.float32)


def _sfx_error(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Error/invalid action tone — descending two-tone buzz."""
    note_d = max(0.07, max(duration, 0.18) / 2.0)
    note_n = int(note_d * sr)
    first = _sine(600.0, note_d, sr) * _exp_env(note_n, 12.0)
    second = _sine(380.0, note_d, sr) * _exp_env(note_n, 12.0)
    return np.concatenate([first, second]).astype(np.float32)


def _sfx_item_get(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Item / chest pickup — ascending arpeggio with shimmer."""
    base = pitch_hz or 523.25  # C5
    ratios = [1.0, 1.2599, 1.5, 2.0]  # major arpeggio
    note_d = max(0.07, max(duration, 0.4) / len(ratios))
    parts: list[np.ndarray] = []
    for i, r in enumerate(ratios):
        nn = int(note_d * sr)
        t = np.arange(nn, dtype=np.float64) / sr
        f = base * r
        tone = (
            0.70 * np.sin(2.0 * np.pi * f * t)
            + 0.20 * np.sin(2.0 * np.pi * 2.0 * f * t)
            + 0.10 * np.sin(2.0 * np.pi * 3.0 * f * t)
        )
        sparkle = 0.12 * np.sin(2.0 * np.pi * f * 4.5 * t + i * 0.7)
        parts.append(((tone + sparkle) * _exp_env(nn, 8.0)).astype(np.float32))
    return np.concatenate(parts).astype(np.float32)


def _sfx_spell_wind(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Wind/air spell — swooping whoosh with magical sparkle."""
    d = max(duration, 0.5)
    n = int(d * sr)
    # Core wind body
    wind = _moving_band_noise(n, 600.0, 8000.0, bandwidth=2000.0, sr=sr, rng=rng)
    arc = np.sin(np.linspace(0.0, np.pi, n, dtype=np.float64)).astype(np.float32)
    base = pitch_hz or 700.0
    t = np.arange(n, dtype=np.float64) / sr
    # Rising crystalline tone for the magic character
    sparkle = np.zeros(n, dtype=np.float64)
    for ratio in (1.0, 1.5, 2.0, 3.0):
        sparkle += 0.15 * np.sin(2.0 * np.pi * base * ratio * t + rng.uniform(0, 2 * np.pi))
    sparkle_env = np.linspace(0.0, 1.0, n, dtype=np.float64) * np.exp(-3.0 * t)
    dry = (0.65 * wind * arc + 0.35 * sparkle.astype(np.float32) * sparkle_env.astype(np.float32)).astype(np.float32)
    wet = _reverb(dry, sr, room_seconds=0.8, decay=3.8, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.6 * dry + 0.4 * wet).astype(np.float32)


def _sfx_spell_earth(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Earth/stone spell — deep rumble + rocky crash."""
    d = max(duration, 0.7)
    n = int(d * sr)
    rumble = _band_noise(n, 30.0, 250.0, sr, rng)
    crack = _band_noise(n, 600.0, 5000.0, sr, rng)
    # Low frequency punch
    punch_n = max(1, int(0.08 * sr))
    punch_t = np.arange(punch_n, dtype=np.float64) / sr
    freq_glide = np.linspace(120.0, 40.0, punch_n)
    punch_phase = 2.0 * np.pi * np.cumsum(freq_glide / sr)
    punch = np.sin(punch_phase).astype(np.float32) * _exp_env(punch_n, 8.0)
    out = np.zeros(n, dtype=np.float32)
    out[:punch_n] = punch
    env = _adsr(n, sr, attack_ms=5.0, decay_ms=150.0, sustain=0.28, release_ms=350.0)
    out += (0.55 * rumble + 0.30 * crack) * env
    wet = _reverb(out, sr, room_seconds=1.5, decay=5.0, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.6 * out + 0.4 * wet).astype(np.float32)


def _sfx_spell_dark(duration: float, pitch_hz: float | None, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Dark/shadow spell — ominous low drones with distorted overtones."""
    d = max(duration, 0.8)
    n = int(d * sr)
    base = pitch_hz or 80.0
    t = np.arange(n, dtype=np.float64) / sr
    # Detuned minor clusters for dissonance
    sig = np.zeros(n, dtype=np.float64)
    for detune in (-0.015, 0.0, 0.013, -0.028):
        f = base * (1.0 + detune)
        sig += np.sin(2.0 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    # Distort for a menacing character
    sig = np.tanh(sig * 2.5)
    dark_noise = _band_noise(n, 150.0, 1500.0, sr, rng) * 0.25
    env = _adsr(n, sr, attack_ms=80.0, decay_ms=200.0, sustain=0.55, release_ms=400.0)
    dry = ((sig.astype(np.float32) + dark_noise) * env).astype(np.float32)
    wet = _reverb(dry, sr, room_seconds=2.0, decay=6.0, seed=int(rng.integers(0, 2**31 - 1)))
    return (0.55 * dry + 0.45 * wet).astype(np.float32)


_SFX_FUNCTIONS: dict[str, Callable[[float, float | None, int, np.random.Generator], np.ndarray]] = {
    "explosion": _sfx_explosion,
    "footstep": _sfx_footstep,
    "footstep_stone": _sfx_footstep_stone,
    "footstep_grass": _sfx_footstep_grass,
    "footstep_dirt": _sfx_footstep_dirt,
    "footstep_wood": _sfx_footstep_wood,
    "footstep_metal": _sfx_footstep_metal,
    "footstep_water": _sfx_footstep_water,
    "footstep_water_shallow": _sfx_footstep_water,
    "footstep_hard": _sfx_footstep_stone,
    "footstep_soft": _sfx_footstep_grass,
    "hit": _sfx_hit,
    "impact": _sfx_hit,
    "whoosh": _sfx_whoosh,
    "swing": _sfx_whoosh,
    "laser": _sfx_laser,
    "coin": _sfx_coin,
    "pickup": _sfx_coin,
    "item_get": _sfx_item_get,
    "item": _sfx_item_get,
    "treasure": _sfx_item_get,
    "chest": _sfx_item_get,
    "jump": _sfx_jump,
    "magic": _sfx_magic,
    "spell": _sfx_magic,
    "spell_fire": _sfx_spell_fire,
    "spell_ice": _sfx_spell_ice,
    "spell_thunder": _sfx_spell_thunder,
    "spell_wind": _sfx_spell_wind,
    "spell_earth": _sfx_spell_earth,
    "spell_dark": _sfx_spell_dark,
    "spell_holy": _sfx_spell_holy,
    "holy_light": _sfx_spell_holy,
    "light_spell": _sfx_spell_holy,
    "dark_curse": _sfx_spell_dark,
    "curse": _sfx_spell_dark,
    "spell_buff": _sfx_spell_buff_shield,
    "buff": _sfx_spell_buff_shield,
    "shield_activate": _sfx_spell_buff_shield,
    "aura": _sfx_spell_buff_shield,
    "spell_debuff": _sfx_spell_debuff_poison,
    "debuff": _sfx_spell_debuff_poison,
    "poison": _sfx_spell_debuff_poison,
    "status_ailment": _sfx_spell_debuff_poison,
    "summon_charge": _sfx_summon_charge,
    "limit_break_charge": _sfx_summon_charge,
    "heal": _sfx_cure,
    "cure": _sfx_cure,
    "summon": _sfx_summon,
    "limit_break": _sfx_limit_break,
    "limit": _sfx_limit_break,
    "ultimate": _sfx_limit_break,
    "save_point": _sfx_save_point,
    "checkpoint": _sfx_save_point,
    "level_up": _sfx_level_up,
    "levelup": _sfx_level_up,
    "exp": _sfx_level_up,
    "game_over": _sfx_game_over,
    "gameover": _sfx_game_over,
    "defeat": _sfx_game_over,
    "parry": _sfx_parry,
    "block": _sfx_parry,
    "block_parry": _sfx_parry,
    "dodge": _sfx_dodge_evade,
    "evade": _sfx_dodge_evade,
    "dodge_evade": _sfx_dodge_evade,
    "damage_taken": _sfx_damage_taken,
    "hurt": _sfx_damage_taken,
    "critical_hit": _sfx_critical_hit,
    "sword": _sfx_sword,
    "sword_swing": _sfx_sword,
    "slash": _sfx_sword,
    "arrow": _sfx_arrow,
    "bow": _sfx_arrow,
    "shoot": _sfx_arrow,
    "projectile": _sfx_arrow,
    "door": _sfx_door,
    "door_open": _sfx_door,
    "door_close": _sfx_door,
    "glass_break": _sfx_glass_break,
    "glass": _sfx_glass_break,
    "shatter": _sfx_glass_break,
    "break": _sfx_glass_break,
    "heartbeat": _sfx_heartbeat,
    "heart": _sfx_heartbeat,
    "pulse": _sfx_heartbeat,
    "water": _sfx_water,
    "splash": _sfx_water,
    "rain": _sfx_water,
    "river": _sfx_water,
    "wind": _sfx_wind,
    "wind_howl": _sfx_wind,
    "gust": _sfx_wind,
    "ui_click": _sfx_ui_click,
    "click": _sfx_ui_click,
    "tick": _sfx_ui_click,
    "ping": _sfx_ui_click,
    "confirm": _sfx_confirm,
    "menu_open": _sfx_confirm,
    "cancel": _sfx_cancel,
    "menu_close": _sfx_cancel,
    "menu_navigate": _sfx_menu_navigate,
    "navigate": _sfx_menu_navigate,
    "cursor": _sfx_menu_navigate,
    "select": _sfx_menu_navigate,
    "error": _sfx_error,
    "invalid": _sfx_error,
    "deny": _sfx_error,
    "fire": _sfx_spell_fire,
    "ice": _sfx_spell_ice,
    "thunder": _sfx_spell_thunder,
    "lightning": _sfx_spell_thunder,
    "bolt": _sfx_spell_thunder,
    "earth": _sfx_spell_earth,
    "stone": _sfx_spell_earth,
    "dark": _sfx_spell_dark,
    "shadow": _sfx_spell_dark,
    "beep": _sfx_confirm,
    "chest_open": _sfx_chest_open,
    "treasure_open": _sfx_chest_open,
    "dialogue_blip": _sfx_dialogue_blip,
    "text_advance": _sfx_dialogue_blip,
    "transition": _sfx_transition_whoosh,
    "transition_whoosh": _sfx_transition_whoosh,
    "scene_transition": _sfx_transition_whoosh,
    "battle_start_sting": _sfx_transition_whoosh,
    "teleport": _sfx_transition_whoosh,
    "warp": _sfx_transition_whoosh,
    "generic": _sfx_generic,
}


def synthesise_sfx(
    sfx_type: str,
    duration: float,
    pitch_hz: float | None = None,
    sample_rate: int = 44100,
    seed: int | None = None,
) -> np.ndarray:
    """Generate mono float32 audio for an SFX type; deterministic with a seed, non-deterministic otherwise."""
    rng = np.random.default_rng(seed)
    fn = _SFX_FUNCTIONS.get(sfx_type.lower(), _sfx_generic)
    audio = fn(duration, pitch_hz, sample_rate, rng).astype(np.float32)
    peak = float(np.max(np.abs(audio)))
    if peak > 1e-9:
        target = 10.0 ** (-5.0 / 20.0)
        audio = (audio / peak * target).astype(np.float32)
    return audio


def available_sfx_types() -> list[str]:
    return sorted(_SFX_FUNCTIONS)
