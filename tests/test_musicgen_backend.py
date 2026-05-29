from __future__ import annotations

import contextlib
import sys
import types

import numpy as np
import pytest

from audio_engine.ai.backends.musicgen_backend import MusicGenBackend


def test_backend_name():
    backend = MusicGenBackend(sample_rate=22050)
    assert backend.name == "musicgen"


def test_backend_default_model_path_is_medium():
    backend = MusicGenBackend(sample_rate=22050)
    assert backend.model_path.name == "musicgen-medium"


def test_invalid_model_size_raises_clear_error():
    with pytest.raises(ValueError, match="Allowed sizes: medium, small"):
        MusicGenBackend(sample_rate=22050, model_size="smol")


def test_is_available_false_when_model_absent(tmp_path):
    backend = MusicGenBackend(model_path=tmp_path / "missing", sample_rate=22050)
    assert backend.is_available() is False


def test_fallback_generation_without_model(tmp_path):
    backend = MusicGenBackend(model_path=tmp_path / "missing", sample_rate=22050, seed=1)
    music = backend.generate_music_audio("battle", duration=1.0)
    sfx = backend.generate_sfx_audio("explosion", duration=0.4, prompt="heavy impact")
    voice = backend.generate_voice_audio("hello")

    assert music.ndim == 2 and music.shape[1] == 2
    assert isinstance(sfx, np.ndarray) and sfx.ndim == 1 and sfx.size > 0
    assert isinstance(voice, np.ndarray) and voice.ndim == 1 and voice.size > 0


def test_long_form_generation_preserves_duration_with_overlap(monkeypatch):
    sample_rate = 10
    captured_tokens: list[int] = []

    class _DummyModel:
        class _Config:
            class _AudioEncoder:
                frame_rate = sample_rate
                sampling_rate = sample_rate

            audio_encoder = _AudioEncoder()

        config = _Config()

        def generate(self, **kwargs):
            tokens = int(kwargs["max_new_tokens"])
            captured_tokens.append(tokens)
            return np.ones((1, tokens), dtype=np.float32)

    class _DummyProcessor:
        def __call__(self, text, padding, return_tensors):
            return {}

    backend = MusicGenBackend(sample_rate=sample_rate)
    dummy_torch = types.SimpleNamespace(
        manual_seed=lambda _seed: None,
        no_grad=lambda: contextlib.nullcontext(),
    )
    monkeypatch.setitem(sys.modules, "torch", dummy_torch)
    monkeypatch.setattr(backend, "is_available", lambda: True)
    monkeypatch.setattr(backend, "_load_model_bundle", lambda: (_DummyModel(), _DummyProcessor()))

    audio = backend.generate_music_audio("battle", duration=65.0)

    assert captured_tokens == [300, 310, 60]
    assert audio.shape == (650, 2)
    assert np.all(np.abs(audio[-sample_rate:]) > 0.0)
