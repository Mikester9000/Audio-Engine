"""Tests for the AudioExporter class."""

import struct
import wave
from pathlib import Path

import numpy as np
import pytest

from audio_engine.export.audio_exporter import AudioExporter

SR = 22050


def _stereo(duration: float = 0.1) -> np.ndarray:
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    right = np.sin(2 * np.pi * 880 * t).astype(np.float32)
    return np.column_stack([left, right])


def _mono(duration: float = 0.1) -> np.ndarray:
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)


def test_export_wav_stereo(tmp_path):
    exp = AudioExporter(sample_rate=SR, bit_depth=16)
    out = exp.export(_stereo(), tmp_path / "test.wav", fmt="wav")
    assert out.exists()
    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 2
        assert wf.getframerate() == SR


def test_export_wav_mono(tmp_path):
    exp = AudioExporter(sample_rate=SR, bit_depth=16)
    out = exp.export(_mono(), tmp_path / "mono.wav", fmt="wav")
    assert out.exists()
    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 1


def test_export_wav_32bit(tmp_path):
    exp = AudioExporter(sample_rate=SR, bit_depth=32)
    out = exp.export(_stereo(), tmp_path / "test32.wav", fmt="wav")
    assert out.exists()
    data = out.read_bytes()
    # Check WAVE format type = 3 (IEEE float)
    fmt_type = struct.unpack_from("<H", data, 20)[0]
    assert fmt_type == 3


def test_export_invalid_bit_depth():
    with pytest.raises(ValueError):
        AudioExporter(bit_depth=24)


def test_export_invalid_shape():
    exp = AudioExporter(sample_rate=SR)
    with pytest.raises(ValueError):
        exp.export(np.zeros((10, 3)), "/tmp/bad.wav")


def test_export_clips_over_range(tmp_path):
    exp = AudioExporter(sample_rate=SR, bit_depth=16)
    loud = np.ones((SR, 2), dtype=np.float32) * 5.0
    out = exp.export(loud, tmp_path / "loud.wav")
    assert out.exists()


def test_write_loop_points(tmp_path):
    exp = AudioExporter(sample_rate=SR)
    out = exp.export(_mono(), tmp_path / "loop.wav")
    exp.write_loop_points(out, loop_start=100, loop_end=5000)
    data = out.read_bytes()
    assert b"smpl" in data


def test_extension_override(tmp_path):
    exp = AudioExporter(sample_rate=SR)
    # Provide .mp3 path but request wav – should be saved as .wav
    out = exp.export(_mono(), tmp_path / "test.mp3", fmt="wav")
    assert out.suffix == ".wav"


def test_ogg_missing_dep_raises(tmp_path, monkeypatch):
    """If soundfile is not installed, OGG export raises ImportError."""
    import sys
    monkeypatch.setitem(sys.modules, "soundfile", None)
    exp = AudioExporter(sample_rate=SR)
    with pytest.raises((ImportError, ModuleNotFoundError)):
        exp.export(_mono(), tmp_path / "test.ogg", fmt="ogg")
