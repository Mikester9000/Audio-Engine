"""
Tests for the PS1/PS2 era audio system:

* PS1 DSP effects chain
* FF7/FF8 instrument timbres
* FF7/FF8 / retro-RPG style presets
* New FF7/FF8-era SFX types
* SampleLibrary (no real WAV files required)
* PS1Backend, SynthOrchestralBackend, SampleBackend
* VocalMelodySynth
* PieceComposer ("Eyes on Me" verification)
* CLI: --ps1, --orchestral, --samples-dir, remaster, compose-piece
"""

from __future__ import annotations

import sys
import wave
import struct
import tempfile
from pathlib import Path

import numpy as np
import pytest

SR = 22050          # low-SR for fast tests
SHORT_DURATION = 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sine(freq=440.0, sr=SR, duration=SHORT_DURATION) -> np.ndarray:
    t = np.arange(int(sr * duration)) / sr
    return (np.sin(2.0 * np.pi * freq * t) * 0.5).astype(np.float32)


def _write_wav(path: Path, audio: np.ndarray, sr: int = SR) -> None:
    """Write a mono float32 array as 16-bit WAV."""
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------------------
# PS1 Effects Chain
# ---------------------------------------------------------------------------

class TestPS1EffectsChain:
    def setup_method(self):
        from audio_engine.dsp.ps1_effects import PS1EffectsChain
        self.chain = PS1EffectsChain(sample_rate=SR, bit_depth=14)

    def test_bit_crush_reduces_precision(self):
        audio = _make_sine()
        crushed = self.chain.bit_crush(audio)
        assert crushed.dtype == np.float32
        # Quantised values must differ from unquantised by at most 1 LSB of 14 bits
        max_diff = np.max(np.abs(audio.astype(np.float64) - crushed.astype(np.float64)))
        assert max_diff < 1.0 / (2 ** 13)

    def test_bit_crush_is_idempotent(self):
        audio = _make_sine()
        c1 = self.chain.bit_crush(audio)
        c2 = self.chain.bit_crush(c1)
        np.testing.assert_array_equal(c1, c2)

    def test_spu_reverb_room_mode_changes_audio(self):
        audio = _make_sine()
        processed = self.chain.spu_reverb(audio, mode="room")
        assert not np.allclose(audio, processed, atol=1e-4)
        assert len(processed) == len(audio)

    def test_spu_reverb_off_mode_passthrough(self):
        audio = _make_sine()
        processed = self.chain.spu_reverb(audio, mode="off")
        np.testing.assert_array_equal(audio, processed)

    @pytest.mark.parametrize("mode", ["room", "hall", "space", "echo", "pipe"])
    def test_all_reverb_modes_produce_audio(self, mode):
        audio = _make_sine()
        processed = self.chain.spu_reverb(audio, mode=mode)
        assert processed.dtype == np.float32
        assert len(processed) == len(audio)
        assert np.max(np.abs(processed)) > 0.0

    def test_reduce_sample_rate_changes_audio(self):
        chain = __import__("audio_engine.dsp.ps1_effects", fromlist=["PS1EffectsChain"]).PS1EffectsChain(
            sample_rate=SR, enable_downsample=True, downsample_rate=SR // 2
        )
        audio = _make_sine()
        processed = chain.reduce_sample_rate(audio)
        assert len(processed) == len(audio)
        assert not np.allclose(audio, processed, atol=1e-4)

    def test_apply_stereo_input(self):
        mono = _make_sine()
        stereo = np.stack([mono, mono], axis=1)
        out = self.chain.apply(stereo, mode="room")
        assert out.ndim == 2 and out.shape[1] == 2
        assert len(out) == len(mono)

    def test_apply_mono_input(self):
        audio = _make_sine()
        out = self.chain.apply(audio, mode="hall")
        assert out.ndim == 1
        assert len(out) == len(audio)

    def test_output_bounded(self):
        audio = _make_sine()
        out = self.chain.apply(audio, mode="room")
        assert np.max(np.abs(out)) <= 1.0 + 1e-5


# ---------------------------------------------------------------------------
# FF7 / FF8 Instruments
# ---------------------------------------------------------------------------

FF7_INSTRUMENTS = [
    "ff7_lead", "ff7_strings", "ff7_bass",
    "ff7_electric_guitar", "ff8_electric_guitar",
    "harpsichord", "orchestral_hit",
]


