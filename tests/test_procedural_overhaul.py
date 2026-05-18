from __future__ import annotations

import numpy as np

from audio_engine.ai.generator import MusicGenerator
from audio_engine.ai.sfx_synth import synthesise_sfx
from audio_engine.ai.voice_synth import VOICE_PRESETS, synthesise_voice
from audio_engine.composer.phrase import MotifBank, SectionPlanner
from audio_engine.composer.sequencer import Sequencer
from audio_engine.cli import build_parser, main


def _spectral_centroid(audio: np.ndarray, sample_rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(audio.astype(np.float64)))
    freqs = np.fft.rfftfreq(len(audio), d=1.0 / sample_rate)
    denom = np.sum(spectrum) + 1e-9
    return float(np.sum(freqs * spectrum) / denom)


def test_section_planner_is_deterministic_and_covers_bars():
    a = SectionPlanner(style="battle", total_bars=16, seed=17).plan()
    b = SectionPlanner(style="battle", total_bars=16, seed=17).plan()
    assert a == b
    assert a[0].bar_start == 0
    assert sum(block.bar_length for block in a) == 16
    for prev, nxt in zip(a, a[1:]):
        assert prev.bar_start + prev.bar_length == nxt.bar_start


def test_section_planner_short_forms_still_cover_requested_bars():
    plan = SectionPlanner(style="battle", total_bars=4, seed=17).plan()
    assert sum(block.bar_length for block in plan) == 4
    assert [block.role.name for block in plan] == ["INTRO", "A_PHRASE", "CLIMAX", "CADENCE"]


def test_section_planner_seed_none_does_not_collide_with_zero(monkeypatch):
    class _StubSystemRandom:
        def randrange(self, start: int, stop: int | None = None) -> int:
            return 12345

    monkeypatch.setattr("audio_engine.composer.phrase.random.SystemRandom", lambda: _StubSystemRandom())
    none_seed = SectionPlanner(style="battle", total_bars=16, seed=None).plan()
    zero_seed = SectionPlanner(style="battle", total_bars=16, seed=0).plan()
    assert none_seed != zero_seed


def test_motif_bank_variations_change_sequence():
    bank = MotifBank(scale_degree_count=7, seed=5)
    motif = bank.seed_motif()
    assert bank.sequence_up(motif) != motif
    assert bank.sequence_down(motif) != motif
    assert bank.invert(motif) != motif


def test_sfx_profiles_have_distinct_spectral_character():
    sr = 22050
    explosion = synthesise_sfx("explosion", duration=0.8, sample_rate=sr, seed=3)
    coin = synthesise_sfx("coin", duration=0.8, sample_rate=sr, seed=3)
    magic = synthesise_sfx("magic", duration=0.8, sample_rate=sr, seed=3)
    thunder = synthesise_sfx("thunder", duration=0.8, sample_rate=sr, seed=3)
    footstep = synthesise_sfx("footstep", duration=0.8, sample_rate=sr, seed=3)

    for arr in (explosion, coin, magic, thunder, footstep):
        assert arr.dtype == np.float32
        assert arr.size > 0
        assert np.max(np.abs(arr)) > 0.0

    c_explosion = _spectral_centroid(explosion, sr)
    c_coin = _spectral_centroid(coin, sr)
    c_magic = _spectral_centroid(magic, sr)
    c_thunder = _spectral_centroid(thunder, sr)
    c_footstep = _spectral_centroid(footstep, sr)

    assert c_coin > c_explosion
    assert abs(c_magic - c_footstep) > 120.0
    assert abs(c_thunder - c_coin) > 200.0


def test_music_generator_structured_and_deterministic():
    g1 = MusicGenerator(sample_rate=22050, seed=42)
    g2 = MusicGenerator(sample_rate=22050, seed=42)
    seq = g1.generate(style="battle", bars=16)
    assert "lead_melody" in seq._tracks
    assert "bass_line" in seq._tracks

    a1 = g1.generate_audio(style="battle", bars=16)
    a2 = g2.generate_audio(style="battle", bars=16)
    assert a1.ndim == 2 and a1.shape[1] == 2
    assert a1.dtype == np.float32
    np.testing.assert_array_equal(a1, a2)


def test_music_generator_seed_none_does_not_collide_with_zero(monkeypatch):
    class _StubSystemRandom:
        def randrange(self, start: int, stop: int | None = None) -> int:
            return 54321

    monkeypatch.setattr("audio_engine.ai.generator.random.SystemRandom", lambda: _StubSystemRandom())
    none_seed = MusicGenerator(sample_rate=22050, seed=None).generate_audio(style="battle", bars=4)
    zero_seed = MusicGenerator(sample_rate=22050, seed=0).generate_audio(style="battle", bars=4)
    assert not np.array_equal(none_seed, zero_seed)


def test_voice_synth_non_silent_and_deterministic():
    text = "Will we reach the crystal?"
    for preset in sorted(VOICE_PRESETS):
        audio = synthesise_voice(text, voice_preset=preset, speed=1.0, sample_rate=22050, seed=11)
        assert audio.dtype == np.float32
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0.0

    a = synthesise_voice("The gate is open.", voice_preset="narrator", seed=7)
    b = synthesise_voice("The gate is open.", voice_preset="narrator", seed=7)
    np.testing.assert_array_equal(a, b)


def test_low_sample_rate_sfx_and_voice_paths_stay_valid():
    sfx = synthesise_sfx("ui_click", duration=0.05, sample_rate=1000, seed=1)
    voice = synthesise_voice("s", sample_rate=4000, seed=2)
    assert sfx.dtype == np.float32
    assert sfx.size > 0
    assert voice.dtype == np.float32
    assert voice.size > 0


class _ConstantInstrument:
    def __init__(self, value: float = 0.1, sample_rate: int = 22050) -> None:
        self.value = value
        self.sample_rate = sample_rate

    def render(self, frequency: float, duration: float) -> np.ndarray:
        return np.full(int(duration * self.sample_rate), self.value, dtype=np.float32)


def test_sequencer_limits_to_eight_active_layers():
    sr = 22050
    seq = Sequencer(sample_rate=sr)
    for i in range(9):
        seq.add_track(f"t{i}", _ConstantInstrument(sample_rate=sr), pan=0.0, volume=1.0, priority=i + 1, role="harmony")
        seq.add_note(f"t{i}", 440.0, 0.0, 0.25, velocity=1.0)

    audio = seq.render(duration=0.25)
    assert audio.shape == (int(0.25 * sr), 2)
    assert audio.dtype == np.float32

    # At pan=0, per-track constant power gain is sqrt(0.5). 8 active notes should remain.
    expected = 8 * 0.1 * np.sqrt(0.5)
    assert np.isclose(audio[0, 0], expected, atol=1e-3)


def test_studio_import_and_cli_entrypoint(monkeypatch):
    import audio_engine.ui as ui

    called = {"ok": False}

    def _fake_launch() -> None:
        called["ok"] = True

    monkeypatch.setattr(ui, "launch_studio", _fake_launch)
    parser = build_parser()
    parsed = parser.parse_args(["studio"])
    assert parsed.command == "studio"

    rc = main(["studio"])
    assert rc == 0
    assert called["ok"] is True
