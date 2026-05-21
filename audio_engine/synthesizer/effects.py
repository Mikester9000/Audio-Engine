"""
Effects – reverb, chorus, delay, distortion, and compression.

All effects operate on NumPy float32 arrays at the engine sample rate.

The reverb implementation builds a structured synthetic impulse response with:
  * Discrete early reflections (more room-like than a single diffuse noise tail)
  * Late reverberation tail (exponentially decaying noise shaped to Nyquist)
  * Unique RNG seed derived from the input signal's CRC so each call produces
    a distinct but deterministic room tail rather than the same fixed IR

This is fast (all via FFT convolution) and sounds much richer than a single
decayed white-noise IR.
"""

from __future__ import annotations

import zlib

import numpy as np
from scipy.signal import fftconvolve  # type: ignore[import]

__all__ = ["Effects"]

# Early-reflection tap offsets (ms) and gains — dense, diffuse feel
_ER_DELAYS_MS = (7.0, 13.0, 19.0, 27.0, 36.0, 48.0, 63.0)
_ER_GAINS     = (0.75, 0.58, 0.44, 0.32, 0.22, 0.14, 0.09)


class Effects:
    """Collection of audio effects processors.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # Reverb
    # ------------------------------------------------------------------

    def reverb(
        self,
        signal: np.ndarray,
        room_size: float = 0.5,
        wet: float = 0.3,
        decay: float = 1.5,
    ) -> np.ndarray:
        """High-quality synthetic reverb with early reflections.

        Builds a structured impulse response (IR) that combines:

        1. **Early reflections** — discrete echo taps derived from *room_size*.
        2. **Late reverb** — decaying noise tail with spectral balance.

        The IR is generated from a seed derived from the signal's CRC32, so
        every unique audio block gets a distinct room character while remaining
        deterministic within a run.

        Parameters
        ----------
        room_size:
            0–1 controls reverb tail length and early-reflection spread.
        wet:
            Dry/wet mix (0 = dry, 1 = fully wet).
        decay:
            Exponential decay rate of the late-reverb tail.
        """
        wet = float(np.clip(wet, 0.0, 1.0))
        room_size = float(np.clip(room_size, 0.01, 1.0))
        if len(signal) == 0:
            return signal.astype(np.float32)

        sr = self.sample_rate
        sig_f64 = signal.astype(np.float64)

        # --- Impulse response length (up to 2 s for large rooms) ---
        ir_seconds = max(0.08, room_size * 2.0)
        ir_len = max(32, int(ir_seconds * sr))

        # --- Unique late-reverb seed from signal content ---
        crc = zlib.crc32(signal[:min(256, len(signal))].tobytes()) & 0x7FFF_FFFF
        rng = np.random.default_rng(crc)

        # --- Build structured IR ---
        ir = np.zeros(ir_len, dtype=np.float64)

        # Early reflections
        for dt_ms, gain in zip(_ER_DELAYS_MS, _ER_GAINS):
            pos = max(1, int(dt_ms * 0.001 * sr * (0.7 + 0.6 * room_size)))
            if pos < ir_len:
                ir[pos] += gain

        # Late reverb: spectrally shaped noise with exponential decay
        late_onset = max(1, int(0.05 * ir_seconds * sr))
        late_noise = rng.standard_normal(ir_len)
        # Apply a gentle spectral shaping (roll off >8 kHz to avoid shrillness)
        from scipy.signal import butter, sosfilt  # type: ignore[import]
        nyq = sr / 2.0
        hi_cut = min(8000.0, nyq * 0.8)
        sos = butter(2, hi_cut / nyq, btype="low", output="sos")
        late_noise = sosfilt(sos, late_noise)
        t = np.arange(ir_len, dtype=np.float64) / sr
        late_env = np.exp(-decay * t)
        late_env[:late_onset] = 0.0
        ir += late_noise * late_env * 0.35

        # Normalise IR to unity power
        ir_power = np.sqrt(np.mean(ir ** 2))
        if ir_power > 1e-12:
            ir /= ir_power / 0.15  # target RMS of 0.15 to avoid clipping

        # --- Convolve and mix ---
        wet_sig = fftconvolve(sig_f64, ir, mode="full")[: len(sig_f64)]

        # Normalise wet to match dry level
        wet_peak = np.max(np.abs(wet_sig))
        dry_peak = np.max(np.abs(sig_f64))
        if wet_peak > 1e-9 and dry_peak > 1e-9:
            wet_sig = wet_sig * (dry_peak / wet_peak)

        return (wet * wet_sig + (1.0 - wet) * sig_f64).astype(np.float32)

    # ------------------------------------------------------------------
    # Delay
    # ------------------------------------------------------------------

    def delay(
        self,
        signal: np.ndarray,
        delay_time: float = 0.25,
        feedback: float = 0.4,
        wet: float = 0.3,
    ) -> np.ndarray:
        """Tape-style echo delay.

        Parameters
        ----------
        delay_time:
            Delay time in seconds.
        feedback:
            Amount of signal fed back (0–0.9 to avoid runaway).
        wet:
            Wet/dry mix.
        """
        feedback = np.clip(feedback, 0.0, 0.9)
        wet = np.clip(wet, 0.0, 1.0)
        delay_samples = int(delay_time * self.sample_rate)
        output = np.copy(signal).astype(np.float64)
        buffer = np.zeros(delay_samples + len(signal))
        buffer[: len(signal)] = signal.astype(np.float64)
        for i in range(len(signal)):
            if i + delay_samples < len(buffer):
                buffer[i + delay_samples] += feedback * output[i]
                output[i] += wet * buffer[i]
        return output.astype(np.float32)

    # ------------------------------------------------------------------
    # Chorus
    # ------------------------------------------------------------------

    def chorus(
        self,
        signal: np.ndarray,
        rate: float = 1.5,
        depth: float = 0.003,
        wet: float = 0.5,
    ) -> np.ndarray:
        """Modulated delay-line chorus effect.

        Parameters
        ----------
        rate:
            LFO rate in Hz.
        depth:
            Modulation depth in seconds (typical 1–10 ms).
        wet:
            Wet/dry mix.
        """
        wet = np.clip(wet, 0.0, 1.0)
        n = len(signal)
        if n == 0:
            return signal.astype(np.float32)
        t = np.arange(n) / self.sample_rate
        lfo = depth * self.sample_rate * (0.5 + 0.5 * np.sin(2.0 * np.pi * rate * t))
        sig_f64 = signal.astype(np.float64)
        idx = np.arange(n, dtype=np.float64) - lfo
        idx = np.clip(idx, 0.0, n - 1.0)
        idx0 = np.floor(idx).astype(np.int64)
        idx1 = np.clip(idx0 - 1, 0, n - 1)
        frac = idx - idx0
        s0 = sig_f64[idx0]
        s1 = sig_f64[idx1]
        chorus_out = s0 + frac * (s1 - s0)
        return (wet * chorus_out + (1.0 - wet) * sig_f64).astype(np.float32)

    # ------------------------------------------------------------------
    # Distortion
    # ------------------------------------------------------------------

    def distortion(
        self, signal: np.ndarray, drive: float = 5.0, tone: float = 0.5
    ) -> np.ndarray:
        """Soft-clip distortion / overdrive.

        Parameters
        ----------
        drive:
            Amount of gain before clipping (1 = clean, >5 = heavy).
        tone:
            High-frequency content mix (0 = dark, 1 = bright).
        """
        driven = np.clip(signal.astype(np.float64) * drive, -1.0, 1.0)
        clipped = np.tanh(driven * 2.0) / np.tanh(2.0)
        # Simple tone stack via mixing original (pre-emphasis) with clipped
        result = (1.0 - tone) * clipped + tone * driven / max(drive, 1.0)
        max_amp = np.max(np.abs(result))
        if max_amp > 0:
            result /= max_amp
        return result.astype(np.float32)

    # ------------------------------------------------------------------
    # Compressor
    # ------------------------------------------------------------------

    def compress(
        self,
        signal: np.ndarray,
        threshold: float = 0.5,
        ratio: float = 4.0,
        makeup_gain: float = 1.2,
    ) -> np.ndarray:
        """Simple peak compressor / limiter.

        Parameters
        ----------
        threshold:
            Level above which gain reduction starts (0–1).
        ratio:
            Compression ratio (e.g. 4 = 4:1).
        makeup_gain:
            Post-compression gain to restore perceived loudness.
        """
        sig = signal.astype(np.float64)
        abs_sig = np.abs(sig)
        gain = np.where(
            abs_sig > threshold,
            threshold + (abs_sig - threshold) / ratio,
            abs_sig,
        )
        # Avoid division by zero
        scale = np.where(abs_sig > 1e-9, gain / (abs_sig + 1e-9), 1.0)
        return (sig * scale * makeup_gain).astype(np.float32)

    # ------------------------------------------------------------------
    # Normalise / master limiter
    # ------------------------------------------------------------------

    def normalise(self, signal: np.ndarray, target: float = 0.9) -> np.ndarray:
        """Scale signal so the peak amplitude equals *target*."""
        peak = np.max(np.abs(signal))
        if peak < 1e-9:
            return signal
        return (signal * (target / peak)).astype(np.float32)
