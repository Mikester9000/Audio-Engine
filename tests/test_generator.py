"""Tests for the AI MusicGenerator."""

import numpy as np
import pytest

from audio_engine.ai.generator import MusicGenerator
from audio_engine.composer.sequencer import Sequencer

SR = 22050


@pytest.fixture(scope="module")
def gen():
    return MusicGenerator(sample_rate=SR, seed=42)


def test_available_styles_non_empty(gen):
    styles = gen.available_styles()
    assert len(styles) > 0


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
