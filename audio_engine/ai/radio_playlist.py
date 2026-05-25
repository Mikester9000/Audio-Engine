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

Presets — Final Fantasy radio / era mixes
-----------------------------------------
``"ff_radio"``       — Cross-era FF radio mix (FF1/4/6–10/12–16 + Prelude/Victory).
``"ff7_album"``      — All FF7 styles in album order.
``"ff8_album"``      — All FF8 styles including Eyes on Me vocal.
``"battle_mix"``     — All battle themes across the series.
``"emotional_mix"``  — All slow / emotional / ballad tracks.
``"boss_mix"``       — Boss / final boss themes.
``"overworld_mix"``  — Overworld / travel themes.
``"vocal_album"``    — All tracks that feature vocal melodies.
``"modern_ff"``      — FF13–FF16 modern era.
``"classic_ff"``     — FF1–FF9 classic era.

Presets — Multi-genre albums with Final Fantasy epicness
---------------------------------------------------------
Each genre album blends its source genre with the orchestral grandeur,
emotional depth, and melodic expressiveness of the Final Fantasy series —
think the intimacy of Tifa's Theme, the sweep of Eyes on Me, the power
of One-Winged Angel, applied across many musical traditions.

``"jazz_album"``         — Jazz from big-band epic to late-night ballads.
``"blues_album"``        — Blues from cinematic epics to slow ballads.
``"pop_album"``          — Pop from anthemic to intimate ballads.
``"rock_album"``         — Rock from orchestral power to acoustic cool-down.
``"electronic_album"``   — Electronic from EDM to synthwave to space ambient.
``"metal_album"``        — Metal from orchestral fury to choral grandeur.
``"world_music_album"``  — World music: Celtic, Latin, ethnic, global.
``"ambient_album"``      — Ambient: nature, space, healing, atmospheric.
``"acoustic_album"``     — Acoustic and piano-led intimate pieces.
``"cinematic_album"``    — Pure cinematic orchestral film-score quality.

Usage
-----
>>> from audio_engine.ai.radio_playlist import RadioPlaylistGenerator
>>> gen = RadioPlaylistGenerator(sample_rate=44100, seed=0)
>>> gen.generate_playlist("ff_radio", output_dir="output/radio", track_duration=60.0)
Generating ff_radio playlist (14 tracks)…
  [1/14] Prelude (ff-prelude) …
  …
  Done. Playlist saved to output/radio/playlist.json

>>> gen.generate_album("jazz", output_dir="output/jazz_album", title="Midnight Jazz")
Generating jazz album (6 tracks) → output/jazz_album
  [1/6] Epic Jazz (jazz_epic) …
  …
  Done. Album manifest: output/jazz_album/album.json

CLI
---
    audio-engine generate-radio-playlist \\
        --preset jazz_album \\
        --track-duration 60 \\
        --output-dir output/jazz_album \\
        --format wav

    audio-engine generate-album \\
        --genre jazz \\
        --title "Midnight Jazz" \\
        --track-duration 60 \\
        --output-dir output/jazz_album
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np

from audio_engine.ai.music_library import FF_RADIO_CATALOG, MusicLibrary, TrackEntry

__all__ = ["RadioPlaylistGenerator", "PLAYLIST_PRESETS", "GENRE_PRESETS"]


# ---------------------------------------------------------------------------
# Playlist presets
# ---------------------------------------------------------------------------

