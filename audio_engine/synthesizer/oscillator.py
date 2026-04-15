"""
Oscillator – waveform generators.

Provides sine, square, sawtooth, triangle, and noise waveforms that are the
building-blocks of every synthesised sound in the engine.
"""

from __future__ import annotations

import numpy as np

__all__ = ["Oscillator"]


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
        """Square wave with variable *duty_cycle* (0–1)."""
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
        """Sawtooth wave.  *rising=True* → ramp-up, *rising=False* → ramp-down."""
        from scipy.signal import sawtooth as scipy_saw  # type: ignore[import]

        phase = self._phase(frequency, duration)
        width = 1.0 if rising else 0.0
        return amplitude * scipy_saw(phase, width=width)

    def triangle(self, frequency: float, duration: float, amplitude: float = 1.0) -> np.ndarray:
        """Triangle wave (symmetric sawtooth)."""
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

        Example
        -------
        >>> osc.additive(440.0, 1.0, [(1, 1.0), (2, 0.5), (3, 0.25)])
        """
        result = np.zeros(int(self.sample_rate * duration))
        for harmonic, rel_amp in harmonics:
            result = result + rel_amp * np.sin(self._phase(frequency * harmonic, duration))
        # Normalise
        max_amp = np.max(np.abs(result))
        if max_amp > 0:
            result = result / max_amp
        return amplitude * result

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
