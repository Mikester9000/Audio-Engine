"""
Radio/Playlist generator — FF15-style radio that can play any style.

Generates a sequenced playlist of full musical pieces, each individually
exported as a WAV (or OGG) file, with optional metadata JSON.

Workflow
--------
1. Pick a set of style keys (or use a preset playlist like ``"ff7_album"``
   or ``"ff_radio"``).
2. For each track, call the :class:`PieceComposer` to generate a full
   structured piece (intro → verse → chorus → bridge → outro).
3. Export each piece to a numbered file (e.g. ``01-ff7-battle.wav``).
4. Write a ``playlist.json`` manifest with track metadata.

Presets
-------
``"ff_radio"``       — One track from every FF game (FF1–FF16), radio mix.
``"ff7_album"``      — All FF7 styles in album order.
``"ff8_album"``      — All FF8 styles including Eyes on Me vocal.
``"battle_mix"``     — All battle themes across the series.
``"emotional_mix"``  — All slow / emotional / ballad tracks.
``"boss_mix"``       — Boss / final boss themes.
``"overworld_mix"``  — Overworld / travel themes.
``"vocal_album"``    — All tracks that feature vocal melodies.
``"modern_ff"``      — FF13–FF16 modern era.
``"classic_ff"``     — FF1–FF9 classic era.

Usage
-----
>>> from audio_engine.ai.radio_playlist import RadioPlaylistGenerator
>>> gen = RadioPlaylistGenerator(sample_rate=44100, seed=0)
>>> gen.generate_playlist("ff_radio", output_dir="output/radio", track_duration=60.0)
Generating ff_radio playlist (27 tracks)…
  [1/27] Prelude (ff-prelude) …
  …
  Done. Playlist saved to output/radio/playlist.json

CLI
---
    audio-engine generate-radio-playlist \\
        --preset ff_radio \\
        --track-duration 60 \\
        --output-dir output/radio \\
        --format wav
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np

from audio_engine.ai.music_library import FF_RADIO_CATALOG, MusicLibrary, TrackEntry

__all__ = ["RadioPlaylistGenerator", "PLAYLIST_PRESETS"]


# ---------------------------------------------------------------------------
# Playlist presets
# ---------------------------------------------------------------------------

PlaylistPreset = Literal[
    "ff_radio", "ff7_album", "ff8_album",
    "battle_mix", "emotional_mix", "boss_mix",
    "overworld_mix", "vocal_album", "modern_ff", "classic_ff",
]

PLAYLIST_PRESETS: dict[str, list[str]] = {
    "ff_radio": [
        "prelude", "ff1_overworld", "ff4_theme", "ff6_opera",
        "ff7_overworld", "ff8_ballad", "ff9_overworld", "ff10_zanarkand",
        "ff12_battle", "ff13_theme", "ff14_overworld", "ff15_road",
        "ff16_theme", "victory",
    ],
    "ff7_album": [
        "prelude", "ff7_overworld", "ff7_town", "ff7_battle",
        "ff7_boss", "ff7_sad", "victory",
    ],
    "ff8_album": [
        "prelude", "ff8_ballad", "ff8_battle", "healing", "victory",
    ],
    "battle_mix": [
        "ff1_battle", "ff4_battle", "ff6_battle", "ff7_battle",
        "ff8_battle", "ff9_battle", "ff10_battle", "ff12_battle",
        "ff13_battle", "ff14_battle", "ff15_road", "ff16_battle",
        "rock_battle",
    ],
    "emotional_mix": [
        "ff6_sad", "ff7_sad", "ff8_ballad", "ff10_zanarkand",
        "ff10_calm", "ff13_theme", "piano_ballad", "healing",
    ],
    "boss_mix": [
        "ff6_battle", "ff7_boss", "ff10_battle", "ff12_battle",
        "ff14_battle", "ff16_battle", "orchestral_epic",
    ],
    "overworld_mix": [
        "ff1_overworld", "ff9_overworld", "ff7_overworld",
        "ff14_overworld", "ff15_road", "world_map", "celtic_adventure",
    ],
    "vocal_album": [
        "ff6_opera", "ff8_ballad", "ff14_overworld", "ff16_theme",
        "choral_fantasy",
    ],
    "modern_ff": [
        "ff13_battle", "ff13_theme", "ff14_battle", "ff14_overworld",
        "ff15_road", "ff15_radio", "ff16_battle", "ff16_theme",
    ],
    "classic_ff": [
        "ff1_battle", "ff1_overworld", "ff4_battle", "ff4_theme",
        "ff6_battle", "ff6_opera", "ff6_sad", "ff7_battle",
        "ff7_overworld", "ff7_sad", "ff8_ballad", "ff9_overworld",
        "prelude", "victory",
    ],
}

# Default section structure for each track type in a full piece
_PIECE_SECTIONS: dict[str, list[str]] = {
    "battle":   ["intro", "verse", "chorus", "verse", "chorus", "outro"],
    "boss":     ["intro", "verse", "chorus", "bridge", "chorus", "outro"],
    "overworld":["intro", "verse", "chorus", "bridge", "chorus", "outro"],
    "theme":    ["intro", "verse", "pre_chorus", "chorus", "bridge", "chorus", "outro"],
    "ballad":   ["intro", "verse", "pre_chorus", "chorus", "verse", "chorus", "bridge", "outro"],
    "opera":    ["intro", "verse", "pre_chorus", "chorus", "bridge", "chorus", "outro"],
    "ambient":  ["intro", "verse", "chorus", "outro"],
    "fanfare":  ["intro", "chorus", "outro"],
    "radio":    ["intro", "verse", "chorus", "bridge", "chorus", "outro"],
}


class RadioPlaylistGenerator:
    """Generate a full playlist of exported audio pieces.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    seed:
        RNG seed for reproducibility.
    backend:
        Generation backend (``"synth_orchestral"`` | ``"ps1"`` | ``"procedural"``).
    vocal_preset:
        Voice preset for VocalMelodySynth.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        seed: int | None = None,
        backend: str = "synth_orchestral",
        vocal_preset: str = "soprano",
    ) -> None:
        self.sample_rate = sample_rate
        self._seed = seed
        self._backend = backend
        self._vocal_preset = vocal_preset
        self._lib = MusicLibrary()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_playlist(
        self,
        preset_or_styles: PlaylistPreset | list[str],
        output_dir: str | Path = "output/radio",
        track_duration: float = 60.0,
        fmt: str = "wav",
        with_vocals: bool | None = None,
        force: bool = False,
        quiet: bool = False,
        progress_callback=None,
    ) -> dict:
        """Generate a full playlist of audio files.

        Parameters
        ----------
        preset_or_styles:
            Preset name string (e.g. ``"ff_radio"``) or explicit list of
            style keys.
        output_dir:
            Directory to write audio files and ``playlist.json`` into.
        track_duration:
            Target duration per track in seconds.
        fmt:
            Output format: ``"wav"`` or ``"ogg"``.
        with_vocals:
            ``True`` forces vocal overlay on all tracks; ``False`` disables
            it; ``None`` (default) enables it only on tracks flagged
            ``with_vocals=True`` in the catalog.
        force:
            Re-generate even if the output file already exists.
        quiet:
            Suppress progress output.
        progress_callback:
            Optional ``(message: str) -> None`` callback for progress.

        Returns
        -------
        dict
            Playlist manifest (also written to ``<output_dir>/playlist.json``).
        """
        if isinstance(preset_or_styles, str):
            style_keys = PLAYLIST_PRESETS.get(preset_or_styles, [preset_or_styles])
            preset_name = preset_or_styles
        else:
            style_keys = list(preset_or_styles)
            preset_name = "custom"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        def _log(msg: str) -> None:
            if not quiet:
                print(msg, flush=True)
            if progress_callback:
                progress_callback(msg)

        _log(f"Generating '{preset_name}' playlist ({len(style_keys)} tracks) → {output_dir}")

        tracks = []
        for i, style_key in enumerate(style_keys, start=1):
            entry = self._lib.get(style_key)
            display = entry.display_name if entry else style_key
            fname = f"{i:02d}-{(entry.export_filename if entry else style_key)}.{fmt}"
            out_path = output_dir / fname

            _log(f"  [{i}/{len(style_keys)}] {display} ({style_key}) …")

            if out_path.exists() and not force:
                _log(f"    → Skipping (already exists): {fname}")
                track_record = self._make_track_record(i, entry, style_key, fname, track_duration, skipped=True)
            else:
                try:
                    audio = self._compose_track(
                        style_key=style_key,
                        entry=entry,
                        duration=track_duration,
                        with_vocals=with_vocals,
                        quiet=quiet,
                    )
                    actual_duration = audio.shape[0] / self.sample_rate
                    self._export(audio, out_path, fmt)
                    _log(f"    → {fname} ({actual_duration:.1f}s)")
                    track_record = self._make_track_record(
                        i, entry, style_key, fname, actual_duration, skipped=False
                    )
                except Exception as exc:
                    _log(f"    ! Error generating {style_key}: {exc}")
                    track_record = self._make_track_record(
                        i, entry, style_key, fname, 0.0, skipped=False, error=str(exc)
                    )

            tracks.append(track_record)

        manifest = {
            "preset": preset_name,
            "track_count": len(tracks),
            "total_duration_s": sum(t.get("duration_s", 0) for t in tracks),
            "backend": self._backend,
            "sample_rate": self.sample_rate,
            "format": fmt,
            "tracks": tracks,
        }

        manifest_path = output_dir / "playlist.json"
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        _log(f"\nDone. {len(tracks)} tracks. Playlist manifest: {manifest_path}")
        return manifest

    def generate_track(
        self,
        style_key: str,
        output_path: str | Path,
        duration: float = 60.0,
        fmt: str = "wav",
        with_vocals: bool | None = None,
    ) -> Path:
        """Generate and export a single full-piece track.

        Parameters
        ----------
        style_key:
            Any style key from the music library or generator.
        output_path:
            Path for the output audio file.
        duration:
            Target track duration in seconds.
        fmt:
            ``"wav"`` or ``"ogg"``.
        with_vocals:
            Vocal overlay override.  ``None`` uses catalog default.

        Returns
        -------
        Path
            Path to the written audio file.
        """
        entry = self._lib.get(style_key)
        audio = self._compose_track(style_key, entry, duration, with_vocals)
        out_path = Path(output_path)
        self._export(audio, out_path, fmt)
        return out_path

    def available_presets(self) -> list[str]:
        """Return list of built-in playlist preset names."""
        return list(PLAYLIST_PRESETS.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compose_track(
        self,
        style_key: str,
        entry: TrackEntry | None,
        duration: float,
        with_vocals: bool | None,
        quiet: bool = False,
    ) -> np.ndarray:
        """Generate a full structured piece for one track."""
        from audio_engine.ai.piece_composer import PieceComposer, SECTION_TEMPLATES

        track_type = entry.track_type if entry else "theme"
        sections = _PIECE_SECTIONS.get(track_type, _PIECE_SECTIONS["theme"])

        # Validate sections against available templates
        valid = list(SECTION_TEMPLATES.keys())
        sections = [s for s in sections if s in valid]
        if not sections:
            sections = ["intro", "verse", "chorus", "outro"]

        # Decide on vocals
        if with_vocals is None:
            use_vocals = bool(entry and entry.with_vocals)
        else:
            use_vocals = with_vocals

        composer = PieceComposer(
            sample_rate=self.sample_rate,
            seed=self._seed,
            backend=self._backend,
            vocal_preset=self._vocal_preset,
        )

        return composer.compose(
            style=style_key,
            sections=sections,
            with_vocals=use_vocals,
            duration=duration,
            quiet=quiet,
        )

    def _export(self, audio: np.ndarray, path: Path, fmt: str) -> None:
        from audio_engine.export.audio_exporter import AudioExporter
        exporter = AudioExporter(sample_rate=self.sample_rate)
        exporter.export(audio, str(path), fmt=fmt)

    @staticmethod
    def _make_track_record(
        index: int,
        entry: TrackEntry | None,
        style_key: str,
        filename: str,
        duration: float,
        skipped: bool = False,
        error: str | None = None,
    ) -> dict:
        base: dict = {
            "index": index,
            "style_key": style_key,
            "filename": filename,
            "duration_s": round(duration, 2),
            "skipped": skipped,
        }
        if entry:
            base.update({
                "display_name": entry.display_name,
                "game": entry.game,
                "game_full": entry.game_full,
                "track_type": entry.track_type,
                "bpm": entry.bpm_approx,
                "composer": entry.composer,
                "mood": entry.key_mood,
                "with_vocals": entry.with_vocals,
                "tags": entry.tags,
            })
        if error:
            base["error"] = error
        return base
