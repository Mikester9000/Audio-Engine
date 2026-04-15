"""
StemRenderer – export individual tracks from a Sequencer as separate files.

Stems are individual instrument/bus channels rendered in isolation.  Stem
exports are used for:
- Adaptive/interactive audio (muting individual layers at runtime)
- Post-production remix / re-edit workflows
- DAW import for further human editing

Usage
-----
>>> from audio_engine.render import StemRenderer
>>> from audio_engine.ai import MusicGenerator
>>> generator = MusicGenerator(sample_rate=44100)
>>> seq = generator.generate("battle", bars=8)
>>> renderer = StemRenderer(output_dir="stems/", sample_rate=44100)
>>> renderer.render_stems(seq)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np

from audio_engine.export.audio_exporter import AudioExporter

__all__ = ["StemRenderer"]


class StemRenderer:
    """Render multi-track :class:`~audio_engine.composer.Sequencer` stems to disk.

    Parameters
    ----------
    output_dir:
        Directory where stem files will be written.
    sample_rate:
        Audio sample rate in Hz.
    bit_depth:
        Output bit depth: 16 or 32.
    fmt:
        Output format: ``"wav"`` or ``"ogg"``.

    Example
    -------
    >>> renderer = StemRenderer("stems/", sample_rate=44100)
    >>> renderer.render_stems(sequencer)
    """

    def __init__(
        self,
        output_dir: str | Path = "stems",
        sample_rate: int = 44100,
        bit_depth: Literal[16, 32] = 16,
        fmt: Literal["wav", "ogg"] = "wav",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.fmt = fmt
        self._exporter = AudioExporter(sample_rate=sample_rate, bit_depth=bit_depth)

    def render_stems(
        self,
        sequencer,  # type: Sequencer – avoid circular import
        prefix: str = "",
        normalise_stems: bool = True,
    ) -> dict[str, Path]:
        """Render each track in *sequencer* to a separate file.

        Parameters
        ----------
        sequencer:
            A :class:`~audio_engine.composer.Sequencer` instance populated
            with notes.
        prefix:
            Optional filename prefix (e.g. the track name / style).
        normalise_stems:
            If ``True``, each stem is normalised to -3 dBFS independently.

        Returns
        -------
        dict[str, Path]
            Mapping from track name to the written file path.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_paths: dict[str, Path] = {}

        for track_name, track in sequencer._tracks.items():
            # Create a temporary single-track sequencer copy
            import copy
            single = copy.deepcopy(sequencer)
            # Remove all other tracks
            to_remove = [k for k in single._tracks if k != track_name]
            for k in to_remove:
                del single._tracks[k]

            stem_audio = single.render()

            if normalise_stems:
                peak = np.max(np.abs(stem_audio))
                if peak > 1e-9:
                    stem_audio = (stem_audio / peak * 0.707).astype(np.float32)

            safe_name = track_name.replace(" ", "_").replace("/", "_")
            filename = f"{prefix}{safe_name}.{self.fmt}" if prefix else f"{safe_name}.{self.fmt}"
            file_path = self.output_dir / filename

            self._exporter.export(stem_audio, file_path, fmt=self.fmt)
            out_paths[track_name] = file_path

        return out_paths

    def render_mix(
        self,
        sequencer,
        filename: str = "mix",
        normalise: bool = True,
    ) -> Path:
        """Render the full mix (all tracks) to a single file.

        Parameters
        ----------
        sequencer:
            Populated :class:`~audio_engine.composer.Sequencer`.
        filename:
            Output filename without extension.
        normalise:
            If ``True``, normalise to -0.3 dBFS.

        Returns
        -------
        Path
            Written file path.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        mix = sequencer.render()

        if normalise:
            peak = np.max(np.abs(mix))
            if peak > 1e-9:
                target = 10.0 ** (-0.3 / 20.0)
                mix = (mix / peak * target).astype(np.float32)

        file_path = self.output_dir / f"{filename}.{self.fmt}"
        return self._exporter.export(mix, file_path, fmt=self.fmt)
