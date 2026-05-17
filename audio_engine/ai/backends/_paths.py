"""Shared path helpers for optional backend model directories."""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODELS_ROOT = _REPO_ROOT / "models"
DEFAULT_AUDIO_FRAME_RATE = 50


def default_model_dir(model_folder: str) -> Path:
    return _MODELS_ROOT / model_folder
