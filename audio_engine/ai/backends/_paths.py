"""Shared helpers for optional backend model directories and availability."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path


_MODEL_REQUIREMENTS: dict[str, dict[str, tuple[tuple[str, ...], ...] | tuple[str, ...]]] = {
    "musicgen-small": {
        "required_files": ("config.json",),
        "required_any": (
            ("preprocessor_config.json", "processor_config.json", "tokenizer_config.json"),
            ("model.safetensors", "pytorch_model.bin", "model.bin", "model.pt", "model.pth"),
        ),
    },
    "audiogen-medium": {
        "required_files": ("config.json",),
        "required_any": (
            ("preprocessor_config.json", "processor_config.json", "tokenizer_config.json"),
            ("model.safetensors", "pytorch_model.bin", "model.bin", "model.pt", "model.pth"),
        ),
    },
    "kokoro": {
        "required_files": ("config.json",),
        "required_any": (
            ("model.safetensors", "pytorch_model.bin", "model.bin", "model.pt", "model.pth"),
        ),
    },
}


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODELS_ROOT = _REPO_ROOT / "models"
DEFAULT_AUDIO_FRAME_RATE = 50


def default_model_dir(model_folder: str) -> Path:
    return _MODELS_ROOT / model_folder


def can_import_module(module_name: str) -> bool:
    try:
        import_module(module_name)
    except Exception:
        return False
    return True


def has_complete_model_snapshot(path: Path) -> bool:
    if not path.is_dir():
        return False

    requirements = _MODEL_REQUIREMENTS.get(path.name)
    if requirements is None:
        return any(path.iterdir())

    for relative_path in requirements.get("required_files", ()):
        if not (path / relative_path).is_file():
            return False

    for candidates in requirements.get("required_any", ()):
        if not any((path / candidate).exists() for candidate in candidates):
            return False

    return True
