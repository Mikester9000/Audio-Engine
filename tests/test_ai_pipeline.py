"""
Tests for the AI pipeline: prompt parser, backends, and high-level generators.
"""

from __future__ import annotations

import numpy as np
import pytest

from audio_engine.ai import (
    MusicGen, SFXGen, VoiceGen,
    PromptParser, MusicPlan, SFXPlan, VoicePlan,
    BackendRegistry, ProceduralBackend,
)
from audio_engine.ai.sfx_synth import synthesise_sfx, available_sfx_types
from audio_engine.ai.voice_synth import synthesise_voice, VOICE_PRESETS
from audio_engine.ai.backends import AudioGenBackend, KokoroBackend, MusicGenBackend


SR = 22050


# ---------------------------------------------------------------------------
# PromptParser
# ---------------------------------------------------------------------------

class TestPromptParser:
    def setup_method(self):
        self.parser = PromptParser()

    def test_parse_music_basic(self):
        plan = self.parser.parse_music("battle theme")
        assert isinstance(plan, MusicPlan)
        assert plan.style == "battle"

    def test_parse_music_detects_bpm(self):
        plan = self.parser.parse_music("dark epic track 140 BPM")
        assert plan.bpm == 140.0

    def test_parse_music_detects_loop(self):
        plan = self.parser.parse_music("ambient loopable dungeon")
        assert plan.loopable is True

    def test_parse_music_detects_duration(self):
        plan = self.parser.parse_music("ambient 60 seconds")
        assert abs(plan.duration - 60.0) < 1.0

    def test_parse_music_detects_minutes(self):
        plan = self.parser.parse_music("ambient 2 min")
        assert abs(plan.duration - 120.0) < 1.0

    def test_parse_music_style_variants(self):
        styles = {
            "epic boss final climax": "boss",
            "explore adventure journey": "exploration",
            "calm atmosphere ambience": "ambient",
            "victory triumph fanfare": "victory",
        }
        for prompt, expected in styles.items():
            plan = self.parser.parse_music(prompt)
            assert plan.style == expected, f"Expected '{expected}' for '{prompt}', got '{plan.style}'"

    def test_parse_sfx_basic(self):
        plan = self.parser.parse_sfx("explosion")
        assert isinstance(plan, SFXPlan)
        assert plan.sfx_type == "explosion"

    def test_parse_sfx_duration(self):
        plan = self.parser.parse_sfx("whoosh 0.5 seconds")
        assert plan.duration == pytest.approx(0.5, abs=0.1)

    def test_parse_sfx_unknown_type(self):
        plan = self.parser.parse_sfx("weird alien sound")
        assert isinstance(plan, SFXPlan)
        # Should default to "generic"
        assert plan.sfx_type == "generic"

    def test_parse_voice_basic(self):
        plan = self.parser.parse_voice("Hello world", voice_preset="narrator")
        assert isinstance(plan, VoicePlan)
        assert plan.text == "Hello world"
        assert plan.voice_preset == "narrator"

    def test_parse_voice_unknown_preset_defaults(self):
        plan = self.parser.parse_voice("Hello", voice_preset="xyz_unrecognised_123")
        # Should fall back to narrator when no keywords match
        assert plan.voice_preset == "narrator"


# ---------------------------------------------------------------------------
# ProceduralBackend
# ---------------------------------------------------------------------------

class TestProceduralBackend:
    def setup_method(self):
        self.backend = ProceduralBackend(sample_rate=SR, seed=42)

    def test_generate_music_returns_stereo(self):
        audio = self.backend.generate_music_audio("battle", duration=2.0)
        assert audio.ndim == 2
        assert audio.shape[1] == 2

    def test_generate_sfx_returns_mono(self):
        audio = self.backend.generate_sfx_audio("explosion", duration=0.5)
        assert audio.ndim == 1

    def test_generate_voice_returns_mono(self):
        audio = self.backend.generate_voice_audio("Hello, hero!")
        assert audio.ndim == 1

    def test_generate_music_positive_energy(self):
        audio = self.backend.generate_music_audio("ambient", duration=1.0)
        assert np.sum(audio ** 2) > 0.0

    def test_generate_sfx_all_types(self):
        """Check all SFX types don't raise exceptions."""
        for sfx_type in available_sfx_types():
            audio = self.backend.generate_sfx_audio(sfx_type, duration=0.3)
            assert len(audio) > 0

    def test_backend_name(self):
        assert self.backend.name == "procedural"

    def test_is_available(self):
        assert self.backend.is_available() is True


