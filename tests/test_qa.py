"""Tests for the QA module: LoudnessMeter, ClippingDetector, LoopAnalyzer."""

from __future__ import annotations

import numpy as np
import pytest

from audio_engine.qa import LoudnessMeter, ClippingDetector, LoopAnalyzer
from audio_engine.qa.loudness_meter import LoudnessResult
from audio_engine.qa.clipping_detector import ClippingReport
from audio_engine.qa.loop_analyzer import LoopReport


SR = 22050


def _sine(freq: float, duration: float = 1.0, amp: float = 0.5, sr: int = SR) -> np.ndarray:
    t = np.arange(int(duration * sr)) / sr
    return (amp * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


def _stereo(sig: np.ndarray) -> np.ndarray:
    return np.stack([sig, sig], axis=1)


# ---------------------------------------------------------------------------
# LoudnessMeter
# ---------------------------------------------------------------------------

class TestLoudnessMeter:
    def test_silence_returns_very_low_lufs(self):
        meter = LoudnessMeter(SR)
        silent = np.zeros(SR * 5, dtype=np.float32)
        lufs = meter.integrated_loudness(silent)
        assert lufs < -100.0

    def test_loud_signal_returns_higher_lufs(self):
        meter = LoudnessMeter(SR)
        loud = np.ones(SR * 5, dtype=np.float32) * 0.9
        quiet = np.ones(SR * 5, dtype=np.float32) * 0.01
        assert meter.integrated_loudness(loud) > meter.integrated_loudness(quiet)

    def test_stereo_signal_measured(self):
        meter = LoudnessMeter(SR)
        stereo = _stereo(_sine(440.0, duration=3.0))
        lufs = meter.integrated_loudness(stereo)
        assert lufs < 0.0  # should be a finite negative number

    def test_true_peak_at_full_scale(self):
        meter = LoudnessMeter(SR)
        full = np.ones(SR, dtype=np.float32)
        tp = meter.true_peak(full)
        assert abs(tp) < 1.0  # 0 dBFS ± 1 dB

    def test_true_peak_silence(self):
        meter = LoudnessMeter(SR)
        tp = meter.true_peak(np.zeros(SR, dtype=np.float32))
        assert tp < -100.0

    def test_measure_returns_result_object(self):
        meter = LoudnessMeter(SR)
        audio = _sine(440.0, duration=3.0)
        result = meter.measure(audio)
        assert isinstance(result, LoudnessResult)
        assert hasattr(result, "integrated_lufs")
        assert hasattr(result, "true_peak_dbfs")
        assert hasattr(result, "loudness_range_lu")

    def test_loudness_range_short_signal(self):
        """Short signals (< 3 s) return 0 LU range – acceptable."""
        meter = LoudnessMeter(SR)
        short = _sine(440.0, duration=1.0)
        lra = meter.loudness_range(short)
        assert lra >= 0.0


# ---------------------------------------------------------------------------
# ClippingDetector
# ---------------------------------------------------------------------------

class TestClippingDetector:
    def test_no_clipping_sine(self):
        detector = ClippingDetector(threshold=0.999)
        sig = _sine(440.0, amp=0.5)
        report = detector.detect(sig)
        assert not report.has_clipping
        assert report.clipped_samples == 0

    def test_clipping_detected(self):
        detector = ClippingDetector(threshold=0.9)
        # Signal at 1.0 peak will clip above 0.9
        clipped = np.ones(100, dtype=np.float32)
        report = detector.detect(clipped)
        assert report.has_clipping
        assert report.clipped_samples > 0

    def test_stereo_clips_reported_per_channel(self):
        detector = ClippingDetector(threshold=0.9)
        # Only the left channel clips
        sig = np.zeros((100, 2), dtype=np.float32)
        sig[:, 0] = 1.0  # left clips
        sig[:, 1] = 0.5  # right OK
        report = detector.detect(sig)
        assert report.has_clipping
        assert report.clipped_samples_per_channel[0] > 0
        assert report.clipped_samples_per_channel[1] == 0

    def test_clip_ratio_calculation(self):
        detector = ClippingDetector(threshold=0.5)
        sig = np.ones(100, dtype=np.float32)  # all samples clip
        report = detector.detect(sig)
        assert abs(report.clip_ratio - 1.0) < 1e-5

    def test_summary_no_clipping(self):
        detector = ClippingDetector()
        sig = _sine(440.0, amp=0.3)
        report = detector.detect(sig)
        assert "OK" in report.summary()

    def test_summary_clipping(self):
        detector = ClippingDetector(threshold=0.9)
        sig = np.ones(100, dtype=np.float32)
        report = detector.detect(sig)
        assert "CLIPPING" in report.summary()

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            ClippingDetector(threshold=0.0)

    def test_report_peak_dbfs(self):
        detector = ClippingDetector()
        sig = np.ones(100, dtype=np.float32)
        report = detector.detect(sig)
        assert abs(report.peak_dbfs) < 0.01  # ~0 dBFS

    def test_detect_wav(self, tmp_path):
        """Smoke test: write a WAV, then detect clipping from file."""
        import wave
        import struct

        path = tmp_path / "test.wav"
        samples = np.ones(1000, dtype=np.int16) * 32767  # full scale 16-bit
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(samples.tobytes())

        detector = ClippingDetector(threshold=0.999)
        report = detector.detect_wav(str(path))
        assert isinstance(report, ClippingReport)


# ---------------------------------------------------------------------------
# LoopAnalyzer
# ---------------------------------------------------------------------------

class TestLoopAnalyzer:
    def test_seamless_loop_detected(self):
        """A signal that ends and starts at zero should be seamless."""
        n = SR
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        # Exactly one period – start and end are both zero-crossings
        audio = np.sin(t).astype(np.float32)
        analyzer = LoopAnalyzer(SR, jump_threshold=0.1)
        report = analyzer.analyze(audio)
        # amplitude jump at the exact period boundary is 0
        assert report.amplitude_jump < 0.1

    def test_large_jump_detected(self):
        """A signal with a large discontinuity at the loop point."""
        n = SR
        audio = np.zeros(n, dtype=np.float32)
        audio[0] = 1.0    # start at +1
        audio[-1] = -1.0  # end at -1 → jump = 2
        analyzer = LoopAnalyzer(SR, jump_threshold=0.1)
        report = analyzer.analyze(audio)
        assert report.amplitude_jump >= 1.0

    def test_custom_loop_points(self):
        n = SR
        audio = np.zeros(n, dtype=np.float32)
        audio[100] = 0.8   # large value at loop end
        audio[200] = 0.0   # clean start
        analyzer = LoopAnalyzer(SR)
        report = analyzer.analyze(audio, loop_start=200, loop_end=100)
        assert isinstance(report, LoopReport)

    def test_summary_strings(self):
        n = 2000
        audio = np.sin(np.linspace(0, 2 * np.pi, n)).astype(np.float32)
        analyzer = LoopAnalyzer(SR)
        report = analyzer.analyze(audio)
        summary = report.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_stereo_analysis(self):
        n = SR
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        mono = np.sin(t).astype(np.float32)
        stereo = np.stack([mono, mono], axis=1)
        analyzer = LoopAnalyzer(SR)
        report = analyzer.analyze(stereo)
        assert isinstance(report, LoopReport)


# ---------------------------------------------------------------------------
# SpectralAnalyzer
# ---------------------------------------------------------------------------

from audio_engine.qa import SpectralAnalyzer
from audio_engine.qa.spectral_analyzer import SpectralReport


class TestSpectralAnalyzer:
    def test_returns_spectral_report(self):
        sa = SpectralAnalyzer(sample_rate=SR)
        audio = _sine(1000.0, duration=1.0)
        report = sa.analyze(audio)
        assert isinstance(report, SpectralReport)

    def test_band_ratios_sum_to_one(self):
        sa = SpectralAnalyzer(sample_rate=SR)
        audio = _sine(440.0, duration=1.0)
        report = sa.analyze(audio)
        total = report.low_ratio + report.mid_ratio + report.high_ratio
        assert abs(total - 1.0) < 0.01

    def test_low_freq_dominant_in_bass_signal(self):
        """A 60 Hz sine should have majority energy in the low band."""
        sa = SpectralAnalyzer(sample_rate=SR, low_cutoff=250.0)
        audio = _sine(60.0, duration=1.0)
        report = sa.analyze(audio)
        assert report.low_ratio > 0.5

    def test_high_freq_dominant_in_treble_signal(self):
        """A 8 kHz sine should have majority energy in the high band."""
        sa = SpectralAnalyzer(sample_rate=SR, high_cutoff=4000.0)
        audio = _sine(8000.0, duration=1.0)
        report = sa.analyze(audio)
        assert report.high_ratio > 0.5

    def test_spectral_balance_fails_for_single_tone(self):
        """A pure 1 kHz tone concentrates nearly all energy in the mid band → imbalanced."""
        sa = SpectralAnalyzer(sample_rate=SR, max_band_ratio=0.90)
        audio = _sine(1000.0, duration=1.0)
        report = sa.analyze(audio)
        # A single-frequency tone is spectrally dominant in one band
        assert not report.spectral_balance_ok

    def test_spectral_balance_fails_for_all_bass(self):
        """A pure 80 Hz tone concentrates all energy in lows → imbalanced."""
        sa = SpectralAnalyzer(sample_rate=SR, max_band_ratio=0.90)
        audio = _sine(80.0, duration=1.0)
        report = sa.analyze(audio)
        assert not report.spectral_balance_ok

    def test_intelligibility_ok_with_high_freq(self):
        """High-frequency content above 2 kHz passes intelligibility check."""
        sa = SpectralAnalyzer(sample_rate=SR, min_hf_ratio=0.01)
        audio = _sine(5000.0, duration=1.0)
        report = sa.analyze(audio)
        assert report.intelligibility_ok

    def test_intelligibility_fails_for_pure_low_freq(self):
        """A 40 Hz tone has no high-frequency content → fails intelligibility."""
        sa = SpectralAnalyzer(sample_rate=SR, min_hf_ratio=0.05)
        audio = _sine(40.0, duration=1.0)
        report = sa.analyze(audio)
        assert not report.intelligibility_ok

    def test_silence_handled_gracefully(self):
        sa = SpectralAnalyzer(sample_rate=SR)
        silent = np.zeros(SR, dtype=np.float32)
        report = sa.analyze(silent)
        assert report.spectral_balance_ok  # silence is not imbalanced
        assert not report.intelligibility_ok  # silence has no HF content

    def test_stereo_input_accepted(self):
        sa = SpectralAnalyzer(sample_rate=SR)
        stereo = _stereo(_sine(440.0, duration=1.0))
        report = sa.analyze(stereo)
        assert isinstance(report, SpectralReport)

    def test_summary_string(self):
        sa = SpectralAnalyzer(sample_rate=SR)
        audio = _sine(1000.0, duration=1.0)
        report = sa.analyze(audio)
        summary = report.summary()
        assert isinstance(summary, str)
        assert "Spectral" in summary

    def test_centroid_in_expected_range(self):
        """Spectral centroid for a 1 kHz tone should be near 1 kHz."""
        sa = SpectralAnalyzer(sample_rate=SR)
        audio = _sine(1000.0, duration=1.0)
        report = sa.analyze(audio)
        assert 800.0 < report.spectral_centroid_hz < 1200.0
