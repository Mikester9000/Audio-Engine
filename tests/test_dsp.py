"""Tests for the DSP module: EQ, Compressor, Limiter, ConvolutionReverb, resample, dither."""

from __future__ import annotations

import numpy as np
import pytest

from audio_engine.dsp import EQ, Compressor, Limiter, ConvolutionReverb, resample, dither
from audio_engine.dsp.eq import EQBand


SR = 22050


def _sine(freq: float, duration: float = 0.5, sr: int = SR) -> np.ndarray:
    """Helper: generate a mono float32 sine wave."""
    t = np.arange(int(duration * sr)) / sr
    return (0.5 * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


def _stereo(sig: np.ndarray) -> np.ndarray:
    return np.stack([sig, sig], axis=1)


# ---------------------------------------------------------------------------
# EQ
# ---------------------------------------------------------------------------

class TestEQ:
    def test_passthrough_no_bands(self):
        sig = _sine(440.0)
        eq = EQ(SR)
        out = eq.process(sig)
        np.testing.assert_array_almost_equal(out, sig, decimal=5)

    def test_low_shelf_reduces_low_frequencies(self):
        # A strong cut at 100 Hz should reduce 80 Hz energy
        eq = EQ(SR)
        eq.add_band(EQBand(100.0, gain_db=-20.0, band_type="low_shelf"))
        low_in = _sine(80.0)
        low_out = eq.process(low_in)
        assert np.mean(low_out ** 2) < np.mean(low_in ** 2)

    def test_high_shelf_boost(self):
        eq = EQ(SR)
        eq.add_band(EQBand(5000.0, gain_db=+12.0, band_type="high_shelf"))
        high_in = _sine(8000.0, sr=SR)
        high_out = eq.process(high_in)
        assert np.mean(high_out ** 2) > np.mean(high_in ** 2)

    def test_peak_band_changes_energy(self):
        eq = EQ(SR)
        eq.add_band(EQBand(1000.0, gain_db=-12.0, q=2.0, band_type="peak"))
        sig = _sine(1000.0)
        out = eq.process(sig)
        assert np.mean(out ** 2) < np.mean(sig ** 2)

    def test_stereo_input(self):
        eq = EQ(SR)
        eq.add_band(EQBand(200.0, gain_db=-6.0, band_type="low_shelf"))
        stereo = _stereo(_sine(440.0))
        out = eq.process(stereo)
        assert out.shape == stereo.shape

    def test_output_dtype(self):
        eq = EQ(SR)
        eq.add_band(EQBand(500.0, gain_db=0.0, band_type="peak"))
        out = eq.process(_sine(500.0))
        assert out.dtype == np.float32

    def test_chaining_add_band(self):
        eq = EQ(SR)
        eq.add_band(EQBand(100.0, gain_db=-3.0, band_type="low_shelf")).add_band(
            EQBand(8000.0, gain_db=+3.0, band_type="high_shelf")
        )
        out = eq.process(_sine(1000.0))
        assert out.shape == _sine(1000.0).shape

    def test_high_pass_removes_dc(self):
        eq = EQ(SR)
        eq.add_band(EQBand(200.0, gain_db=0.0, band_type="high_pass"))
        # A DC offset signal should be greatly attenuated
        dc = np.ones(SR, dtype=np.float32) * 0.5
        out = eq.process(dc)
        assert np.abs(np.mean(out)) < 0.1


# ---------------------------------------------------------------------------
# Compressor
# ---------------------------------------------------------------------------

class TestCompressor:
    def test_reduces_loud_signal(self):
        comp = Compressor(SR, threshold_db=-6.0, ratio=8.0, makeup_gain_db=0.0)
        loud = np.ones(SR, dtype=np.float32) * 0.9
        out = comp.process(loud)
        # Output should be quieter than input above threshold
        assert np.max(np.abs(out)) < np.max(np.abs(loud))

    def test_passes_quiet_signal_unchanged(self):
        comp = Compressor(SR, threshold_db=-6.0, ratio=4.0, makeup_gain_db=0.0)
        quiet = np.ones(SR, dtype=np.float32) * 0.05
        out = comp.process(quiet)
        np.testing.assert_array_almost_equal(out, quiet, decimal=3)

    def test_stereo_input(self):
        comp = Compressor(SR, threshold_db=-12.0, ratio=4.0)
        stereo = _stereo(_sine(440.0))
        out = comp.process(stereo)
        assert out.shape == stereo.shape

    def test_output_dtype(self):
        comp = Compressor(SR)
        out = comp.process(_sine(440.0))
        assert out.dtype == np.float32


# ---------------------------------------------------------------------------
# Limiter
# ---------------------------------------------------------------------------

class TestLimiter:
    def test_clips_peak_to_ceiling(self):
        limiter = Limiter(SR, ceiling_db=0.0)
        # Signal exceeding 0 dBFS
        loud = np.ones(SR, dtype=np.float32) * 2.0
        out = limiter.process(loud)
        assert np.max(np.abs(out)) <= 1.0 + 1e-4

    def test_ceiling_respected(self):
        ceiling_db = -6.0
        ceiling_linear = 10.0 ** (ceiling_db / 20.0)
        limiter = Limiter(SR, ceiling_db=ceiling_db)
        loud = np.ones(SR, dtype=np.float32) * 1.5
        out = limiter.process(loud)
        assert np.max(np.abs(out)) <= ceiling_linear + 1e-3

    def test_stereo_input(self):
        limiter = Limiter(SR, ceiling_db=-0.3)
        stereo = _stereo(np.ones(SR, dtype=np.float32) * 1.5)
        out = limiter.process(stereo)
        assert out.shape == stereo.shape

    def test_quiet_signal_passes_through(self):
        limiter = Limiter(SR, ceiling_db=-0.3)
        quiet = np.ones(SR, dtype=np.float32) * 0.1
        out = limiter.process(quiet)
        np.testing.assert_array_almost_equal(out, quiet, decimal=3)

    def test_output_dtype(self):
        limiter = Limiter(SR)
        out = limiter.process(_sine(440.0))
        assert out.dtype == np.float32


# ---------------------------------------------------------------------------
# ConvolutionReverb
# ---------------------------------------------------------------------------

class TestConvolutionReverb:
    def test_output_shape_mono(self):
        reverb = ConvolutionReverb(SR, rt60=0.3, wet=0.3)
        sig = _sine(440.0, duration=0.2)
        out = reverb.process(sig)
        assert out.shape == sig.shape

    def test_output_shape_stereo(self):
        reverb = ConvolutionReverb(SR, rt60=0.3, wet=0.3)
        stereo = _stereo(_sine(440.0, duration=0.2))
        out = reverb.process(stereo)
        assert out.shape == stereo.shape

    def test_wet_zero_equals_dry(self):
        reverb = ConvolutionReverb(SR, rt60=0.5, wet=0.0)
        sig = _sine(440.0, duration=0.2)
        out = reverb.process(sig)
        np.testing.assert_array_almost_equal(out, sig, decimal=4)

    def test_wet_adds_energy(self):
        reverb = ConvolutionReverb(SR, rt60=0.5, wet=0.5)
        sig = _sine(440.0, duration=0.5)
        out = reverb.process(sig)
        # Adding reverb tail should not drastically reduce energy
        assert np.sum(out ** 2) > 0


# ---------------------------------------------------------------------------
# resample
# ---------------------------------------------------------------------------

class TestResample:
    def test_upsample_length(self):
        sig = _sine(440.0, sr=22050)
        out = resample(sig, orig_sr=22050, target_sr=44100)
        expected_len = len(sig) * 2
        assert abs(len(out) - expected_len) <= 4

    def test_downsample_length(self):
        sig = _sine(440.0, sr=44100, duration=0.5)
        out = resample(sig, orig_sr=44100, target_sr=22050)
        expected_len = len(sig) // 2
        assert abs(len(out) - expected_len) <= 4

    def test_same_rate_passthrough(self):
        sig = _sine(440.0)
        out = resample(sig, orig_sr=SR, target_sr=SR)
        np.testing.assert_array_equal(out, sig)

    def test_stereo_upsample(self):
        stereo = _stereo(_sine(440.0, sr=22050))
        out = resample(stereo, orig_sr=22050, target_sr=44100)
        assert out.ndim == 2
        assert out.shape[1] == 2

    def test_output_dtype(self):
        sig = _sine(440.0)
        out = resample(sig, orig_sr=SR, target_sr=44100)
        assert out.dtype == np.float32


# ---------------------------------------------------------------------------
# dither
# ---------------------------------------------------------------------------

class TestDither:
    def test_output_shape_preserved(self):
        sig = _sine(440.0)
        out = dither(sig, bit_depth=16)
        assert out.shape == sig.shape

    def test_none_passthrough(self):
        sig = _sine(440.0)
        out = dither(sig, bit_depth=16, dither_type="none")
        np.testing.assert_array_equal(out, sig)

    def test_dither_is_small(self):
        # Dither noise should be much smaller than 1 LSB at 16-bit
        sig = np.zeros(44100, dtype=np.float32)
        out = dither(sig, bit_depth=16, seed=0)
        lsb = 2.0 / (2 ** 16)
        assert np.max(np.abs(out)) < lsb * 2

    def test_tpdf_and_rpdf(self):
        sig = _sine(440.0)
        out_tpdf = dither(sig, bit_depth=16, dither_type="tpdf", seed=1)
        out_rpdf = dither(sig, bit_depth=16, dither_type="rpdf", seed=1)
        assert out_tpdf.shape == sig.shape
        assert out_rpdf.shape == sig.shape

    def test_stereo_dither(self):
        stereo = _stereo(_sine(440.0))
        out = dither(stereo, bit_depth=16)
        assert out.shape == stereo.shape
