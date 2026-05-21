"""
Oscillator – waveform generators.

Provides sine, square, sawtooth, triangle, noise, and band-limited waveforms
that are the building-blocks of every synthesised sound in the engine.

Band-limited variants (``bl_sawtooth``, ``bl_square``, ``bl_triangle``) use
additive synthesis capped at the Nyquist frequency, eliminating the aliasing
that makes raw scipy waveforms sound harsh and digital.  Use them by default
for any pitched instrument — especially strings, brass, and pads.
"""

from __future__ import annotations

import numpy as np

__all__ = ["Oscillator"]

# Maximum number of harmonics computed for band-limited waveforms.
# 40 harmonics gives very good alias suppression (content up to ~20 kHz for
# 440 Hz fundamentals) while keeping the vectorised computation fast.
_BL_MAX_HARMONICS = 40


class Oscillator:
    """Generate audio waveforms at a given sample rate.

    Parameters
    ----------
    sample_rate:
        Samples per second (default 44 100 Hz).
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def _time_array(self, frequency: float, duration: float) -> np.ndarray:
        """Return a phase-continuous time array for *duration* seconds."""
        num_samples = int(self.sample_rate * duration)
        return np.linspace(0.0, duration, num_samples, endpoint=False)

    def _phase(self, frequency: float, duration: float) -> np.ndarray:
        """Return a 2π-normalised phase array."""
        t = self._time_array(frequency, duration)
        return 2.0 * np.pi * frequency * t

    # ------------------------------------------------------------------
    # Waveforms
    # ------------------------------------------------------------------

    def sine(self, frequency: float, duration: float, amplitude: float = 1.0) -> np.ndarray:
        """Pure sine wave."""
        return amplitude * np.sin(self._phase(frequency, duration))

    def square(
        self,
        frequency: float,
        duration: float,
        amplitude: float = 1.0,
        duty_cycle: float = 0.5,
    ) -> np.ndarray:
        """Square wave with variable *duty_cycle* (0–1).

        Prefer :meth:`bl_square` for pitched instruments to avoid aliasing.
        """
        from scipy.signal import square as scipy_square  # type: ignore[import]

        phase = self._phase(frequency, duration)
        return amplitude * scipy_square(phase, duty=duty_cycle)

    def sawtooth(
        self,
        frequency: float,
        duration: float,
        amplitude: float = 1.0,
        rising: bool = True,
    ) -> np.ndarray:
        """Sawtooth wave.  *rising=True* → ramp-up, *rising=False* → ramp-down.

        Prefer :meth:`bl_sawtooth` for pitched instruments to avoid aliasing.
        """
        from scipy.signal import sawtooth as scipy_saw  # type: ignore[import]

        phase = self._phase(frequency, duration)
        width = 1.0 if rising else 0.0
        return amplitude * scipy_saw(phase, width=width)

    def triangle(self, frequency: float, duration: float, amplitude: float = 1.0) -> np.ndarray:
        """Triangle wave (symmetric sawtooth).

        Prefer :meth:`bl_triangle` for pitched instruments to avoid aliasing.
        """
        from scipy.signal import sawtooth as scipy_saw  # type: ignore[import]

        phase = self._phase(frequency, duration)
        return amplitude * scipy_saw(phase, width=0.5)

    def noise(self, duration: float, amplitude: float = 1.0, seed: int | None = None) -> np.ndarray:
        """White noise."""
        rng = np.random.default_rng(seed)
        num_samples = int(self.sample_rate * duration)
        return amplitude * (rng.random(num_samples) * 2.0 - 1.0)

    def pulse(
        self,
        frequency: float,
        duration: float,
        amplitude: float = 1.0,
        pulse_width: float = 0.25,
    ) -> np.ndarray:
        """Pulse wave – alias for square with variable duty cycle."""
        return self.square(frequency, duration, amplitude, duty_cycle=pulse_width)

    # ------------------------------------------------------------------
    # Band-limited waveforms (alias-free pitched oscillators)
    # ------------------------------------------------------------------

    def bl_sawtooth(
        self,
        frequency: float,
        duration: float,
        amplitude: float = 1.0,
        rising: bool = True,
    ) -> np.ndarray:
        """Band-limited sawtooth via additive synthesis.

        Sums sine harmonics up to the Nyquist limit, so no aliasing folds back
        into the audible spectrum.  Results in a warm, smooth tone compared to
        the raw scipy sawtooth.

        The Gibbs ringing is attenuated using a Lanczos sigma factor.
        Uses fully-vectorised NumPy operations for CPU efficiency.
        """
        frequency = max(frequency, 1.0)
        nyquist = self.sample_rate / 2.0
        n_harmonics = min(int(nyquist / frequency), _BL_MAX_HARMONICS)
        n_harmonics = max(n_harmonics, 1)
        n_samples = max(1, int(self.sample_rate * duration))
        t = np.arange(n_samples, dtype=np.float64) / self.sample_rate
        N = float(n_harmonics)
        k = np.arange(1, n_harmonics + 1, dtype=np.float64)[:, None]
        sigma = np.sinc(k / (N + 1.0))
        coeff = ((-1.0) ** (k + 1) / k) * sigma
        if not rising:
            coeff = -coeff
        phases = 2.0 * np.pi * k * frequency * t[None, :]
        out = np.sum(coeff * np.sin(phases), axis=0)
        out *= 2.0 / np.pi
        peak = np.max(np.abs(out))
        if peak > 1e-9:
            out /= peak
        return (amplitude * out).astype(np.float32)

    def bl_square(
        self,
        frequency: float,
        duration: float,
        amplitude: float = 1.0,
        duty_cycle: float = 0.5,
    ) -> np.ndarray:
        """Band-limited square / pulse wave via additive synthesis.

        Only odd harmonics are included (up to Nyquist).  Lanczos sigma
        correction suppresses ringing at the waveform edges.
        Uses fully-vectorised NumPy operations for CPU efficiency.
        """
        frequency = max(frequency, 1.0)
        nyquist = self.sample_rate / 2.0
        n_harmonics = min(int(nyquist / frequency), _BL_MAX_HARMONICS)
        n_harmonics = max(n_harmonics, 1)
        n_samples = max(1, int(self.sample_rate * duration))
        t = np.arange(n_samples, dtype=np.float64) / self.sample_rate
        N = float(n_harmonics)
        phase_shift = 2.0 * np.pi * duty_cycle
        k = np.arange(1, n_harmonics + 1, dtype=np.float64)[:, None]
        sigma = np.sinc(k / (N + 1.0))
        coeff = (2.0 / (np.pi * k)) * sigma * np.sin(k * phase_shift / 2.0)
        phases = 2.0 * np.pi * k * frequency * t[None, :]
        out = np.sum(coeff * np.sin(phases), axis=0)
        peak = np.max(np.abs(out))
        if peak > 1e-9:
            out /= peak
        return (amplitude * out).astype(np.float32)

    def bl_triangle(
        self,
        frequency: float,
        duration: float,
        amplitude: float = 1.0,
    ) -> np.ndarray:
        """Band-limited triangle wave via additive synthesis.

        Triangle waves have rapidly decaying harmonics (1/k²) so they're
        naturally much softer than sawtooth.
        Uses fully-vectorised NumPy operations for CPU efficiency.
        """
        frequency = max(frequency, 1.0)
        nyquist = self.sample_rate / 2.0
        max_n = min(int(nyquist / frequency), _BL_MAX_HARMONICS)
        n_samples = max(1, int(self.sample_rate * duration))
        t = np.arange(n_samples, dtype=np.float64) / self.sample_rate
        odd_k = np.arange(1, 2 * max_n + 1, 2, dtype=np.float64)
        odd_k = odd_k[odd_k * frequency < nyquist]
        if len(odd_k) == 0:
            odd_k = np.array([1.0])
        idx = np.arange(len(odd_k), dtype=np.float64)
        signs = (-1.0) ** idx
        coeffs = (signs / (odd_k ** 2))[:, None]
        phases = 2.0 * np.pi * odd_k[:, None] * frequency * t[None, :]
        out = np.sum(coeffs * np.sin(phases), axis=0)
        out *= 8.0 / np.pi ** 2
        peak = np.max(np.abs(out))
        if peak > 1e-9:
            out /= peak
        return (amplitude * out).astype(np.float32)

    # ------------------------------------------------------------------
    # Additive synthesis helper
    # ------------------------------------------------------------------

    def additive(
        self,
        frequency: float,
        duration: float,
        harmonics: list[tuple[int, float]],
        amplitude: float = 1.0,
    ) -> np.ndarray:
        """Additive synthesis from a list of (harmonic_number, relative_amplitude) pairs.

        Only harmonics below the Nyquist frequency are included, preventing
        aliasing when high harmonic numbers are requested.

        Example
        -------
        >>> osc.additive(440.0, 1.0, [(1, 1.0), (2, 0.5), (3, 0.25)])
        """
        nyquist = self.sample_rate / 2.0
        n_samples = max(1, int(self.sample_rate * duration))
        t = np.arange(n_samples, dtype=np.float64) / self.sample_rate
        result = np.zeros(n_samples, dtype=np.float64)
        for harmonic, rel_amp in harmonics:
            f_h = frequency * harmonic
            if f_h >= nyquist:
                continue
            result += rel_amp * np.sin(2.0 * np.pi * f_h * t)
        max_amp = np.max(np.abs(result))
        if max_amp > 0:
            result = result / max_amp
        return (amplitude * result).astype(np.float32)

    # ------------------------------------------------------------------
    # Frequency modulation
    # ------------------------------------------------------------------

    def fm(
        self,
        carrier_freq: float,
        modulator_freq: float,
        duration: float,
        modulation_index: float = 2.0,
        amplitude: float = 1.0,
    ) -> np.ndarray:
        """Frequency-modulation synthesis (Yamaha DX-style).

        Parameters
        ----------
        carrier_freq:
            Base pitch of the sound.
        modulator_freq:
            Frequency of the modulating oscillator.
        modulation_index:
            Depth of frequency deviation (higher → more complex timbre).
        """
        t = self._time_array(carrier_freq, duration)
        modulator = modulation_index * np.sin(2.0 * np.pi * modulator_freq * t)
        carrier = amplitude * np.sin(2.0 * np.pi * carrier_freq * t + modulator)
        return carrier
