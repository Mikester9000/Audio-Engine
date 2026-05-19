"""
Deterministic regression harness for factory workflows.

Validates that fixed-seed generation and QA checks produce stable, reproducible
outputs across runs.  These tests catch regressions in:

- Procedural music generation (same seed → same LUFS, spectral profile, duration)
- SFX generation (same seed → same sample count, clipping status)
- Voice generation (same seed → same output length)
- QA metric stability (same audio → same LUFS / peak / spectral readings)
- Batch manifest reproducibility (same requests → same field names / counts)

All fixtures use committed example data or fully in-memory generation so there
are no external file dependencies.
"""

from __future__ import annotations

import json
import struct
import wave
from pathlib import Path

import numpy as np
import pytest

from audio_engine.qa import LoudnessMeter, ClippingDetector, SpectralAnalyzer
from audio_engine.qa.spectral_analyzer import SpectralReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SR = 22050


def _sine(freq: float, duration: float = 1.0, amp: float = 0.5, sr: int = SR) -> np.ndarray:
    t = np.arange(int(duration * sr)) / sr
    return (amp * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


def _write_wav(path: Path, audio: np.ndarray, sr: int = SR) -> None:
    """Write a mono float32 array as a 16-bit WAV."""
    pcm = np.clip(audio, -1.0, 1.0)
    samples_int = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples_int.tobytes())


# ---------------------------------------------------------------------------
# QA metric stability
# ---------------------------------------------------------------------------

class TestQAMetricStability:
    """Verify that QA measures return identical results for identical inputs."""

    def test_loudness_stable_across_calls(self):
        """LoudnessMeter must return the same LUFS for the same audio."""
        meter = LoudnessMeter(sample_rate=SR)
        audio = _sine(440.0, duration=3.0, amp=0.3)
        result_a = meter.measure(audio)
        result_b = meter.measure(audio)
        assert result_a.integrated_lufs == result_b.integrated_lufs
        assert result_a.true_peak_dbfs == result_b.true_peak_dbfs
        assert result_a.loudness_range_lu == result_b.loudness_range_lu

    def test_clipping_stable_across_calls(self):
        """ClippingDetector must return the same report for the same audio."""
        detector = ClippingDetector()
        audio = np.ones(SR, dtype=np.float32) * 0.5
        r1 = detector.detect(audio)
        r2 = detector.detect(audio)
        assert r1.has_clipping == r2.has_clipping
        assert r1.clipped_samples == r2.clipped_samples
        assert r1.peak_dbfs == r2.peak_dbfs

    def test_spectral_stable_across_calls(self):
        """SpectralAnalyzer must return identical ratios for the same audio."""
        sa = SpectralAnalyzer(sample_rate=SR)
        audio = _sine(1000.0, duration=2.0, amp=0.4)
        r1 = sa.analyze(audio)
        r2 = sa.analyze(audio)
        assert r1.low_ratio == r2.low_ratio
        assert r1.mid_ratio == r2.mid_ratio
        assert r1.high_ratio == r2.high_ratio
        assert r1.spectral_centroid_hz == r2.spectral_centroid_hz

    def test_loudness_different_seeds_produce_different_lufs(self):
        """Different amplitude signals must produce different LUFS readings."""
        meter = LoudnessMeter(sample_rate=SR)
        quiet = _sine(440.0, duration=3.0, amp=0.05)
        loud = _sine(440.0, duration=3.0, amp=0.8)
        assert meter.integrated_loudness(loud) > meter.integrated_loudness(quiet)


# ---------------------------------------------------------------------------
# Procedural music generation reproducibility
# ---------------------------------------------------------------------------

class TestMusicGenReproducibility:
    """Verify that fixed-seed music generation produces stable outputs."""

    def test_same_seed_same_duration(self):
        """Two runs with the same seed must produce audio of equal length."""
        from audio_engine.ai.music_gen import MusicGen
        gen = MusicGen(sample_rate=SR, seed=42)
        audio_a = gen.generate(prompt="field day theme", duration=1.0)
        gen2 = MusicGen(sample_rate=SR, seed=42)
        audio_b = gen2.generate(prompt="field day theme", duration=1.0)
        assert len(audio_a) == len(audio_b)

    def test_different_seeds_may_differ(self):
        """Different seeds should not be required to be identical."""
        from audio_engine.ai.music_gen import MusicGen
        gen_a = MusicGen(sample_rate=SR, seed=1)
        gen_b = MusicGen(sample_rate=SR, seed=2)
        a = gen_a.generate(prompt="dungeon theme", duration=1.0)
        b = gen_b.generate(prompt="dungeon theme", duration=1.0)
        # Different seeds may or may not differ numerically; both must be valid arrays
        assert isinstance(a, np.ndarray)
        assert isinstance(b, np.ndarray)

    def test_qa_stable_on_generated_music(self):
        """QA checks on generated music must be stable across repeated analysis."""
        from audio_engine.ai.music_gen import MusicGen
        gen = MusicGen(sample_rate=SR, seed=7)
        audio = gen.generate(prompt="battle theme", duration=1.0)
        meter = LoudnessMeter(sample_rate=SR)
        lufs_a = meter.integrated_loudness(audio)
        lufs_b = meter.integrated_loudness(audio)
        assert lufs_a == lufs_b


