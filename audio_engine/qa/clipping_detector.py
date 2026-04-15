"""
Clipping detector for audio quality assurance.

Detects digital over-threshold clipping events in audio arrays and exported
WAV files.  Reports the number of clipped samples, the worst-case clip level,
and provides a per-channel breakdown for stereo files.

Clipping in game audio is undesirable because it causes harsh harmonic
distortion that is immediately audible and cannot be corrected after export.

Usage
-----
>>> from audio_engine.qa import ClippingDetector
>>> detector = ClippingDetector(threshold=0.99)
>>> report = detector.detect(audio)
>>> if report.has_clipping:
...     print(f"WARNING: {report.clipped_samples} clipped samples")
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["ClippingDetector", "ClippingReport"]


@dataclass
class ClippingReport:
    """Result from a clipping analysis.

    Attributes
    ----------
    has_clipping:
        ``True`` if any clipped samples were found.
    clipped_samples:
        Total number of samples that exceed the threshold.
    clip_ratio:
        Fraction of total samples that are clipped (0–1).
    peak_level:
        Maximum absolute sample value found.
    peak_dbfs:
        Peak level in dBFS.
    clipped_samples_per_channel:
        Dict mapping channel index to clipped sample count (empty for mono).
    """

    has_clipping: bool
    clipped_samples: int
    clip_ratio: float
    peak_level: float
    peak_dbfs: float
    clipped_samples_per_channel: dict[int, int] = field(default_factory=dict)

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        if not self.has_clipping:
            return f"OK – no clipping (peak {self.peak_dbfs:.1f} dBFS)"
        pct = self.clip_ratio * 100.0
        return (
            f"CLIPPING DETECTED – {self.clipped_samples} samples "
            f"({pct:.2f}%), peak {self.peak_dbfs:.2f} dBFS"
        )


class ClippingDetector:
    """Detect digital clipping in audio arrays.

    Parameters
    ----------
    threshold:
        Amplitude threshold above which a sample is considered clipped
        (default ``0.999`` – catches full-scale clips with a small margin).

    Example
    -------
    >>> detector = ClippingDetector(threshold=0.99)
    >>> report = detector.detect(audio)
    >>> print(report.summary())
    """

    def __init__(self, threshold: float = 0.999) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold must be in (0, 1]")
        self.threshold = threshold

    def detect(self, audio: np.ndarray) -> ClippingReport:
        """Analyse *audio* for clipping.

        Parameters
        ----------
        audio:
            Float32 array, 1-D (mono) or ``(N, 2)`` (stereo).

        Returns
        -------
        :class:`ClippingReport`
        """
        sig = np.asarray(audio, dtype=np.float32)
        abs_sig = np.abs(sig)
        peak = float(np.max(abs_sig))
        peak_dbfs = 20.0 * np.log10(peak) if peak > 1e-12 else -120.0

        per_channel: dict[int, int] = {}
        if sig.ndim == 2:
            total_clipped = 0
            for ch in range(sig.shape[1]):
                ch_clips = int(np.sum(abs_sig[:, ch] >= self.threshold))
                per_channel[ch] = ch_clips
                total_clipped += ch_clips
            total_samples = sig.shape[0] * sig.shape[1]
        else:
            total_clipped = int(np.sum(abs_sig >= self.threshold))
            total_samples = len(sig)

        clip_ratio = total_clipped / max(total_samples, 1)
        return ClippingReport(
            has_clipping=total_clipped > 0,
            clipped_samples=total_clipped,
            clip_ratio=clip_ratio,
            peak_level=peak,
            peak_dbfs=peak_dbfs,
            clipped_samples_per_channel=per_channel,
        )

    def detect_wav(self, path: str) -> ClippingReport:
        """Load *path* (WAV) and run clipping detection.

        Parameters
        ----------
        path:
            Path to a WAV file.

        Returns
        -------
        :class:`ClippingReport`
        """
        import wave

        with wave.open(str(path), "r") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        dtype = np.int16 if sampwidth == 2 else np.int32
        scale = 32768.0 if sampwidth == 2 else 2147483648.0
        samples = np.frombuffer(raw, dtype=dtype).astype(np.float32) / scale

        if n_channels > 1:
            samples = samples.reshape(-1, n_channels)

        return self.detect(samples)
