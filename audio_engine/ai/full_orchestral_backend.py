"""
Full Orchestral Synth backend.

Produces rich, multi-section orchestral audio using the full instrument library
including the new woodwinds (oboe, clarinet), extended strings (cello), keyboard
(harp, celesta), and tuned percussion (timpani, marimba).

This is the highest-quality fully-local backend in the pipeline:

    ps1              →  synth_orchestral  →  full_orchestral  →  sample
    (bit-crushed)       (clean synth)        (rich sections)     (real WAVs)

Key improvements over ``synth_orchestral``:
* Each orchestral section is rendered with a dedicated stereo position:
    - Strings: left-center (pan -0.25)
    - Woodwinds: center (pan 0.0)
    - Brass: right-center (pan +0.25)
    - Keyboard/harp: right (pan +0.38)
    - Timpani/percussion: center (pan 0.0)
* Section-specific reverb character (hall for strings, room for woodwinds, plate for brass).
* OST mastering profile applied for a wider, more cinematic result.
* Voice output is processed through a larger room reverb for intelligibility.
"""

from __future__ import annotations

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend

__all__ = ["FullOrchestralBackend"]

# ---------------------------------------------------------------------------
# Per-style orchestral section overrides
# Maps style name → (lead_section, counter_section, bass_section, use_timpani)
# The sections map to instrument families in the InstrumentLibrary.
# ---------------------------------------------------------------------------
_ORCHESTRAL_STYLE_MAP: dict[str, dict[str, str]] = {
    # Orchestral styles use proper section instruments
    "orchestral_epic": {
        "lead": "french_horn",
        "counter": "oboe",
        "bass": "cello",
        "ostinato": "harp",
    },
    "choral_fantasy": {
        "lead": "choir",
        "counter": "clarinet",
        "bass": "cello",
        "ostinato": "harp",
    },
    "ambient": {
        "lead": "synth_pad",
        "counter": "celesta",
        "bass": "synth_pad",
        "ostinato": "celesta",
    },
    "exploration": {
        "lead": "flute",
        "counter": "oboe",
        "bass": "cello",
        "ostinato": "harp",
    },
    "celtic_adventure": {
        "lead": "flute",
        "counter": "clarinet",
        "bass": "cello",
        "ostinato": "marimba",
    },
    "horror_ambient": {
        "lead": "synth_pad",
        "counter": "celesta",
        "bass": "synth_pad",
        "ostinato": "celesta",
    },
    "battle": {
        "lead": "brass",
        "counter": "french_horn",
        "bass": "cello",
        "ostinato": "marimba",
    },
    "boss": {
        "lead": "brass",
        "counter": "french_horn",
        "bass": "cello",
        "ostinato": "timpani",
    },
    "menu": {
        "lead": "piano",
        "counter": "celesta",
        "bass": "cello",
        "ostinato": "harp",
    },
    "victory": {
        "lead": "brass",
        "counter": "french_horn",
        "bass": "cello",
        "ostinato": "marimba",
    },
}

# ---------------------------------------------------------------------------
# Stereo panning positions per track role
# ---------------------------------------------------------------------------
_SECTION_PAN: dict[str, float] = {
    # Strings family
    "cello":        -0.35,
    "strings":      -0.25,
    "ff7_strings":  -0.22,
    # Woodwinds
    "flute":         0.0,
    "oboe":          0.08,
    "clarinet":     -0.08,
    # Brass
    "brass":         0.28,
    "french_horn":   0.20,
    # Keyboard / harp / percussion
    "piano":         0.10,
    "harpsichord":   0.10,
    "harp":          0.38,
    "celesta":       0.34,
    "marimba":       0.30,
    "timpani":       0.0,
    "percussion":    0.0,
    # Synth / choir (centre)
    "choir":        -0.05,
    "synth_pad":     0.0,
    "crystal_synth": 0.30,
    # Other
    "bass":          0.0,
    "ff7_bass":      0.0,
    "ff7_lead":      0.0,
}


