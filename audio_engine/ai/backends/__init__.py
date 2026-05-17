"""Optional neural backends.

Backends are registered only when their dependencies are importable and
required local model folders are present.
"""

from __future__ import annotations

from audio_engine.ai.backend import BackendRegistry
from audio_engine.ai.backends.audiogen_backend import AudioGenBackend
from audio_engine.ai.backends.kokoro_backend import KokoroBackend
from audio_engine.ai.backends.musicgen_backend import MusicGenBackend


def _try_register(backend_cls: type) -> None:
    try:
        backend = backend_cls()
        if backend.is_available():
            BackendRegistry.register(backend.name, backend_cls)
    except Exception:
        # Optional backend import/initialization failures should not break fallback behavior.
        pass


for _backend_cls in (MusicGenBackend, AudioGenBackend, KokoroBackend):
    _try_register(_backend_cls)


__all__ = ["MusicGenBackend", "AudioGenBackend", "KokoroBackend"]
