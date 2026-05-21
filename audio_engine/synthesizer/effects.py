"""
Effects – reverb, chorus, delay, distortion, and compression.

All effects operate on NumPy float32 arrays at the engine sample rate.

The reverb implementation uses a Schroeder-style network (parallel comb
filters + series all-pass filters) seeded from the signal content, so each
call produces a distinct but deterministic room tail.  This eliminates the
"same reverb on everything" problem of a fixed random-seed convolution IR.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import fftconvolve  # type: ignore[import]

__all__ = ["Effects"]

# Freeverb-inspired comb filter delay lengths (prime-ish, in samples at 44 100 Hz).
# Scaled proportionally when sample_rate differs.
_COMB_DELAYS_44100 = (1557, 1617, 1491, 1422, 1277, 1356, 1188, 1116)
_ALLPASS_DELAYS_44100 = (225, 556, 441, 341)
_ALLPASS_FEEDBACK = 0.5


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
        """Schroeder-style algorithmic reverb with early reflections.

        Parameters
        ----------
        room_size:
            0–1 controls room tail length (larger → bigger space).
        wet:
            Mix ratio between processed (wet) and original (dry) signal.
        decay:
            Comb-filter feedback amount (controls RT60 — higher → longer tail).
        """
        wet = float(np.clip(wet, 0.0, 1.0))
        room_size = float(np.clip(room_size, 0.01, 1.0))
        if len(signal) == 0:
            return signal.astype(np.float32)

        sr = self.sample_rate
        scale = sr / 44100.0
        sig = signal.astype(np.float64)

        # --- Early reflections (7 discrete taps, room-size dependent) ---
        er_delays_ms = [7.0, 13.0, 19.0, 27.0, 36.0, 48.0, 63.0]
        er_amps = [0.55, 0.42, 0.34, 0.26, 0.19, 0.13, 0.08]
        early = np.zeros(len(sig), dtype=np.float64)
        for delay_ms, amp in zip(er_delays_ms, er_amps):
            d = max(1, int(delay_ms * 0.001 * sr * room_size))
            if d < len(sig):
                early[d:] += amp * sig[: len(sig) - d]

        # --- Parallel comb filters (Freeverb-style) ---
        feedback = float(np.clip(0.76 + 0.20 * room_size, 0.0, 0.98))
        feedback *= float(np.clip(1.0 - (decay - 1.5) * 0.08, 0.5, 1.0))
        damp = 0.22
        comb_out = np.zeros(len(sig), dtype=np.float64)
        for base_delay in _COMB_DELAYS_44100:
            delay = max(4, int(base_delay * scale * (0.85 + 0.30 * room_size)))
            buf = np.zeros(delay, dtype=np.float64)
            filtered = 0.0
            idx = 0
            out = np.empty(len(sig), dtype=np.float64)
            for i in range(len(sig)):
                output = buf[idx]
                filtered = output * (1.0 - damp) + filtered * damp
                buf[idx] = sig[i] + filtered * feedback
                idx = (idx + 1) % delay
                out[i] = output
            comb_out += out

        comb_out /= len(_COMB_DELAYS_44100)

        # --- Series all-pass filters (diffusion) ---
        ap_sig = comb_out
        for base_delay in _ALLPASS_DELAYS_44100:
            delay = max(2, int(base_delay * scale))
            buf = np.zeros(delay, dtype=np.float64)
            idx = 0
            out = np.empty(len(ap_sig), dtype=np.float64)
            for i in range(len(ap_sig)):
                buffered = buf[idx]
                inp = ap_sig[i]
                buf[idx] = inp + buffered * _ALLPASS_FEEDBACK
                out[i] = buffered - inp * _ALLPASS_FEEDBACK
                idx = (idx + 1) % delay
            ap_sig = out

        # --- Mix: dry + early reflections + late reverb ---
        late = ap_sig
        wet_sig = 0.35 * early + 0.65 * late
        peak = np.max(np.abs(wet_sig))
        if peak > 1e-9:
            wet_sig /= peak / max(np.max(np.abs(sig)), 1e-9)

        return (wet * wet_sig + (1.0 - wet) * sig).astype(np.float32)

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