PlaylistPreset = Literal[
    "ff_radio", "ff7_album", "ff8_album",
    "battle_mix", "emotional_mix", "boss_mix",
    "overworld_mix", "vocal_album", "modern_ff", "classic_ff",
    # Multi-genre albums with Final Fantasy epicness
    "jazz_album", "blues_album", "pop_album", "rock_album",
    "electronic_album", "metal_album", "world_music_album",
    "ambient_album", "acoustic_album", "cinematic_album",
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

    # ------------------------------------------------------------------
    # Multi-genre albums — each genre treated with Final Fantasy epicness:
    # sweeping orchestration, emotional melodic depth, cinematic dynamics.
    # ------------------------------------------------------------------

    "jazz_album": [
        "jazz_epic",       # Big-band jazz with orchestral grandeur
        "jazz_ballad",     # Slow emotional jazz ballad (Tifa's Theme feel)
        "jazz_swing",      # Upbeat swing with epic brass
        "jazz_lounge",     # Late-night jazz lounge
        "blues_epic",      # Blues-tinged epic crossover track
        "piano_ballad",    # Solo piano closer
    ],
    "blues_album": [
        "blues_epic",      # Blues with cinematic orchestral weight
        "blues_ballad",    # Slow emotional blues ballad
        "rock_ballad_epic",# Rock-blues ballad crossover
        "jazz_ballad",     # Jazz-blues midnight ballad
        "piano_ballad",    # Intimate piano closer
    ],
    "pop_album": [
        "pop_epic",        # Anthemic pop with orchestral grandeur
        "pop_ballad_epic", # Epic pop ballad (Stand By Me energy)
        "rnb_ballad",      # R&B soul ballad
        "jazz_ballad",     # Jazz-pop crossover
        "acoustic_epic",   # Stripped-back acoustic track
        "choral_fantasy",  # Choral pop closer
    ],
    "rock_album": [
        "rock_epic",       # Orchestral rock (One-Winged Angel energy)
        "rock_ballad_epic",# Epic rock ballad (Noctis's Theme style)
        "blues_epic",      # Blues-rock crossover
        "metal_epic",      # Heavy closer
        "rock_battle",     # Fast rock battle track
        "acoustic_epic",   # Acoustic ballad cool-down
    ],
    "electronic_album": [
        "electronic_epic", # EDM with orchestral depth
        "synthwave_epic",  # Retrowave nostalgic epic
        "electronic_ambient",# Atmospheric chill-out
        "rnb_ballad",      # Electronic R&B crossover
        "ambient_space",   # Space-electronic closer
        "pop_epic",        # Electronic-pop fusion
    ],
    "metal_album": [
        "metal_epic",      # Orchestral metal opener (FF16 grandeur)
        "rock_epic",       # Orchestral rock crossover
        "ff16_battle",     # FF16 metal battle
        "ff6_battle",      # Classic decisive battle
        "rock_battle",     # Modern rock battle
        "choral_fantasy",  # Choral metal closer
    ],
    "world_music_album": [
        "world_epic",      # World music with orchestral treatment
        "latin_epic",      # Latin rhythms with FF grandeur
        "celtic_adventure",# Celtic folk adventure
        "choral_fantasy",  # Sacred choral world music
        "acoustic_epic",   # Acoustic world crossover
        "cinematic_orchestral",# Cinematic world closer
    ],
    "ambient_album": [
        "ambient_nature",  # Nature-inspired ambient
        "ambient_space",   # Space ambient
        "electronic_ambient",# Electronic chill ambient
        "healing",         # FF inn theme / healing ambient
        "choral_fantasy",  # Choral ambient
        "prelude",         # Iconic FF prelude closer
    ],
    "acoustic_album": [
        "acoustic_epic",   # Acoustic with emotional depth
        "piano_ballad",    # Solo piano ballad
        "jazz_ballad",     # Jazz-acoustic crossover
        "blues_ballad",    # Blues acoustic ballad
        "folk_tavern",     # Folk acoustic
        "ff10_zanarkand",  # To Zanarkand — solo piano icon
    ],
    "cinematic_album": [
        "cinematic_orchestral",# Pure cinematic orchestral
        "orchestral_epic", # Hans Zimmer meets Uematsu
        "choral_fantasy",  # Sacred choral cinematic
        "world_epic",      # World cinematic crossover
        "ff7_overworld",   # Nostalgic cinematic overworld
        "ff10_zanarkand",  # Emotional cinematic closer
    ],
}

# ---------------------------------------------------------------------------
# Genre → preset mapping for the generate-album command
# ---------------------------------------------------------------------------

GENRE_PRESETS: dict[str, str] = {
    "jazz":         "jazz_album",
    "blues":        "blues_album",
    "pop":          "pop_album",
    "rock":         "rock_album",
    "electronic":   "electronic_album",
    "edm":          "electronic_album",
    "metal":        "metal_album",
    "world":        "world_music_album",
    "latin":        "world_music_album",
    "ambient":      "ambient_album",
    "acoustic":     "acoustic_album",
    "folk":         "acoustic_album",
    "country":      "acoustic_album",
    "cinematic":    "cinematic_album",
    "orchestral":   "cinematic_album",
    "rnb":          "pop_album",
    "soul":         "pop_album",
    "synthwave":    "electronic_album",
    "retrowave":    "electronic_album",
    "classical":    "cinematic_album",
}

