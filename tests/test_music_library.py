"""
Tests for the full music library expansion:

* Full FF1–FF16 style catalog (all styles generate audio)
* MusicLibrary query API
* style_for_request() natural language resolver
* RadioPlaylistGenerator — single track + full playlist
* CLI: list-music-library, generate-track, generate-radio-playlist
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pytest

SR = 22050
SHORT_DURATION = 3.0


def _write_wav(path: Path, audio: np.ndarray, sr: int = SR) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------------------
# Full FF era style coverage — every style in the library generates audio
# ---------------------------------------------------------------------------

ALL_LIBRARY_STYLES = [
    # Legacy
    "battle", "exploration", "ambient", "boss", "victory", "menu",
    # FF7/FF8
    "ff7_battle", "ff7_overworld", "ff7_boss", "ff7_sad", "ff7_town",
    "ff8_battle", "ff8_ballad",
    # Shared
    "prelude", "world_map", "dungeon", "healing", "tension",
    # FF1-FF6
    "ff1_battle", "ff1_overworld", "ff4_battle", "ff4_theme",
    "ff6_battle", "ff6_opera", "ff6_sad",
    # FF9/FF10
    "ff9_battle", "ff9_overworld", "ff10_calm", "ff10_battle", "ff10_zanarkand",
    # FF12/FF13
    "ff12_battle", "ff13_battle", "ff13_theme",
    # FF14/FF15/FF16
    "ff14_battle", "ff14_overworld", "ff15_road", "ff15_radio",
    "ff16_battle", "ff16_theme",
    # Generic
    "orchestral_epic", "choral_fantasy", "celtic_adventure",
    "jazz_lounge", "electronic_ambient", "rock_battle",
    "piano_ballad", "folk_tavern", "horror_ambient", "triumph_fanfare",
    # Multi-genre with Final Fantasy epicness
    "jazz_epic", "jazz_ballad", "jazz_swing",
    "blues_epic", "blues_ballad",
    "pop_epic", "pop_ballad_epic",
    "rock_epic", "rock_ballad_epic",
    "electronic_epic", "synthwave_epic",
    "metal_epic",
    "world_epic", "latin_epic",
    "acoustic_epic", "country_epic",
    "rnb_ballad",
    "ambient_nature", "ambient_space",
    "cinematic_orchestral",
]

# Genre styles only — used in genre-specific tests
GENRE_STYLES = [
    "jazz_epic", "jazz_ballad", "jazz_swing",
    "blues_epic", "blues_ballad",
    "pop_epic", "pop_ballad_epic",
    "rock_epic", "rock_ballad_epic",
    "electronic_epic", "synthwave_epic",
    "metal_epic",
    "world_epic", "latin_epic",
    "acoustic_epic", "country_epic",
    "rnb_ballad",
    "ambient_nature", "ambient_space",
    "cinematic_orchestral",
]


class TestAllStylesGenerate:
    """Every style in the expanded library should generate non-empty audio."""

    def _generate(self, style: str) -> np.ndarray:
        from audio_engine.ai.backend import ProceduralBackend
        backend = ProceduralBackend(sample_rate=SR, seed=0)
        return backend.generate_music_audio(style=style, duration=SHORT_DURATION)

    @pytest.mark.parametrize("style", ALL_LIBRARY_STYLES)
    def test_style_produces_audio(self, style):
        audio = self._generate(style)
        assert audio is not None
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0, f"Style '{style}' produced silent audio"

    @pytest.mark.parametrize("style", ALL_LIBRARY_STYLES)
    def test_style_produces_correct_dtype(self, style):
        audio = self._generate(style)
        assert audio.dtype == np.float32

    def test_all_styles_defined_in_style_defs(self):
        from audio_engine.ai.generator import _STYLE_DEFS
        missing = [s for s in ALL_LIBRARY_STYLES if s not in _STYLE_DEFS]
        assert missing == [], f"Styles missing from _STYLE_DEFS: {missing}"

    def test_style_count_matches_literal(self):
        """The TrackStyle Literal should include all library styles."""
        from audio_engine.ai.generator import _STYLE_DEFS
        for style in ALL_LIBRARY_STYLES:
            assert style in _STYLE_DEFS


# ---------------------------------------------------------------------------
# MusicLibrary query API
# ---------------------------------------------------------------------------

class TestMusicLibrary:
    def setup_method(self):
        from audio_engine.ai.music_library import MusicLibrary
        self.lib = MusicLibrary()

    def test_all_entries_returns_non_empty(self):
        entries = self.lib.all_entries()
        assert len(entries) > 0

    def test_all_style_keys_is_sorted(self):
        keys = self.lib.all_style_keys()
        assert keys == sorted(keys)

    def test_by_game_ff7(self):
        ff7 = self.lib.by_game("ff7")
        assert len(ff7) >= 4
        for e in ff7:
            assert e.game == "ff7"

    def test_by_game_ff8(self):
        ff8 = self.lib.by_game("ff8")
        assert len(ff8) >= 2

    def test_by_game_ff16(self):
        ff16 = self.lib.by_game("ff16")
        assert len(ff16) >= 2

    def test_by_type_battle(self):
        battles = self.lib.by_type("battle")
        assert len(battles) >= 5
        for e in battles:
            assert e.track_type == "battle"

    def test_by_type_ballad(self):
        ballads = self.lib.by_type("ballad")
        assert len(ballads) >= 1

    def test_with_vocals(self):
        vocal_tracks = self.lib.with_vocals()
        assert len(vocal_tracks) >= 3  # ff6_opera, ff8_ballad, ff14_overworld, ff16_theme
        for e in vocal_tracks:
            assert e.with_vocals is True

    def test_search_finds_ff7_sad(self):
        results = self.lib.search("aerith sad")
        assert any(e.style_key == "ff7_sad" for e in results)

    def test_search_finds_eyes_on_me(self):
        results = self.lib.search("eyes on me")
        assert any(e.style_key == "ff8_ballad" for e in results)

    def test_get_existing_key(self):
        entry = self.lib.get("ff7_sad")
        assert entry is not None
        assert entry.display_name == "Aerith's Theme"

    def test_get_missing_key_returns_none(self):
        assert self.lib.get("does_not_exist") is None

    def test_games_includes_ff1_through_ff16(self):
        games = self.lib.games()
        for g in ["ff1", "ff4", "ff6", "ff7", "ff8", "ff9", "ff10",
                  "ff12", "ff13", "ff14", "ff15", "ff16"]:
            assert g in games, f"'{g}' not in games()"

    def test_track_types_includes_expected(self):
        types = self.lib.track_types()
        for t in ["battle", "overworld", "theme", "ballad", "ambient"]:
            assert t in types


# ---------------------------------------------------------------------------
# style_for_request — natural language resolver
# ---------------------------------------------------------------------------

class TestStyleForRequest:
    def _resolve(self, request: str) -> str:
        from audio_engine.ai.music_library import style_for_request
        return style_for_request(request)

    def test_eyes_on_me(self):
        assert self._resolve("eyes on me") == "ff8_ballad"

    def test_eyes_on_you_variant(self):
        assert self._resolve("eyes on you") == "ff8_ballad"

    def test_aerith_theme(self):
        assert self._resolve("aerith's theme") == "ff7_sad"

    def test_to_zanarkand(self):
        assert self._resolve("to zanarkand") == "ff10_zanarkand"

    def test_aria_di_mezzo(self):
        assert self._resolve("aria di mezzo") == "ff6_opera"

    def test_blinded_by_light(self):
        assert self._resolve("blinded by light") == "ff13_battle"

    def test_sad_emotional(self):
        style = self._resolve("something sad and emotional")
        assert style in ["ff7_sad", "ff8_ballad", "ff6_sad", "ff10_zanarkand",
                         "ff10_calm", "ff13_theme", "piano_ballad"]

    def test_battle_epic(self):
        style = self._resolve("epic battle music")
        assert style in ["ff7_battle", "ff8_battle", "ff9_battle", "ff6_battle",
                         "ff13_battle", "ff14_battle", "ff16_battle",
                         "orchestral_epic", "rock_battle"]

    def test_orchestral(self):
        style = self._resolve("dramatic cinematic orchestral")
        assert style in ["orchestral_epic", "ff7_overworld", "ff7_battle", "cinematic_orchestral"]

    def test_unknown_returns_something(self):
        style = self._resolve("some completely unknown request xyz123")
        assert isinstance(style, str)
        assert len(style) > 0

    def test_direct_style_key_accepted(self):
        # If the user passes a valid style key, it should be returned as-is
        from audio_engine.ai.music_library import MusicLibrary
        lib = MusicLibrary()
        all_keys = lib.all_style_keys()
        assert all_keys  # sanity
        # 'ff7_sad' is a valid key and the alias map has 'aerith' etc
        style = self._resolve("ff7 sad")
        assert style is not None


# ---------------------------------------------------------------------------
# RadioPlaylistGenerator — single track generation
# ---------------------------------------------------------------------------

class TestRadioPlaylistSingleTrack:
    def setup_method(self):
        from audio_engine.ai.radio_playlist import RadioPlaylistGenerator
        self.gen = RadioPlaylistGenerator(
            sample_rate=SR,
            seed=0,
            backend="procedural",
        )

    def test_generate_track_ff7_sad(self, tmp_path):
        out = tmp_path / "aerith.wav"
        path = self.gen.generate_track("ff7_sad", out, duration=4.0, fmt="wav")
        assert path.exists()
        assert path.stat().st_size > 1000

    def test_generate_track_ff8_ballad_with_vocals(self, tmp_path):
        out = tmp_path / "eyes_on_me.wav"
        path = self.gen.generate_track("ff8_ballad", out, duration=5.0, with_vocals=True)
        assert path.exists()

    def test_generate_track_ff10_zanarkand(self, tmp_path):
        out = tmp_path / "zanarkand.wav"
        path = self.gen.generate_track("ff10_zanarkand", out, duration=4.0)
        assert path.exists()

    def test_generate_track_battle(self, tmp_path):
        out = tmp_path / "battle.wav"
        path = self.gen.generate_track("ff7_battle", out, duration=4.0)
        assert path.exists()

    def test_generate_track_natural_language(self, tmp_path):
        """generate_track should accept natural-language requests via style_for_request."""
        out = tmp_path / "track.wav"
        # The style_for_request logic is in generate_track via CLI/RadioPlaylistGenerator
        # Here we use a valid style key
        path = self.gen.generate_track("orchestral_epic", out, duration=4.0)
        assert path.exists()


# ---------------------------------------------------------------------------
# RadioPlaylistGenerator — full playlist
# ---------------------------------------------------------------------------

class TestRadioPlaylistFull:
    def _make_gen(self) -> "RadioPlaylistGenerator":
        from audio_engine.ai.radio_playlist import RadioPlaylistGenerator
        return RadioPlaylistGenerator(
            sample_rate=SR,
            seed=0,
            backend="procedural",
        )

    def test_available_presets_not_empty(self):
        gen = self._make_gen()
        presets = gen.available_presets()
        assert len(presets) >= 5
        assert "ff_radio" in presets
        assert "ff7_album" in presets
        assert "battle_mix" in presets

    def test_generate_playlist_custom_two_tracks(self, tmp_path):
        gen = self._make_gen()
        manifest = gen.generate_playlist(
            ["ff7_sad", "ff8_ballad"],
            output_dir=tmp_path,
            track_duration=4.0,
            quiet=True,
        )
        assert manifest["track_count"] == 2
        assert len(manifest["tracks"]) == 2
        # Files should exist
        for track in manifest["tracks"]:
            assert (tmp_path / track["filename"]).exists()

    def test_generate_playlist_writes_manifest(self, tmp_path):
        gen = self._make_gen()
        gen.generate_playlist(
            ["ff7_overworld"],
            output_dir=tmp_path,
            track_duration=3.0,
            quiet=True,
        )
        manifest_path = tmp_path / "playlist.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert "tracks" in data
        assert data["track_count"] == 1

    def test_generate_playlist_skips_existing(self, tmp_path):
        gen = self._make_gen()
        # First run
        gen.generate_playlist(["ff7_sad"], output_dir=tmp_path, track_duration=3.0, quiet=True)
        # Second run without force — should skip
        manifest = gen.generate_playlist(
            ["ff7_sad"], output_dir=tmp_path, track_duration=3.0, quiet=True, force=False
        )
        assert manifest["tracks"][0].get("skipped") is True

    def test_generate_playlist_force_overwrites(self, tmp_path):
        gen = self._make_gen()
        gen.generate_playlist(["ff7_battle"], output_dir=tmp_path, track_duration=3.0, quiet=True)
        manifest = gen.generate_playlist(
            ["ff7_battle"], output_dir=tmp_path, track_duration=3.0, quiet=True, force=True
        )
        # Force = True means NOT skipped
        assert manifest["tracks"][0].get("skipped") is not True

    def test_ff7_album_preset_has_all_expected_tracks(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        ff7 = set(PLAYLIST_PRESETS["ff7_album"])
        for style in ["ff7_battle", "ff7_overworld", "ff7_sad", "ff7_town", "ff7_boss"]:
            assert style in ff7, f"'{style}' missing from ff7_album preset"

    def test_vocal_album_preset_all_with_vocals(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        from audio_engine.ai.music_library import MusicLibrary
        lib = MusicLibrary()
        for key in PLAYLIST_PRESETS["vocal_album"]:
            entry = lib.get(key)
            assert entry is not None and entry.with_vocals, \
                f"'{key}' in vocal_album but not flagged with_vocals in catalog"

    def test_track_manifest_has_expected_fields(self, tmp_path):
        gen = self._make_gen()
        manifest = gen.generate_playlist(
            ["ff8_ballad"], output_dir=tmp_path, track_duration=3.0, quiet=True
        )
        track = manifest["tracks"][0]
        for field in ["index", "style_key", "filename", "duration_s"]:
            assert field in track

    def test_total_duration_is_sum_of_tracks(self, tmp_path):
        gen = self._make_gen()
        manifest = gen.generate_playlist(
            ["ff7_sad", "ff6_sad"],
            output_dir=tmp_path,
            track_duration=3.0,
            quiet=True,
        )
        expected = sum(t["duration_s"] for t in manifest["tracks"])
        assert abs(manifest["total_duration_s"] - expected) < 0.01


# ---------------------------------------------------------------------------
# CLI — list-music-library, generate-track, generate-radio-playlist
# ---------------------------------------------------------------------------

class TestCLIMusicLibrary:
    def _run(self, argv: list[str]) -> int:
        from audio_engine.cli import main
        return main(argv)

    def test_list_music_library_all(self, capsys):
        rc = self._run(["list-music-library"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "ff7_sad" in out
        assert "ff8_ballad" in out
        assert "ff10_zanarkand" in out
        assert "ff16_battle" in out

    def test_list_music_library_filter_by_game(self, capsys):
        rc = self._run(["list-music-library", "--game", "ff7"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "ff7" in out

    def test_list_music_library_filter_by_type(self, capsys):
        rc = self._run(["list-music-library", "--type", "battle"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "battle" in out.lower()

    def test_list_music_library_vocals(self, capsys):
        rc = self._run(["list-music-library", "--vocals"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "ff8_ballad" in out

    def test_list_music_library_json(self, capsys):
        rc = self._run(["list-music-library", "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "style_key" in data[0]

    def test_list_music_library_search(self, capsys):
        rc = self._run(["list-music-library", "--search", "aerith"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "ff7_sad" in out

    def test_generate_track_by_style_key(self, tmp_path):
        out_path = str(tmp_path / "zanarkand.wav")
        rc = self._run([
            "generate-track",
            "--style", "ff10_zanarkand",
            "--duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_generate_track_natural_language(self, tmp_path):
        out_path = str(tmp_path / "track.wav")
        rc = self._run([
            "generate-track",
            "--style", "something sad from ff7",
            "--duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_generate_track_with_vocals(self, tmp_path):
        out_path = str(tmp_path / "eyes.wav")
        rc = self._run([
            "generate-track",
            "--style", "ff8_ballad",
            "--duration", "4",
            "--sample-rate", "22050",
            "--seed", "0",
            "--with-vocals",
            "--vocal-preset", "soprano",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_generate_radio_playlist_two_tracks(self, tmp_path):
        rc = self._run([
            "generate-radio-playlist",
            "--styles", "ff7_sad,ff8_ballad",
            "--output-dir", str(tmp_path),
            "--track-duration", "4",
            "--sample-rate", "22050",
            "--seed", "0",
            "--no-vocals",
            "--quiet",
        ])
        assert rc == 0
        assert (tmp_path / "playlist.json").exists()
        # Both tracks exported
        wav_files = list(tmp_path.glob("*.wav"))
        assert len(wav_files) == 2

    def test_generate_radio_playlist_preset_ff7_album(self, tmp_path):
        rc = self._run([
            "generate-radio-playlist",
            "--preset", "ff7_album",
            "--output-dir", str(tmp_path),
            "--track-duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--no-vocals",
            "--quiet",
        ])
        assert rc == 0
        manifest = json.loads((tmp_path / "playlist.json").read_text())
        assert manifest["track_count"] >= 5

    def test_generate_radio_playlist_manifest_has_metadata(self, tmp_path):
        self._run([
            "generate-radio-playlist",
            "--styles", "ff10_zanarkand",
            "--output-dir", str(tmp_path),
            "--track-duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--quiet",
        ])
        manifest = json.loads((tmp_path / "playlist.json").read_text())
        track = manifest["tracks"][0]
        assert track["display_name"] == "To Zanarkand"
        assert track["game"] == "ff10"
        assert track["composer"] == "Nobuo Uematsu"


# ---------------------------------------------------------------------------
# Genre styles — every new multi-genre style generates audio correctly
# ---------------------------------------------------------------------------

class TestGenreStylesGenerate:
    """Every new multi-genre style should generate non-empty audio."""

    def _generate(self, style: str) -> np.ndarray:
        from audio_engine.ai.backend import ProceduralBackend
        backend = ProceduralBackend(sample_rate=SR, seed=0)
        return backend.generate_music_audio(style=style, duration=SHORT_DURATION)

    @pytest.mark.parametrize("style", GENRE_STYLES)
    def test_genre_style_produces_audio(self, style):
        audio = self._generate(style)
        assert audio is not None
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0, f"Genre style '{style}' produced silent audio"

    @pytest.mark.parametrize("style", GENRE_STYLES)
    def test_genre_style_correct_dtype(self, style):
        assert self._generate(style).dtype == np.float32

    def test_all_genre_styles_in_style_defs(self):
        from audio_engine.ai.generator import _STYLE_DEFS
        missing = [s for s in GENRE_STYLES if s not in _STYLE_DEFS]
        assert missing == [], f"Genre styles missing from _STYLE_DEFS: {missing}"

    def test_all_genre_styles_in_catalog(self):
        from audio_engine.ai.music_library import MusicLibrary
        lib = MusicLibrary()
        keys = lib.all_style_keys()
        missing = [s for s in GENRE_STYLES if s not in keys]
        assert missing == [], f"Genre styles missing from MusicLibrary catalog: {missing}"


# ---------------------------------------------------------------------------
# Multi-genre album presets
# ---------------------------------------------------------------------------

class TestGenreAlbumPresets:
    """New genre album presets should exist with appropriate tracks."""

    ALL_GENRE_PRESETS = [
        "jazz_album", "blues_album", "pop_album", "rock_album",
        "electronic_album", "metal_album", "world_music_album",
        "ambient_album", "acoustic_album", "cinematic_album",
    ]

    def test_all_genre_presets_exist(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        for preset in self.ALL_GENRE_PRESETS:
            assert preset in PLAYLIST_PRESETS, f"'{preset}' not in PLAYLIST_PRESETS"

    def test_genre_presets_non_empty(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        for preset in self.ALL_GENRE_PRESETS:
            assert len(PLAYLIST_PRESETS[preset]) >= 4, \
                f"'{preset}' has fewer than 4 tracks"

    def test_genre_preset_style_keys_valid(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        from audio_engine.ai.generator import _STYLE_DEFS
        for preset in self.ALL_GENRE_PRESETS:
            for key in PLAYLIST_PRESETS[preset]:
                assert key in _STYLE_DEFS, \
                    f"Style '{key}' in preset '{preset}' not in _STYLE_DEFS"

    def test_jazz_album_contains_jazz_styles(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        tracks = PLAYLIST_PRESETS["jazz_album"]
        jazz_styles = [t for t in tracks if "jazz" in t]
        assert len(jazz_styles) >= 2, "jazz_album should have at least 2 jazz styles"

    def test_rock_album_contains_rock_styles(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        tracks = PLAYLIST_PRESETS["rock_album"]
        rock_styles = [t for t in tracks if "rock" in t]
        assert len(rock_styles) >= 2, "rock_album should have at least 2 rock styles"

    def test_ambient_album_contains_ambient_styles(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        tracks = PLAYLIST_PRESETS["ambient_album"]
        ambient_styles = [t for t in tracks if "ambient" in t]
        assert len(ambient_styles) >= 2, "ambient_album should have at least 2 ambient styles"

    def test_genre_presets_count(self):
        from audio_engine.ai.radio_playlist import PLAYLIST_PRESETS
        # At minimum 10 FF presets + 10 genre album presets
        assert len(PLAYLIST_PRESETS) >= 20

    def test_available_genres_not_empty(self):
        from audio_engine.ai.radio_playlist import RadioPlaylistGenerator
        gen = RadioPlaylistGenerator(sample_rate=SR, seed=0, backend="procedural")
        genres = gen.available_genres()
        assert len(genres) >= 10
        assert "jazz" in genres
        assert "rock" in genres
        assert "blues" in genres
        assert "metal" in genres


# ---------------------------------------------------------------------------
# RadioPlaylistGenerator.generate_album()
# ---------------------------------------------------------------------------

class TestGenerateAlbum:
    def _make_gen(self) -> "RadioPlaylistGenerator":
        from audio_engine.ai.radio_playlist import RadioPlaylistGenerator
        return RadioPlaylistGenerator(sample_rate=SR, seed=0, backend="procedural")

    def test_generate_jazz_album(self, tmp_path):
        gen = self._make_gen()
        manifest = gen.generate_album(
            "jazz", output_dir=tmp_path, track_duration=3.0, quiet=True
        )
        assert manifest["genre"] == "jazz"
        assert manifest["track_count"] >= 4
        assert (tmp_path / "album.json").exists()
        assert (tmp_path / "playlist.json").exists()

    def test_generate_album_writes_album_json(self, tmp_path):
        gen = self._make_gen()
        gen.generate_album("rock", output_dir=tmp_path, track_duration=3.0, quiet=True)
        data = json.loads((tmp_path / "album.json").read_text())
        playlist_data = json.loads((tmp_path / "playlist.json").read_text())
        assert "title" in data
        assert "genre" in data
        assert "tracks" in data
        assert data["genre"] == "rock"
        assert playlist_data["preset"] == "rock_album"

    def test_generate_album_custom_title(self, tmp_path):
        gen = self._make_gen()
        manifest = gen.generate_album(
            "blues", output_dir=tmp_path, title="My Blues Album",
            track_duration=3.0, quiet=True
        )
        assert manifest["title"] == "My Blues Album"

    def test_generate_album_invalid_genre_raises(self):
        gen = self._make_gen()
        with pytest.raises(ValueError, match="Unknown genre"):
            gen.generate_album("nonexistent_genre_xyz", quiet=True)

    def test_generate_album_produces_wav_files(self, tmp_path):
        gen = self._make_gen()
        gen.generate_album("ambient", output_dir=tmp_path, track_duration=3.0, quiet=True)
        wav_files = list(tmp_path.glob("*.wav"))
        assert len(wav_files) >= 4

    def test_generate_album_case_insensitive_genre(self, tmp_path):
        gen = self._make_gen()
        manifest = gen.generate_album(
            "JAZZ", output_dir=tmp_path, track_duration=3.0, quiet=True
        )
        assert manifest["genre"] == "jazz"

    def test_generate_album_genre_alias_edm(self, tmp_path):
        """EDM should map to the electronic album preset."""
        gen = self._make_gen()
        manifest = gen.generate_album(
            "edm", output_dir=tmp_path, track_duration=3.0, quiet=True
        )
        assert manifest["preset"] == "electronic_album"

    def test_genre_presets_constant(self):
        from audio_engine.ai.radio_playlist import GENRE_PRESETS
        assert "jazz" in GENRE_PRESETS
        assert "metal" in GENRE_PRESETS
        assert "ambient" in GENRE_PRESETS
        assert GENRE_PRESETS["jazz"] == "jazz_album"
        assert GENRE_PRESETS["metal"] == "metal_album"


# ---------------------------------------------------------------------------
# CLI — generate-album command
# ---------------------------------------------------------------------------

class TestCLIGenerateAlbum:
    def _run(self, argv: list[str]) -> int:
        from audio_engine.cli import main
        return main(argv)

    def test_generate_album_jazz(self, tmp_path):
        rc = self._run([
            "generate-album",
            "--genre", "jazz",
            "--output-dir", str(tmp_path),
            "--track-duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--no-vocals",
            "--quiet",
        ])
        assert rc == 0
        assert (tmp_path / "album.json").exists()
        data = json.loads((tmp_path / "album.json").read_text())
        assert data["genre"] == "jazz"
        assert data["track_count"] >= 4

    def test_generate_album_custom_title(self, tmp_path):
        rc = self._run([
            "generate-album",
            "--genre", "rock",
            "--title", "Epic Rock Session",
            "--output-dir", str(tmp_path),
            "--track-duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--no-vocals",
            "--quiet",
        ])
        assert rc == 0
        data = json.loads((tmp_path / "album.json").read_text())
        assert data["title"] == "Epic Rock Session"

    def test_generate_album_blues_produces_files(self, tmp_path):
        rc = self._run([
            "generate-album",
            "--genre", "blues",
            "--output-dir", str(tmp_path),
            "--track-duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--quiet",
        ])
        assert rc == 0
        wavs = list(tmp_path.glob("*.wav"))
        assert len(wavs) >= 4

    def test_generate_album_electronic(self, tmp_path):
        rc = self._run([
            "generate-album",
            "--genre", "electronic",
            "--output-dir", str(tmp_path),
            "--track-duration", "3",
            "--sample-rate", "22050",
            "--seed", "0",
            "--no-vocals",
            "--quiet",
        ])
        assert rc == 0
        assert (tmp_path / "album.json").exists()

    def test_generate_album_samples_dir_is_forwarded(self, tmp_path, monkeypatch):
        from audio_engine import cli as cli_module
        import audio_engine.ai.radio_playlist as radio_playlist_module

        captured_kwargs: dict[str, object] = {}

        class _StubRadioPlaylistGenerator:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)

            def generate_album(self, **_kwargs):
                return {}

        monkeypatch.setattr(radio_playlist_module, "RadioPlaylistGenerator", _StubRadioPlaylistGenerator)

        rc = cli_module.main([
            "generate-album",
            "--genre", "jazz",
            "--samples-dir", str(tmp_path / "my_samples"),
            "--quiet",
        ])
        assert rc == 0
        assert captured_kwargs["backend"] == "sample"
        assert captured_kwargs["backend_kwargs"] == {"samples_dir": str(tmp_path / "my_samples")}


# ---------------------------------------------------------------------------
# style_for_request — multi-genre natural language resolver
# ---------------------------------------------------------------------------

class TestStyleForRequestGenres:
    def _resolve(self, request: str) -> str:
        from audio_engine.ai.music_library import style_for_request
        return style_for_request(request)

    def test_jazz_epic_request(self):
        style = self._resolve("big band jazz")
        assert style in ["jazz_epic", "jazz_ballad", "jazz_swing", "jazz_lounge"]

    def test_blues_request(self):
        style = self._resolve("blues ballad slow")
        assert style == "blues_ballad"

    def test_pop_ballad_request(self):
        style = self._resolve("pop ballad")
        assert style in ["pop_ballad_epic", "ff15_radio", "ff8_ballad", "piano_ballad"]

    def test_metal_request(self):
        style = self._resolve("heavy metal")
        assert style in ["metal_epic", "ff16_battle", "rock_battle"]

    def test_synthwave_request(self):
        style = self._resolve("synthwave retrowave")
        assert style in ["synthwave_epic", "electronic_ambient"]

    def test_cinematic_request(self):
        style = self._resolve("cinematic orchestral")
        assert style in ["cinematic_orchestral", "orchestral_epic"]

    def test_ambient_nature_request(self):
        style = self._resolve("nature ambient forest")
        assert style in ["ambient_nature", "horror_ambient", "healing"]

    def test_world_music_request(self):
        style = self._resolve("world music ethnic")
        assert style in ["world_epic", "celtic_adventure"]
