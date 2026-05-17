from __future__ import annotations

import numpy as np

from audio_engine.ai.backends.musicgen_backend import MusicGenBackend


def test_backend_name():
    backend = MusicGenBackend(sample_rate=22050)
    assert backend.name == "musicgen"


def test_backend_default_model_path_is_medium():
    backend = MusicGenBackend(sample_rate=22050)
    assert backend.model_path.name == "musicgen-medium"


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