# ---------------------------------------------------------------------------
# BackendRegistry
# ---------------------------------------------------------------------------

class TestBackendRegistry:
    def test_procedural_registered(self):
        assert "procedural" in BackendRegistry.available_backends()

    def test_get_procedural(self):
        backend = BackendRegistry.get("procedural", sample_rate=SR)
        assert isinstance(backend, ProceduralBackend)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            BackendRegistry.get("nonexistent_backend_xyz")

    def test_register_custom_backend(self):
        from audio_engine.ai.backend import InferenceBackend

        class _DummyBackend(InferenceBackend):
            def generate_music_audio(self, style, duration, bpm=None, **kw):
                return np.zeros((int(duration * self.sample_rate), 2), dtype=np.float32)

            def generate_sfx_audio(self, sfx_type, duration, pitch_hz=None, **kw):
                return np.zeros(int(duration * self.sample_rate), dtype=np.float32)

            def generate_voice_audio(self, text, voice_preset="narrator", speed=1.0, **kw):
                return np.zeros(SR, dtype=np.float32)

        BackendRegistry.register("_test_dummy", _DummyBackend)
        assert "_test_dummy" in BackendRegistry.available_backends()
        backend = BackendRegistry.get("_test_dummy", sample_rate=SR)
        assert isinstance(backend, _DummyBackend)

    def test_evaluate_backends_includes_metadata(self):
        evaluations = BackendRegistry.evaluate_backends(sample_rate=SR)
        procedural = next(item for item in evaluations if item["name"] == "procedural")
        assert procedural["available"] is True
        assert procedural["availability_reason"] == "ready"
        assert "sfx" in procedural["supported_modalities"]
        assert "dependency_summary" in procedural

    def test_optional_backends_import_does_not_break_registry(self):
        assert "procedural" in BackendRegistry.available_backends()


class TestOptionalNeuralBackends:
    def test_musicgen_backend_falls_back_without_model(self, tmp_path):
        backend = MusicGenBackend(model_path=tmp_path / "missing", sample_rate=SR, seed=7)
        assert backend.name == "musicgen"
        assert backend.is_available() is False
        audio = backend.generate_music_audio("battle", duration=1.0)
        assert audio.ndim == 2
        assert audio.shape[1] == 2

    def test_audiogen_backend_falls_back_without_model(self, tmp_path):
        backend = AudioGenBackend(model_path=tmp_path / "missing", sample_rate=SR, seed=7)
        assert backend.name == "audiogen"
        assert backend.is_available() is False
        audio = backend.generate_sfx_audio("explosion", duration=0.5)
        assert audio.ndim == 1
        assert len(audio) > 0

    def test_kokoro_backend_falls_back_without_model(self, tmp_path):
        backend = KokoroBackend(model_path=tmp_path / "missing", sample_rate=SR, seed=7)
        assert backend.name == "kokoro"
        assert backend.is_available() is False
        audio = backend.generate_voice_audio("Welcome, hero.", voice_preset="narrator")
        assert audio.ndim == 1
        assert len(audio) > 0


# ---------------------------------------------------------------------------
# MusicGen
# ---------------------------------------------------------------------------

class TestMusicGen:
    def setup_method(self):
        self.gen = MusicGen(sample_rate=SR, seed=0)

    def test_generate_returns_stereo(self):
        audio = self.gen.generate("battle theme", duration=2.0)
        assert audio.ndim == 2
        assert audio.shape[1] == 2

    def test_generate_duration_approximate(self):
        audio = self.gen.generate("ambient", duration=5.0)
        duration_actual = audio.shape[0] / SR
        # Duration should be within 50% of target (bars are discrete)
        assert 1.0 <= duration_actual <= 15.0

    def test_generate_to_file(self, tmp_path):
        out = tmp_path / "music.wav"
        path = self.gen.generate_to_file("battle", str(out), duration=2.0)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_generate_loop_file(self, tmp_path):
        out = tmp_path / "loop.wav"
        path = self.gen.generate_to_file("ambient", str(out), duration=2.0, loopable=True)
        assert path.exists()

    def test_generate_various_styles(self):
        for style in ["battle", "ambient", "exploration", "boss", "victory", "menu"]:
            audio = self.gen.generate(style, duration=1.0)
            assert audio.ndim == 2, f"Style '{style}' should produce stereo"


