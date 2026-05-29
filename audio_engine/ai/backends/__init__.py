"""Optional neural backends.

Backends are registered only when their dependencies are importable and
required local model folders are present.
"""

from __future__ import annotations

from audio_engine.ai.backend import BackendRegistry
from audio_engine.ai.backends.musicgen_backend import MusicGenBackend, MusicGenSmallBackend


def _try_register(backend_cls: type) -> None:
    try:
        backend = backend_cls()
        if backend.is_available():
            BackendRegistry.register(backend.name, backend_cls)
    except Exception:
        # Optional backend import/initialization failures should not break fallback behavior.
        pass


for _backend_cls in (MusicGenBackend, MusicGenSmallBackend):
    _try_register(_backend_cls)


__all__ = ["MusicGenBackend", "MusicGenSmallBackend"]
