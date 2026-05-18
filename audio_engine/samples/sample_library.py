"""
Sample library — load and pitch-shift .wav samples for orchestral remastering.

Drop-in workflow
----------------
1. Create the category subdirectories under the ``samples/`` folder (or any
   directory you specify):

   samples/
   ├── strings/      ← violin, viola, cello, double-bass WAV files
   ├── brass/        ← french horn, trumpet, trombone, tuba WAV files
   ├── choir/        ← vowel-pad WAV files
   ├── piano/        ← piano multi-samples
   ├── flute/        ← flute / woodwind samples
   ├── electric_guitar/ ← electric guitar samples
   ├── percussion/   ← kick, snare, hi-hat, tom WAV files
   └── sfx/          ← sound effect one-shots

2. Name files anything — the library scans all ``.wav`` files recursively
   within each category subdirectory.

3. Use :class:`SampleLibrary` to load and pitch-shift samples at runtime.

Remastering approach
--------------------
:class:`SampleLibrary` is used by :class:`~audio_engine.ai.sample_backend.SampleBackend`
to *blend* procedural output with real recordings.  When samples are present the
mix uses the sample audio as the primary texture and the procedural signal as a
harmonic pad underneath.  When no samples exist the pipeline silently falls back
to pure procedural synthesis.

Pitch shifting
--------------
Samples are pitch-shifted via ratio-based resampling (``scipy.signal.resample``
when available, otherwise numpy interpolation).  This is the same
technique used by tracker software and early samplers — appropriate for the
PS1/PS2 aesthetic where pitch shifting was done in hardware via playback rate.
"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

__all__ = ["SampleLibrary"]

# ---------------------------------------------------------------------------
# Known category folder names and the instrument/role they map to.
# A user can add any sub-directory; these are the ones the engine will look
# for when a specific category is requested.
# ---------------------------------------------------------------------------

_KNOWN_CATEGORIES: List[str] = [
    "strings",
    "brass",
    "choir",
    "piano",
    "flute",
    "electric_guitar",
    "percussion",
    "sfx",
    "orchestral_hit",
    "crystal_synth",
    "bass",
    "ff7_lead",
    "ff7_strings",
    "ff7_bass",
    "ff7_electric_guitar",
    "harpsichord",
    "synth_pad",
    "voice",
]


def _load_wav(path: Path) -> Tuple[np.ndarray, int]:
    """Load a WAV file as a float32 mono array and return (audio, sample_rate).

    Multi-channel files are averaged to mono.
    """
    with wave.open(str(path), "r") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(sampwidth, np.int16)
    scale = {1: 128.0, 2: 32768.0, 4: 2147483648.0}.get(sampwidth, 32768.0)
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float32) / scale

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    return samples, sr


def _resample(audio: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """Resample *audio* from *src_sr* to *dst_sr*."""
    if src_sr == dst_sr:
        return audio
    try:
        from scipy.signal import resample_poly  # type: ignore[import]
        from math import gcd
        g = gcd(dst_sr, src_sr)
        up = dst_sr // g
        down = src_sr // g
        return resample_poly(audio, up, down).astype(np.float32)
    except ImportError:
        ratio = dst_sr / src_sr
        new_len = max(1, int(len(audio) * ratio))
        return np.interp(
            np.linspace(0, len(audio) - 1, new_len),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)


def _pitch_shift_ratio(audio: np.ndarray, ratio: float, sr: int) -> np.ndarray:
    """Pitch-shift by resampling at a different rate then trimming/padding.

    *ratio* > 1.0 pitches up; < 1.0 pitches down.
    This is the tracker/hardware-sampler approach: play the sample back at a
    different speed.  The output has the same number of samples as the input.
    """
    if abs(ratio - 1.0) < 1e-6:
        return audio
    n = len(audio)
    new_len = max(1, int(n / ratio))
    # Resample to target length
    try:
        from scipy.signal import resample  # type: ignore[import]
        shifted = resample(audio.astype(np.float64), new_len).astype(np.float32)
    except ImportError:
        shifted = np.interp(
            np.linspace(0, n - 1, new_len),
            np.arange(n),
            audio,
        ).astype(np.float32)

    # Trim or zero-pad to original length
    if len(shifted) >= n:
        return shifted[:n]
    pad = np.zeros(n - len(shifted), dtype=np.float32)
    return np.concatenate([shifted, pad])


class SampleLibrary:
    """Scan a root directory for .wav samples organised by category.

    Parameters
    ----------
    root:
        Root directory to scan.  Typically the ``samples/`` folder in the
        project, but any directory works.
    sample_rate:
        Engine sample rate.  Samples are resampled to this rate on load.

    Example
    -------
    >>> lib = SampleLibrary("samples/", sample_rate=44100)
    >>> audio = lib.get_sample("strings", pitch_ratio=1.0)
    """

    def __init__(self, root: str | Path, sample_rate: int = 44100) -> None:
        self.root = Path(root)
        self.sample_rate = sample_rate
        # category → list of (path, audio)
        self._cache: Dict[str, List[np.ndarray]] = {}
        self._scan()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _scan(self) -> None:
        """Scan root for .wav files and cache them by category."""
        if not self.root.exists():
            return

        for item in self.root.iterdir():
            if item.is_dir():
                category = item.name
                wavs = sorted(item.rglob("*.wav")) + sorted(item.rglob("*.WAV"))
                if wavs:
                    self._cache[category] = []
                    for wav in wavs:
                        try:
                            audio, sr = _load_wav(wav)
                            if sr != self.sample_rate:
                                audio = _resample(audio, sr, self.sample_rate)
                            self._cache[category].append(audio)
                        except Exception:
                            pass  # skip unreadable files
            elif item.suffix.lower() == ".wav":
                # Flat files go into a special "root" category
                category = "root"
                try:
                    audio, sr = _load_wav(item)
                    if sr != self.sample_rate:
                        audio = _resample(audio, sr, self.sample_rate)
                    self._cache.setdefault(category, []).append(audio)
                except Exception:
                    pass

    def available_categories(self) -> list[str]:
        """Return sorted list of categories with at least one loaded sample."""
        return sorted(self._cache)

    def has_category(self, category: str) -> bool:
        """Return ``True`` if *category* has at least one loaded sample."""
        return category in self._cache and len(self._cache[category]) > 0

    # ------------------------------------------------------------------
    # Sample access
    # ------------------------------------------------------------------

    def get_sample(
        self,
        category: str,
        pitch_ratio: float = 1.0,
        duration: float | None = None,
        index: int = 0,
        rng: Optional[np.random.Generator] = None,
    ) -> Optional[np.ndarray]:
        """Return a pitch-shifted sample from *category*, or ``None`` if unavailable.

        Parameters
        ----------
        category:
            Category name (e.g. ``"strings"``, ``"brass"``).
        pitch_ratio:
            Pitch-shift ratio (2.0 = one octave up, 0.5 = one octave down).
        duration:
            If set, trim or loop the sample to this length in seconds.
        index:
            Which sample to pick within the category (wraps around).
        rng:
            Optional RNG for random sample selection (overrides *index*).

        Returns
        -------
        np.ndarray or None
        """
        samples = self._cache.get(category)
        if not samples:
            return None

        if rng is not None:
            idx = int(rng.integers(0, len(samples)))
        else:
            idx = index % len(samples)

        audio = samples[idx].copy()

        if abs(pitch_ratio - 1.0) > 1e-6:
            audio = _pitch_shift_ratio(audio, pitch_ratio, self.sample_rate)

        if duration is not None:
            target_n = int(duration * self.sample_rate)
            if len(audio) < target_n:
                # Loop
                reps = target_n // len(audio) + 1
                audio = np.tile(audio, reps)
            audio = audio[:target_n]

        return audio.astype(np.float32)

    def blend(
        self,
        procedural: np.ndarray,
        category: str,
        pitch_ratio: float = 1.0,
        sample_weight: float = 0.65,
        duration: float | None = None,
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        """Blend a procedural signal with a real sample from *category*.

        Parameters
        ----------
        procedural:
            Procedural synthesis output (mono float32).
        category:
            Sample category to blend in.
        pitch_ratio:
            Pitch ratio for the sample.
        sample_weight:
            Weight of the sample in the mix (0 = all procedural, 1 = all
            sample).  Default 0.65 gives a noticeably richer, more organic
            sound while preserving the procedural harmonic structure.
        duration:
            If set, target the blend duration in seconds.
        rng:
            Optional RNG for sample selection.

        Returns
        -------
        np.ndarray
            Mono float32 blend, same length as *procedural*.
        """
        n = len(procedural)
        dur = duration or n / self.sample_rate
        sample_audio = self.get_sample(category, pitch_ratio=pitch_ratio, duration=dur, rng=rng)

        if sample_audio is None:
            return procedural

        # Align lengths
        if len(sample_audio) > n:
            sample_audio = sample_audio[:n]
        elif len(sample_audio) < n:
            pad = np.zeros(n - len(sample_audio), dtype=np.float32)
            sample_audio = np.concatenate([sample_audio, pad])

        mixed = sample_weight * sample_audio + (1.0 - sample_weight) * procedural
        # Normalise
        peak = np.max(np.abs(mixed))
        if peak > 1e-9:
            mixed = mixed / peak
        return mixed.astype(np.float32)

    def remaster(
        self,
        audio: np.ndarray,
        category_map: dict[str, float],
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        """Remaster a stereo or mono signal by blending in multiple sample categories.

        Parameters
        ----------
        audio:
            Input audio ``(N,)`` mono or ``(N, 2)`` stereo.
        category_map:
            Mapping of category name → blend weight (0–1).  Categories without
            loaded samples are silently skipped.
        rng:
            Optional RNG.

        Returns
        -------
        np.ndarray
            Remastered audio, same shape as *audio*.
        """
        stereo = audio.ndim == 2
        if stereo:
            mono = audio.mean(axis=1)
        else:
            mono = audio.astype(np.float32)

        result = mono.copy()
        n = len(mono)
        dur = n / self.sample_rate

        for category, weight in category_map.items():
            if not self.has_category(category):
                continue
            blended = self.blend(result, category, sample_weight=weight, duration=dur, rng=rng)
            result = blended

        if stereo:
            # Spread the mono remastered result back to stereo with slight pan spread
            left  = result * 0.9
            right = result * 0.9
            return np.stack([left, right], axis=1).astype(np.float32)
        return result