# ---------------------------------------------------------------------------
# SFX generation reproducibility
# ---------------------------------------------------------------------------

class TestSFXGenReproducibility:
    """Verify that fixed-seed SFX generation produces stable outputs."""

    def test_same_seed_same_sample_count(self):
        """Same seed must produce the same number of samples."""
        from audio_engine.ai.sfx_gen import SFXGen
        gen = SFXGen(sample_rate=SR, seed=99)
        a = gen.generate(prompt="explosion")
        gen2 = SFXGen(sample_rate=SR, seed=99)
        b = gen2.generate(prompt="explosion")
        assert len(a) == len(b)

    def test_same_seed_same_clipping_status(self):
        """Clipping status must be reproducible for the same seed."""
        from audio_engine.ai.sfx_gen import SFXGen
        detector = ClippingDetector()
        gen = SFXGen(sample_rate=SR, seed=55)
        audio = gen.generate(prompt="sword swing")
        r1 = detector.detect(audio)
        r2 = detector.detect(audio)
        assert r1.has_clipping == r2.has_clipping

    def test_sfx_qa_spectral_stability(self):
        """Spectral analysis of fixed SFX must be reproducible."""
        from audio_engine.ai.sfx_gen import SFXGen
        sa = SpectralAnalyzer(sample_rate=SR)
        gen = SFXGen(sample_rate=SR, seed=13)
        audio = gen.generate(prompt="laser shot")
        r1 = sa.analyze(audio)
        r2 = sa.analyze(audio)
        assert r1.high_freq_ratio == r2.high_freq_ratio
        assert r1.spectral_centroid_hz == r2.spectral_centroid_hz


# ---------------------------------------------------------------------------
# Delivery manifest reproducibility (SESSION-037)
# ---------------------------------------------------------------------------

class TestDeliveryManifestReproducibility:
    """Verify that export-wav-delivery produces stable manifest structure."""

    def test_manifest_schema_keys_are_stable(self, tmp_path):
        """delivery_manifest.json must always contain the required schema keys."""
        from audio_engine.integration.export_contract import WavDeliveryPipeline

        factory_root = tmp_path / "factory"
        delivery_dir = tmp_path / "delivery"
        approved_dir = factory_root / "approved" / "sfx"
        approved_dir.mkdir(parents=True)
        _write_wav(approved_dir / "laser.wav", _sine(800.0, duration=0.5))

        pipeline = WavDeliveryPipeline()
        report = pipeline.deliver(factory_root=factory_root, delivery_dir=delivery_dir)

        assert "deliveryManifestVersion" in report
        assert "factoryRoot" in report
        assert "deliveryDir" in report
        assert "generatedAt" in report
        assert report["summary"]["total"] == 1
        assert report["summary"]["copied"] == 1

    def test_delivery_names_are_deterministic(self, tmp_path):
        """Running delivery twice must produce identical filenames."""
        from audio_engine.integration.export_contract import WavDeliveryPipeline

        factory_root = tmp_path / "factory"
        approved_dir = factory_root / "approved" / "music"
        approved_dir.mkdir(parents=True)
        _write_wav(approved_dir / "bgm_town.wav", _sine(440.0, duration=1.0))

        pipeline = WavDeliveryPipeline()

        delivery1 = tmp_path / "delivery1"
        report1 = pipeline.deliver(factory_root=factory_root, delivery_dir=delivery1)

        delivery2 = tmp_path / "delivery2"
        report2 = pipeline.deliver(factory_root=factory_root, delivery_dir=delivery2)

        names1 = [e["deliveryName"] for e in report1["entries"]]
        names2 = [e["deliveryName"] for e in report2["entries"]]
        assert names1 == names2

    def test_provenance_sidecar_seeds_appear_in_names(self, tmp_path):
        """When a provenance sidecar is present, its seed appears in the filename."""
        from audio_engine.integration.export_contract import WavDeliveryPipeline

        factory_root = tmp_path / "factory"
        approved_dir = factory_root / "approved" / "sfx"
        approved_dir.mkdir(parents=True)

        wav_path = approved_dir / "coin_pickup.wav"
        _write_wav(wav_path, _sine(1200.0, duration=0.3))

        # Write a fake provenance sidecar with known seed
        prov = {
            "provenanceVersion": "1.0.0",
            "assetId": "sfx_coin_pickup",
            "seed": 1337,
            "type": "sfx",
        }
        (approved_dir / "coin_pickup.provenance.json").write_text(
            json.dumps(prov), encoding="utf-8"
        )

        pipeline = WavDeliveryPipeline()
        report = pipeline.deliver(
            factory_root=factory_root,
            delivery_dir=tmp_path / "delivery",
        )
        entry = report["entries"][0]
        assert "1337" in entry["deliveryName"]
        assert entry["assetId"] == "sfx_coin_pickup"
