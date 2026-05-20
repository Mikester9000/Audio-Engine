from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

from audio_engine.integration.asset_pipeline import RemasterBatchPipeline
from audio_engine.render.remaster import RemasterPipeline


def _write_wav(path: Path, audio: np.ndarray, sr: int = 22050) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def _read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    return (np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0)


def _tone(sr: int = 22050, seconds: float = 0.25, hz: float = 440.0) -> np.ndarray:
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False)
    return np.sin(2.0 * np.pi * hz * t).astype(np.float32)


def test_remaster_pipeline_passthrough_when_no_samples(tmp_path):
    src = tmp_path / "input.wav"
    dst = tmp_path / "output.wav"
    _write_wav(src, _tone())

    pipeline = RemasterPipeline(seed=0)
    out = pipeline.remaster_file(src, dst, samples_dir=tmp_path / "empty")
    assert out.exists()
    assert _read_wav(out).shape == _read_wav(src).shape


def test_remaster_pipeline_uses_events_when_samples_exist(tmp_path):
    src = tmp_path / "input.wav"
    dst = tmp_path / "output.wav"
    samples = tmp_path / "samples" / "orchestral" / "strings"
    events = tmp_path / "events.json"

    _write_wav(src, _tone(hz=220.0))
    _write_wav(samples / "ensemble_C4.wav", _tone(hz=261.63))
    events.write_text(
        json.dumps(
            [
                {
                    "instrument": "strings",
                    "note": "E4",
                    "startSeconds": 0.0,
                    "durationSeconds": 0.2,
                    "velocity": 1.0,
                }
            ]
        ),
        encoding="utf-8",
    )

    pipeline = RemasterPipeline(seed=0)
    out = pipeline.remaster_file(src, dst, samples_dir=tmp_path / "samples", events_json=events)
    assert out.exists()
    assert not np.allclose(_read_wav(src), _read_wav(out), atol=1e-4)


def test_remaster_batch_pipeline_writes_machine_readable_report(tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    samples = tmp_path / "samples" / "orchestral" / "strings"
    events_dir = tmp_path / "events"

    _write_wav(input_dir / "music" / "track.wav", _tone())
    _write_wav(samples / "section_C4.wav", _tone(hz=261.63))
    events_dir.mkdir(parents=True, exist_ok=True)
    (events_dir / "track.events.json").write_text(
        json.dumps(
            [
                {
                    "instrument": "strings",
                    "note": "D4",
                    "startSeconds": 0.0,
                    "durationSeconds": 0.2,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = RemasterBatchPipeline().execute(
        input_dir=input_dir,
        output_dir=output_dir,
        samples_dir=tmp_path / "samples",
        events_dir=events_dir,
    )
    assert len(result.records) == 1
    assert result.records[0].status == "ok"
    assert (output_dir / "music" / "track.wav").exists()
    report_path = output_dir / "remaster_batch_result.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["records"][0]["status"] == "ok"
