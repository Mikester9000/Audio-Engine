"""Tests for tools/download_models.py helper functions."""

from __future__ import annotations

import types
import sys
from pathlib import Path

import pytest


# Add tools/ to path so we can import download_models directly
TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"


def _import_download_models():
    if "download_models" in sys.modules:
        return sys.modules["download_models"]
    import importlib.util

    spec = importlib.util.spec_from_file_location("download_models", TOOLS_DIR / "download_models.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    sys.modules["download_models"] = module
    return module


@pytest.fixture()
def dm():
    return _import_download_models()


def test_skip_flag_returns_zero(dm, capsys):
    rc = dm.main(["--skip"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "manual placement" in captured.out.lower()


def test_skip_flag_prints_model_directory(dm, capsys):
    dm.main(["--skip"])
    captured = capsys.readouterr()
    assert "musicgen-medium" in captured.out


def test_skip_flag_prints_hf_token_hint(dm, capsys):
    dm.main(["--skip"])
    captured = capsys.readouterr()
    assert "HF_TOKEN" in captured.out


def test_is_model_present_false_for_empty_dir(dm, tmp_path):
    target = tmp_path / "musicgen-medium"
    target.mkdir()
    # Empty directory should not be considered present
    assert dm._is_model_present(target) is False


def test_is_model_present_false_for_missing_dir(dm, tmp_path):
    target = tmp_path / "musicgen-medium"
    assert dm._is_model_present(target) is False


def test_model_specs_contains_musicgen(dm):
    labels = [spec["label"] for spec in dm.MODEL_SPECS]
    assert "MusicGen Medium" in labels


def test_model_specs_target_paths_under_models_dir(dm):
    for spec in dm.MODEL_SPECS:
        target = spec["target"]
        assert "models" in str(target).replace("\\", "/")


def test_download_skipped_when_model_present(dm, tmp_path, monkeypatch):
    """If model already present, download is not called."""
    target = tmp_path / "musicgen-medium"
    target.mkdir()
    (target / "config.json").write_text("{}", encoding="utf-8")

    called = []

    monkeypatch.setattr(dm, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(
        dm,
        "MODEL_SPECS",
        ({"repo_id": "facebook/musicgen-medium", "target": target, "label": "MusicGen Medium", "size": "~1.5GB"},),
    )
    monkeypatch.setattr(dm, "_is_model_present", lambda p: True)
    monkeypatch.setattr(dm, "_download_model", lambda *a, **kw: called.append(1))

    rc = dm.main([])
    assert rc == 0
    assert called == [], "download should not be called when model already present"


def test_download_failure_shows_manual_instructions(dm, tmp_path, monkeypatch, capsys):
    """A download error prints manual placement instructions and returns 1."""
    target = tmp_path / "musicgen-medium"

    monkeypatch.setattr(dm, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(
        dm,
        "MODEL_SPECS",
        ({"repo_id": "facebook/musicgen-medium", "target": target, "label": "MusicGen Medium", "size": "~1.5GB"},),
    )
    monkeypatch.setattr(dm, "_is_model_present", lambda p: False)
    monkeypatch.setattr(dm, "_download_model", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("network error")))

    rc = dm.main([])
    assert rc == 1
    captured = capsys.readouterr()
    assert "manual" in captured.out.lower() or "ERROR" in captured.out


def test_download_model_retries_and_passes_hf_token(dm, monkeypatch):
    calls = []

    def fake_snapshot_download(**kwargs):
        calls.append(kwargs)
        if len(calls) < 3:
            raise RuntimeError("transient network error")
        return "ok"

    fake_hf = types.ModuleType("huggingface_hub")
    fake_hf.snapshot_download = fake_snapshot_download
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)
    monkeypatch.setattr(dm.time, "sleep", lambda *_: None)
    monkeypatch.setenv("HF_TOKEN", "token-123")

    dm._download_model("facebook/musicgen-small", Path("/tmp/target"))

    assert len(calls) == 3
    assert calls[-1]["repo_id"] == "facebook/musicgen-small"
    assert calls[-1]["local_dir"] == "/tmp/target"
    assert calls[-1]["token"] == "token-123"
    assert calls[-1]["resume_download"] is True
    assert calls[-1]["etag_timeout"] == dm.DOWNLOAD_ETAG_TIMEOUT_SECONDS


def test_download_model_raises_after_all_retries(dm, monkeypatch):
    def fake_snapshot_download(**kwargs):
        raise RuntimeError("persistent network error")

    fake_hf = types.ModuleType("huggingface_hub")
    fake_hf.snapshot_download = fake_snapshot_download
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)
    monkeypatch.setattr(dm.time, "sleep", lambda *_: None)

    with pytest.raises(RuntimeError, match="multiple attempts"):
        dm._download_model("facebook/musicgen-medium", Path("/tmp/target"))
