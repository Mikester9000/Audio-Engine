"""
AudioExporter – write rendered audio arrays to disk.

Supported output formats
------------------------
``wav``  (built-in, no extra dependencies)
    Uncompressed PCM – highest quality, largest files.
    Compatible with all game engines.

``ogg``  (requires the ``soundfile`` extra)
    Vorbis-compressed – smaller files, still lossless quality at high
    bitrates.  Supported by Godot, Unity, Unreal.

The export module always writes 16-bit signed PCM for WAV (or 32-bit float
when ``bit_depth=32`` is requested) and accepts mono or stereo input.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path
from typing import Literal

import numpy as np

__all__ = ["AudioExporter"]

BitDepth = Literal[16, 32]


class AudioExporter:
    """Export NumPy audio arrays to game-engine–compatible files.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    bit_depth:
        Output bit depth: 16 (default) or 32.
    """

    def __init__(self, sample_rate: int = 44100, bit_depth: BitDepth = 16) -> None:
        if bit_depth not in (16, 32):
            raise ValueError("bit_depth must be 16 or 32")
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(
        self,
        audio: np.ndarray,
        path: str | Path,
        fmt: Literal["wav", "ogg"] = "wav",
    ) -> Path:
        """Write *audio* to *path* in the requested format.

        Parameters
        ----------
        audio:
            Float32 NumPy array, either 1-D (mono) or shape ``(N, 2)`` (stereo).
        path:
            Output file path.  The file extension is overridden if it does not
            match *fmt*.
        fmt:
            Output format: ``"wav"`` (default) or ``"ogg"``.

        Returns
        -------
        Path
            Resolved path of the written file.
        """
        path = Path(path).with_suffix(f".{fmt}")
        path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure mono/stereo float32 in range [-1, 1]
        audio = self._validate(audio)

        if fmt == "wav":
            return self._write_wav(audio, path)
        elif fmt == "ogg":
            return self._write_ogg(audio, path)
        else:  # pragma: no cover
            raise ValueError(f"Unsupported format '{fmt}'")

    # ------------------------------------------------------------------
    # Format writers
    # ------------------------------------------------------------------

    def _write_wav(self, audio: np.ndarray, path: Path) -> Path:
        """Write a standard WAV file using the stdlib ``wave`` module."""
        mono = audio.ndim == 1
        n_channels = 1 if mono else 2
        samples = audio if mono else audio.flatten()

        if self.bit_depth == 16:
            pcm = (samples * 32767.0).clip(-32768, 32767).astype(np.int16)
            sampwidth = 2
        else:
            # 32-bit float PCM (IEEE 754) – not strictly supported by stdlib
            # wave module, so we write a raw RIFF file manually.
            return self._write_wav_float32(audio, path, n_channels)

        with wave.open(str(path), "w") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm.tobytes())

        return path

    def _write_wav_float32(self, audio: np.ndarray, path: Path, n_channels: int) -> Path:
        """Write a 32-bit float RIFF WAV file manually (IEEE format)."""
        samples = audio if audio.ndim == 1 else audio.flatten()
        pcm = samples.astype(np.float32)
        data_bytes = pcm.tobytes()
        num_frames = len(pcm) // n_channels

        # RIFF header fields
        block_align = n_channels * 4   # 4 bytes per float32 sample
        byte_rate = self.sample_rate * block_align

        with open(path, "wb") as f:
            # RIFF chunk
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(data_bytes)))
            f.write(b"WAVE")
            # fmt  sub-chunk (IEEE float = type 3)
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))          # sub-chunk size
            f.write(struct.pack("<H", 3))            # audio format: IEEE float
            f.write(struct.pack("<H", n_channels))
            f.write(struct.pack("<I", self.sample_rate))
            f.write(struct.pack("<I", byte_rate))
            f.write(struct.pack("<H", block_align))
            f.write(struct.pack("<H", 32))           # bits per sample
            # data sub-chunk
            f.write(b"data")
            f.write(struct.pack("<I", len(data_bytes)))
            f.write(data_bytes)

        return path

    def _write_ogg(self, audio: np.ndarray, path: Path) -> Path:
        """Write an OGG Vorbis file using soundfile (optional dependency)."""
        try:
            import soundfile as sf  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "The 'soundfile' package is required for OGG export.  "
                "Install it with:  pip install audio-engine[ogg]"
            ) from exc

        subtype = "VORBIS"
        sf.write(str(path), audio, self.sample_rate, subtype=subtype)
        return path

    # ------------------------------------------------------------------
    # Metadata / loop-point helpers (game engine integration)
    # ------------------------------------------------------------------

    def write_loop_points(
        self,
        path: str | Path,
        loop_start: int,
        loop_end: int,
    ) -> None:
        """Embed ``smpl`` loop-point chunk into an existing WAV file.

        Most game engines (Godot, Unity, GameMaker) read the ``smpl`` chunk
        to set up seamless audio looping.

        Parameters
        ----------
        path:
            Path to an existing WAV file.
        loop_start:
            Loop start in samples.
        loop_end:
            Loop end in samples (inclusive).
        """
        path = Path(path)
        data = path.read_bytes()

        # Build smpl chunk
        manufacturer = product = sample_period = midi_unity_note = 0
        midi_pitch_fraction = smpte_format = smpte_offset = 0
        num_loops = 1
        sampler_data = 0
        cue_point_id = play_type = fraction = play_count = 0

        loop_chunk = struct.pack(
            "<IIIIIIIIi",
            manufacturer, product, sample_period,
            midi_unity_note, midi_pitch_fraction,
            smpte_format, smpte_offset,
            num_loops, sampler_data,
        )
        loop_chunk += struct.pack(
            "<IIIIii",
            cue_point_id, play_type,
            loop_start, loop_end,
            fraction, play_count,
        )

        smpl_chunk = b"smpl" + struct.pack("<I", len(loop_chunk)) + loop_chunk

        # Inject before "data" chunk and update RIFF size
        data_pos = data.find(b"data")
        new_data = data[:data_pos] + smpl_chunk + data[data_pos:]
        # Update RIFF chunk size (bytes 4–8)
        riff_size = struct.pack("<I", len(new_data) - 8)
        new_data = new_data[:4] + riff_size + new_data[8:]
        path.write_bytes(new_data)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(audio: np.ndarray) -> np.ndarray:
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim not in (1, 2):
            raise ValueError(f"audio must be 1-D or 2-D, got shape {audio.shape}")
        if audio.ndim == 2 and audio.shape[1] != 2:
            raise ValueError(f"Stereo audio must have shape (N, 2), got {audio.shape}")
        # Clip to [-1, 1] to prevent clipping artefacts
        return np.clip(audio, -1.0, 1.0)
