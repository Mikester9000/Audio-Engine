"""
PS1/PS2 SPU effects chain.

Simulates the Sony PlayStation 1 & 2 Sound Processing Unit (SPU/SPU2)
characteristics used on the original Final Fantasy VII and VIII soundtracks:

* **Bit-crush** — 14-bit effective quantisation (16-bit ADPCM 4:1 compression
  artefacts give roughly a 13-14 bit noise floor).
* **Sample-rate reduction** — optional 22 050 Hz internal stage then back to
  the engine SR, producing mild staircase aliasing.
* **SPU reverb** — a delay-feedback network with four modes that mirror the
  PS1 hardware reverb configurations (Room, Hall, Space, Echo).  The algorithm
  is a faithful approximation of the SPU's comb+all-pass network without
  requiring MPEG-compressed sample data.

All operations are intentionally lightweight (no external models, no
convolution IRs) so they add zero overhead for offline generation.

Usage
-----
>>> chain = PS1EffectsChain(sample_rate=44100)
>>> processed = chain.apply(audio, mode="room")   # audio: float32 ndarray

Adding a new reverb mode
------------------------
Define a dict in ``_SPU_REVERB_MODES`` with keys
``delay_ms``, ``feedback``, ``lp_cutoff``, ``wet``, ``pre_delay_ms``.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

__all__ = ["PS1EffectsChain", "SPUReverbMode"]

SPUReverbMode = Literal["room", "hall", "space", "echo", "pipe", "off"]

# ---------------------------------------------------------------------------
# SPU reverb mode parameter table
# Approximates the PS1 hardware reverb algorithm register values.
# delay_ms      : comb-filter delay tap lengths (ms)
# feedback      : feedback coefficient (< 1 to avoid instability)
# lp_cutoff     : low-pass cutoff on feedback path (Hz)
# wet           : wet/dry mix
# pre_delay_ms  : silence before reverb tail
# ---------------------------------------------------------------------------

_SPU_REVERB_MODES: dict[str, dict] = {
    "room": {
        "delay_ms":     [27.0, 41.0, 53.0, 67.0],
        "feedback":     0.45,
        "lp_cutoff":    3500.0,
        "wet":          0.30,
        "pre_delay_ms": 8.0,
    },
    "hall": {
        "delay_ms":     [37.0, 56.0, 77.0, 101.0],
        "feedback":     0.55,
        "lp_cutoff":    4500.0,
        "wet":          0.38,
        "pre_delay_ms": 15.0,
    },
    "space": {
        "delay_ms":     [60.0, 90.0, 120.0, 160.0],
        "feedback":     0.65,
        "lp_cutoff":    6000.0,
        "wet":          0.45,
        "pre_delay_ms": 20.0,
    },
    "echo": {
        "delay_ms":     [125.0, 250.0, 375.0, 500.0],
        "feedback":     0.40,
        "lp_cutoff":    5000.0,
        "wet":          0.35,
        "pre_delay_ms": 0.0,
    },
    "pipe": {
        "delay_ms":     [18.0, 26.0, 36.0, 48.0],
        "feedback":     0.70,
        "lp_cutoff":    2800.0,
        "wet":          0.28,
        "pre_delay_ms": 5.0,
    },
}


def _ms_to_samples(ms: float, sr: int) -> int:
    return max(1, int(ms * sr / 1000.0))


def _lp_filter(signal: np.ndarray, cutoff_hz: float, sr: int) -> np.ndarray:
    """Single-pole IIR low-pass filter (vectorised via scipy.signal.lfilter when available)."""
    if cutoff_hz >= sr / 2.0:
        return signal
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    try:
        from scipy.signal import lfilter  # type: ignore[import]
        b = np.array([alpha], dtype=np.float64)
        a = np.array([1.0, -(1.0 - alpha)], dtype=np.float64)
        return lfilter(b, a, signal.astype(np.float64)).astype(np.float32)
    except ImportError:
        out = np.empty_like(signal, dtype=np.float64)
        prev = float(signal[0])
        for i, x in enumerate(signal):
            prev = prev + alpha * (float(x) - prev)
            out[i] = prev
        return out.astype(np.float32)


class PS1EffectsChain:
    """PS1/PS2 SPU effects chain that produces the FF7/FF8 audio character.

    Parameters
    ----------
    sample_rate:
        Engine sample rate in Hz (typically 44 100).
    bit_depth:
        Effective bit depth after ADPCM simulation (default 14).
    enable_downsample:
        If ``True``, reduce to ``downsample_rate`` then upsample, adding
        mild aliasing similar to PS1 low-rate samples.
    downsample_rate:
        Internal sample rate to simulate (default 22 050 Hz).
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        bit_depth: int = 14,
        enable_downsample: bool = False,
        downsample_rate: int = 22050,
    ) -> None:
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.enable_downsample = enable_downsample
        self.downsample_rate = downsample_rate

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(
        self,
        audio: np.ndarray,
        mode: SPUReverbMode = "room",
    ) -> np.ndarray:
        """Apply the full PS1 effects chain to *audio*.

        Parameters
        ----------
        audio:
            Mono or stereo float32 array ``(N,)`` or ``(N, 2)``.
        mode:
            SPU reverb mode.  Use ``"off"`` to skip reverb (bit-crush
            and optional downsampling still apply).

        Returns
        -------
        np.ndarray
            Processed float32 audio, same shape as input.
        """
        stereo = audio.ndim == 2
        if stereo:
            left  = self._process_mono(audio[:, 0], mode)
            right = self._process_mono(audio[:, 1], mode)
            return np.stack([left, right], axis=1)
        return self._process_mono(audio, mode)

    # ------------------------------------------------------------------
    # Individual stages (public for testing / selective use)
    # ------------------------------------------------------------------

    def bit_crush(self, audio: np.ndarray) -> np.ndarray:
        """Quantise *audio* to :attr:`bit_depth` bits then back to float32.

        Simulates the quantisation noise floor of 16-bit ADPCM 4:1 compression
        used by the PS1 SPU.
        """
        levels = float(2 ** self.bit_depth)
        quantised = np.round(audio.astype(np.float64) * levels) / levels
        return quantised.astype(np.float32)

    def reduce_sample_rate(self, audio: np.ndarray) -> np.ndarray:
        """Downsample to :attr:`downsample_rate` then upsample back.

        Creates mild staircase aliasing — the character of PS1 samples that
        were internally stored at 22 050 Hz or lower.
        """
        ratio = self.sample_rate / self.downsample_rate
        if ratio <= 1.0:
            return audio
        step = int(ratio)
        decimated = audio[::step]
        # Nearest-neighbour upsample
        upsampled = np.repeat(decimated, step)
        n = len(audio)
        if len(upsampled) >= n:
            return upsampled[:n].astype(np.float32)
        # Pad if rounding caused short output
        pad = np.zeros(n - len(upsampled), dtype=np.float32)
        return np.concatenate([upsampled, pad]).astype(np.float32)

    def spu_reverb(self, audio: np.ndarray, mode: SPUReverbMode = "room") -> np.ndarray:
        """Apply SPU-style comb-filter reverb to a mono signal.

        Parameters
        ----------
        audio:
            Mono float32 array.
        mode:
            Reverb mode key (see :data:`_SPU_REVERB_MODES`).
        """
        if mode == "off" or mode not in _SPU_REVERB_MODES:
            return audio

        params = _SPU_REVERB_MODES[mode]
        sr = self.sample_rate
        sig = audio.astype(np.float64)
        n = len(sig)

        pre_delay_n = _ms_to_samples(params["pre_delay_ms"], sr)
        feedback = float(params["feedback"])
        lp_cutoff = float(params["lp_cutoff"])
        wet = float(params["wet"])

        # Build multi-tap comb reverb (vectorised via scipy.signal.lfilter when available)
        reverb_out = np.zeros(n + 1024, dtype=np.float64)
        n_taps = len(params["delay_ms"])
        try:
            from scipy.signal import lfilter  # type: ignore[import]
            for delay_ms in params["delay_ms"]:
                delay_n = _ms_to_samples(delay_ms, sr) + pre_delay_n
                # Feedback comb filter: y[n] = x[n-D] + feedback*y[n-D]
                # Transfer function: H(z) = z^{-D} / (1 - feedback*z^{-D})
                b_comb = np.zeros(delay_n + 1, dtype=np.float64)
                b_comb[delay_n] = 1.0
                a_comb = np.zeros(delay_n + 1, dtype=np.float64)
                a_comb[0] = 1.0
                a_comb[delay_n] = -feedback
                tail = lfilter(b_comb, a_comb, sig)
                reverb_out[:n] += tail / n_taps
        except ImportError:
            for delay_ms in params["delay_ms"]:
                delay_n = _ms_to_samples(delay_ms, sr) + pre_delay_n
                tail = np.zeros(n, dtype=np.float64)
                for i in range(n):
                    if i >= delay_n:
                        tail[i] = sig[i - delay_n] + feedback * tail[i - delay_n]
                reverb_out[:n] += tail / n_taps

        reverb_out = reverb_out[:n]

        # Low-pass filter on the reverb tail (SPU darkens the feedback)
        reverb_filtered = _lp_filter(reverb_out.astype(np.float32), lp_cutoff, sr)

        mixed = (1.0 - wet) * sig + wet * reverb_filtered.astype(np.float64)
        # Normalise to avoid clipping without changing character
        peak = np.max(np.abs(mixed))
        if peak > 1.0:
            mixed /= peak
        return mixed.astype(np.float32)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_mono(self, audio: np.ndarray, mode: SPUReverbMode) -> np.ndarray:
        sig = audio.astype(np.float32)
        if self.enable_downsample:
            sig = self.reduce_sample_rate(sig)
        sig = self.bit_crush(sig)
        if mode != "off":
            sig = self.spu_reverb(sig, mode)
        return sig
