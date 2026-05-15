"""
Tests for the Game Engine for Teaching integration layer.

These tests verify:
  1. The asset manifest is complete and consistent.
  2. AssetPipeline.generate_all() creates all expected files.
  3. AssetPipeline.verify() correctly identifies present/missing assets.
  4. The CLI commands generate-game-assets and verify-game-assets work.
  5. GenerationManifest serialisation round-trips correctly.
  6. The C++ AudioSystem.hpp and Lua audio.lua files are present and
     syntactically valid (ASCII / non-empty).
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import wave

import pytest

from audio_engine.integration import (
    AssetPipeline,
    AudioPlan,
    FactoryInputError,
    GenerationManifest,
    GenerationRequestBatch,
    PlanBatchOrchestrator,
    RequestBatchRecord,
    RequestBatchResult,
    MUSIC_MANIFEST,
    SFX_MANIFEST,
    VOICE_MANIFEST,
    MusicAsset,
    SFXAsset,
    VoiceAsset,
    load_audio_plan,
    load_generation_request_batch,
    parse_audio_plan,
    parse_generation_request_batch,
)
from audio_engine.integration.game_state_map import (
    MUSIC_MANIFEST,
    SFX_MANIFEST,
    VOICE_MANIFEST,
)
from audio_engine.cli import main

# Absolute path to the integration package.
INTEGRATION_DIR = Path(__file__).parent.parent / "audio_engine" / "integration"
EXAMPLE_FACTORY_INPUTS_DIR = (
    Path(__file__).parent.parent
    / "docs"
    / "AI_FACTORY"
    / "EXAMPLES"
    / "gamerewritten_vertical_slice"
)


# ---------------------------------------------------------------------------
# Manifest structure tests
# ---------------------------------------------------------------------------

class TestManifestStructure:
    """Verify that the game-state-map manifests are internally consistent."""

    def test_music_manifest_not_empty(self):
        assert len(MUSIC_MANIFEST) > 0

    def test_sfx_manifest_not_empty(self):
        assert len(SFX_MANIFEST) > 0

    def test_voice_manifest_not_empty(self):
        assert len(VOICE_MANIFEST) > 0

    def test_music_filenames_unique(self):
        filenames = [a.filename for a in MUSIC_MANIFEST]
        assert len(filenames) == len(set(filenames)), "Duplicate music filenames"

    def test_sfx_filenames_unique(self):
        filenames = [a.filename for a in SFX_MANIFEST]
        assert len(filenames) == len(set(filenames)), "Duplicate SFX filenames"

    def test_voice_filenames_unique(self):
        filenames = [a.filename for a in VOICE_MANIFEST]
        assert len(filenames) == len(set(filenames)), "Duplicate voice filenames"

    def test_sfx_event_keys_unique(self):
        keys = [a.event for a in SFX_MANIFEST]
        assert len(keys) == len(set(keys)), "Duplicate SFX event keys"

    def test_voice_keys_unique(self):
        keys = [a.key for a in VOICE_MANIFEST]
        assert len(keys) == len(set(keys)), "Duplicate voice keys"

    def test_music_filenames_are_wav(self):
        for a in MUSIC_MANIFEST:
            assert a.filename.endswith(".wav"), f"{a.filename} should be .wav"

    def test_sfx_filenames_are_wav(self):
        for a in SFX_MANIFEST:
            assert a.filename.endswith(".wav"), f"{a.filename} should be .wav"

    def test_voice_filenames_are_wav(self):
        for a in VOICE_MANIFEST:
            assert a.filename.endswith(".wav"), f"{a.filename} should be .wav"

    def test_music_durations_positive(self):
        for a in MUSIC_MANIFEST:
            assert a.duration > 0, f"{a.filename} has non-positive duration"

    def test_sfx_durations_positive(self):
        for a in SFX_MANIFEST:
            assert a.duration > 0, f"{a.filename} has non-positive duration"

    def test_music_prompts_non_empty(self):
        for a in MUSIC_MANIFEST:
            assert a.prompt.strip(), f"{a.filename} has empty prompt"

    def test_sfx_prompts_non_empty(self):
        for a in SFX_MANIFEST:
            assert a.prompt.strip(), f"{a.filename} has empty prompt"

    def test_voice_texts_non_empty(self):
        for a in VOICE_MANIFEST:
            assert a.text.strip(), f"{a.key} has empty text"

    def test_voice_presets_valid(self):
        valid = {"narrator", "hero", "villain", "announcer", "npc"}
        for a in VOICE_MANIFEST:
            assert a.voice in valid, f"{a.key} has invalid voice preset '{a.voice}'"

    def test_sfx_filenames_have_sfx_prefix(self):
        for a in SFX_MANIFEST:
            assert a.filename.startswith("sfx_"), (
                f"{a.filename} should start with 'sfx_'"
            )

    def test_music_filenames_have_music_prefix(self):
        for a in MUSIC_MANIFEST:
            assert a.filename.startswith("music_"), (
                f"{a.filename} should start with 'music_'"
            )

    def test_voice_filenames_have_voice_prefix(self):
        for a in VOICE_MANIFEST:
            assert a.filename.startswith("voice_"), (
                f"{a.filename} should start with 'voice_'"
            )

    def test_known_game_states_covered(self):
        """All GameState values mentioned in Types.hpp must have a music track."""
        states_with_music = {a.game_state for a in MUSIC_MANIFEST}
        required = {"MAIN_MENU", "EXPLORING", "COMBAT", "DIALOGUE", "VEHICLE"}
        missing = required - states_with_music
        assert not missing, f"Missing music tracks for game states: {missing}"

    def test_essential_sfx_events_present(self):
        """Key SFX events must be present (used by AudioSystem.hpp spot check)."""
        events = {a.event for a in SFX_MANIFEST}
        essential = {"combat_hit", "spell_cast", "level_up", "ui_confirm"}
        missing = essential - events
        assert not missing, f"Missing essential SFX events: {missing}"


# ---------------------------------------------------------------------------
# GenerationManifest serialisation
# ---------------------------------------------------------------------------

class TestGenerationManifest:
    def test_summary_not_empty(self):
        m = GenerationManifest(output_dir="/tmp/test")
        m.music.append({"game_state": "EXPLORING", "file": "x.wav", "status": "ok"})
        summary = m.summary()
        assert "Music" in summary
        assert "1 assets" in summary

    def test_json_round_trip(self):
        m = GenerationManifest(
            output_dir="/tmp/assets",
            music=[{"game_state": "COMBAT", "file": "a.wav", "status": "ok"}],
            sfx=[{"event": "hit", "file": "b.wav", "status": "ok"}],
            voice=[{"key": "welcome", "file": "c.wav", "status": "ok"}],
            errors=["something went wrong"],
            total_duration_seconds=3.14,
        )
        restored = GenerationManifest.from_json(m.to_json())
        assert restored.output_dir == m.output_dir
        assert restored.music == m.music
        assert restored.sfx == m.sfx
        assert restored.voice == m.voice
        assert restored.errors == m.errors
        assert abs(restored.total_duration_seconds - m.total_duration_seconds) < 0.001

    def test_to_json_is_valid_json(self):
        m = GenerationManifest(output_dir="/tmp")
        data = json.loads(m.to_json())  # should not raise
        assert "output_dir" in data
        assert "music" in data
        assert "sfx" in data
        assert "voice" in data

    def test_errors_reported_in_summary(self):
        m = GenerationManifest(output_dir="/tmp")
        m.errors.append("sfx/missing.wav: some error")
        assert "Errors" in m.summary()


# ---------------------------------------------------------------------------
# Factory input loaders
# ---------------------------------------------------------------------------

class TestFactoryInputLoaders:
    def test_load_audio_plan_fixture(self):
        plan = load_audio_plan(EXAMPLE_FACTORY_INPUTS_DIR / "audio_plan.vertical_slice.v1.json")

        assert isinstance(plan, AudioPlan)
        assert plan.project == "GameRewritten"
        assert plan.scope == "vertical-slice"
        assert plan.priorities.music == "high"
        assert len(plan.asset_groups) >= 2
        assert plan.asset_groups[0].targets[0].asset_id == "bgm_field_day"
        assert plan.asset_groups[0].targets[0].target_path == "Content/Audio/bgm_field_day.ogg"

    @pytest.mark.parametrize(
        ("filename", "expected_type", "expected_request_count"),
        [
            ("generation_requests.music.v1.json", "music", 15),
            ("generation_requests.sfx.v1.json", "sfx", 10),
            ("generation_requests.voice.v1.json", "voice", 2),
        ],
    )
    def test_load_generation_request_fixture(self, filename, expected_type, expected_request_count):
        batch = load_generation_request_batch(EXAMPLE_FACTORY_INPUTS_DIR / filename)

        assert isinstance(batch, GenerationRequestBatch)
        assert batch.project == "GameRewritten"
        assert len(batch.requests) == expected_request_count
        assert all(request.type == expected_type for request in batch.requests)
        assert all(request.qa.review_status == "draft" for request in batch.requests)
        assert all(request.seed >= 0 for request in batch.requests)
        assert all(request.output.target_path for request in batch.requests)
        assert all(request.output.sample_rate > 0 for request in batch.requests)
        assert all(request.output.channels > 0 for request in batch.requests)

    def test_music_fixture_includes_required_fanfare_requests(self):
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.music.v1.json"
        )
        fanfare_requests = {
            request.asset_id: request
            for request in batch.requests
            if request.asset_id in {"fanfare_item_obtain", "fanfare_quest_complete"}
        }
        assert set(fanfare_requests) == {"fanfare_item_obtain", "fanfare_quest_complete"}
        for request in fanfare_requests.values():
            assert request.type == "music"
            assert request.output.format == "wav"
            assert request.qa.loop_required is False

    def test_generation_request_loader_rejects_missing_request_id(self):
        invalid_batch = {
            "requestBatchVersion": "1.0.0",
            "project": "GameRewritten",
            "scope": "vertical-slice",
            "requests": [
                {
                    "requestVersion": "1.0.0",
                    "assetId": "bgm_field_day",
                    "type": "music",
                    "backend": "procedural",
                    "seed": 42,
                    "prompt": "loopable field theme",
                    "styleFamily": "heroic-sci-fantasy",
                    "output": {
                        "targetPath": "Content/Audio/bgm_field_day.ogg",
                        "format": "ogg",
                        "sampleRate": 44100,
                        "channels": 2,
                    },
                    "qa": {
                        "loopRequired": True,
                        "reviewStatus": "draft",
                        "notes": [],
                    },
                }
            ],
        }

        with pytest.raises(FactoryInputError, match="requestId"):
            parse_generation_request_batch(invalid_batch, source="invalid_generation_request")

    @staticmethod
    def _base_generation_request_batch() -> dict:
        return {
            "requestBatchVersion": "1.0.0",
            "project": "GameRewritten",
            "scope": "vertical-slice",
            "requests": [
                {
                    "requestVersion": "1.0.0",
                    "requestId": "req_music_field_day_v1",
                    "assetId": "bgm_field_day",
                    "type": "music",
                    "backend": "procedural",
                    "seed": 42,
                    "prompt": "loopable field theme",
                    "styleFamily": "heroic-sci-fantasy",
                    "output": {
                        "targetPath": "Content/Audio/bgm_field_day.ogg",
                        "format": "ogg",
                        "sampleRate": 44100,
                        "channels": 2,
                    },
                    "qa": {
                        "loopRequired": True,
                        "reviewStatus": "draft",
                        "notes": [],
                    },
                }
            ],
        }

    def test_generation_request_loader_rejects_invalid_constraints(self):
        invalid_cases = [
            ("requests[0].seed", -1, "non-negative"),
            ("requests[0].type", "muisc", "one of"),
            ("requests[0].output.sampleRate", 0, "positive integer"),
            ("requests[0].output.channels", -2, "positive integer"),
            ("requests[0].output.format", "mp3", "one of"),
            ("requests[0].qa.reviewStatus", "drfat", "one of"),
        ]

        for path, value, expected_error in invalid_cases:
            invalid_batch = self._base_generation_request_batch()
            cursor = invalid_batch
            parts = path.split(".")
            for part in parts[:-1]:
                if "[" in part and part.endswith("]"):
                    key, index = part[:-1].split("[")
                    cursor = cursor[key][int(index)]
                else:
                    cursor = cursor[part]
            cursor[parts[-1]] = value

            with pytest.raises(FactoryInputError, match=expected_error):
                parse_generation_request_batch(invalid_batch, source="invalid_generation_request")

    def test_generation_request_loader_rejects_duplicates(self):
        invalid_batch = self._base_generation_request_batch()
        duplicate_request = json.loads(json.dumps(invalid_batch["requests"][0]))
        duplicate_request["requestId"] = invalid_batch["requests"][0]["requestId"]
        duplicate_request["output"]["targetPath"] = "Content/Audio/bgm_field_night.ogg"
        invalid_batch["requests"].append(duplicate_request)

        with pytest.raises(FactoryInputError, match="duplicates an existing requestId"):
            parse_generation_request_batch(invalid_batch, source="invalid_generation_request")

        invalid_batch = self._base_generation_request_batch()
        duplicate_path_request = json.loads(json.dumps(invalid_batch["requests"][0]))
        duplicate_path_request["requestId"] = "req_music_field_day_v2"
        invalid_batch["requests"].append(duplicate_path_request)

        with pytest.raises(FactoryInputError, match="duplicates an existing targetPath"):
            parse_generation_request_batch(invalid_batch, source="invalid_generation_request")

    def test_generation_request_loader_accepts_valid_sfx_variant_family(self):
        batch = {
            "requestBatchVersion": "1.0.0",
            "project": "GameRewritten",
            "scope": "variation-tests",
            "requests": [
                {
                    "requestVersion": "1.0.0",
                    "requestId": "req_sfx_ui_confirm_var01",
                    "assetId": "sfx_ui_confirm_var01",
                    "type": "sfx",
                    "backend": "procedural",
                    "seed": 101,
                    "prompt": "ui confirm click variant one",
                    "styleFamily": "heroic-sci-fantasy",
                    "output": {
                        "targetPath": "Content/Audio/sfx_ui_confirm_var01.wav",
                        "format": "wav",
                        "sampleRate": 44100,
                        "channels": 1,
                    },
                    "qa": {"loopRequired": False, "reviewStatus": "draft"},
                },
                {
                    "requestVersion": "1.0.0",
                    "requestId": "req_sfx_ui_confirm_var02",
                    "assetId": "sfx_ui_confirm_var02",
                    "type": "sfx",
                    "backend": "procedural",
                    "seed": 102,
                    "prompt": "ui confirm click variant two",
                    "styleFamily": "heroic-sci-fantasy",
                    "output": {
                        "targetPath": "Content/Audio/sfx_ui_confirm_var02.wav",
                        "format": "wav",
                        "sampleRate": 44100,
                        "channels": 1,
                    },
                    "qa": {"loopRequired": False, "reviewStatus": "draft"},
                },
            ],
        }

        parsed = parse_generation_request_batch(batch, source="valid_variant_batch")
        assert len(parsed.requests) == 2

    def test_generation_request_loader_rejects_variant_family_seed_reuse(self):
        batch = {
            "requestBatchVersion": "1.0.0",
            "project": "GameRewritten",
            "scope": "variation-tests",
            "requests": [
                {
                    "requestVersion": "1.0.0",
                    "requestId": "req_sfx_ui_confirm_var01",
                    "assetId": "sfx_ui_confirm_var01",
                    "type": "sfx",
                    "backend": "procedural",
                    "seed": 101,
                    "prompt": "ui confirm click variant one",
                    "styleFamily": "heroic-sci-fantasy",
                    "output": {
                        "targetPath": "Content/Audio/sfx_ui_confirm_var01.wav",
                        "format": "wav",
                        "sampleRate": 44100,
                        "channels": 1,
                    },
                    "qa": {"loopRequired": False, "reviewStatus": "draft"},
                },
                {
                    "requestVersion": "1.0.0",
                    "requestId": "req_sfx_ui_confirm_var02",
                    "assetId": "sfx_ui_confirm_var02",
                    "type": "sfx",
                    "backend": "procedural",
                    "seed": 101,
                    "prompt": "ui confirm click variant two",
                    "styleFamily": "heroic-sci-fantasy",
                    "output": {
                        "targetPath": "Content/Audio/sfx_ui_confirm_var02.wav",
                        "format": "wav",
                        "sampleRate": 44100,
                        "channels": 1,
                    },
                    "qa": {"loopRequired": False, "reviewStatus": "draft"},
                },
            ],
        }

        with pytest.raises(FactoryInputError, match="duplicates another variant seed"):
            parse_generation_request_batch(batch, source="invalid_variant_batch")

    def test_audio_plan_loader_rejects_invalid_duration_and_duplicates(self):
        invalid_plan = {
            "planVersion": "1.0.0",
            "project": "GameRewritten",
            "scope": "vertical-slice",
            "priorities": {"music": "high", "sfx": "high", "voice": "low"},
            "styleFamilies": ["heroic-sci-fantasy"],
            "assetGroups": [
                {
                    "groupId": "music-field",
                    "type": "music",
                    "required": True,
                    "targets": [
                        {
                            "assetId": "bgm_field_day",
                            "gameplayRole": "field exploration",
                            "targetPath": "Content/Audio/bgm_field_day.ogg",
                            "loop": True,
                            "durationTargetSeconds": 0,
                        }
                    ],
                }
            ],
        }

        with pytest.raises(FactoryInputError, match="finite positive number"):
            parse_audio_plan(invalid_plan, source="invalid_audio_plan")

        duplicate_plan = json.loads(json.dumps(invalid_plan))
        duplicate_plan["assetGroups"][0]["targets"][0]["durationTargetSeconds"] = 90
        duplicate_plan["assetGroups"].append(
            {
                "groupId": "music-combat",
                "type": "music",
                "required": True,
                "targets": [
                    {
                        "assetId": "bgm_field_day",
                        "gameplayRole": "combat",
                        "targetPath": "Content/Audio/bgm_combat.ogg",
                        "loop": True,
                        "durationTargetSeconds": 60,
                    }
                ],
            }
        )

        with pytest.raises(FactoryInputError, match="duplicates an existing assetId"):
            parse_audio_plan(duplicate_plan, source="invalid_audio_plan")

        duplicate_path_plan = json.loads(json.dumps(invalid_plan))
        duplicate_path_plan["assetGroups"][0]["targets"][0]["durationTargetSeconds"] = 90
        duplicate_path_plan["assetGroups"].append(
            {
                "groupId": "music-combat",
                "type": "music",
                "required": True,
                "targets": [
                    {
                        "assetId": "bgm_combat",
                        "gameplayRole": "combat",
                        "targetPath": "Content/Audio/bgm_field_day.ogg",
                        "loop": True,
                        "durationTargetSeconds": 60,
                    }
                ],
            }
        )

        with pytest.raises(FactoryInputError, match="duplicates an existing targetPath"):
            parse_audio_plan(duplicate_path_plan, source="invalid_audio_plan")


# ---------------------------------------------------------------------------
# AssetPipeline.verify()
# ---------------------------------------------------------------------------

class TestAssetPipelineVerify:
    def test_empty_dir_all_missing(self, tmp_path):
        (tmp_path / "music").mkdir()
        (tmp_path / "sfx").mkdir()
        (tmp_path / "voice").mkdir()
        pipeline = AssetPipeline()
        report = pipeline.verify(tmp_path)
        assert len(report["missing"]) > 0
        assert len(report["present"]) == 0

    def test_partial_assets_reported(self, tmp_path):
        (tmp_path / "music").mkdir()
        (tmp_path / "sfx").mkdir()
        (tmp_path / "voice").mkdir()
        # Create just one music file
        (tmp_path / "music" / "music_main_menu.wav").touch()
        pipeline = AssetPipeline()
        report = pipeline.verify(tmp_path)
        assert "music/music_main_menu.wav" in report["present"]
        assert len(report["missing"]) > 0

    def test_all_present(self, tmp_path):
        """If every expected file is touched, verify should report all present."""
        (tmp_path / "music").mkdir()
        (tmp_path / "sfx").mkdir()
        (tmp_path / "voice").mkdir()
        for a in MUSIC_MANIFEST:
            (tmp_path / "music" / a.filename).touch()
        for a in SFX_MANIFEST:
            (tmp_path / "sfx" / a.filename).touch()
        for a in VOICE_MANIFEST:
            (tmp_path / "voice" / a.filename).touch()
        pipeline = AssetPipeline()
        report = pipeline.verify(tmp_path)
        assert len(report["missing"]) == 0
        assert len(report["present"]) == (
            len(MUSIC_MANIFEST) + len(SFX_MANIFEST) + len(VOICE_MANIFEST)
        )


# ---------------------------------------------------------------------------
# AssetPipeline.generate_all() – smoke test (short duration)
# ---------------------------------------------------------------------------

class TestAssetPipelineGenerate:
    """Smoke tests: generate a small subset of assets and verify output."""

    def _fast_music(self, asset: MusicAsset, path: Path) -> None:
        """Helper: generate 2 s of music instead of the full duration."""
        from audio_engine.ai.music_gen import MusicGen
        from audio_engine.export.audio_exporter import AudioExporter

        gen = MusicGen(sample_rate=22050, seed=0)
        audio = gen.generate(asset.prompt, duration=2.0, loopable=asset.loopable)
        AudioExporter(22050, 16).export(audio, path, fmt="wav")

    def test_generate_sfx_only(self, tmp_path, monkeypatch):
        """generate_sfx_only should create all SFX WAV files."""
        pipeline = AssetPipeline(sample_rate=22050, seed=0)
        manifest = pipeline.generate_sfx_only(tmp_path)
        assert len(manifest.errors) == 0, f"Errors: {manifest.errors}"
        sfx_dir = tmp_path / "sfx"
        for a in SFX_MANIFEST:
            assert (sfx_dir / a.filename).exists(), f"Missing SFX: {a.filename}"

    def test_generate_voice_only(self, tmp_path):
        """generate_voice_only should create all voice WAV files."""
        pipeline = AssetPipeline(sample_rate=22050, seed=0)
        manifest = pipeline.generate_voice_only(tmp_path)
        assert len(manifest.errors) == 0, f"Errors: {manifest.errors}"
        voice_dir = tmp_path / "voice"
        for a in VOICE_MANIFEST:
            assert (voice_dir / a.filename).exists(), f"Missing voice: {a.filename}"

    def test_skip_existing(self, tmp_path):
        """skip_existing=True should not regenerate existing files."""
        sfx_dir = tmp_path / "sfx"
        sfx_dir.mkdir()
        first_asset = SFX_MANIFEST[0]
        existing = sfx_dir / first_asset.filename
        existing.write_bytes(b"PLACEHOLDER")
        mtime_before = existing.stat().st_mtime

        pipeline = AssetPipeline(seed=0, skip_existing=True)
        pipeline.generate_sfx_only(tmp_path)

        mtime_after = existing.stat().st_mtime
        assert mtime_before == mtime_after, "File was regenerated despite skip_existing=True"

    def test_manifest_json_written(self, tmp_path):
        """generate_all should write manifest.json."""
        pipeline = AssetPipeline(sample_rate=22050, seed=0)
        pipeline.generate_all(tmp_path)
        manifest_path = tmp_path / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert "music" in data
        assert "sfx" in data
        assert "voice" in data

    def test_progress_callback_called(self, tmp_path):
        """progress_callback should be invoked at least once per category."""
        messages: list[str] = []
        pipeline = AssetPipeline(
            sample_rate=22050, seed=0,
            progress_callback=messages.append,
        )
        pipeline.generate_sfx_only(tmp_path)
        assert len(messages) > 0


# ---------------------------------------------------------------------------
# CLI: generate-game-assets and verify-game-assets
# ---------------------------------------------------------------------------

class TestCLIIntegration:
    def test_generate_game_assets_sfx_only(self, tmp_path, capsys):
        rc = main([
            "generate-game-assets",
            "--output-dir", str(tmp_path),
            "--only", "sfx",
            "--sample-rate", "22050",
            "--seed", "0",
        ])
        assert rc == 0
        sfx_dir = tmp_path / "sfx"
        assert sfx_dir.exists()
        assert any(sfx_dir.iterdir())

    def test_generate_game_assets_voice_only(self, tmp_path):
        rc = main([
            "generate-game-assets",
            "--output-dir", str(tmp_path),
            "--only", "voice",
            "--sample-rate", "22050",
            "--seed", "0",
        ])
        assert rc == 0
        voice_dir = tmp_path / "voice"
        assert voice_dir.exists()

    def test_verify_game_assets_missing(self, tmp_path):
        """verify-game-assets should return non-zero when assets are missing."""
        rc = main(["verify-game-assets", "--assets-dir", str(tmp_path)])
        assert rc != 0

    def test_verify_game_assets_present(self, tmp_path, capsys):
        """verify-game-assets should return 0 when all files are present."""
        (tmp_path / "music").mkdir()
        (tmp_path / "sfx").mkdir()
        (tmp_path / "voice").mkdir()
        for a in MUSIC_MANIFEST:
            (tmp_path / "music" / a.filename).touch()
        for a in SFX_MANIFEST:
            (tmp_path / "sfx" / a.filename).touch()
        for a in VOICE_MANIFEST:
            (tmp_path / "voice" / a.filename).touch()
        rc = main(["verify-game-assets", "--assets-dir", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "All assets present" in captured.out

    def test_verify_nonexistent_dir(self, tmp_path):
        rc = main(["verify-game-assets", "--assets-dir", str(tmp_path / "nonexistent")])
        assert rc != 0

    def test_generate_with_force_flag(self, tmp_path):
        """--force should regenerate even when files exist."""
        (tmp_path / "sfx").mkdir()
        first = SFX_MANIFEST[0]
        existing = tmp_path / "sfx" / first.filename
        existing.write_bytes(b"STALE")
        main([
            "generate-game-assets", "--output-dir", str(tmp_path),
            "--only", "sfx", "--sample-rate", "22050", "--seed", "0", "--force",
        ])
        assert existing.stat().st_size > 4  # was regenerated (WAV > 4 bytes)


# ---------------------------------------------------------------------------
# Integration artefact files – verify they exist and are non-empty
# ---------------------------------------------------------------------------

class TestIntegrationArtefacts:
    def test_cpp_header_exists(self):
        hpp = INTEGRATION_DIR / "cpp" / "AudioSystem.hpp"
        assert hpp.exists(), f"AudioSystem.hpp not found at {hpp}"
        content = hpp.read_text(encoding="utf-8")
        assert len(content) > 1000, "AudioSystem.hpp appears truncated"

    def test_cpp_header_contains_class(self):
        hpp = (INTEGRATION_DIR / "cpp" / "AudioSystem.hpp").read_text(encoding="utf-8")
        assert "class AudioSystem" in hpp

    def test_cpp_header_contains_lua_bindings(self):
        hpp = (INTEGRATION_DIR / "cpp" / "AudioSystem.hpp").read_text(encoding="utf-8")
        assert "Lua_PlaySFX" in hpp
        assert "Lua_PlayMusic" in hpp
        assert "Lua_PlayVoice" in hpp

    def test_cpp_header_contains_game_state_map(self):
        hpp = (INTEGRATION_DIR / "cpp" / "AudioSystem.hpp").read_text(encoding="utf-8")
        assert "MAIN_MENU" in hpp
        assert "EXPLORING" in hpp
        assert "COMBAT" in hpp

    def test_lua_script_exists(self):
        lua = INTEGRATION_DIR / "lua" / "audio.lua"
        assert lua.exists(), f"audio.lua not found at {lua}"
        content = lua.read_text(encoding="utf-8")
        assert len(content) > 500, "audio.lua appears truncated"

    def test_lua_script_hooks_all_events(self):
        lua = (INTEGRATION_DIR / "lua" / "audio.lua").read_text(encoding="utf-8")
        assert "on_combat_start" in lua
        assert "on_camp_rest" in lua
        assert "on_level_up" in lua
        assert "Audio.PlaySFX" in lua
        assert "Audio.PlayVoice" in lua

    def test_lua_script_nil_safe(self):
        """Lua bindings should be guarded with 'if audio_play_sfx then'."""
        lua = (INTEGRATION_DIR / "lua" / "audio.lua").read_text(encoding="utf-8")
        assert "if audio_play_sfx" in lua

    def test_game_state_map_imports_cleanly(self):
        """The game_state_map module should import without errors."""
        from audio_engine.integration import game_state_map  # noqa: F401

    def test_asset_pipeline_imports_cleanly(self):
        from audio_engine.integration import AssetPipeline  # noqa: F401

    def test_integration_init_exports(self):
        from audio_engine import integration
        assert hasattr(integration, "AssetPipeline")
        assert hasattr(integration, "MUSIC_MANIFEST")
        assert hasattr(integration, "SFX_MANIFEST")
        assert hasattr(integration, "VOICE_MANIFEST")
        assert hasattr(integration, "RequestBatchRecord")
        assert hasattr(integration, "RequestBatchResult")


# ---------------------------------------------------------------------------
# RequestBatchPipeline tests
# ---------------------------------------------------------------------------

class TestRequestBatchPipeline:
    """Tests for the request-batch generation pipeline."""

    def test_imports_cleanly(self):
        from audio_engine.integration import RequestBatchPipeline
        assert RequestBatchPipeline is not None

    def test_execute_sfx_batch_creates_files(self, tmp_path):
        """Execute the committed SFX request batch; verify output files are created."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        assert len(manifest.errors) == 0, f"Errors during batch execution: {manifest.errors}"
        assert len(manifest.sfx) == len(batch.requests)

        drafts_sfx_dir = tmp_path / "drafts" / "sfx"
        assert drafts_sfx_dir.exists()
        for record in manifest.sfx:
            assert Path(record["file"]).exists(), f"Missing output: {record['file']}"
            assert Path(record["file"]).stat().st_size > 0

    def test_execute_sfx_batch_manifest_has_required_fields(self, tmp_path):
        """Each manifest record must carry request_id, asset_id, seed, type, file, status."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        for record in manifest.sfx:
            for key in ("request_id", "asset_id", "seed", "type", "file", "status"):
                assert key in record, f"Missing key '{key}' in SFX record: {record}"
            assert record["status"] == "ok"

    def test_execute_sfx_batch_seeds_are_explicit(self, tmp_path):
        """Seeds in manifest records must match the request definitions."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        request_seeds = {r.request_id: r.seed for r in batch.requests}
        for record in manifest.sfx:
            assert record["seed"] == request_seeds[record["request_id"]], (
                f"Seed mismatch for {record['request_id']}"
            )

    def test_execute_skip_existing(self, tmp_path):
        """skip_existing=True must not overwrite files that already exist."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )

        # Pre-create one output file as a sentinel using the request_id stem convention.
        first_request = batch.requests[0]
        type_dir = tmp_path / "drafts" / first_request.type
        type_dir.mkdir(parents=True)
        sentinel_name = (
            first_request.request_id + "." + first_request.output.format.lower()
        )
        sentinel = type_dir / sentinel_name
        sentinel.write_bytes(b"SENTINEL")

        pipeline = RequestBatchPipeline(skip_existing=True)
        manifest = pipeline.execute(batch, tmp_path)

        # Sentinel file must not have been overwritten.
        assert sentinel.read_bytes() == b"SENTINEL"

        # Corresponding record should be marked skipped.
        skipped = [r for r in manifest.sfx if r["request_id"] == first_request.request_id]
        assert skipped and skipped[0]["status"] == "skipped"

    def test_execute_writes_batch_manifest_json(self, tmp_path):
        """execute() must write batch_manifest.json under <output_dir>/drafts/."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        pipeline.execute(batch, tmp_path)

        manifest_path = tmp_path / "drafts" / "batch_manifest.json"
        assert manifest_path.exists(), "batch_manifest.json was not written"
        data = json.loads(manifest_path.read_text())
        assert "sfx" in data
        assert "errors" in data

    def test_execute_music_batch_creates_files(self, tmp_path, monkeypatch):
        """Execute one WAV-format music request (monkeypatched to 2 s duration)."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch
        from audio_engine.ai.music_gen import MusicGen
        from audio_engine.integration.factory_inputs import GenerationRequestBatch

        # Monkeypatch generate() to produce a short dummy signal instead of 30 s.
        import numpy as np

        original_generate = MusicGen.generate

        def _fast_generate(self, prompt, duration=30.0, loopable=False):
            return original_generate(self, prompt, duration=2.0, loopable=loopable)

        monkeypatch.setattr(MusicGen, "generate", _fast_generate)

        full_batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.music.v1.json"
        )
        wav_requests = [r for r in full_batch.requests if r.output.format == "wav"]
        assert wav_requests, "No WAV-format music requests found in fixture"
        batch = GenerationRequestBatch(
            request_batch_version=full_batch.request_batch_version,
            project=full_batch.project,
            scope=full_batch.scope,
            requests=[wav_requests[0]],
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        assert len(manifest.errors) == 0, f"Errors during music batch execution: {manifest.errors}"
        assert len(manifest.music) == len(batch.requests)
        for record in manifest.music:
            assert Path(record["file"]).exists(), f"Missing output: {record['file']}"
            assert record["seed"] > 0

    def test_execute_request_batch_ogg_missing_encoder_is_error(self, tmp_path, monkeypatch):
        """OGG requests must fail (not silently fall back to WAV) when OGG export is unavailable."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch
        from audio_engine.integration.factory_inputs import GenerationRequestBatch
        from audio_engine.export.audio_exporter import AudioExporter

        full_batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.music.v1.json"
        )
        ogg_requests = [r for r in full_batch.requests if r.output.format == "ogg"]
        assert ogg_requests, "No OGG-format music requests found in fixture"
        batch = GenerationRequestBatch(
            request_batch_version=full_batch.request_batch_version,
            project=full_batch.project,
            scope=full_batch.scope,
            requests=[ogg_requests[0]],
        )

        def _simulate_missing_encoder(_exporter, audio, path):  # pragma: no cover - injected behavior
            raise ImportError("soundfile missing for test")

        monkeypatch.setattr(AudioExporter, "_write_ogg", _simulate_missing_encoder)

        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        assert len(manifest.errors) == 1
        assert "soundfile missing for test" in manifest.errors[0]
        expected_wav_fallback = tmp_path / "drafts" / "music" / f"{ogg_requests[0].request_id}.wav"
        assert not expected_wav_fallback.exists(), "Unexpected WAV fallback file was written"

    def test_execute_music_batch_full_fixture_without_encoder_dependency(self, tmp_path, monkeypatch):
        """Execute the full committed music fixture with a patched OGG writer for broad integration coverage."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch
        from audio_engine.export.audio_exporter import AudioExporter

        def _fake_write_ogg(_exporter, audio, path):  # pragma: no cover - injected behavior
            return _exporter._write_wav(audio, path)

        monkeypatch.setattr(AudioExporter, "_write_ogg", _fake_write_ogg)

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.music.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        assert len(manifest.errors) == 0, manifest.errors
        assert len(manifest.music) == len(batch.requests)

    def test_request_batch_pipeline_uses_request_backend(self, tmp_path):
        """RequestBatchPipeline must respect request.backend for generation."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch
        from audio_engine.integration.factory_inputs import GenerationRequestBatch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        bad_request = replace(batch.requests[0], backend="invalid_backend")
        single_request_batch = GenerationRequestBatch(
            request_batch_version=batch.request_batch_version,
            project=batch.project,
            scope=batch.scope,
            requests=[bad_request],
        )

        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(single_request_batch, tmp_path)
        assert len(manifest.errors) == 1
        assert "Unknown backend 'invalid_backend'" in manifest.errors[0]

    def test_progress_callback_invoked(self, tmp_path):
        """Progress messages should be emitted during batch execution."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        messages: list[str] = []
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(
            progress_callback=messages.append,
            skip_existing=False,
        )
        pipeline.execute(batch, tmp_path)

        assert len(messages) > 0, "No progress messages were emitted"

    def test_provenance_files_written(self, tmp_path):
        """execute() must write a .provenance.json sidecar for every generated file."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        assert len(manifest.errors) == 0
        for record in manifest.sfx:
            audio_path = Path(record["file"])
            provenance_path = audio_path.with_name(audio_path.stem + ".provenance.json")
            assert provenance_path.exists(), f"Missing provenance file: {provenance_path}"

    def test_provenance_required_fields(self, tmp_path):
        """Each .provenance.json must contain the required traceability fields."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        required_keys = {
            "provenanceVersion",
            "requestId",
            "assetId",
            "type",
            "backend",
            "seed",
            "generatedOutputPath",
            "targetImportPath",
            "reviewStatus",
            "generatedAt",
        }
        for record in manifest.sfx:
            audio_path = Path(record["file"])
            provenance_path = audio_path.with_name(audio_path.stem + ".provenance.json")
            data = json.loads(provenance_path.read_text())
            missing = required_keys - data.keys()
            assert not missing, (
                f"Provenance for {record['request_id']} is missing keys: {missing}"
            )

    def test_provenance_seed_matches_request(self, tmp_path):
        """Seed in provenance file must match the seed in the batch request."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(batch, tmp_path)

        request_seeds = {r.request_id: r.seed for r in batch.requests}
        for record in manifest.sfx:
            audio_path = Path(record["file"])
            provenance_path = audio_path.with_name(audio_path.stem + ".provenance.json")
            data = json.loads(provenance_path.read_text())
            assert data["seed"] == request_seeds[data["requestId"]], (
                f"Provenance seed mismatch for {data['requestId']}"
            )

    def test_provenance_includes_sfx_variant_metadata(self, tmp_path):
        """SFX variant requests should record variation family/index in provenance."""
        from audio_engine.integration import RequestBatchPipeline

        variant_batch = parse_generation_request_batch(
            {
                "requestBatchVersion": "1.0.0",
                "project": "GameRewritten",
                "scope": "variation-tests",
                "requests": [
                    {
                        "requestVersion": "1.0.0",
                        "requestId": "req_sfx_ui_confirm_var01",
                        "assetId": "sfx_ui_confirm_var01",
                        "type": "sfx",
                        "backend": "procedural",
                        "seed": 101,
                        "prompt": "ui confirm click variant one",
                        "styleFamily": "heroic-sci-fantasy",
                        "output": {
                            "targetPath": "Content/Audio/sfx_ui_confirm_var01.wav",
                            "format": "wav",
                            "sampleRate": 44100,
                            "channels": 1,
                        },
                        "qa": {"loopRequired": False, "reviewStatus": "draft"},
                    },
                    {
                        "requestVersion": "1.0.0",
                        "requestId": "req_sfx_ui_confirm_var02",
                        "assetId": "sfx_ui_confirm_var02",
                        "type": "sfx",
                        "backend": "procedural",
                        "seed": 102,
                        "prompt": "ui confirm click variant two",
                        "styleFamily": "heroic-sci-fantasy",
                        "output": {
                            "targetPath": "Content/Audio/sfx_ui_confirm_var02.wav",
                            "format": "wav",
                            "sampleRate": 44100,
                            "channels": 1,
                        },
                        "qa": {"loopRequired": False, "reviewStatus": "draft"},
                    },
                ],
            },
            source="variant_provenance_batch",
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        manifest = pipeline.execute(variant_batch, tmp_path)
        assert not manifest.errors

        observed_indices: list[int] = []
        for record in manifest.sfx:
            audio_path = Path(record["file"])
            provenance_path = audio_path.with_name(audio_path.stem + ".provenance.json")
            data = json.loads(provenance_path.read_text())
            assert data["variationFamily"] == "sfx_ui_confirm"
            observed_indices.append(data["variationIndex"])
        assert set(observed_indices) == {1, 2}

    def test_provenance_not_written_for_skipped(self, tmp_path):
        """No provenance file should be written for skipped (already-existing) files."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        # Pre-create the first output file as a sentinel using the request_id stem convention.
        first_request = batch.requests[0]
        type_dir = tmp_path / "drafts" / first_request.type
        type_dir.mkdir(parents=True)
        sentinel_name = (
            first_request.request_id + "." + first_request.output.format.lower()
        )
        sentinel = type_dir / sentinel_name
        sentinel.write_bytes(b"SENTINEL")

        pipeline = RequestBatchPipeline(skip_existing=True)
        pipeline.execute(batch, tmp_path)

        # Provenance file must NOT be written for the skipped file.
        prov_path = sentinel.with_name(sentinel.stem + ".provenance.json")
        assert not prov_path.exists(), (
            "Provenance file should not be written for skipped assets"
        )


class TestDraftExportPipeline:
    """Tests for the DraftExportPipeline."""

    def _make_factory_root_with_sfx(self, tmp_path: Path) -> Path:
        """Generate a batch of SFX into tmp_path/drafts/ and return tmp_path."""
        from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch

        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = RequestBatchPipeline(skip_existing=False)
        pipeline.execute(batch, tmp_path)
        return tmp_path

    def test_export_creates_files(self, tmp_path):
        """DraftExportPipeline.export() must copy audio files to the export surface."""
        from audio_engine.integration import DraftExportPipeline

        factory_root = self._make_factory_root_with_sfx(tmp_path)
        pipeline = DraftExportPipeline()
        manifest = pipeline.export(factory_root)

        assert manifest["summary"]["total"] > 0
        for entry in manifest["entries"]:
            dest = Path(entry["destination"])
            assert dest.exists(), f"Exported file missing: {dest}"

    def test_export_uses_provenance_targetImportPath(self, tmp_path):
        """Exported filenames must match targetImportPath from provenance sidecars."""
        from audio_engine.integration import DraftExportPipeline

        factory_root = self._make_factory_root_with_sfx(tmp_path)
        pipeline = DraftExportPipeline()
        manifest = pipeline.export(factory_root)

        for entry in manifest["entries"]:
            source_path = Path(entry["source"])
            provenance_path = source_path.with_name(source_path.stem + ".provenance.json")
            if provenance_path.exists():
                provenance = json.loads(provenance_path.read_text())
                expected_name = Path(provenance["targetImportPath"]).name
                actual_name = Path(entry["destination"]).name
                assert actual_name == expected_name, (
                    f"Expected exported name {expected_name!r}, got {actual_name!r}"
                )

    def test_export_writes_manifest(self, tmp_path):
        """DraftExportPipeline.export() must write export_manifest.json."""
        from audio_engine.integration import DraftExportPipeline

        factory_root = self._make_factory_root_with_sfx(tmp_path)
        pipeline = DraftExportPipeline()
        pipeline.export(factory_root)

        manifest_path = tmp_path / "exports" / "gamerewritten" / "export_manifest.json"
        assert manifest_path.exists(), "export_manifest.json was not written"
        data = json.loads(manifest_path.read_text())
        assert "exportManifestVersion" in data
        assert "entries" in data
        assert "summary" in data
        assert len(data["entries"]) > 0

    def test_export_manifest_has_required_fields(self, tmp_path):
        """Each entry in export_manifest.json must have 'source' and 'destination' keys."""
        from audio_engine.integration import DraftExportPipeline

        factory_root = self._make_factory_root_with_sfx(tmp_path)
        pipeline = DraftExportPipeline()
        pipeline.export(factory_root)

        manifest_path = tmp_path / "exports" / "gamerewritten" / "export_manifest.json"
        data = json.loads(manifest_path.read_text())
        for entry in data["entries"]:
            assert "source" in entry, "Missing 'source' in entry"
            assert "destination" in entry, "Missing 'destination' in entry"

    def test_export_does_not_modify_drafts(self, tmp_path):
        """DraftExportPipeline.export() must not delete or modify files in drafts/."""
        from audio_engine.integration import DraftExportPipeline

        factory_root = self._make_factory_root_with_sfx(tmp_path)

        # Record all files in drafts/ before export.
        drafts_dir = tmp_path / "drafts"
        before = set(str(p) for p in drafts_dir.rglob("*") if p.is_file())

        pipeline = DraftExportPipeline()
        pipeline.export(factory_root)

        after = set(str(p) for p in drafts_dir.rglob("*") if p.is_file())
        assert before == after, (
            "DraftExportPipeline modified the drafts/ directory.\n"
            f"  Removed: {before - after}\n"
            f"  Added: {after - before}"
        )

    def test_export_raises_on_empty_drafts(self, tmp_path):
        """DraftExportPipeline.export() must raise ValueError if no audio files exist."""
        from audio_engine.integration import DraftExportPipeline

        # Don't generate anything; drafts/ is empty.
        pipeline = DraftExportPipeline()
        with pytest.raises(ValueError, match="No audio files found"):
            pipeline.export(tmp_path)

    def test_export_falls_back_to_audio_name_without_provenance(self, tmp_path):
        """If no provenance sidecar exists, the audio filename is used as-is."""
        from audio_engine.integration import DraftExportPipeline

        # Create a WAV file without a provenance sidecar.
        drafts_sfx = tmp_path / "drafts" / "sfx"
        drafts_sfx.mkdir(parents=True)
        wav_path = drafts_sfx / "test_no_provenance.wav"
        wav_path.write_bytes(b"RIFF")  # Minimal placeholder.

        pipeline = DraftExportPipeline()
        manifest = pipeline.export(tmp_path)

        assert len(manifest["entries"]) == 1
        exported_name = Path(manifest["entries"][0]["destination"]).name
        assert exported_name == "test_no_provenance.wav"


# ---------------------------------------------------------------------------
# PlanBatchOrchestrator tests
# ---------------------------------------------------------------------------

class TestPlanBatchOrchestrator:
    """Tests for plan-driven batch orchestration."""

    @staticmethod
    def _make_sfx_plan_from_batch(batch: GenerationRequestBatch) -> AudioPlan:
        selected = batch.requests[:2]
        plan_payload = {
            "planVersion": "1.0.0",
            "project": batch.project,
            "scope": batch.scope,
            "priorities": {"music": "high", "sfx": "high", "voice": "low"},
            "styleFamilies": ["heroic-sci-fantasy"],
            "assetGroups": [
                {
                    "groupId": "sfx-required",
                    "type": "sfx",
                    "required": True,
                    "targets": [
                        {
                            "assetId": req.asset_id,
                            "gameplayRole": f"role-{index}",
                            "targetPath": req.output.target_path,
                            "loop": req.qa.loop_required,
                            "durationTargetSeconds": 0.2,
                        }
                        for index, req in enumerate(selected)
                    ],
                }
            ],
        }
        return parse_audio_plan(plan_payload, source="test_plan")

    def test_execute_plan_drives_subset_generation(self, tmp_path):
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        plan = self._make_sfx_plan_from_batch(batch)
        orchestrator = PlanBatchOrchestrator(skip_existing=False)
        manifest = orchestrator.execute(plan, [batch], tmp_path)

        assert len(manifest.errors) == 0, manifest.errors
        assert len(manifest.sfx) == 2
        produced_request_ids = [record["request_id"] for record in manifest.sfx]
        expected_request_ids = [batch.requests[0].request_id, batch.requests[1].request_id]
        assert produced_request_ids == expected_request_ids

    def test_execute_plan_missing_required_request_raises(self, tmp_path):
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        plan = self._make_sfx_plan_from_batch(batch)
        truncated_batch = replace(batch, requests=[batch.requests[0]])
        orchestrator = PlanBatchOrchestrator(skip_existing=False)

        with pytest.raises(ValueError, match="missing generation requests for required plan assetIds"):
            orchestrator.execute(plan, [truncated_batch], tmp_path)

    def test_execute_plan_rejects_type_mismatch(self, tmp_path):
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        plan = self._make_sfx_plan_from_batch(batch)
        mismatched_request = replace(batch.requests[0], type="music")
        bad_batch = replace(batch, requests=[mismatched_request, batch.requests[1]])
        orchestrator = PlanBatchOrchestrator(skip_existing=False)

        with pytest.raises(ValueError, match="plan/request type mismatch"):
            orchestrator.execute(plan, [bad_batch], tmp_path)

    def test_execute_plan_rejects_target_path_mismatch(self, tmp_path):
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        plan = self._make_sfx_plan_from_batch(batch)
        mismatched_request = replace(
            batch.requests[0],
            output=replace(batch.requests[0].output, target_path="Content/Audio/other.wav"),
        )
        bad_batch = replace(batch, requests=[mismatched_request, batch.requests[1]])
        orchestrator = PlanBatchOrchestrator(skip_existing=False)

        with pytest.raises(ValueError, match="plan/request targetPath mismatch"):
            orchestrator.execute(plan, [bad_batch], tmp_path)

    def test_execute_plan_rejects_unsupported_plan_format(self, tmp_path):
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        plan = self._make_sfx_plan_from_batch(batch)
        target = plan.asset_groups[0].targets[0]
        bad_plan = parse_audio_plan(
            {
                "planVersion": plan.plan_version,
                "project": plan.project,
                "scope": plan.scope,
                "priorities": {
                    "music": plan.priorities.music,
                    "sfx": plan.priorities.sfx,
                    "voice": plan.priorities.voice,
                },
                "styleFamilies": plan.style_families,
                "assetGroups": [
                    {
                        "groupId": "sfx-required",
                        "type": "sfx",
                        "required": True,
                        "targets": [
                            {
                                "assetId": target.asset_id,
                                "gameplayRole": target.gameplay_role,
                                "targetPath": target.target_path.replace(".wav", ".mp3"),
                                "loop": target.loop,
                                "durationTargetSeconds": target.duration_target_seconds,
                            }
                        ],
                    }
                ],
            },
            source="bad_plan",
        )
        bad_request = replace(
            batch.requests[0],
            output=replace(
                batch.requests[0].output,
                target_path=target.target_path.replace(".wav", ".mp3"),
                format="mp3",
            ),
        )
        bad_batch = replace(batch, requests=[bad_request])
        orchestrator = PlanBatchOrchestrator(skip_existing=False)

        with pytest.raises(ValueError, match="unsupported plan target format"):
            orchestrator.execute(bad_plan, [bad_batch], tmp_path)


# ---------------------------------------------------------------------------
# RequestBatch execution
# ---------------------------------------------------------------------------

class TestRequestBatchExecution:
    """Smoke tests for AssetPipeline.execute_request_batch() using committed fixtures."""

    def test_execute_sfx_batch_from_fixture(self, tmp_path):
        """All SFX requests in the committed fixture should produce output files."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            batch,
            tmp_path,
            default_sfx_duration=0.1,  # short for test speed
        )

        assert isinstance(result, RequestBatchResult)
        assert result.project == "GameRewritten"
        assert result.scope == "vertical-slice"
        assert len(result.records) == len(batch.requests)

        errors = [r for r in result.records if r.status == "error"]
        assert not errors, f"SFX batch had errors: {[r.error for r in errors]}"

        for record in result.records:
            assert record.status == "ok"
            assert Path(record.output_path).exists(), f"Missing output: {record.output_path}"

    def test_execute_sfx_batch_from_fixture_passes_qa_gate(self, tmp_path):
        """Committed SFX fixture should pass qa-batch loudness/peak/clipping checks."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(batch, tmp_path)
        assert not [record for record in result.records if record.status == "error"]

        report_path = tmp_path / "qa_report.json"
        exit_code = main(
            [
                "qa-batch",
                "--input-dir",
                str(tmp_path / "Content" / "Audio"),
                "--output-report",
                str(report_path),
                "--recursive",
                "--quiet",
            ]
        )
        assert exit_code == 0
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["summary"]["failed"] == 0

    def test_execute_music_batch_first_request(self, tmp_path):
        """At least the WAV-format music request (stinger) should produce a non-empty output file."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.music.v1.json"
        )
        # Use the stinger request which outputs WAV (no optional soundfile dep needed).
        wav_requests = [r for r in batch.requests if r.output.format == "wav"]
        assert wav_requests, "No WAV-format music requests found in fixture"

        from audio_engine.integration.factory_inputs import GenerationRequestBatch

        single_request_batch = GenerationRequestBatch(
            request_batch_version=batch.request_batch_version,
            project=batch.project,
            scope=batch.scope,
            requests=[wav_requests[0]],
        )

        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            single_request_batch,
            tmp_path,
            default_music_duration=2.0,  # short for test speed
        )

        assert len(result.records) == 1
        record = result.records[0]
        assert record.status == "ok", f"Music request failed: {record.error}"
        assert Path(record.output_path).exists()
        assert Path(record.output_path).stat().st_size > 0

    def test_seeds_are_per_request(self, tmp_path):
        """Each result record must carry the seed from its source request."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            batch,
            tmp_path,
            default_sfx_duration=0.1,
        )

        request_seeds = {req.request_id: req.seed for req in batch.requests}
        for record in result.records:
            assert record.seed == request_seeds[record.request_id], (
                f"Seed mismatch for {record.request_id}: "
                f"expected {request_seeds[record.request_id]}, got {record.seed}"
            )

    def test_skip_existing_files(self, tmp_path):
        """force=False should skip files that already exist."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        first_request = batch.requests[0]
        existing_path = tmp_path / first_request.output.target_path
        existing_path.parent.mkdir(parents=True, exist_ok=True)
        existing_path.write_bytes(b"PLACEHOLDER")
        mtime_before = existing_path.stat().st_mtime

        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            batch,
            tmp_path,
            force=False,
            default_sfx_duration=0.1,
        )

        first_record = next(r for r in result.records if r.request_id == first_request.request_id)
        assert first_record.status == "skipped"
        assert existing_path.stat().st_mtime == mtime_before, "File was modified despite force=False"

    def test_force_overwrites_existing_files(self, tmp_path):
        """force=True should regenerate files that already exist."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        from audio_engine.integration.factory_inputs import GenerationRequestBatch

        single_request_batch = GenerationRequestBatch(
            request_batch_version=batch.request_batch_version,
            project=batch.project,
            scope=batch.scope,
            requests=[batch.requests[0]],
        )
        first_request = single_request_batch.requests[0]
        existing_path = tmp_path / first_request.output.target_path
        existing_path.parent.mkdir(parents=True, exist_ok=True)
        existing_path.write_bytes(b"STALE")

        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            single_request_batch,
            tmp_path,
            force=True,
            default_sfx_duration=0.1,
        )

        assert result.records[0].status == "ok"
        assert existing_path.stat().st_size > 4, "File was not overwritten"

    def test_result_summary_non_empty(self, tmp_path):
        """RequestBatchResult.summary() should produce a non-empty string."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            batch,
            tmp_path,
            default_sfx_duration=0.1,
        )
        summary = result.summary()
        assert "GameRewritten" in summary
        assert "OK" in summary

    def test_result_to_json_roundtrip(self):
        """RequestBatchResult.to_json() should produce valid JSON."""
        result = RequestBatchResult(
            output_dir="/tmp/test",
            project="TestProject",
            scope="test",
            records=[
                RequestBatchRecord(
                    request_id="req_test_1",
                    asset_id="sfx_test",
                    type="sfx",
                    seed=42,
                    output_path="/tmp/test/sfx.wav",
                    status="ok",
                )
            ],
            total_duration_seconds=0.5,
        )
        data = json.loads(result.to_json())
        assert data["project"] == "TestProject"
        assert len(data["records"]) == 1
        assert data["records"][0]["seed"] == 42
        assert data["records"][0]["status"] == "ok"

    def test_execute_request_batch_rejects_unsafe_target_path(self, tmp_path):
        """Unsafe targetPath values should be rejected and recorded as errors."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        bad_request = replace(
            batch.requests[0],
            output=replace(batch.requests[0].output, target_path="../escape.wav"),
        )
        single_request_batch = replace(batch, requests=[bad_request])

        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            single_request_batch,
            tmp_path,
            default_sfx_duration=0.1,
        )

        assert len(result.records) == 1
        assert result.records[0].status == "error"
        assert "unsafe targetPath" in (result.records[0].error or "")

    def test_music_request_uses_request_backend(self, tmp_path):
        """Music request backend must be respected for request-batch execution."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.music.v1.json"
        )
        wav_requests = [r for r in batch.requests if r.output.format == "wav"]
        assert wav_requests, "No WAV-format music requests found in fixture"
        bad_backend_request = replace(wav_requests[0], backend="invalid_backend")
        single_request_batch = replace(batch, requests=[bad_backend_request])

        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            single_request_batch,
            tmp_path,
            default_music_duration=0.1,
        )

        assert len(result.records) == 1
        assert result.records[0].status == "error"
        assert "Unknown backend 'invalid_backend'" in (result.records[0].error or "")

    def test_execute_sfx_request_honors_channels_and_actual_export_path(self, tmp_path):
        """SFX requests should honor channels and record the path actually written by exporter."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        request = replace(
            batch.requests[0],
            output=replace(
                batch.requests[0].output,
                target_path="Content/Audio/custom_sfx_path.ogg",
                format="wav",
                channels=2,
            ),
        )
        single_request_batch = replace(batch, requests=[request])

        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            single_request_batch,
            tmp_path,
            default_sfx_duration=0.1,
        )

        assert len(result.records) == 1
        record = result.records[0]
        assert record.status == "ok", record.error
        assert record.output_path.endswith(".wav")
        output_path = Path(record.output_path)
        assert output_path.exists()
        with wave.open(str(output_path), "rb") as wav_file:
            assert wav_file.getnchannels() == 2

    def test_execute_voice_request_honors_channels_and_actual_export_path(self, tmp_path):
        """Voice requests should honor channels/format and record the actual exporter path."""
        batch = parse_generation_request_batch(
            {
                "requestBatchVersion": "1.0.0",
                "project": "GameRewritten",
                "scope": "tests",
                "requests": [
                    {
                        "requestVersion": "1.0.0",
                        "requestId": "req_voice_test_v1",
                        "assetId": "voice_test",
                        "type": "voice",
                        "backend": "procedural",
                        "seed": 12,
                        "prompt": "Welcome to the dungeon.",
                        "styleFamily": "fantasy-rpg",
                        "output": {
                            "targetPath": "Content/Audio/voice_test.ogg",
                            "format": "wav",
                            "sampleRate": 22050,
                            "channels": 2,
                        },
                        "qa": {
                            "loopRequired": False,
                            "reviewStatus": "draft",
                        },
                    }
                ],
            },
            source="voice_test_batch",
        )
        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(batch, tmp_path)

        assert len(result.records) == 1
        record = result.records[0]
        assert record.status == "ok", record.error
        assert record.output_path.endswith(".wav")
        output_path = Path(record.output_path)
        assert output_path.exists()
        with wave.open(str(output_path), "rb") as wav_file:
            assert wav_file.getnchannels() == 2

    def test_execute_request_batch_rejects_unsupported_channel_count(self, tmp_path):
        """Unsupported channel counts should fail with a clear per-request error."""
        batch = load_generation_request_batch(
            EXAMPLE_FACTORY_INPUTS_DIR / "generation_requests.sfx.v1.json"
        )
        bad_request = replace(
            batch.requests[0],
            output=replace(batch.requests[0].output, channels=3),
        )
        single_request_batch = replace(batch, requests=[bad_request])
        pipeline = AssetPipeline()
        result = pipeline.execute_request_batch(
            single_request_batch,
            tmp_path,
            default_sfx_duration=0.1,
        )

        assert len(result.records) == 1
        assert result.records[0].status == "error"
        assert "unsupported channel count 3" in (result.records[0].error or "")


# ---------------------------------------------------------------------------
# ApprovalWorkflow tests (SESSION-006)
# ---------------------------------------------------------------------------

class TestApprovalWorkflow:
    """Tests for the approval workflow (draft → approved promotion)."""

    def _make_draft_with_provenance(self, tmp_path: Path, request_id: str = "req_sfx_test_v1") -> Path:
        """Create a minimal draft WAV + provenance sidecar and return the WAV path."""
        import wave as wv

        drafts_sfx = tmp_path / "drafts" / "sfx"
        drafts_sfx.mkdir(parents=True, exist_ok=True)
        wav_path = drafts_sfx / f"{request_id}.wav"

        # Write a minimal valid WAV (100 samples of silence).
        with wv.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(b"\x00\x00" * 100)

        prov = {
            "provenanceVersion": "1.0.0",
            "requestId": request_id,
            "assetId": "sfx_test",
            "type": "sfx",
            "backend": "procedural",
            "seed": 42,
            "prompt": "test sfx",
            "styleFamily": "heroic-sci-fantasy",
            "generatedOutputPath": str(wav_path),
            "targetImportPath": f"Content/Audio/{request_id}.wav",
            "reviewStatus": "draft",
            "generatedAt": "2026-05-15T00:00:00+00:00",
        }
        prov_path = wav_path.with_name(wav_path.stem + ".provenance.json")
        prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")
        return wav_path

    def test_approve_copies_audio_file(self, tmp_path):
        """approve() must copy the audio file to approved/<type>/."""
        from audio_engine.integration import ApprovalWorkflow

        draft_path = self._make_draft_with_provenance(tmp_path)
        workflow = ApprovalWorkflow()
        record = workflow.approve(tmp_path, draft_path)

        approved_path = Path(record["approvedPath"])
        assert approved_path.exists(), f"Approved file not found: {approved_path}"
        assert approved_path.stat().st_size > 0

    def test_approve_places_file_in_approved_type_dir(self, tmp_path):
        """Approved files must land in <factory_root>/approved/<type>/."""
        from audio_engine.integration import ApprovalWorkflow

        draft_path = self._make_draft_with_provenance(tmp_path)
        workflow = ApprovalWorkflow()
        record = workflow.approve(tmp_path, draft_path)

        approved_path = Path(record["approvedPath"])
        expected_dir = tmp_path / "approved" / "sfx"
        assert approved_path.parent == expected_dir

    def test_approve_updates_review_status_in_provenance(self, tmp_path):
        """approve() must set reviewStatus = 'approved' in both provenance files."""
        from audio_engine.integration import ApprovalWorkflow

        draft_path = self._make_draft_with_provenance(tmp_path)
        workflow = ApprovalWorkflow()
        record = workflow.approve(tmp_path, draft_path)

        # Check approved provenance.
        approved_prov_path = Path(record["approvedPath"]).with_name(
            Path(record["approvedPath"]).stem + ".provenance.json"
        )
        assert approved_prov_path.exists()
        approved_prov = json.loads(approved_prov_path.read_text())
        assert approved_prov["reviewStatus"] == "approved"
        assert "approvedAt" in approved_prov
        assert "approvedPath" in approved_prov

        # Draft provenance should also be updated.
        draft_prov_path = draft_path.with_name(draft_path.stem + ".provenance.json")
        draft_prov = json.loads(draft_prov_path.read_text())
        assert draft_prov["reviewStatus"] == "approved"

    def test_approve_record_has_required_fields(self, tmp_path):
        """approve() return value must contain all required keys."""
        from audio_engine.integration import ApprovalWorkflow

        draft_path = self._make_draft_with_provenance(tmp_path)
        workflow = ApprovalWorkflow()
        record = workflow.approve(tmp_path, draft_path)

        for key in ("requestId", "assetId", "type", "draftPath", "approvedPath", "approvedAt"):
            assert key in record, f"Missing key '{key}' in approval record"
        assert record["type"] == "sfx"

    def test_approve_raises_on_draft_path_outside_factory(self, tmp_path):
        """approve() must raise ValueError when draft_path is outside factory_root/drafts/."""
        from audio_engine.integration import ApprovalWorkflow
        import wave as wv

        # Create a WAV file outside the factory's drafts tree.
        outside = tmp_path / "outside"
        outside.mkdir()
        wav_path = outside / "stray.wav"
        with wv.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(b"\x00\x00" * 100)

        factory_root = tmp_path / "factory"
        factory_root.mkdir()
        workflow = ApprovalWorkflow()
        with pytest.raises(ValueError, match="draft_path must be under"):
            workflow.approve(factory_root, wav_path)

    def test_approve_raises_on_traversal_in_asset_type(self, tmp_path):
        """approve() must raise ValueError when the provenance 'type' contains path traversal."""
        from audio_engine.integration import ApprovalWorkflow
        import wave as wv
        import json as _json

        drafts_sfx = tmp_path / "drafts" / "sfx"
        drafts_sfx.mkdir(parents=True)
        wav_path = drafts_sfx / "req_traversal.wav"
        with wv.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(b"\x00\x00" * 100)

        prov = {
            "provenanceVersion": "1.0.0",
            "requestId": "req_traversal",
            "assetId": "traversal_test",
            "type": "../outside",  # Malicious traversal value.
            "reviewStatus": "draft",
        }
        prov_path = wav_path.with_name(wav_path.stem + ".provenance.json")
        prov_path.write_text(_json.dumps(prov), encoding="utf-8")

        workflow = ApprovalWorkflow()
        with pytest.raises(ValueError, match="unsafe asset type"):
            workflow.approve(tmp_path, wav_path)

    def test_approve_raises_on_missing_file(self, tmp_path):
        """approve() must raise FileNotFoundError when the draft file does not exist."""
        from audio_engine.integration import ApprovalWorkflow

        workflow = ApprovalWorkflow()
        missing = tmp_path / "drafts" / "sfx" / "nonexistent.wav"
        with pytest.raises(FileNotFoundError, match="draft file not found"):
            workflow.approve(tmp_path, missing)

    def test_approve_raises_on_unsupported_extension(self, tmp_path):
        """approve() must raise ValueError for unsupported file types."""
        from audio_engine.integration import ApprovalWorkflow

        drafts_sfx = tmp_path / "drafts" / "sfx"
        drafts_sfx.mkdir(parents=True, exist_ok=True)
        bad_file = drafts_sfx / "test.mp3"
        bad_file.write_bytes(b"MP3DATA")
        workflow = ApprovalWorkflow()
        with pytest.raises(ValueError, match="unsupported file type"):
            workflow.approve(tmp_path, bad_file)

    def test_approve_without_provenance_sidecar(self, tmp_path):
        """approve() must still work even if no .provenance.json sidecar exists."""
        from audio_engine.integration import ApprovalWorkflow
        import wave as wv

        drafts_sfx = tmp_path / "drafts" / "sfx"
        drafts_sfx.mkdir(parents=True)
        wav_path = drafts_sfx / "req_no_prov.wav"
        with wv.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(b"\x00\x00" * 100)

        workflow = ApprovalWorkflow()
        record = workflow.approve(tmp_path, wav_path)

        assert Path(record["approvedPath"]).exists()
        assert record["type"] == "sfx"  # Inferred from parent directory name.

    def test_approve_batch_approves_multiple_files(self, tmp_path):
        """approve_batch() must approve all provided files."""
        from audio_engine.integration import ApprovalWorkflow

        paths = [
            self._make_draft_with_provenance(tmp_path, f"req_sfx_batch_{i}_v1")
            for i in range(3)
        ]
        workflow = ApprovalWorkflow()
        records = workflow.approve_batch(tmp_path, paths)

        assert len(records) == 3
        assert all(r["status"] == "ok" for r in records)
        for record in records:
            assert Path(record["approvedPath"]).exists()

    def test_approve_batch_records_errors_without_raising(self, tmp_path):
        """approve_batch() must record individual errors without raising."""
        from audio_engine.integration import ApprovalWorkflow

        draft_path = self._make_draft_with_provenance(tmp_path)
        missing_path = tmp_path / "drafts" / "sfx" / "does_not_exist.wav"
        workflow = ApprovalWorkflow()
        records = workflow.approve_batch(tmp_path, [draft_path, missing_path])

        assert len(records) == 2
        ok_records = [r for r in records if r.get("status") == "ok"]
        err_records = [r for r in records if r.get("status") == "error"]
        assert len(ok_records) == 1
        assert len(err_records) == 1
        assert "error" in err_records[0]

    def test_approve_draft_cli_command(self, tmp_path, capsys):
        """approve-draft CLI command must approve a file and return exit code 0."""
        draft_path = self._make_draft_with_provenance(tmp_path)
        rc = main([
            "approve-draft",
            "--factory-root", str(tmp_path),
            "--draft-file", str(draft_path),
        ])
        assert rc == 0
        captured = capsys.readouterr()
        assert "1 approved" in captured.out

        approved_path = tmp_path / "approved" / "sfx" / draft_path.name
        assert approved_path.exists()

    def test_approve_draft_cli_with_report(self, tmp_path):
        """approve-draft CLI must write a JSON report when --output-report is given."""
        draft_path = self._make_draft_with_provenance(tmp_path)
        report_path = tmp_path / "approval_report.json"
        rc = main([
            "approve-draft",
            "--factory-root", str(tmp_path),
            "--draft-file", str(draft_path),
            "--output-report", str(report_path),
        ])
        assert rc == 0
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert "approvals" in data
        assert len(data["approvals"]) == 1
        assert data["approvals"][0]["status"] == "ok"

    def test_approve_draft_cli_missing_file_returns_nonzero(self, tmp_path):
        """approve-draft CLI must return non-zero when a draft file is missing."""
        rc = main([
            "approve-draft",
            "--factory-root", str(tmp_path),
            "--draft-file", str(tmp_path / "drafts" / "sfx" / "nonexistent.wav"),
        ])
        assert rc != 0

    def test_integration_init_exports_approval_workflow(self):
        """ApprovalWorkflow must be exported from audio_engine.integration."""
        from audio_engine import integration
        assert hasattr(integration, "ApprovalWorkflow")