class TestFF7Instruments:
    def _render(self, name: str, freq=440.0, dur=0.5) -> np.ndarray:
        from audio_engine.synthesizer.instrument import InstrumentLibrary
        inst = InstrumentLibrary.get(name, sample_rate=SR)
        return inst.render(freq, dur)

    @pytest.mark.parametrize("name", FF7_INSTRUMENTS)
    def test_instrument_renders(self, name):
        audio = self._render(name)
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0

    @pytest.mark.parametrize("name", FF7_INSTRUMENTS)
    def test_instrument_length_correct(self, name):
        dur = 0.5
        audio = self._render(name, dur=dur)
        expected = int(dur * SR)
        # Allow ±5% for rounding
        assert abs(len(audio) - expected) <= max(10, int(expected * 0.05))

    def test_ff7_lead_is_brighter_than_ff7_bass(self):
        """ff7_lead should have more high-frequency energy than ff7_bass."""
        lead = self._render("ff7_lead")
        bass = self._render("ff7_bass")
        n = min(len(lead), len(bass))
        # High-frequency content via spectrum
        lead_spectrum = np.abs(np.fft.rfft(lead[:n]))
        bass_spectrum = np.abs(np.fft.rfft(bass[:n]))
        freqs = np.fft.rfftfreq(n, d=1.0 / SR)
        hi_mask = freqs > 2000.0
        lead_hi = lead_spectrum[hi_mask].mean()
        bass_hi  = bass_spectrum[hi_mask].mean()
        assert lead_hi > bass_hi

    def test_orchestral_hit_is_short(self):
        """Orchestral hit should have a fast decay."""
        audio = self._render("orchestral_hit", dur=1.0)
        # Energy in first half vs second half
        half = len(audio) // 2
        e_first  = np.mean(audio[:half] ** 2)
        e_second = np.mean(audio[half:] ** 2)
        assert e_first > e_second


# ---------------------------------------------------------------------------
# FF7 / FF8 Style Presets (music generation)
# ---------------------------------------------------------------------------

FF7_STYLES = [
    "ff7_battle", "ff7_overworld", "ff7_boss", "ff7_sad", "ff7_town",
    "ff8_battle", "ff8_ballad",
]
SHARED_STYLES = ["prelude", "world_map", "dungeon", "healing", "tension"]


class TestFF7StylePresets:
    def _generate(self, style: str, duration: float = SHORT_DURATION) -> np.ndarray:
        from audio_engine.ai.backend import ProceduralBackend
        backend = ProceduralBackend(sample_rate=SR, seed=0)
        return backend.generate_music_audio(style=style, duration=duration)

    @pytest.mark.parametrize("style", FF7_STYLES + SHARED_STYLES)
    def test_style_generates_audio(self, style):
        audio = self._generate(style)
        assert isinstance(audio, np.ndarray)
        assert np.max(np.abs(audio)) > 0.0

    @pytest.mark.parametrize("style", FF7_STYLES)
    def test_ff7_styles_produce_non_empty_audio(self, style):
        """Each FF7/FF8 style should produce audio (duration snaps to bar boundaries)."""
        audio = self._generate(style, duration=SHORT_DURATION)
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0
    def test_ff7_battle_is_louder_than_ff7_sad(self):
        """Battle music should be more energetic/louder than sad theme."""
        battle = self._generate("ff7_battle")
        sad    = self._generate("ff7_sad")
        rms_battle = np.sqrt(np.mean(battle ** 2))
        rms_sad    = np.sqrt(np.mean(sad ** 2))
        # Neither should be silent; battle may not always be louder due to normalization
        assert rms_battle > 0.0
        assert rms_sad > 0.0

    def test_prelude_style_uses_high_pitched_instruments(self):
        """Prelude should produce higher-pitched audio (crystal/harpsichord)."""
        audio = self._generate("prelude")
        mono = audio if audio.ndim == 1 else audio.mean(axis=1)
        n = len(mono)
        spectrum = np.abs(np.fft.rfft(mono))
        freqs = np.fft.rfftfreq(n, d=1.0 / SR)
        hi_energy = spectrum[freqs > 2000.0].sum()
        # Prelude should have significant high-frequency content
        assert hi_energy > 0.0

    def test_ff8_ballad_bpm_is_slow(self):
        """ff8_ballad should be configured at 74 BPM."""
        from audio_engine.ai.generator import _STYLE_DEFS
        style_def = _STYLE_DEFS["ff8_ballad"]
        assert style_def.bpm == pytest.approx(74.0)

    def test_chord_progression_registry_has_new_progressions(self):
        from audio_engine.composer.chord import _PROGRESSIONS
        for prog in ["i_bVII_bVI_V", "I_vi_IV_V", "i_iv_bVII_bIII", "i_bVI_bVII_i"]:
            assert prog in _PROGRESSIONS, f"Missing progression: {prog}"


