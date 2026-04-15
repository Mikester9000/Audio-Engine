"""
Convolution reverb using a synthetic impulse response.

Generates a natural-sounding synthetic impulse response (IR) using
filtered exponentially-decaying noise.  The IR length, decay curve, and
pre-delay can be configured to emulate different acoustic spaces:
rooms, halls, plates, and ambiences.

For production use, a real measured IR (WAV file) can be loaded instead
of the synthetic one via :meth:`ConvolutionReverb.load_ir`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt  # type: ignore[import]

__all__ = ["ConvolutionReverb"]


def _build_synthetic_ir(
    sample_rate: int,
    rt60: float,
    room_size: float,
    brightness: float,
    pre_delay_ms: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate a synthetic exponential-decay impulse response.

    Parameters
    ----------
    sample_rate:
        Sample rate in Hz.
    rt60:
        Reverberation time in seconds (time for the tail to decay by 60 dB).
    room_size:
        Relative room size 0–1 (scales the IR length).
    brightness:
        High-frequency content 0 (dark) – 1 (bright).  Controls a high-shelf
        applied to the IR.
    pre_delay_ms:
        Silence gap before the reverb tail begins, in milliseconds.
    rng:
        NumPy random generator for reproducibility.

    Returns
    -------
    np.ndarray
        Mono float64 IR.
    """
    ir_length = max(int(rt60 * sample_rate * (0.5 + 0.5 * room_size)), 128)
    pre_delay_samples = int(pre_delay_ms * sample_rate / 1000.0)

    # Exponentially-decaying white noise
    t = np.linspace(0.0, rt60, ir_length)
    decay = np.exp(-6.908 * t / rt60)  # -60 dB at rt60
    noise = rng.standard_normal(ir_length) * decay

    # Tone control – low-pass to control brightness
    cutoff = 800.0 + brightness * 16000.0
    cutoff = np.clip(cutoff, 100.0, sample_rate / 2.0 - 100.0)
    sos = butter(2, cutoff / (sample_rate / 2.0), btype="low", output="sos")
    noise = sosfilt(sos, noise)

    # Normalise
    peak = np.max(np.abs(noise))
    if peak > 1e-9:
        noise /= peak

    # Add pre-delay silence
    if pre_delay_samples > 0:
        noise = np.concatenate([np.zeros(pre_delay_samples), noise])

    return noise.astype(np.float64)


class ConvolutionReverb:
    """Convolution-based room reverb.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    rt60:
        Reverb decay time (seconds from full level to -60 dB).
    room_size:
        0–1 controls IR length; larger = bigger room.
    wet:
        Wet/dry mix (0 = fully dry, 1 = fully wet).
    brightness:
        0 = dark/warm, 1 = bright/airy.
    pre_delay_ms:
        Milliseconds of silence before the reverb tail (emulates distance).
    seed:
        Seed for the synthetic IR noise generator.

    Example
    -------
    >>> reverb = ConvolutionReverb(44100, rt60=2.0, room_size=0.7, wet=0.25)
    >>> output = reverb.process(audio)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        rt60: float = 1.5,
        room_size: float = 0.5,
        wet: float = 0.3,
        brightness: float = 0.5,
        pre_delay_ms: float = 20.0,
        seed: int = 42,
    ) -> None:
        self.sample_rate = sample_rate
        self.wet = np.clip(wet, 0.0, 1.0)
        self._rng = np.random.default_rng(seed)
        self._ir = _build_synthetic_ir(
            sample_rate, rt60, room_size, brightness, pre_delay_ms, self._rng
        )

    def load_ir(self, path: str | Path) -> None:
        """Load a real impulse response from a WAV file.

        Replaces the synthetic IR with a measured room IR for more realistic
        reverberation.  The IR is automatically resampled if the WAV file's
        sample rate differs from the engine sample rate.

        Parameters
        ----------
        path:
            Path to a mono or stereo WAV file containing the impulse response.
        """
        import wave
        import struct

        path = Path(path)
        with wave.open(str(path), "r") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            ir_sr = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        # Decode to float
        dtype = np.int16 if sampwidth == 2 else np.int32
        scale = 32768.0 if sampwidth == 2 else 2147483648.0
        samples = np.frombuffer(raw, dtype=dtype).astype(np.float64) / scale

        # Collapse stereo to mono
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1)

        # Resample if necessary
        if ir_sr != self.sample_rate:
            from audio_engine.dsp.resample import resample as _resample
            samples_f32 = samples.astype(np.float32)
            samples_f32 = _resample(samples_f32, ir_sr, self.sample_rate)
            samples = samples_f32.astype(np.float64)

        # Normalise
        peak = np.max(np.abs(samples))
        if peak > 1e-9:
            samples /= peak

        self._ir = samples

    def process(self, signal: np.ndarray) -> np.ndarray:
        """Apply convolution reverb to *signal*.

        Parameters
        ----------
        signal:
            1-D mono or ``(N, 2)`` stereo float32 array.

        Returns
        -------
        np.ndarray
            Wet/dry blended signal, same shape as input.
        """
        stereo = signal.ndim == 2
        sig = signal.astype(np.float64)

        if stereo:
            left_wet = fftconvolve(sig[:, 0], self._ir, mode="full")[: len(sig)]
            right_wet = fftconvolve(sig[:, 1], self._ir, mode="full")[: len(sig)]
            wet_sig = np.stack([left_wet, right_wet], axis=1)
        else:
            wet_sig = fftconvolve(sig, self._ir, mode="full")[: len(sig)]

        result = self.wet * wet_sig + (1.0 - self.wet) * sig
        return result.astype(np.float32)