# Default album titles for each genre
_GENRE_TITLES: dict[str, str] = {
    "jazz_album":        "Epic Jazz — A Final Fantasy Jazz Session",
    "blues_album":       "Cinematic Blues — Orchestral Soul",
    "pop_album":         "Epic Pop — Anthems of Eternity",
    "rock_album":        "Orchestral Rock — Power and Grace",
    "electronic_album":  "Epic Electronic — Synthwave Meets Orchestra",
    "metal_album":       "Orchestral Metal — Fury and Majesty",
    "world_music_album": "World Epic — Global Journeys",
    "ambient_album":     "Ambient Visions — Spaces and Silences",
    "acoustic_album":    "Acoustic Echoes — Intimate Epics",
    "cinematic_album":   "Cinematic Orchestral — Grand Compositions",
}
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
        backend_kwargs: dict[str, object] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self._seed = seed
        self._backend = backend
        self._vocal_preset = vocal_preset
        self._backend_kwargs = dict(backend_kwargs or {})
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
            use_vocals = self._resolve_use_vocals(entry=entry, with_vocals=with_vocals)
            instrumental_path = (
                self._instrumental_companion_path(out_path) if use_vocals else None
            )

            _log(f"  [{i}/{len(style_keys)}] {display} ({style_key}) …")

            skip_track = out_path.exists() and not force
            if use_vocals and instrumental_path is not None and not instrumental_path.exists():
                skip_track = False
            if skip_track:
                _log(f"    → Skipping (already exists): {fname}")
                track_record = self._make_track_record(
                    i,
                    entry,
                    style_key,
                    fname,
                    track_duration,
                    skipped=True,
                    rendered_with_vocals=use_vocals,
                    instrumental_filename=instrumental_path.name if instrumental_path is not None else None,
                )
            else:
                try:
                    audio = self._compose_track(
                        style_key=style_key,
                        entry=entry,
                        duration=track_duration,
                        with_vocals=use_vocals,
                        quiet=quiet,
                    )
                    actual_duration = audio.shape[0] / self.sample_rate
                    self._export(audio, out_path, fmt)
                    if use_vocals and instrumental_path is not None:
                        instrumental_audio = self._compose_track(
                            style_key=style_key,
                            entry=entry,
                            duration=track_duration,
                            with_vocals=False,
                            quiet=quiet,
                        )
                        self._export(instrumental_audio, instrumental_path, fmt)
                    _log(f"    → {fname} ({actual_duration:.1f}s)")
                    track_record = self._make_track_record(
                        i,
                        entry,
                        style_key,
                        fname,
                        actual_duration,
                        skipped=False,
                        rendered_with_vocals=use_vocals,
                        instrumental_filename=instrumental_path.name if instrumental_path is not None else None,
                    )
                except Exception as exc:
                    _log(f"    ! Error generating {style_key}: {exc}")
                    track_record = self._make_track_record(
                        i,
                        entry,
                        style_key,
                        fname,
                        0.0,
                        skipped=False,
                        error=str(exc),
                        rendered_with_vocals=use_vocals,
                        instrumental_filename=instrumental_path.name if instrumental_path is not None else None,
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
        use_vocals = self._resolve_use_vocals(entry=entry, with_vocals=with_vocals)
        audio = self._compose_track(style_key, entry, duration, use_vocals)
        out_path = Path(output_path)
        self._export(audio, out_path, fmt)
        if use_vocals:
            instrumental_audio = self._compose_track(style_key, entry, duration, with_vocals=False)
            self._export(
                instrumental_audio,
                self._instrumental_companion_path(out_path),
                fmt,
            )
        return out_path

    def available_presets(self) -> list[str]:
        """Return list of built-in playlist preset names."""
        return list(PLAYLIST_PRESETS.keys())

    def available_genres(self) -> list[str]:
        """Return sorted list of genre names accepted by :meth:`generate_album`."""
        return sorted(GENRE_PRESETS.keys())

    def generate_album(
        self,
        genre: str,
        output_dir: str | Path = "output/album",
        title: str | None = None,
        track_duration: float = 60.0,
        fmt: str = "wav",
        with_vocals: bool | None = None,
        force: bool = False,
        quiet: bool = False,
    ) -> dict:
        """Generate a full multi-track album for a given music genre.

        Every album is produced with Final Fantasy-style epicness: sweeping
        orchestration, emotionally expressive melodies, and cinematic dynamics,
        applied to the source genre's harmonic and rhythmic character.

        Parameters
        ----------
        genre:
            Genre name (case-insensitive).  Supported genres: ``jazz``,
            ``blues``, ``pop``, ``rock``, ``electronic``, ``metal``,
            ``world``, ``ambient``, ``acoustic``, ``cinematic``, and
            aliases such as ``edm``, ``synthwave``, ``folk``, ``country``,
            ``rnb``, ``soul``, ``orchestral``.
        output_dir:
            Directory to write track files and ``album.json`` manifest into.
        title:
            Album title string.  If ``None``, a default title for the genre
            is used.
        track_duration:
            Target duration per track in seconds (default: 60).
        fmt:
            Output format: ``"wav"`` or ``"ogg"``.
        with_vocals:
            Vocal overlay override.  ``None`` uses per-track catalog default.
        force:
            Re-generate tracks even if the output files already exist.
        quiet:
            Suppress progress output.

        Returns
        -------
        dict
            Album manifest (also written to ``<output_dir>/album.json``).

        Raises
        ------
        ValueError
            If *genre* is not recognised.
        """
        genre_key = genre.lower().strip()
        preset_name = GENRE_PRESETS.get(genre_key)
        if preset_name is None:
            available = ", ".join(sorted(GENRE_PRESETS))
            raise ValueError(
                f"Unknown genre '{genre}'.  Available genres: {available}"
            )

        album_title = title or _GENRE_TITLES.get(preset_name, f"{genre.title()} Album")

        def _log(msg: str) -> None:
            if not quiet:
                print(msg, flush=True)

        style_keys = PLAYLIST_PRESETS.get(preset_name, [])
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        _log(f"Generating {genre_key} album '{album_title}' ({len(style_keys)} tracks) → {output_dir}")

        # Generate using the underlying playlist logic
        playlist_manifest = self.generate_playlist(
            preset_or_styles=preset_name,
            output_dir=output_dir,
            track_duration=track_duration,
            fmt=fmt,
            with_vocals=with_vocals,
            force=force,
            quiet=quiet,
        )

        # Write album.json with additional album-level metadata
        album_manifest = {
            "title": album_title,
            "genre": genre_key,
            "preset": preset_name,
            "track_count": playlist_manifest["track_count"],
            "total_duration_s": playlist_manifest["total_duration_s"],
            "backend": self._backend,
            "sample_rate": self.sample_rate,
            "format": fmt,
            "tracks": playlist_manifest["tracks"],
        }

        album_path = output_dir / "album.json"
        with open(album_path, "w", encoding="utf-8") as fh:
            json.dump(album_manifest, fh, indent=2)

        _log(f"\nDone. {len(style_keys)} tracks. Album manifest: {album_path}")
        return album_manifest

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compose_track(
        self,
        style_key: str,
        entry: TrackEntry | None,
        duration: float,
        with_vocals: bool,
        quiet: bool = False,
    ) -> np.ndarray:
        """Generate a full structured piece for one track.

        Notes
        -----
        ``with_vocals`` is resolved by :meth:`_resolve_use_vocals` before this
        method is called so composition here is fully explicit.
        """
        from audio_engine.ai.piece_composer import PieceComposer, SECTION_TEMPLATES

        track_type = entry.track_type if entry else "theme"
        sections = _PIECE_SECTIONS.get(track_type, _PIECE_SECTIONS["theme"])

        # Validate sections against available templates
        valid = list(SECTION_TEMPLATES.keys())
        sections = [s for s in sections if s in valid]
        if not sections:
            sections = ["intro", "verse", "chorus", "outro"]

        composer = PieceComposer(
            sample_rate=self.sample_rate,
            seed=self._seed,
            backend=self._backend,
            vocal_preset=self._vocal_preset,
            backend_kwargs=self._backend_kwargs,
        )

        return composer.compose(
            style=style_key,
            sections=sections,
            with_vocals=with_vocals,
            duration=duration,
            quiet=quiet,
        )

    @staticmethod
    def _resolve_use_vocals(*, entry: TrackEntry | None, with_vocals: bool | None) -> bool:
        if with_vocals is None:
            return bool(entry and entry.with_vocals)
        return bool(with_vocals)

    @staticmethod
    def _instrumental_companion_path(path: Path) -> Path:
        return path.with_name(f"{path.stem}__instrumental{path.suffix}")

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
        rendered_with_vocals: bool | None = None,
        instrumental_filename: str | None = None,
    ) -> dict:
        base: dict = {
            "index": index,
            "style_key": style_key,
            "filename": filename,
            "duration_s": round(duration, 2),
            "skipped": skipped,
        }
        if rendered_with_vocals is not None:
            base["rendered_with_vocals"] = bool(rendered_with_vocals)
        if instrumental_filename:
            base["instrumental_filename"] = instrumental_filename
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