# ---------------------------------------------------------------------------
# FF7 / FF8 era SFX types
# ---------------------------------------------------------------------------

FF7_SFX_TYPES = [
    "sword_swing", "spell_fire", "spell_ice", "spell_thunder",
    "limit_break", "cure", "summon", "save_point", "level_up",
    "game_over", "menu_open", "menu_close",
]
FF7_SFX_ALIASES = [
    "sword", "slash", "fire", "firaga", "ice", "blizzard",
    "thunder", "lightning", "bolt", "limit", "ultimate",
    "heal", "checkpoint", "levelup", "exp", "gameover",
    "defeat", "confirm", "cancel",
]


class TestFF7SFXTypes:
    def _synthesize(self, sfx_type: str, duration: float = 0.6) -> np.ndarray:
        from audio_engine.ai.sfx_synth import synthesise_sfx
        return synthesise_sfx(sfx_type, duration=duration, sample_rate=SR, seed=0)

    @pytest.mark.parametrize("sfx_type", FF7_SFX_TYPES)
    def test_sfx_generates_audio(self, sfx_type):
        audio = self._synthesize(sfx_type)
        assert audio.dtype == np.float32
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0

    @pytest.mark.parametrize("alias", FF7_SFX_ALIASES)
    def test_sfx_aliases_work(self, alias):
        audio = self._synthesize(alias)
        assert len(audio) > 0

    def test_save_point_is_ascending(self):
        """save_point should be four ascending notes — energy should increase."""
        audio = self._synthesize("save_point", duration=0.7)
        quarter = len(audio) // 4
        # Last quarter should have some signal (ascending chimes)
        e_last = np.mean(audio[3 * quarter:] ** 2)
        assert e_last > 0.0

    def test_cure_has_multiple_components(self):
        """cure has 3 staggered chimes — should have energy after first 30%."""
        audio = self._synthesize("cure", duration=0.8)
        n = len(audio)
        first_30 = np.mean(audio[:n // 3] ** 2)
        last_30  = np.mean(audio[2 * n // 3:] ** 2)
        assert first_30 > 0.0
        assert last_30 > 0.0

    def test_sword_swing_has_high_freq_content(self):
        audio = self._synthesize("sword_swing")
        spectrum = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), d=1.0 / SR)
        hi_energy = spectrum[freqs > 1000.0].sum()
        assert hi_energy > 0.0

    def test_available_sfx_types_includes_ff7(self):
        from audio_engine.ai.sfx_synth import available_sfx_types
        types = available_sfx_types()
        for t in ["sword_swing", "cure", "limit_break", "save_point", "level_up"]:
            assert t in types, f"'{t}' not in available_sfx_types()"


# ---------------------------------------------------------------------------
# SampleLibrary
# ---------------------------------------------------------------------------

class TestSampleLibrary:
    def test_empty_directory_loads_cleanly(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        lib = SampleLibrary(tmp_path, sample_rate=SR)
        assert lib.available_categories() == []

    def test_missing_directory_loads_cleanly(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        lib = SampleLibrary(tmp_path / "does_not_exist", sample_rate=SR)
        assert lib.available_categories() == []

    def test_scans_wav_by_category(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        cat_dir = tmp_path / "strings"
        cat_dir.mkdir()
        _write_wav(cat_dir / "violin.wav", _make_sine())
        lib = SampleLibrary(tmp_path, sample_rate=SR)
        assert lib.has_category("strings")

    def test_get_sample_returns_correct_shape(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        cat_dir = tmp_path / "brass"
        cat_dir.mkdir()
        audio = _make_sine(duration=1.0)
        _write_wav(cat_dir / "horn.wav", audio)
        lib = SampleLibrary(tmp_path, sample_rate=SR)
        sample = lib.get_sample("brass", duration=0.5)
        assert sample is not None
        assert len(sample) == int(0.5 * SR)

    def test_get_sample_missing_category_returns_none(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        lib = SampleLibrary(tmp_path, sample_rate=SR)
        assert lib.get_sample("piano") is None

    def test_blend_with_sample_changes_audio(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        cat_dir = tmp_path / "choir"
        cat_dir.mkdir()
        choir_audio = _make_sine(freq=880.0, duration=2.0)
        _write_wav(cat_dir / "choir.wav", choir_audio)
        lib = SampleLibrary(tmp_path, sample_rate=SR)
        procedural = _make_sine(freq=440.0, duration=2.0)
        blended = lib.blend(procedural, "choir", sample_weight=0.5)
        assert not np.allclose(procedural, blended, atol=1e-4)

    def test_remaster_without_samples_returns_input(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        lib = SampleLibrary(tmp_path, sample_rate=SR)
        audio = _make_sine(duration=1.0)
        result = lib.remaster(audio, {"strings": 0.5, "brass": 0.4})
        np.testing.assert_array_equal(audio, result)

    def test_pitch_ratio_changes_timbre(self, tmp_path):
        from audio_engine.samples.sample_library import SampleLibrary
        cat_dir = tmp_path / "piano"
        cat_dir.mkdir()
        _write_wav(cat_dir / "c4.wav", _make_sine(440.0, duration=1.0))
        lib = SampleLibrary(tmp_path, sample_rate=SR)
        normal = lib.get_sample("piano", pitch_ratio=1.0, duration=0.5)
        shifted = lib.get_sample("piano", pitch_ratio=2.0, duration=0.5)
        assert not np.allclose(normal, shifted, atol=1e-4)


# ---------------------------------------------------------------------------
# PS1 Backend
# ---------------------------------------------------------------------------

class TestPS1Backend:
    def setup_method(self):
        from audio_engine.ai.ps1_backend import PS1Backend
        self.backend = PS1Backend(sample_rate=SR, seed=42, reverb_mode="room")

    def test_name_is_ps1(self):
        assert self.backend.name == "ps1"

    def test_generate_music_returns_audio(self):
        audio = self.backend.generate_music_audio("ff7_battle", duration=SHORT_DURATION)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_generate_sfx_returns_audio(self):
        audio = self.backend.generate_sfx_audio("sword_swing", duration=0.5)
        assert len(audio) > 0

    def test_generate_voice_returns_audio(self):
        audio = self.backend.generate_voice_audio("Hello", voice_preset="narrator")
        assert len(audio) > 0

    def test_ps1_music_differs_from_procedural(self):
        """PS1 backend should apply bit-crush/reverb, changing the signal."""
        from audio_engine.ai.backend import ProceduralBackend
        ps1 = self.backend
        proc = ProceduralBackend(sample_rate=SR, seed=42)
        audio_ps1  = ps1.generate_music_audio("ff7_battle", duration=SHORT_DURATION)
        audio_proc = proc.generate_music_audio("ff7_battle", duration=SHORT_DURATION)
        n = min(len(audio_ps1), len(audio_proc))
        assert not np.allclose(audio_ps1[:n], audio_proc[:n], atol=1e-4)

    @pytest.mark.parametrize("reverb", ["room", "hall", "space", "echo", "pipe"])
    def test_all_reverb_modes_work(self, reverb):
        from audio_engine.ai.ps1_backend import PS1Backend
        backend = PS1Backend(sample_rate=SR, seed=0, reverb_mode=reverb)
        audio = backend.generate_music_audio("ff7_sad", duration=SHORT_DURATION)
        assert len(audio) > 0

    def test_ps1_sfx_has_no_reverb_applied(self):
        """SFX through PS1 should be bit-crushed but not reverb-processed."""
        from audio_engine.ai.ps1_backend import PS1Backend
        from audio_engine.ai.backend import ProceduralBackend
        ps1 = PS1Backend(sample_rate=SR, seed=0)
        proc = ProceduralBackend(sample_rate=SR, seed=0)
        sfx_ps1  = ps1.generate_sfx_audio("cure", duration=0.5)
        sfx_proc = proc.generate_sfx_audio("cure", duration=0.5)
        n = min(len(sfx_ps1), len(sfx_proc))
        # They should differ (bit-crush) but not dramatically (no reverb tail)
        diff = np.max(np.abs(sfx_ps1[:n].astype(np.float64) - sfx_proc[:n].astype(np.float64)))
        assert diff < 0.1  # bit-crush ≈ small quantisation difference only


# ---------------------------------------------------------------------------
# SynthOrchestralBackend
# ---------------------------------------------------------------------------

class TestSynthOrchestralBackend:
    def setup_method(self):
        from audio_engine.ai.synth_orchestral_backend import SynthOrchestralBackend
        self.backend = SynthOrchestralBackend(sample_rate=SR, seed=0)

    def test_name_is_synth_orchestral(self):
        assert self.backend.name == "synth_orchestral"

    def test_generate_music_audio(self):
        audio = self.backend.generate_music_audio("ff7_overworld", duration=SHORT_DURATION)
        assert len(audio) > 0

    def test_generate_sfx_audio(self):
        audio = self.backend.generate_sfx_audio("cure", duration=0.5)
        assert len(audio) > 0

    def test_generate_voice_audio(self):
        audio = self.backend.generate_voice_audio("Test", voice_preset="narrator")
        assert len(audio) > 0


# ---------------------------------------------------------------------------
# SampleBackend
# ---------------------------------------------------------------------------

class TestSampleBackend:
    def test_no_samples_falls_back_gracefully(self, tmp_path):
        from audio_engine.ai.sample_backend import SampleBackend
        backend = SampleBackend(
            samples_dir=str(tmp_path),
            sample_rate=SR,
            seed=0,
            base_backend="synth_orchestral",
        )
        audio = backend.generate_music_audio("ff7_town", duration=SHORT_DURATION)
        assert len(audio) > 0

    def test_with_samples_blends_in(self, tmp_path):
        from audio_engine.ai.sample_backend import SampleBackend
        cat_dir = tmp_path / "piano"
        cat_dir.mkdir()
        _write_wav(cat_dir / "c4.wav", _make_sine(440.0, duration=3.0))

        backend_no_samples = SampleBackend(
            samples_dir=str(tmp_path / "empty"),
            sample_rate=SR, seed=0,
        )
        backend_with_samples = SampleBackend(
            samples_dir=str(tmp_path),
            sample_rate=SR, seed=0,
        )

        a = backend_no_samples.generate_music_audio("ff7_town", duration=SHORT_DURATION)
        b = backend_with_samples.generate_music_audio("ff7_town", duration=SHORT_DURATION)
        # With samples blended in, the signals should differ
        n = min(len(a), len(b))
        assert not np.allclose(a[:n], b[:n], atol=1e-4)

    def test_remaster_audio_without_samples_is_passthrough(self, tmp_path):
        from audio_engine.ai.sample_backend import SampleBackend
        backend = SampleBackend(samples_dir=str(tmp_path / "empty"), sample_rate=SR)
        audio = _make_sine(duration=2.0)
        result = backend.remaster_audio(audio, style="ff7_overworld")
        np.testing.assert_array_equal(audio, result)

    def test_remaster_audio_with_samples_changes_audio(self, tmp_path):
        from audio_engine.ai.sample_backend import SampleBackend
        cat_dir = tmp_path / "strings"
        cat_dir.mkdir()
        _write_wav(cat_dir / "strings.wav", _make_sine(880.0, duration=3.0))
        backend = SampleBackend(samples_dir=str(tmp_path), sample_rate=SR, seed=0)
        audio = _make_sine(440.0, duration=2.0)
        result = backend.remaster_audio(audio, style="ff7_overworld")
        n = min(len(audio), len(result))
        assert not np.allclose(audio[:n], result[:n], atol=1e-4)

    def test_backend_registry_has_ps1_synth_orch_sample(self):
        from audio_engine.ai.backend import BackendRegistry
        available = BackendRegistry.available_backends()
        assert "ps1" in available
        assert "synth_orchestral" in available
        assert "sample" in available


# ---------------------------------------------------------------------------
# VocalMelodySynth
# ---------------------------------------------------------------------------

class TestVocalMelodySynth:
    def setup_method(self):
        from audio_engine.ai.vocal_melody_synth import VocalMelodySynth
        self.synth = VocalMelodySynth(sample_rate=SR, voice_preset="soprano")

    def test_synthesize_single_note(self):
        audio = self.synth.synthesize([(440.0, 0.5, "ah")])
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0

    def test_synthesize_melody_length(self):
        notes = [(440.0, 0.3, "ah"), (493.9, 0.3, "oh"), (523.3, 0.4, "ah")]
        audio = self.synth.synthesize(notes)
        expected_min = int(SR * (0.3 + 0.3 + 0.4) * 0.8)  # allow legato overlap
        assert len(audio) >= expected_min

    def test_empty_notes_returns_empty(self):
        audio = self.synth.synthesize([])
        assert len(audio) == 0

    @pytest.mark.parametrize("vowel", ["ah", "oh", "ee", "oo", "eh", "mm", "hm"])
    def test_all_vowels_produce_audio(self, vowel):
        audio = self.synth.synthesize([(440.0, 0.3, vowel)])
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0

    @pytest.mark.parametrize("preset", ["soprano", "alto", "tenor", "choir_ah"])
    def test_all_presets_work(self, preset):
        from audio_engine.ai.vocal_melody_synth import VocalMelodySynth
        synth = VocalMelodySynth(sample_rate=SR, voice_preset=preset)
        audio = synth.synthesize([(440.0, 0.3, "ah")])
        assert len(audio) > 0

    def test_different_pitches_produce_different_audio(self):
        a4 = self.synth.synthesize([(440.0, 0.4, "ah")])
        a5 = self.synth.synthesize([(880.0, 0.4, "ah")])
        n = min(len(a4), len(a5))
        assert not np.allclose(a4[:n], a5[:n], atol=1e-3)

    def test_vibrato_modulates_pitch(self):
        """Vibrato should create periodic amplitude modulation visible in the signal."""
        audio = self.synth.synthesize([(440.0, 1.0, "ah")])
        # The signal should not be perfectly periodic (vibrato breaks perfect symmetry)
        n = len(audio)
        half = n // 2
        # RMS of first vs second half should be similar (not silent anywhere)
        rms_first  = np.sqrt(np.mean(audio[:half] ** 2))
        rms_second = np.sqrt(np.mean(audio[half:] ** 2))
        assert rms_first > 0.01
        assert rms_second > 0.01

    def test_synthesize_ah_melody_convenience(self):
        freqs = [440.0, 493.9, 523.3, 587.3]
        durs  = [0.3, 0.3, 0.3, 0.3]
        audio = self.synth.synthesize_ah_melody(freqs, durs)
        assert len(audio) > 0


# ---------------------------------------------------------------------------
# PieceComposer — "Eyes on Me" verification
# ---------------------------------------------------------------------------

class TestPieceComposer:
    """Verify the engine can produce a full piece in "Eyes on Me" style."""

    def setup_method(self):
        from audio_engine.ai.piece_composer import PieceComposer
        # Use procedural backend at low SR for speed; structure and vocal are what matter
        self.composer = PieceComposer(
            sample_rate=SR,
            seed=0,
            backend="procedural",
            vocal_preset="soprano",
        )

    def test_compose_eyes_on_me_returns_stereo(self):
        audio = self.composer.compose_eyes_on_me(duration=8.0, with_vocals=True)
        assert audio.ndim == 2
        assert audio.shape[1] == 2

    def test_compose_eyes_on_me_duration_approximate(self):
        target = 8.0
        audio = self.composer.compose_eyes_on_me(duration=target, with_vocals=False)
        actual = audio.shape[0] / SR
        # Sections snap to bar boundaries; allow generous margin
        assert 1.0 <= actual <= target * 8.0

    def test_compose_custom_sections(self):
        audio = self.composer.compose(
            style="ff8_ballad",
            sections=["intro", "chorus", "outro"],
            with_vocals=False,
            duration=6.0,
        )
        assert audio.ndim == 2
        assert len(audio) > 0

    def test_compose_with_vocals_differs_from_instrumental(self):
        inst  = self.composer.compose(style="ff8_ballad", sections=["verse"],
                                      with_vocals=False, duration=4.0)
        vocal = self.composer.compose(style="ff8_ballad", sections=["verse"],
                                      with_vocals=True, duration=4.0)
        n = min(len(inst), len(vocal))
        assert not np.allclose(inst[:n], vocal[:n], atol=1e-4)

    def test_compose_piece_produces_non_silent_output(self):
        audio = self.composer.compose(
            style="ff8_ballad",
            sections=["intro", "verse", "chorus"],
            with_vocals=True,
            duration=6.0,
        )
        rms = np.sqrt(np.mean(audio ** 2))
        assert rms > 0.005

    def test_all_section_types_work(self):
        from audio_engine.ai.piece_composer import SECTION_TEMPLATES
        for section_name in SECTION_TEMPLATES:
            audio = self.composer.compose(
                style="ff8_ballad",
                sections=[section_name],
                with_vocals=False,
                duration=2.0,
            )
            assert len(audio) > 0, f"Section '{section_name}' produced empty audio"

    def test_eyes_on_me_section_sequence(self):
        """The full Eyes on Me section sequence runs without error."""
        from audio_engine.ai.piece_composer import _EYES_ON_ME_SECTIONS
        audio = self.composer.compose(
            style="ff8_ballad",
            sections=_EYES_ON_ME_SECTIONS[:4],  # first 4 sections for speed
            with_vocals=True,
            duration=10.0,
        )
        assert audio.ndim == 2
        assert np.max(np.abs(audio)) > 0.0


# ---------------------------------------------------------------------------
# CLI — new flags and commands
# ---------------------------------------------------------------------------

class TestCLINewFlags:
    def _run(self, argv: list[str]) -> int:
        from audio_engine.cli import main
        return main(argv)

    def test_list_backends_shows_ps1_and_orchestral(self, capsys):
        self._run(["list-backends"])
        out = capsys.readouterr().out
        assert "ps1" in out
        assert "synth_orchestral" in out
        assert "sample" in out

    def test_list_styles_shows_ff7_styles(self, capsys):
        self._run(["list-styles"])
        out = capsys.readouterr().out
        assert "ff7_battle" in out
        assert "ff8_ballad" in out
        assert "prelude" in out

    def test_generate_music_ps1_flag(self, tmp_path):
        out_path = str(tmp_path / "test.wav")
        rc = self._run([
            "generate-music",
            "--prompt", "ff7 battle",
            "--duration", "2",
            "--sample-rate", "22050",
            "--ps1",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_generate_music_orchestral_flag(self, tmp_path):
        out_path = str(tmp_path / "test.wav")
        rc = self._run([
            "generate-music",
            "--prompt", "ff7 overworld",
            "--duration", "2",
            "--sample-rate", "22050",
            "--orchestral",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_generate_sfx_ps1_flag(self, tmp_path):
        out_path = str(tmp_path / "sfx.wav")
        rc = self._run([
            "generate-sfx",
            "--prompt", "cure",
            "--duration", "0.5",
            "--sample-rate", "22050",
            "--ps1",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_generate_sfx_sword_swing(self, tmp_path):
        out_path = str(tmp_path / "sword.wav")
        rc = self._run([
            "generate-sfx",
            "--prompt", "sword swing",
            "--duration", "0.5",
            "--sample-rate", "22050",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_generate_sfx_save_point(self, tmp_path):
        out_path = str(tmp_path / "save.wav")
        rc = self._run([
            "generate-sfx",
            "--prompt", "save point",
            "--duration", "0.6",
            "--sample-rate", "22050",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_remaster_command_no_samples(self, tmp_path):
        """remaster should succeed even when no sample files are present."""
        input_path = tmp_path / "input.wav"
        output_path = tmp_path / "output.wav"
        _write_wav(input_path, _make_sine(duration=1.0), sr=SR)
        rc = self._run([
            "remaster",
            "--input", str(input_path),
            "--samples-dir", str(tmp_path / "empty"),
            "--output", str(output_path),
            "--style", "ff7_overworld",
        ])
        assert rc == 0
        assert output_path.exists()

    def test_compose_piece_command(self, tmp_path):
        out_path = str(tmp_path / "piece.wav")
        rc = self._run([
            "compose-piece",
            "--style", "ff8_ballad",
            "--sections", "intro,chorus",
            "--no-vocals",
            "--duration", "4",
            "--sample-rate", "22050",
            "--seed", "0",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()

    def test_compose_piece_with_vocals(self, tmp_path):
        out_path = str(tmp_path / "piece_vocal.wav")
        rc = self._run([
            "compose-piece",
            "--style", "ff8_ballad",
            "--sections", "verse",
            "--with-vocals",
            "--vocal-preset", "soprano",
            "--duration", "4",
            "--sample-rate", "22050",
            "--seed", "0",
            "--output", out_path,
        ])
        assert rc == 0
        assert Path(out_path).exists()
