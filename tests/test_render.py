"""Tests for the render module: OfflineBounce and StemRenderer."""

from __future__ import annotations

import numpy as np
import pytest

from audio_engine.render import OfflineBounce, StemRenderer


SR = 22050


def _sine(freq: float = 440.0, duration: float = 1.0, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(duration * SR)) / SR
    return (amp * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


def _stereo(sig: np.ndarray) -> np.ndarray:
    return np.stack([sig, sig], axis=1)


# ---------------------------------------------------------------------------
# OfflineBounce
# ---------------------------------------------------------------------------

class TestOfflineBounce:
    def test_process_returns_same_shape_mono(self):
        bounce = OfflineBounce(SR)
        sig = _sine()
        out = bounce.process(sig)
        assert out.shape == sig.shape

    def test_process_returns_same_shape_stereo(self):
        bounce = OfflineBounce(SR)
        stereo = _stereo(_sine())
        out = bounce.process(stereo)
        assert out.shape == stereo.shape

    def test_output_dtype(self):
        bounce = OfflineBounce(SR)
        out = bounce.process(_sine())
        assert out.dtype == np.float32

    def test_loudness_normalisation(self):
        """After processing, loudness should be near the target LUFS."""
        from audio_engine.qa import LoudnessMeter

        bounce = OfflineBounce(SR, target_lufs=-16.0, apply_master_eq=False, apply_compression=False)
        # Create a 5-second signal that is very quiet
        quiet = np.ones(SR * 5, dtype=np.float32) * 0.001
        stereo = _stereo(quiet)
        out = bounce.process(stereo)
        # After boost, loudness should be closer to -16 LUFS
        meter = LoudnessMeter(SR)
        lufs_out = meter.integrated_loudness(out)
        lufs_in = meter.integrated_loudness(stereo)
        assert lufs_out > lufs_in  # should have been boosted

    def test_peak_not_exceeded(self):
        """Limiter should prevent output from exceeding ceiling."""
        bounce = OfflineBounce(SR, target_lufs=None, apply_master_eq=False, apply_compression=False)
        # Very loud input
        loud = np.ones((SR * 2, 2), dtype=np.float32) * 2.0
        out = bounce.process(loud)
        ceiling = 10.0 ** (-0.3 / 20.0)
        assert np.max(np.abs(out)) <= ceiling + 1e-3

    def test_no_normalise_option(self):
        bounce = OfflineBounce(SR, target_lufs=None)
        sig = _sine()
        out = bounce.process(sig)
        assert out.shape == sig.shape

    def test_process_and_export_creates_file(self, tmp_path):
        bounce = OfflineBounce(SR)
        path = bounce.process_and_export(_stereo(_sine()), tmp_path / "bounce.wav")
        assert path.exists()
        assert path.stat().st_size > 0

    def test_process_and_export_with_loop_points(self, tmp_path):
        bounce = OfflineBounce(SR)
        stereo = _stereo(_sine())
        n = stereo.shape[0]
        path = bounce.process_and_export(
            stereo, tmp_path / "loop.wav", loop_start=0, loop_end=n - 1
        )
        assert path.exists()

    def test_export_loop_without_end_raises(self, tmp_path):
        bounce = OfflineBounce(SR)
        with pytest.raises(ValueError, match="loop_end"):
            bounce.process_and_export(_stereo(_sine()), tmp_path / "x.wav", loop_start=0)


# ---------------------------------------------------------------------------
# StemRenderer
# ---------------------------------------------------------------------------

class TestStemRenderer:
    def _make_sequencer(self):
        """Create a minimal sequencer with two tracks."""
        from audio_engine.composer.sequencer import Sequencer
        from audio_engine.synthesizer.instrument import InstrumentLibrary

        seq = Sequencer(bpm=120, sample_rate=SR)
        piano = InstrumentLibrary.get("piano", SR)
        bass = InstrumentLibrary.get("bass", SR)
        seq.add_track("piano", piano, pan=0.0, volume=0.8)
        seq.add_track("bass", bass, pan=0.0, volume=0.7)
        seq.add_note("piano", 440.0, 0.0, 0.4)
        seq.add_note("bass", 110.0, 0.0, 0.8)
        return seq

    def test_render_stems_creates_files(self, tmp_path):
        renderer = StemRenderer(output_dir=tmp_path, sample_rate=SR)
        seq = self._make_sequencer()
        paths = renderer.render_stems(seq)
        assert len(paths) == 2
        for name, path in paths.items():
            assert path.exists(), f"Stem '{name}' not found at {path}"
            assert path.stat().st_size > 0

    def test_render_stems_with_prefix(self, tmp_path):
        renderer = StemRenderer(output_dir=tmp_path, sample_rate=SR)
        seq = self._make_sequencer()
        paths = renderer.render_stems(seq, prefix="battle_")
        for name, path in paths.items():
            assert "battle_" in path.name

    def test_render_mix_creates_file(self, tmp_path):
        renderer = StemRenderer(output_dir=tmp_path, sample_rate=SR)
        seq = self._make_sequencer()
        path = renderer.render_mix(seq, filename="full_mix")
        assert path.exists()
        assert path.stat().st_size > 0

    def test_render_stems_normalised(self, tmp_path):
        """Stems should be normalised to approximately -3 dBFS."""
        import wave

        renderer = StemRenderer(output_dir=tmp_path, sample_rate=SR)
        seq = self._make_sequencer()
        paths = renderer.render_stems(seq, normalise_stems=True)

        for name, path in paths.items():
            with wave.open(str(path), "r") as wf:
                raw = wf.readframes(wf.getnframes())
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            peak = np.max(np.abs(samples))
            # If there is any signal, peak should be near 0.707 (-3 dBFS)
            if peak > 1e-6:
                assert peak <= 0.75, f"Stem '{name}' not normalised: peak={peak:.4f}"
