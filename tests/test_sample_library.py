from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from audio_engine.integration.sample_library import (
    OrchestralSampleLibrary,
    midi_to_note_name,
    note_name_to_midi,
)


def _write_wav(path: Path, audio: np.ndarray, sr: int = 22050) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def _tone(sr: int = 22050, seconds: float = 0.15, hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False)
    return np.sin(2.0 * np.pi * hz * t).astype(np.float32)


def test_note_name_midi_roundtrip():
    assert note_name_to_midi("C4") == 60
    assert midi_to_note_name(60) == "C4"


def test_scanner_discovers_instruments_and_notes(tmp_path):
    orch = tmp_path / "samples" / "orchestral"
    _write_wav(orch / "strings" / "violin_C4.wav", _tone())
    _write_wav(orch / "strings" / "violin_G4.wav", _tone(hz=392.0))
    _write_wav(orch / "brass" / "horn_A3.wav", _tone(hz=220.0))

    lib = OrchestralSampleLibrary(orch)
    assert lib.has_instrument("strings")
    assert lib.has_instrument("brass")
    assert lib.available_instruments() == ["brass", "strings"]
    assert [n.note for n in lib.notes_for_instrument("strings")] == ["C4", "G4"]


def test_resolve_nearest_returns_pitch_ratio(tmp_path):
    orch = tmp_path / "samples" / "orchestral"
    _write_wav(orch / "strings" / "section_C4_take1.wav", _tone(hz=261.63))

    lib = OrchestralSampleLibrary(orch)
    match = lib.resolve_nearest("strings", "D4")
    assert match is not None
    assert match.source.note == "C4"
    assert match.target_midi == note_name_to_midi("D4")
    assert np.isclose(match.pitch_ratio, 2 ** (2 / 12), atol=1e-6)