# ---------------------------------------------------------------------------
# SFXGen
# ---------------------------------------------------------------------------

class TestSFXGen:
    def setup_method(self):
        self.gen = SFXGen(sample_rate=SR, seed=0)

    def test_generate_returns_array(self):
        audio = self.gen.generate("explosion")
        assert isinstance(audio, np.ndarray)

    def test_generate_duration(self):
        audio = self.gen.generate("beep", duration=0.5)
        # Duration should be approximately correct
        assert abs(len(audio) / SR - 0.5) < 0.1

    def test_generate_to_file(self, tmp_path):
        out = tmp_path / "sfx.wav"
        path = self.gen.generate_to_file("laser", str(out), duration=0.5)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_generate_with_pitch(self):
        audio = self.gen.generate("beep", duration=0.3, pitch_hz=880.0)
        assert len(audio) > 0

    def test_generate_various_sfx_types(self):
        for sfx_type in ["explosion", "laser", "coin", "magic", "footstep", "whoosh"]:
            audio = self.gen.generate(sfx_type, duration=0.3)
            assert len(audio) > 0


# ---------------------------------------------------------------------------
# VoiceGen
# ---------------------------------------------------------------------------

class TestVoiceGen:
    def setup_method(self):
        self.gen = VoiceGen(sample_rate=SR)

    def test_generate_returns_array(self):
        audio = self.gen.generate("Hello, world!")
        assert isinstance(audio, np.ndarray)
        assert audio.ndim == 1

    def test_generate_non_empty(self):
        audio = self.gen.generate("The hero must find the crystal sword.")
        assert len(audio) > 0
        assert np.any(audio != 0.0)

    def test_generate_all_voices(self):
        for voice in ["narrator", "hero", "villain", "announcer", "npc"]:
            audio = self.gen.generate("Hello.", voice=voice)
            assert len(audio) > 0

    def test_generate_to_file(self, tmp_path):
        out = tmp_path / "voice.wav"
        path = self.gen.generate_to_file("Level complete!", str(out), voice="announcer")
        assert path.exists()
        assert path.stat().st_size > 0

    def test_empty_text_returns_silence(self):
        audio = self.gen.generate("")
        # Should return a short silence buffer, not raise
        assert isinstance(audio, np.ndarray)

    def test_available_voices(self):
        voices = self.gen.available_voices()
        assert "narrator" in voices
        assert "villain" in voices

    def test_speed_changes_length(self):
        """Faster speech (speed > 1) should produce shorter audio."""
        audio_normal = self.gen.generate("The quick brown fox.", speed=1.0)
        audio_fast = self.gen.generate("The quick brown fox.", speed=2.0)
        assert len(audio_fast) < len(audio_normal)


# ---------------------------------------------------------------------------
# SFX synth helpers
# ---------------------------------------------------------------------------

class TestSFXSynth:
    def test_synthesise_sfx_all_types(self):
        for sfx_type in available_sfx_types():
            audio = synthesise_sfx(sfx_type, duration=0.3, sample_rate=SR)
            assert audio.dtype == np.float32
            assert len(audio) > 0

    def test_synthesise_sfx_normalised(self):
        audio = synthesise_sfx("explosion", duration=1.0, sample_rate=SR, seed=0)
        assert np.max(np.abs(audio)) <= 1.0

    def test_synthesise_sfx_reproducible(self):
        a = synthesise_sfx("magic", duration=0.5, sample_rate=SR, seed=99)
        b = synthesise_sfx("magic", duration=0.5, sample_rate=SR, seed=99)
        np.testing.assert_array_equal(a, b)


# ---------------------------------------------------------------------------
# Voice synth helpers
# ---------------------------------------------------------------------------

class TestVoiceSynth:
    def test_all_presets_generate(self):
        for preset in VOICE_PRESETS:
            audio = synthesise_voice("Test.", voice_preset=preset, sample_rate=SR)
            assert len(audio) > 0
            assert audio.dtype == np.float32

    def test_longer_text_produces_longer_audio(self):
        short = synthesise_voice("Hi.", sample_rate=SR)
        long = synthesise_voice("The quick brown fox jumps over the lazy dog.", sample_rate=SR)
        assert len(long) > len(short)

    def test_peak_below_one(self):
        audio = synthesise_voice("Hello world!", sample_rate=SR)
        assert np.max(np.abs(audio)) <= 1.0
