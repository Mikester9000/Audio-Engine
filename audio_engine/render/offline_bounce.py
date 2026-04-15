"""
OfflineBounce – deterministic render + mastering pipeline.

Takes a raw audio array, runs it through a configurable DSP chain
(EQ → Compressor → Limiter), applies loudness normalisation, and exports
to disk.  Designed to produce consistent, production-quality output every
time the same inputs are given.

Usage
-----
>>> from audio_engine.render import OfflineBounce
>>> bounce = OfflineBounce(sample_rate=44100)
>>> out_path = bounce.process_and_export(raw_audio, "master.wav")
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np

from audio_engine.dsp.eq import EQ, EQBand
from audio_engine.dsp.compressor import Compressor
from audio_engine.dsp.limiter import Limiter
from audio_engine.dsp.dither import dither
from audio_engine.export.audio_exporter import AudioExporter

__all__ = ["OfflineBounce"]


def _lufs_loudness(signal: np.ndarray, sample_rate: int) -> float:
    """Compute an approximate integrated loudness in LUFS.

    Uses the simplified K-weighted measurement approach: square the signal,
    average over all samples, and convert to dB.  This is a fast approximation
    suitable for gain normalisation; for a full EBU R128 measurement use
    :class:`~audio_engine.qa.LoudnessMeter`.

    Parameters
    ----------
    signal:
        1-D or ``(N, 2)`` float32 array.
    sample_rate:
        Unused in this approximation; kept for API consistency.

    Returns
    -------
    float
        Approximate integrated loudness in LUFS.
    """
    if signal.ndim == 2:
        # Sum channels with equal weight
        mono = np.mean(signal, axis=1)
    else:
        mono = signal.astype(np.float32)

    mean_sq = np.mean(mono.astype(np.float64) ** 2)
    if mean_sq < 1e-12:
        return -120.0
    return 10.0 * np.log10(mean_sq)


class OfflineBounce:
    """Production render/mastering pipeline for audio assets.

    The pipeline is: ``raw audio → EQ → Compressor → Limiter → Dither → export``.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    bit_depth:
        Output bit depth: 16 or 32.
    target_lufs:
        Target integrated loudness in LUFS (default ``-16`` for game audio /
        streaming; use ``-23`` for broadcast).  Pass ``None`` to skip loudness
        normalisation.
    ceiling_db:
        True-peak ceiling for the final limiter (default ``-0.3`` dBFS).
    apply_master_eq:
        If ``True``, apply a gentle master EQ (low-shelf cut, air band boost)
        to give tracks a polished sound.
    apply_compression:
        If ``True``, apply bus compression before limiting.

    Example
    -------
    >>> bounce = OfflineBounce(sample_rate=44100, target_lufs=-16)
    >>> out = bounce.process_and_export(audio, "output.wav")
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        bit_depth: Literal[16, 32] = 16,
        target_lufs: float | None = -16.0,
        ceiling_db: float = -0.3,
        apply_master_eq: bool = True,
        apply_compression: bool = True,
    ) -> None:
        self.sample_rate = sample_rate
        self.target_lufs = target_lufs
        self._exporter = AudioExporter(sample_rate=sample_rate, bit_depth=bit_depth)
        self._bit_depth = bit_depth

        # Build the mastering chain
        self._eq = self._build_master_eq() if apply_master_eq else None
        self._compressor = (
            Compressor(
                sample_rate=sample_rate,
                threshold_db=-24.0,
                ratio=2.0,
                attack_ms=30.0,
                release_ms=200.0,
                knee_db=6.0,
                makeup_gain_db=1.0,
            )
            if apply_compression
            else None
        )
        self._limiter = Limiter(sample_rate=sample_rate, ceiling_db=ceiling_db)

    def _build_master_eq(self) -> EQ:
        """Return a gentle mastering EQ suitable for most game audio."""
        eq = EQ(self.sample_rate)
        # High-pass filter to remove sub-bass rumble below 30 Hz
        eq.add_band(EQBand(30.0, gain_db=0.0, q=0.707, band_type="high_pass"))
        # Low-shelf: gently tighten the low end
        eq.add_band(EQBand(120.0, gain_db=-1.5, q=0.707, band_type="low_shelf"))
        # Presence/air boost for clarity
        eq.add_band(EQBand(10000.0, gain_db=+1.5, q=0.707, band_type="high_shelf"))
        return eq

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Run *audio* through the mastering chain without exporting.

        Parameters
        ----------
        audio:
            Raw float32 audio array, 1-D or ``(N, 2)``.

        Returns
        -------
        np.ndarray
            Mastered float32 audio, same shape.
        """
        sig = audio.astype(np.float32)

        # 1. Master EQ
        if self._eq is not None:
            sig = self._eq.process(sig)

        # 2. Bus compression
        if self._compressor is not None:
            sig = self._compressor.process(sig)

        # 3. Loudness normalisation
        if self.target_lufs is not None:
            current_lufs = _lufs_loudness(sig, self.sample_rate)
            gain_db = self.target_lufs - current_lufs
            # Cap the boost to avoid unrealistic amplification
            gain_db = np.clip(gain_db, -40.0, 20.0)
            gain_linear = 10.0 ** (gain_db / 20.0)
            sig = (sig.astype(np.float64) * gain_linear).astype(np.float32)

        # 4. True-peak limiting
        sig = self._limiter.process(sig)

        # 5. Dithering (only meaningful when exporting to 16-bit)
        if self._bit_depth == 16:
            sig = dither(sig, bit_depth=16)

        return sig

    def process_and_export(
        self,
        audio: np.ndarray,
        path: str | Path,
        fmt: Literal["wav", "ogg"] = "wav",
        loop_start: int | None = None,
        loop_end: int | None = None,
    ) -> Path:
        """Process *audio* and export to *path*.

        Parameters
        ----------
        audio:
            Raw float32 audio array.
        path:
            Output file path.
        fmt:
            Output format: ``"wav"`` or ``"ogg"``.
        loop_start:
            Loop start in samples (WAV only).
        loop_end:
            Loop end in samples (WAV only).

        Returns
        -------
        Path
            The written file path.
        """
        mastered = self.process(audio)
        out_path = self._exporter.export(mastered, path, fmt=fmt)

        if loop_start is not None and fmt == "wav":
            if loop_end is None:
                raise ValueError("loop_end must be provided when loop_start is set")
            self._exporter.write_loop_points(out_path, loop_start, loop_end)

        return out_path
