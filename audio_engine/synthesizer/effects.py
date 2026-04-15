"""
Effects – reverb, chorus, delay, distortion, and compression.

All effects operate on NumPy float32 arrays at the engine sample rate.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import fftconvolve  # type: ignore[import]

__all__ = ["Effects"]


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
        """Convolution-based reverb using a synthetic impulse response.

        Parameters
        ----------
        room_size:
            0–1 controls IR length (larger → bigger room).
        wet:
            Mix ratio between processed (wet) and original (dry) signal.
        decay:
            Exponential decay rate of the IR.
        """
        wet = np.clip(wet, 0.0, 1.0)
        ir_length = max(int(room_size * self.sample_rate * 2.0), 16)
        rng = np.random.default_rng(42)
        ir = rng.standard_normal(ir_length).astype(np.float64)
        t = np.linspace(0.0, 1.0, ir_length)
        ir *= np.exp(-decay * t)
        ir /= np.sum(np.abs(ir)) + 1e-9
        wet_sig = fftconvolve(signal.astype(np.float64), ir, mode="full")[: len(signal)]
        return (wet * wet_sig + (1.0 - wet) * signal.astype(np.float64)).astype(np.float32)

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
        t = np.arange(n) / self.sample_rate
        lfo = depth * self.sample_rate * (0.5 + 0.5 * np.sin(2.0 * np.pi * rate * t))
        chorus_out = np.zeros(n, dtype=np.float64)
        sig_f64 = signal.astype(np.float64)
        for i in range(n):
            delay_f = lfo[i]
            delay_i = int(delay_f)
            frac = delay_f - delay_i
            idx0 = i - delay_i
            idx1 = idx0 - 1
            s0 = sig_f64[max(idx0, 0)]
            s1 = sig_f64[max(idx1, 0)]
            chorus_out[i] = s0 + frac * (s1 - s0)
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
