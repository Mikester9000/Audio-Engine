"""
Loop analyser – detect discontinuities at audio loop points.

When audio is used as a looping music track or ambient sound in a game, the
end of the audio must connect seamlessly to the beginning.  A "click" or
"pop" at the loop boundary is caused by a sudden discontinuity in the
waveform (amplitude jump) or, less audibly, a phase discontinuity.

This analyser checks:
1. **Amplitude jump** at the loop boundary (most common click cause).
2. **Zero-crossing proximity** – the loop point is near a zero-crossing for
   both the end and the start, minimising the jump.
3. **Cross-correlation similarity** – the short regions around the loop
   boundary are spectrally similar (fade match).

Usage
-----
>>> from audio_engine.qa import LoopAnalyzer
>>> analyzer = LoopAnalyzer(sample_rate=44100)
>>> result = analyzer.analyze(audio)
>>> if result.is_seamless:
...     print("Loop is click-free")
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["LoopAnalyzer", "LoopReport"]


@dataclass
class LoopReport:
    """Result from loop boundary analysis.

    Attributes
    ----------
    is_seamless:
        ``True`` if the loop boundary is within acceptable limits.
    amplitude_jump:
        Absolute amplitude difference at the loop point (0–2).
    amplitude_jump_db:
        Amplitude jump expressed in dB.
    start_near_zero:
        ``True`` if the loop start sample is within the zero-crossing window.
    end_near_zero:
        ``True`` if the loop end sample is within the zero-crossing window.
    boundary_correlation:
        Cross-correlation coefficient (−1–1) between the pre-loop and
        post-loop windows.  Near 1.0 = smooth transition.
    """

    is_seamless: bool
    amplitude_jump: float
    amplitude_jump_db: float
    start_near_zero: bool
    end_near_zero: bool
    boundary_correlation: float

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        status = "SEAMLESS" if self.is_seamless else "CLICK DETECTED"
        return (
            f"{status} – jump {self.amplitude_jump_db:.1f} dB, "
            f"correlation {self.boundary_correlation:.3f}"
        )


class LoopAnalyzer:
    """Analyse audio for loop-boundary click artefacts.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    window_ms:
        Analysis window around the loop boundary in milliseconds
        (default 10 ms).
    jump_threshold:
        Maximum acceptable amplitude jump at the loop boundary (linear,
        0–2).  Above this threshold :attr:`LoopReport.is_seamless` is
        ``False``.  Default ``0.05`` (~−26 dB jump).
    zero_cross_window_ms:
        Window in ms within which the loop point must be near a zero
        crossing to pass the zero-crossing check.  Default ``2 ms``.

    Example
    -------
    >>> analyzer = LoopAnalyzer(sample_rate=44100)
    >>> result = analyzer.analyze(audio)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        window_ms: float = 10.0,
        jump_threshold: float = 0.05,
        zero_cross_window_ms: float = 2.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.window_samples = max(1, int(sample_rate * window_ms / 1000.0))
        self.jump_threshold = jump_threshold
        self._zc_window = max(1, int(sample_rate * zero_cross_window_ms / 1000.0))

    def analyze(
        self,
        audio: np.ndarray,
        loop_start: int | None = None,
        loop_end: int | None = None,
    ) -> LoopReport:
        """Analyse loop boundary of *audio*.

        Parameters
        ----------
        audio:
            Float32 array, 1-D (mono) or ``(N, 2)`` (stereo).
        loop_start:
            Sample index where the loop begins.  Defaults to 0.
        loop_end:
            Sample index where the loop ends.  Defaults to ``len(audio) - 1``.

        Returns
        -------
        :class:`LoopReport`
        """
        # Use mono for analysis
        if audio.ndim == 2:
            mono = np.mean(audio, axis=1).astype(np.float64)
        else:
            mono = audio.astype(np.float64)

        n = len(mono)
        if loop_start is None:
            loop_start = 0
        if loop_end is None:
            loop_end = n - 1

        loop_start = int(np.clip(loop_start, 0, n - 1))
        loop_end = int(np.clip(loop_end, 0, n - 1))

        # 1. Amplitude jump at the loop boundary
        end_sample = mono[loop_end]
        start_sample = mono[loop_start]
        amplitude_jump = float(abs(end_sample - start_sample))
        amplitude_jump_db = (
            20.0 * np.log10(amplitude_jump) if amplitude_jump > 1e-9 else -120.0
        )

        # 2. Zero-crossing proximity check
        start_near_zero = self._near_zero(mono, loop_start)
        end_near_zero = self._near_zero(mono, loop_end)

        # 3. Boundary cross-correlation
        w = self.window_samples
        # Pre-loop tail
        pre_start = max(0, loop_end - w)
        pre_win = mono[pre_start : loop_end + 1]
        # Post-loop head
        post_end = min(n, loop_start + w)
        post_win = mono[loop_start : post_end]

        corr = self._window_correlation(pre_win, post_win)

        is_seamless = (
            amplitude_jump < self.jump_threshold
            and corr > 0.7
        )

        return LoopReport(
            is_seamless=is_seamless,
            amplitude_jump=amplitude_jump,
            amplitude_jump_db=amplitude_jump_db,
            start_near_zero=start_near_zero,
            end_near_zero=end_near_zero,
            boundary_correlation=corr,
        )

    def _near_zero(self, signal: np.ndarray, idx: int) -> bool:
        """Return ``True`` if the region around *idx* passes through zero."""
        w = self._zc_window
        region = signal[max(0, idx - w) : min(len(signal), idx + w + 1)]
        if len(region) < 2:
            return False
        # Check for sign change = zero crossing
        return bool(np.any(region[:-1] * region[1:] <= 0.0))

    @staticmethod
    def _window_correlation(a: np.ndarray, b: np.ndarray) -> float:
        """Compute normalised cross-correlation between two short windows."""
        n = min(len(a), len(b))
        if n < 2:
            return 0.0
        a = a[:n]
        b = b[:n]
        a = a - np.mean(a)
        b = b - np.mean(b)
        norm = np.sqrt(np.sum(a ** 2) * np.sum(b ** 2))
        if norm < 1e-12:
            return 0.0
        return float(np.dot(a, b) / norm)
