"""Tests for the AI MusicGenerator."""

import numpy as np
import pytest

from audio_engine.ai import generator as generator_module
from audio_engine.ai.generator import MusicGenerator
from audio_engine.composer.sequencer import Sequencer

SR = 22050


@pytest.fixture(scope="module")
def gen():
    return MusicGenerator(sample_rate=SR, seed=42)


def test_available_styles_non_empty(gen):
    styles = gen.available_styles()
    assert len(styles) > 0


def test_available_style_metadata_exposes_bpm():
    metadata = MusicGenerator.available_style_metadata()
    assert "battle" in metadata
    assert metadata["battle"]["bpm"] == 140


def test_electronic_styles_use_dedicated_lead_and_bass_synths():
    metadata = MusicGenerator.available_style_metadata()
    electronic = metadata["electronic_epic"]
    synthwave = metadata["synthwave_epic"]
    assert electronic["instruments"][0] == "synth_lead_bright"
    assert electronic["bass_instrument"] == "synth_bass_punch"
    assert synthwave["instruments"][0] == "synth_lead_bright"
    assert synthwave["bass_instrument"] == "synth_bass_punch"


@pytest.mark.parametrize("style", ["battle", "ambient", "menu"])
def test_generate_returns_sequencer(gen, style):
    seq = gen.generate(style=style, bars=2)
    assert isinstance(seq, Sequencer)


@pytest.mark.parametrize("style", ["battle", "ambient", "menu"])
def test_generate_audio_stereo(gen, style):
    audio = gen.generate_audio(style=style, bars=2)
    assert audio.ndim == 2
    assert audio.shape[1] == 2


@pytest.mark.parametrize("style", ["battle", "ambient", "menu"])
def test_generate_audio_dtype(gen, style):
    audio = gen.generate_audio(style=style, bars=2)
    assert audio.dtype == np.float32


@pytest.mark.parametrize("style", ["battle", "ambient", "menu"])
def test_generate_audio_amplitude(gen, style):
    audio = gen.generate_audio(style=style, bars=2)
    assert np.max(np.abs(audio)) <= 1.0 + 1e-5


def test_unknown_style_raises(gen):
    with pytest.raises(ValueError):
        gen.generate(style="nonexistent_xyz")


def test_reproducibility():
    g1 = MusicGenerator(sample_rate=SR, seed=0)
    g2 = MusicGenerator(sample_rate=SR, seed=0)
    a1 = g1.generate_audio("battle", bars=2)
    a2 = g2.generate_audio("battle", bars=2)
    np.testing.assert_array_equal(a1, a2)


@pytest.mark.parametrize(
    "style",
    [
        "hybrid_trailer",
        "neo_noir",
        "festival_folk",
        "sci_fi_pulse",
        "waltz_orchestral",
        "synth_house_modern",
        "techno_drive",
        "trance_uplift",
        "drum_and_bass_neuro",
        "future_bass_modern",
    ],
)
def test_new_styles_generate_audio(style):
    gen = MusicGenerator(sample_rate=SR, seed=7)
    audio = gen.generate_audio(style=style, bars=2)
    assert audio.ndim == 2
    assert audio.shape[1] == 2


def test_style_alignment_validation_has_no_issues():
    issues = MusicGenerator.validate_style_library_alignment()
    assert issues == {}


def test_style_alignment_validation_detects_misaligned_style():
    style_name = "tmp_alignment_ballad_failure"
    generator_module._STYLE_DEFS[style_name] = generator_module._StyleDef(
        bpm=78,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["piano"],
        accompaniment=["strings"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=4,
        ostinato_instrument="harp",
    )
    try:
        issues = MusicGenerator.validate_style_library_alignment()
        assert style_name in issues
        assert "percussion should be disabled for this style family" in issues[style_name]
    finally:
        generator_module._STYLE_DEFS.pop(style_name, None)
