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


def _normalised_band(lo: float, hi: float, sr: int, min_width: float = 0.02) -> tuple[float, float] | None:
    nyq = sr / 2.0
    if nyq <= 0.0 or hi <= 0.0 or lo >= nyq:
        return None
    low = float(np.clip(lo / nyq, 1e-4, 0.999 - min_width))
    high = float(np.clip(hi / nyq, low + min_width, 0.999))
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
    band = _normalised_band(lo, hi, sr)
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
        band = _normalised_band(lo, hi, sr, min_width=0.04)
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


_SFX_FUNCTIONS: dict[str, Callable[[float, float | None, int, np.random.Generator], np.ndarray]] = {
    "explosion": _sfx_explosion,
    "footstep": _sfx_footstep,
    "hit": _sfx_hit,
    "impact": _sfx_hit,
    "whoosh": _sfx_whoosh,
    "swing": _sfx_whoosh,
    "laser": _sfx_laser,
    "coin": _sfx_coin,
    "pickup": _sfx_coin,
    "jump": _sfx_jump,
    "magic": _sfx_magic,
    "spell": _sfx_magic,
    "spell_fire": _sfx_spell_fire,
    "spell_ice": _sfx_spell_ice,
    "spell_thunder": _sfx_spell_thunder,
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
    "sword": _sfx_sword,
    "sword_swing": _sfx_sword,
    "slash": _sfx_sword,
    "ui_click": _sfx_ui_click,
    "click": _sfx_ui_click,
    "tick": _sfx_ui_click,
    "ping": _sfx_ui_click,
    "confirm": _sfx_confirm,
    "menu_open": _sfx_confirm,
    "cancel": _sfx_cancel,
    "menu_close": _sfx_cancel,
    "fire": _sfx_spell_fire,
    "ice": _sfx_spell_ice,
    "thunder": _sfx_spell_thunder,
    "lightning": _sfx_spell_thunder,
    "bolt": _sfx_spell_thunder,
    "water": _sfx_magic,
    "wind": _sfx_whoosh,
    "beep": _sfx_confirm,
    "generic": _sfx_generic,
}


def synthesise_sfx(
    sfx_type: str,
    duration: float,
    pitch_hz: float | None = None,
    sample_rate: int = 44100,
    seed: int | None = None,
) -> np.ndarray:
    """Generate mono float32 audio for an SFX type, deterministic when seed is provided."""
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