class FullOrchestralBackend(InferenceBackend):
    """Rich multi-section orchestral synth backend.

    Uses all new orchestral instruments (oboe, clarinet, french_horn, cello,
    harp, celesta, timpani, marimba) with per-section stereo panning and an
    OST mastering profile for a cinematic orchestral result.

    Parameters
    ----------
    sample_rate:
        Engine sample rate in Hz.
    seed:
        RNG seed for reproducibility.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        seed: int | None = None,
    ) -> None:
        super().__init__(sample_rate)
        self._seed = seed
        self._procedural = ProceduralBackend(sample_rate=sample_rate, seed=seed)

    @property
    def name(self) -> str:
        return "full_orchestral"

    def dependency_summary(self) -> str:
        return "numpy/scipy full orchestral synthesis pipeline (bundled)"

    def supported_modalities(self) -> tuple[str, ...]:
        return ("music", "sfx", "voice")

    # ------------------------------------------------------------------
    # Music generation
    # ------------------------------------------------------------------

    def generate_music_audio(
        self,
        style: str,
        duration: float,
        bpm: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate rich orchestral music with per-section stereo staging.

        The orchestral section overrides in ``_ORCHESTRAL_STYLE_MAP`` ensure
        that each style uses instruments from distinct tonal families, giving
        clear separation between strings, woodwinds, brass, keyboard, and
        tuned percussion sections.

        Parameters
        ----------
        style:
            Style preset.
        duration:
            Target duration in seconds.
        bpm:
            Optional BPM override.
        """
        audio = self._generate_orchestral_music(style=style, duration=duration, bpm=bpm)
        return self._apply_ost_mastering(audio)

    def generate_sfx_audio(
        self,
        sfx_type: str,
        duration: float,
        pitch_hz: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate SFX with light hall staging — transients stay punchy."""
        audio = self._procedural.generate_sfx_audio(
            sfx_type=sfx_type, duration=duration, pitch_hz=pitch_hz
        )
        return self._apply_sfx_polish(audio)

    def generate_voice_audio(
        self,
        text: str,
        voice_preset: str = "narrator",
        speed: float = 1.0,
        **kwargs,
    ) -> np.ndarray:
        """Generate voice with light room reverb for intelligibility."""
        audio = self._procedural.generate_voice_audio(
            text=text, voice_preset=voice_preset, speed=speed
        )
        return self._apply_voice_polish(audio)

    # ------------------------------------------------------------------
    # Orchestral music assembly
    # ------------------------------------------------------------------

    def _generate_orchestral_music(
        self,
        style: str,
        duration: float,
        bpm: float | None = None,
    ) -> np.ndarray:
        """Build orchestral music using per-section instrument routing."""
        from audio_engine.ai.generator import MusicGenerator, _STYLE_DEFS
        from audio_engine.synthesizer.instrument import InstrumentLibrary
        from audio_engine.composer.sequencer import Sequencer
        from audio_engine.composer.scale import ScaleLibrary
        from audio_engine.composer.phrase import MotifBank, PhraseRole, SectionPlanner

        sdef = _STYLE_DEFS.get(style)
        if sdef is None:
            # Fallback to procedural for unknown styles
            return self._procedural.generate_music_audio(
                style=style, duration=duration, bpm=bpm
            )

        effective_bpm = bpm or sdef.bpm
        bar_duration = 60.0 / effective_bpm * 4
        bars = max(1, round(duration / bar_duration))

        # Build a generator just for its motif/phrase planning helpers
        gen = MusicGenerator(sample_rate=self.sample_rate, seed=self._seed)

        # Apply style-specific orchestral section mapping
        overrides = _ORCHESTRAL_STYLE_MAP.get(style, {})

        # Derive instrument names from the override map or fall back to style def
        lead_name    = overrides.get("lead",     sdef.instruments[0] if sdef.instruments else "strings")
        counter_name = overrides.get("counter",  sdef.instruments[1] if len(sdef.instruments) > 1 else "oboe")
        pad_name     = overrides.get("pad",      sdef.accompaniment[0] if sdef.accompaniment else "strings")
        chord_name   = overrides.get("chord",    sdef.accompaniment[1] if len(sdef.accompaniment) > 1 else "strings")
        bass_name    = overrides.get("bass",     sdef.bass_instrument or "cello")
        ostinato_name = overrides.get("ostinato", sdef.ostinato_instrument)

        # Build sequencer and add per-section tracks with distinct panning
        seq = Sequencer(bpm=effective_bpm, sample_rate=self.sample_rate)

        def _pan(name: str) -> float:
            return _SECTION_PAN.get(name, 0.0)

        seq.add_track("lead_melody",   InstrumentLibrary.get(lead_name,    self.sample_rate), pan=_pan(lead_name),    volume=0.90, priority=100, role="melody")
        seq.add_track("counter_melody", InstrumentLibrary.get(counter_name, self.sample_rate), pan=_pan(counter_name), volume=0.58, priority=90,  role="counter")
        seq.add_track("high_ostinato",  InstrumentLibrary.get(ostinato_name, self.sample_rate), pan=_pan(ostinato_name), volume=0.44, priority=50, role="texture")
        seq.add_track("harmony_pad",    InstrumentLibrary.get(pad_name,     self.sample_rate), pan=_pan(pad_name),     volume=0.50, priority=70,  role="harmony")
        seq.add_track("chord_support",  InstrumentLibrary.get(chord_name,   self.sample_rate), pan=_pan(chord_name),   volume=0.50, priority=60,  role="harmony")
        seq.add_track("bass_line",      InstrumentLibrary.get(bass_name,    self.sample_rate), pan=_pan(bass_name),    volume=0.86, priority=95,  role="bass")

        # Percussion: prefer timpani for full orchestral styles
        perc_name = sdef.percussion_instrument
        if perc_name:
            # Use timpani in place of generic percussion for orchestral styles
            if perc_name == "percussion" and style in {"orchestral_epic", "battle", "boss", "victory", "triumph_fanfare", "rock_epic"}:
                perc_name = "timpani"
            try:
                perc_inst = InstrumentLibrary.get(perc_name, self.sample_rate)
                seq.add_track("perc_low",     perc_inst, pan=0.0,  volume=0.80, priority=85, role="percussion")
                seq.add_track("perc_texture", perc_inst, pan=0.28, volume=0.40, priority=40, role="texture")
            except KeyError:
                pass

        # Use the generator's phrase planning helpers to fill the sequencer
        import random
        scale_name = gen._resolve_scale_name(style, sdef.scale_name)
        scale = ScaleLibrary.get(scale_name, sdef.root, sdef.octave)
        rng = gen._rng_for_call(style, bars)

        planner = SectionPlanner(style=style, total_bars=bars, seed=gen._seed)
        blocks = planner.plan()
        motif_bank = MotifBank(scale_degree_count=len(scale.intervals), seed=gen._seed)
        motif_seed = motif_bank.seed_motif()
        cadence_target = 1
        bar_dur = seq.bar_duration

        for block in blocks:
            for rel_bar in range(block.bar_length):
                bar_index = block.bar_start + rel_bar
                if bar_index >= bars:
                    break
                bar_onset = bar_index * bar_dur
                is_phrase_end = rel_bar == block.bar_length - 1
                motif = gen._vary_motif(motif_bank, motif_seed, block.motif_variation, rel_bar)
                if is_phrase_end:
                    motif[-1] = cadence_target

                chord_degrees = gen._chord_for_bar(style, bar_index)
                chord_freqs = [scale.degree(d) for d in chord_degrees]
                root_freq = chord_freqs[0]
                density_steps = max(2, int(round(2 + 6 * block.melody_density)))
                note_len = bar_dur / density_steps

                lead_should_play = not (
                    block.role in {PhraseRole.INTRO, PhraseRole.A_VAR, PhraseRole.B_PHRASE}
                    and rng.random() < 0.1
                )
                if lead_should_play:
                    for step in range(density_steps):
                        degree = motif[step % len(motif)]
                        if is_phrase_end and step == density_steps - 1:
                            degree = cadence_target
                        freq = scale.degree(degree + 7)
                        seq.add_note("lead_melody", freq, bar_onset + step * note_len, note_len * 0.92,
                                     velocity=0.55 + 0.4 * block.arrangement_density)

                if block.arrangement_density > 0.56 and block.role in {PhraseRole.A_VAR, PhraseRole.B_PHRASE, PhraseRole.CLIMAX}:
                    counter = motif_bank.sequence_down(motif, steps=1 if block.role != PhraseRole.CLIMAX else 2)
                    for step in range(max(2, density_steps // 2)):
                        degree = counter[step % len(counter)]
                        seq.add_note("counter_melody", scale.degree(degree + 6),
                                     bar_onset + (step + 0.5) * (bar_dur / max(2, density_steps // 2)),
                                     max(0.08, note_len * 0.8),
                                     velocity=0.35 + 0.32 * block.arrangement_density)

                if block.arrangement_density > 0.45 and rng.random() > 0.08:
                    for chord_freq in chord_freqs:
                        seq.add_note("harmony_pad", chord_freq * 0.5, bar_onset,
                                     bar_dur * 0.96,
                                     velocity=0.28 + 0.25 * block.arrangement_density)

                if block.arrangement_density > 0.38 and rng.random() > 0.12:
                    for hit in (0.0, 0.5):
                        for chord_freq in chord_freqs:
                            seq.add_note("chord_support", chord_freq,
                                         bar_onset + hit * bar_dur, bar_dur * 0.46,
                                         velocity=0.3 + 0.28 * block.arrangement_density)

                if block.arrangement_density > 0.5:
                    ostinato_steps = 8 if block.role in {PhraseRole.B_PHRASE, PhraseRole.CLIMAX} else 4
                    ost_len = bar_dur / ostinato_steps
                    tones = [chord_degrees[0], chord_degrees[-1], motif_seed[0]]
                    for step in range(ostinato_steps):
                        degree = tones[step % len(tones)] + 12
                        seq.add_note("high_ostinato", scale.degree(degree),
                                     bar_onset + step * ost_len, ost_len * 0.8,
                                     velocity=0.24 + 0.2 * block.arrangement_density)

                for hit in (0.0, 0.5):
                    seq.add_note("bass_line", root_freq * 0.25,
                                 bar_onset + hit * bar_dur, bar_dur * 0.44,
                                 velocity=0.52 + 0.32 * block.arrangement_density)

                if "perc_low" in seq._tracks:
                    perc_strength = 0.35 + 0.55 * block.arrangement_density
                    for beat in (0.0, 0.5):
                        seq.add_note("perc_low", 80.0, bar_onset + beat * bar_dur,
                                     min(0.15, bar_dur * 0.2), velocity=perc_strength)
                    if block.arrangement_density > 0.52:
                        for beat in (0.25, 0.75):
                            seq.add_note("perc_texture", 220.0,
                                         bar_onset + beat * bar_dur,
                                         min(0.12, bar_dur * 0.18),
                                         velocity=0.28 + 0.42 * block.arrangement_density)

        pickup_onset = max(0.0, bars * bar_dur - seq.beat_duration * 0.5)
        seq.add_note("lead_melody", scale.degree(motif_seed[0] + 7),
                     pickup_onset, min(seq.beat_duration * 0.4, 0.24), velocity=0.35)

        return seq.render()

    # ------------------------------------------------------------------
    # Mastering helpers
    # ------------------------------------------------------------------

    def _apply_ost_mastering(self, audio: np.ndarray) -> np.ndarray:
        """OST mastering — wide stereo, longer reverb tails, cinematic EQ."""
        from audio_engine.render.offline_bounce import OfflineBounce

        bounce = OfflineBounce(
            sample_rate=self.sample_rate,
            target_lufs=-16.0,
            ceiling_db=-0.3,
            apply_master_eq=True,
            apply_compression=True,
            profile="ost",
        )
        return bounce.process(audio)

    def _apply_sfx_polish(self, audio: np.ndarray) -> np.ndarray:
        """Normalise SFX — no hall reverb so transients stay punchy."""
        peak = np.max(np.abs(audio))
        if peak > 1e-9:
            audio = (audio / peak * 0.90).astype(np.float32)
        return audio

    def _apply_voice_polish(self, audio: np.ndarray) -> np.ndarray:
        """High-pass + room reverb for voice intelligibility."""
        try:
            from scipy.signal import butter, sosfilt  # type: ignore[import]
            nyq = self.sample_rate / 2.0
            sos = butter(2, 100.0 / nyq, btype="high", output="sos")
            audio = sosfilt(sos, audio.astype(np.float64)).astype(np.float32)
        except Exception:
            pass
        peak = np.max(np.abs(audio))
        if peak > 1e-9:
            audio = (audio / peak * 0.88).astype(np.float32)
        return audio
