"""
MusicGenerator – AI-assisted procedural music generation.

Uses a combination of:
  - Markov chain melody generation (trained on interval probabilities derived
    from the target musical style)
  - Rule-based harmonic accompaniment (chord progressions from the scale)
  - Style templates that define orchestration, tempo, and texture

The generated output is a fully-populated :class:`~audio_engine.composer.Sequencer`
ready to be rendered.

Supported styles
----------------
``"battle"``
    Fast, dramatic orchestral – inspired by cinematic RPG combat music.
    Tempo 140 BPM, minor key, full orchestra + percussion.

``"exploration"``
    Moderate-pace, wonder-filled – open world traversal feel.
    Tempo 90 BPM, major key, strings + choir + crystal synth.

``"ambient"``
    Slow, atmospheric – dungeon / menu music.
    Tempo 60 BPM, minor key, pad + choir + reverb.

``"boss"``
    Intense, layered – climactic encounter.
    Tempo 160 BPM, Phrygian, brass + strings + electric guitar.

``"victory"``
    Triumphant fanfare.
    Tempo 120 BPM, major key, brass + piano + strings.

``"menu"``
    Calm, introspective – main menu or loading screen.
    Tempo 80 BPM, major key, piano + strings.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from audio_engine._seed import resolve_base_seed
from audio_engine.composer.scale import Scale, ScaleLibrary
from audio_engine.composer.chord import ChordProgression
from audio_engine.composer.pattern import RhythmPattern
from audio_engine.composer.sequencer import Note, Sequencer
from audio_engine.composer.phrase import MotifBank, PhraseRole, SectionPlanner
from audio_engine.synthesizer.instrument import InstrumentLibrary

__all__ = ["TrackStyle", "MusicGenerator"]

TrackStyle = Literal[
    "battle", "exploration", "ambient", "boss", "victory", "menu",
    # FF7 / FF8 era styles
    "ff7_battle", "ff7_overworld", "ff7_boss", "ff7_sad", "ff7_town",
    "ff8_battle", "ff8_ballad",
    # Shared retro-RPG styles
    "prelude", "world_map", "dungeon", "healing", "tension",
    # Narrative + regional extension presets
    "stealth", "memorial", "mystery", "underscore", "ending",
    "exploration_plains", "exploration_forest", "exploration_coast", "exploration_arid",
    "transition_sting",
    # FF1–FF6 (NES/SNES era) styles
    "ff1_battle", "ff1_overworld", "ff4_battle", "ff4_theme",
    "ff6_battle", "ff6_opera", "ff6_sad",
    # FF9 / FF10 / PS2 era styles
    "ff9_battle", "ff9_overworld", "ff10_calm", "ff10_battle",
    "ff10_zanarkand",
    # FF12 / FF13 / HD era styles
    "ff12_battle", "ff13_battle", "ff13_theme",
    # FF14 / FF15 / FF16 modern era styles
    "ff14_battle", "ff14_overworld", "ff15_road", "ff15_radio",
    "ff16_battle", "ff16_theme",
    # Generic full-piece request styles (non-FF)
    "orchestral_epic", "choral_fantasy", "celtic_adventure",
    "jazz_lounge", "electronic_ambient", "rock_battle",
    "piano_ballad", "folk_tavern", "horror_ambient", "triumph_fanfare",
    # Multi-genre styles — various genres with Final Fantasy epic quality
    "jazz_epic", "jazz_ballad", "jazz_swing",
    "blues_epic", "blues_ballad",
    "pop_epic", "pop_ballad_epic",
    "rock_epic", "rock_ballad_epic",
    "electronic_epic", "synthwave_epic",
    "metal_epic",
    "world_epic", "latin_epic",
    "acoustic_epic", "country_epic",
    "rnb_ballad",
    "ambient_nature", "ambient_space",
    "cinematic_orchestral",
    # Expanded genre and arrangement coverage
    "hybrid_trailer", "neo_noir", "festival_folk", "sci_fi_pulse", "waltz_orchestral",
    # Modern synth/EDM expansion
    "synth_house_modern", "techno_drive", "trance_uplift", "drum_and_bass_neuro", "future_bass_modern",
]


# ---------------------------------------------------------------------------
# Style definitions
# ---------------------------------------------------------------------------

@dataclass
class _StyleDef:
    bpm: float
    scale_name: str
    root: str
    octave: int
    progression_name: str
    instruments: list[str]           # instrument names for melody layer
    accompaniment: list[str]         # instruments for chord backing
    bass_instrument: str
    percussion_instrument: str | None
    melody_pattern: str              # name of a RhythmPattern classmethod
    chord_pattern: str
    bars: int = 8                    # number of bars to generate
    ostinato_instrument: str = "crystal_synth"  # instrument for high-register ostinato texture


@dataclass(frozen=True)
class _TheoryProfile:
    cadence: list[int]
    pre_cadence: list[int]
    closure: list[int]


@dataclass(frozen=True)
class _StyleIntent:
    family: str
    required_any: tuple[str, ...]
    preferred_bass: tuple[str, ...] = ()
    require_percussion: bool = False
    disallow_percussion: bool = False


_STYLE_DEFS: dict[str, _StyleDef] = {
    "battle": _StyleDef(
        bpm=140,
        scale_name="harmonic_minor",
        root="A",
        octave=4,
        progression_name="i_iv_v_i",
        instruments=["brass", "strings"],
        accompaniment=["strings", "choir"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="half_notes",
    ),
    "exploration": _StyleDef(
        bpm=90,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["flute", "oboe"],
        accompaniment=["strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        ostinato_instrument="celesta",
    ),
    "ambient": _StyleDef(
        bpm=60,
        scale_name="natural_minor",
        root="E",
        octave=3,
        progression_name="i_VI_III_VII",
        instruments=["synth_pad", "choir"],
        accompaniment=["synth_pad"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        ostinato_instrument="celesta",
    ),
    "boss": _StyleDef(
        bpm=160,
        scale_name="phrygian",
        root="D",
        octave=4,
        progression_name="i_bII_i_bVII",
        instruments=["brass", "electric_guitar"],
        accompaniment=["strings", "brass"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
    ),
    "victory": _StyleDef(
        bpm=120,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["brass", "piano"],
        accompaniment=["strings", "choir"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=4,
    ),
    "menu": _StyleDef(
        bpm=80,
        scale_name="major",
        root="F",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["piano", "crystal_synth"],
        accompaniment=["strings", "synth_pad"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
    ),

    # -----------------------------------------------------------------------
    # FF7 / FF8 Nobuo Uematsu inspired presets
    # Instrument names refer to the FF7-era timbres in InstrumentLibrary.
    # -----------------------------------------------------------------------

    "ff7_battle": _StyleDef(
        # "Let the Battles Begin!" / "Those Who Fight" energy.
        # Syncopated, urgent, in A harmonic minor at 132 BPM.
        bpm=132,
        scale_name="harmonic_minor",
        root="A",
        octave=4,
        progression_name="i_bVII_bVI_V",
        instruments=["ff7_lead", "brass"],
        accompaniment=["ff7_strings", "brass"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    "ff7_overworld": _StyleDef(
        # "Main Theme of FFVII" sweeping overworld feel.
        # Flowing major melody, strings-led, 84 BPM.
        bpm=84,
        scale_name="major",
        root="E",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["ff7_lead", "oboe"],
        accompaniment=["legato_strings_ps2", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ff7_boss": _StyleDef(
        # "One-Winged Angel" intensity — Phrygian dominant, E, 148 BPM.
        # Full orchestra + choir + electric guitar.
        bpm=148,
        scale_name="phrygian",
        root="E",
        octave=3,
        progression_name="i_bII_i_bVII",
        instruments=["brass", "ff7_electric_guitar"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "ff7_sad": _StyleDef(
        # "Aerith's Theme" / "Who Are You?" emotional weight.
        # Slow, in E major, piano + strings + choir, no percussion.
        bpm=65,
        scale_name="major",
        root="E",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["soft_epiano_ps2", "ff7_strings"],
        accompaniment=["legato_strings_ps2", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ff7_town": _StyleDef(
        # "Ahead on Our Way" / "Under the Rotting Pizza" town warmth.
        # Light, major, piano + flute + strings, 90 BPM.
        bpm=90,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["piano", "flute"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ff8_battle": _StyleDef(
        # "The Man with the Machine Gun" aggressive rock-orchestral hybrid.
        # Dorian B, 144 BPM, electric guitar prominent.
        bpm=144,
        scale_name="dorian",
        root="B",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["ff8_electric_guitar", "brass"],
        accompaniment=["ff7_strings", "brass"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    # -----------------------------------------------------------------------
    # Shared retro-RPG styles
    # -----------------------------------------------------------------------

    "prelude": _StyleDef(
        # Nobuo Uematsu's iconic arpeggio prelude — sparse, crystalline.
        # Uses harpsichord + crystal_synth; slow BPM but eighth-note arpeggios
        # create a flowing 16th-note feel at the actual tempo.
        bpm=72,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["harpsichord", "crystal_synth"],
        accompaniment=["crystal_synth"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    "world_map": _StyleDef(
        # Sweeping overworld map — broad and majestic.
        # Strings + brass + choir, major key, 84 BPM.
        bpm=84,
        scale_name="major",
        root="G",
        octave=3,
        progression_name="I_IV_V_I",
        instruments=["ff7_strings", "brass"],
        accompaniment=["choir", "ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "dungeon": _StyleDef(
        # Dark dungeon / cave — tense and atmospheric.
        # Natural minor, slow, synth pads + choir, no melody beat.
        bpm=70,
        scale_name="natural_minor",
        root="D",
        octave=3,
        progression_name="i_iv_bVII_bIII",
        instruments=["synth_pad", "choir"],
        accompaniment=["synth_pad"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        bars=8,
    ),

    "healing": _StyleDef(
        # Inn / rest / recovery theme — warm and reassuring.
        # Major, gentle piano + flute + strings, 90 BPM.
        bpm=90,
        scale_name="major",
        root="F",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano", "flute"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "tension": _StyleDef(
        # Pre-battle tension / suspense — restless and unresolved.
        # Harmonic minor, mid-tempo, strings + brass stabs.
        bpm=100,
        scale_name="harmonic_minor",
        root="A",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["ff7_strings", "brass"],
        accompaniment=["ff7_strings", "synth_pad"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    "stealth": _StyleDef(
        # Low-visibility stealth movement, sparse and pulse-driven.
        bpm=86,
        scale_name="natural_minor",
        root="D",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["synth_pad", "ff7_strings"],
        accompaniment=["synth_pad"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        bars=8,
    ),

    "memorial": _StyleDef(
        # Reflective memorial cue, piano-forward with restrained strings.
        bpm=62,
        scale_name="major",
        root="E",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano", "flute"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    "mystery": _StyleDef(
        # Puzzle / unknown-space atmosphere with crystalline uncertainty.
        bpm=74,
        scale_name="natural_minor",
        root="B",
        octave=3,
        progression_name="i_VI_III_VII",
        instruments=["celesta", "synth_pad"],
        accompaniment=["choir", "synth_pad"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        bars=8,
    ),

    "underscore": _StyleDef(
        # Cinematic dialogue/cutscene underscore with motion but low foreground density.
        bpm=80,
        scale_name="major",
        root="G",
        octave=3,
        progression_name="I_vi_IV_V",
        instruments=["strings", "oboe"],
        accompaniment=["synth_pad", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ending": _StyleDef(
        # Credits/ending suite with broader, hopeful cadence.
        bpm=72,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["piano", "ff7_strings"],
        accompaniment=["choir", "strings"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=16,
    ),

    "exploration_plains": _StyleDef(
        # Wide-open plains travel identity.
        bpm=92,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["flute", "strings"],
        accompaniment=["choir", "strings"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "exploration_forest": _StyleDef(
        # Forest traversal with woodwind-led movement and shimmer.
        bpm=88,
        scale_name="major",
        root="D",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["oboe", "flute"],
        accompaniment=["strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "exploration_coast": _StyleDef(
        # Coastline travel identity with airy pad and broad harmonic space.
        bpm=86,
        scale_name="major",
        root="A",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["flute", "celesta"],
        accompaniment=["synth_pad", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "exploration_arid": _StyleDef(
        # Dry frontier / arid zone with sparse rhythmic drive.
        bpm=84,
        scale_name="dorian",
        root="E",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["oboe", "strings"],
        accompaniment=["synth_pad", "strings"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="half_notes",
        chord_pattern="syncopated",
        bars=8,
    ),

    "transition_sting": _StyleDef(
        # Short dramatic transition cue for reveals/battle entry.
        bpm=126,
        scale_name="harmonic_minor",
        root="A",
        octave=4,
        progression_name="i_iv_v_i",
        instruments=["brass", "choir"],
        accompaniment=["strings", "brass"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=2,
    ),

    "ff8_ballad": _StyleDef(
        # "Eyes on Me" — slow romantic ballad, the signature FF8 vocal piece.
        # F major, 74 BPM, piano-led with strings + choir.  Designed for
        # use with VocalMelodySynth overlay to create a full vocal arrangement.
        bpm=74,
        scale_name="major",
        root="F",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["soft_epiano_ps2", "flute"],
        accompaniment=["nylon_guitar_ps2", "legato_strings_ps2"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    # -----------------------------------------------------------------------
    # FF1 – FF6  (NES / SNES era — square waves, limited polyphony)
    # -----------------------------------------------------------------------

    "ff1_battle": _StyleDef(
        # Original Final Fantasy battle — NES-era square wave energy.
        # Phrygian, 150 BPM, very simple instrumentation (2 voices).
        bpm=150,
        scale_name="phrygian",
        root="D",
        octave=4,
        progression_name="i_bII_i_bVII",
        instruments=["crystal_synth", "ff7_lead"],
        accompaniment=["synth_pad"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=4,
    ),

    "ff1_overworld": _StyleDef(
        # FF1 overworld — bright, optimistic, NES-era feel.
        # A major, 110 BPM, repetitive 4-bar loop.
        bpm=110,
        scale_name="major",
        root="A",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["crystal_synth", "ff7_lead"],
        accompaniment=["synth_pad"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=4,
    ),

    "ff4_battle": _StyleDef(
        # FF4 "Fight 1" — SNES era, richer polyphony, D minor.
        # The template for everything that followed — urgent, punchy.
        bpm=136,
        scale_name="natural_minor",
        root="D",
        octave=4,
        progression_name="i_bVII_bVI_V",
        instruments=["brass", "crystal_synth"],
        accompaniment=["ff7_strings", "synth_pad"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    "ff4_theme": _StyleDef(
        # FF4 main theme — heroic, major, SNES orchestra.
        # E major, 96 BPM, sweeping strings + brass.
        bpm=96,
        scale_name="major",
        root="E",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["brass", "ff7_strings"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ff6_battle": _StyleDef(
        # FF6 "The Decisive Battle" — dramatic, complex, dissonant.
        # B harmonic minor, 148 BPM, brass-heavy with strings.
        bpm=148,
        scale_name="harmonic_minor",
        root="B",
        octave=3,
        progression_name="i_bII_i_bVII",
        instruments=["brass", "ff7_strings"],
        accompaniment=["brass", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "ff6_opera": _StyleDef(
        # FF6 "Maria and Draco" opera scene — elegant, emotional, major.
        # C major, 80 BPM, strings + piano + choir for the aria feel.
        bpm=80,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano", "flute"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ff6_sad": _StyleDef(
        # FF6 "Aria de Mezzo Carattere" / "Terra's Theme" emotional weight.
        # Minor pentatonic, 70 BPM, piano + strings.
        bpm=70,
        scale_name="natural_minor",
        root="D",
        octave=4,
        progression_name="i_bVI_bVII_i",
        instruments=["piano", "ff7_strings"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    # -----------------------------------------------------------------------
    # FF9 / FF10  (PS1 / early PS2 — transitional era, rich orchestration)
    # -----------------------------------------------------------------------

    "ff9_battle": _StyleDef(
        # FF9 "Battle 1" — energetic, E minor, full SNES-homage orchestration.
        # 140 BPM, similar energy to FF6 but with more instrument layers.
        bpm=140,
        scale_name="harmonic_minor",
        root="E",
        octave=4,
        progression_name="i_bVII_bVI_V",
        instruments=["brass", "ff7_strings"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    "ff9_overworld": _StyleDef(
        # FF9 "Crossing Those Hills" — nostalgic, warm, G major.
        # 88 BPM, flute + strings + choir, feels like classic RPG travel.
        bpm=88,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["flute", "piano"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ff10_calm": _StyleDef(
        # FF10 "To Zanarkand" / "Wandering Flame" quiet moments.
        # E major, 76 BPM, solo piano with very soft strings underneath.
        bpm=76,
        scale_name="major",
        root="E",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["soft_epiano_ps2", "piano"],
        accompaniment=["legato_strings_ps2"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    "ff10_battle": _StyleDef(
        # FF10 "Fight with Seymour" / "Otherworld" aggressive rock/orchestral.
        # F# harmonic minor, 144 BPM, heavy electric guitar + brass.
        bpm=144,
        scale_name="harmonic_minor",
        root="F",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["ff8_electric_guitar", "brass"],
        accompaniment=["legato_strings_ps2", "brass"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    "ff10_zanarkand": _StyleDef(
        # "To Zanarkand" — the iconic melancholy piano intro.
        # A major, 70 BPM, solo piano, absolutely minimal.
        bpm=70,
        scale_name="major",
        root="A",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["soft_epiano_ps2"],
        accompaniment=["piano"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    # -----------------------------------------------------------------------
    # FF12 / FF13  (PS2 / PS3 — cinematic, orchestral with electronic elements)
    # -----------------------------------------------------------------------

    "ff12_battle": _StyleDef(
        # FF12 "Boss Battle" — Hitoshi Sakimoto style: dissonant brass,
        # irregular metre, D minor, 120 BPM.
        bpm=120,
        scale_name="natural_minor",
        root="D",
        octave=3,
        progression_name="i_iv_bVII_bIII",
        instruments=["brass", "ff7_strings"],
        accompaniment=["brass", "synth_pad"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    "ff13_battle": _StyleDef(
        # FF13 "Blinded by Light" — Masashi Hamauzu style: synth + orchestra,
        # major key unusually for battle, 140 BPM, modern hybrid.
        bpm=140,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["brass", "ff8_electric_guitar"],
        accompaniment=["ff7_strings", "synth_pad"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "ff13_theme": _StyleDef(
        # FF13 "Promised Eternity" — serene, Eb major, piano + strings + choir.
        # 80 BPM, emotional and flowing.
        bpm=80,
        scale_name="major",
        root="E",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano", "flute"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    # -----------------------------------------------------------------------
    # FF14 / FF15 / FF16  (modern era — full live orchestra, choral, rock)
    # -----------------------------------------------------------------------

    "ff14_battle": _StyleDef(
        # FF14 "Torn from the Heavens" / "Answers" energy — Soken style.
        # Heavy, aggressive, G minor, 150 BPM, electric guitar + full orchestra.
        bpm=150,
        scale_name="harmonic_minor",
        root="G",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["ff8_electric_guitar", "brass"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "ff14_overworld": _StyleDef(
        # FF14 overworld/zone music — vast open-world adventuring feel.
        # C major, 90 BPM, full orchestral sweep with choir.
        bpm=90,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["ff7_strings", "brass"],
        accompaniment=["choir", "ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "ff15_road": _StyleDef(
        # FF15 road trip / daytime travel — rock + orchestral, carefree.
        # E major, 120 BPM, electric guitar lead over strings.
        bpm=120,
        scale_name="major",
        root="E",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["ff8_electric_guitar", "piano"],
        accompaniment=["ff7_strings", "brass"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "ff15_radio": _StyleDef(
        # FF15 Regalia radio — plays covers of classic FF tracks.
        # Mixed bag; here represented as a bright major pop-ish version.
        # G major, 100 BPM, piano + electric guitar.
        bpm=100,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["piano", "ff8_electric_guitar"],
        accompaniment=["ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "ff16_battle": _StyleDef(
        # FF16 "Titan Lost" / "Away" — Soken's most intense work.
        # B minor, 156 BPM, brutal orchestra + choir + electric guitar.
        bpm=156,
        scale_name="harmonic_minor",
        root="B",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["brass", "ff8_electric_guitar"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        bars=8,
    ),

    "ff16_theme": _StyleDef(
        # FF16 main theme — epic, choral, dark fantasy.
        # D minor, 88 BPM, full choir-led orchestral theme.
        bpm=88,
        scale_name="harmonic_minor",
        root="D",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["brass", "ff7_strings"],
        accompaniment=["choir", "brass"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    # -----------------------------------------------------------------------
    # Generic full-piece request styles — non-FF, broad use cases
    # -----------------------------------------------------------------------

    "orchestral_epic": _StyleDef(
        # Full cinematic orchestral epic — Hans Zimmer / John Williams territory.
        # D minor, 104 BPM, full orchestra.
        bpm=104,
        scale_name="harmonic_minor",
        root="D",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["french_horn", "brass"],
        accompaniment=["cello", "ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument="timpani",
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        ostinato_instrument="harp",
        bars=8,
    ),

    "choral_fantasy": _StyleDef(
        # Full choir + orchestra fantasy — sacred-fantasy blend.
        # A minor, 76 BPM, choir-led with strings and piano.
        bpm=76,
        scale_name="natural_minor",
        root="A",
        octave=3,
        progression_name="i_VI_III_VII",
        instruments=["choir", "ff7_strings"],
        accompaniment=["choir", "piano"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        ostinato_instrument="harp",
        bars=8,
    ),

    "celtic_adventure": _StyleDef(
        # Celtic / folk-adventure style — flute lead, lively.
        # D major (Dorian feel), 120 BPM.
        bpm=120,
        scale_name="dorian",
        root="D",
        octave=4,
        progression_name="i_bVII_bVI_bVII",
        instruments=["flute", "clarinet"],
        accompaniment=["ff7_strings"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="four_on_the_floor",
        ostinato_instrument="marimba",
        bars=8,
    ),

    "jazz_lounge": _StyleDef(
        # Smooth jazz lounge — late-night atmosphere.
        # C major, 88 BPM, piano + strings, jazz chord extensions.
        bpm=88,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="ii_V_I_VI",
        instruments=["piano"],
        accompaniment=["ff7_strings", "synth_pad"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        bars=8,
    ),

    "electronic_ambient": _StyleDef(
        # Electronic ambient / chill — synth pads, no melody.
        # E minor, 70 BPM, pure atmosphere.
        bpm=70,
        scale_name="natural_minor",
        root="E",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["synth_pad", "crystal_synth"],
        accompaniment=["synth_pad"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        bars=8,
    ),

    "rock_battle": _StyleDef(
        # Modern rock battle theme — electric guitar-driven, aggressive.
        # A minor, 144 BPM, power chords + driving drums.
        bpm=144,
        scale_name="natural_minor",
        root="A",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["ff8_electric_guitar", "brass"],
        accompaniment=["ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "piano_ballad": _StyleDef(
        # Solo piano ballad — intimate, emotional.
        # F major, 66 BPM.
        bpm=66,
        scale_name="major",
        root="F",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano"],
        accompaniment=["piano"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    "folk_tavern": _StyleDef(
        # Tavern / folk shanty — lively, happy drinking-song energy.
        # G major, 130 BPM, piano + flute.
        bpm=130,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["piano", "flute"],
        accompaniment=["ff7_strings"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "horror_ambient": _StyleDef(
        # Horror / dark ambient — unsettling, tense, dissonant.
        # C# minor, 55 BPM, pads + choir stabs.
        bpm=55,
        scale_name="phrygian",
        root="C",
        octave=3,
        progression_name="i_bII_i_bVII",
        instruments=["synth_pad", "choir"],
        accompaniment=["synth_pad"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        ostinato_instrument="celesta",
        bars=8,
    ),

    "triumph_fanfare": _StyleDef(
        # Victory / triumph fanfare — short, punchy, celebratory.
        # Bb major, 120 BPM, full brass + strings.
        bpm=120,
        scale_name="major",
        root="B",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["brass", "ff7_strings"],
        accompaniment=["brass", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="four_on_the_floor",
        chord_pattern="half_notes",
        bars=4,
    ),

    # -----------------------------------------------------------------------
    # Multi-genre styles — various genres with Final Fantasy epic quality
    # Each style blends its source genre with the orchestral grandeur,
    # emotional depth, and melodic expressiveness of the FF series.
    # -----------------------------------------------------------------------

    "jazz_epic": _StyleDef(
        # Big-band jazz fused with orchestral grandeur — think Uematsu meets Ellington.
        # G major, 104 BPM, piano + brass + strings + choir.
        bpm=104,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="ii_V_I_VI",
        instruments=["piano", "brass"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        bars=8,
    ),

    "jazz_ballad": _StyleDef(
        # Slow jazz ballad with emotional depth — Tifa's Theme reimagined as late-night jazz.
        # E minor, 72 BPM, solo piano leading into strings.
        bpm=72,
        scale_name="natural_minor",
        root="E",
        octave=4,
        progression_name="ii_V_I_VI",
        instruments=["piano"],
        accompaniment=["strings", "synth_pad"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    "jazz_swing": _StyleDef(
        # Upbeat swing jazz with epic orchestral weight — playful yet grand.
        # C major, 126 BPM, piano + brass, lively swing feel.
        bpm=126,
        scale_name="major",
        root="C",
        octave=4,
        progression_name="ii_V_I_VI",
        instruments=["piano", "brass"],
        accompaniment=["ff7_strings"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="syncopated",
        bars=8,
    ),

    "blues_epic": _StyleDef(
        # Blues with cinematic orchestral weight — gritty guitar over sweeping strings and brass.
        # A blues scale, 88 BPM, electric guitar + piano leading strings and brass.
        bpm=88,
        scale_name="blues",
        root="A",
        octave=3,
        progression_name="I_IV_V_I",
        instruments=["electric_guitar", "piano"],
        accompaniment=["ff7_strings", "brass"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        bars=8,
    ),

    "blues_ballad": _StyleDef(
        # Slow emotional blues ballad — intimate piano over warm strings.
        # A blues scale, 60 BPM, soulful and melancholic.
        bpm=60,
        scale_name="blues",
        root="A",
        octave=3,
        progression_name="I_IV_V_I",
        instruments=["piano", "electric_guitar"],
        accompaniment=["strings"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    "pop_epic": _StyleDef(
        # Modern pop with FF orchestral grandeur — anthemic and emotionally sweeping.
        # D major, 100 BPM, piano + synth pad over full orchestra.
        bpm=100,
        scale_name="major",
        root="D",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["piano", "synth_pad"],
        accompaniment=["ff7_strings", "choir", "brass"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "pop_ballad_epic": _StyleDef(
        # Epic pop ballad — the energy of Stand By Me and Eyes on Me.
        # A major, 80 BPM, solo piano building to full orchestral swell.
        bpm=80,
        scale_name="major",
        root="A",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="ambient",
        bars=8,
    ),

    "rock_epic": _StyleDef(
        # Full orchestral rock — electric guitar fury with choral grandeur, One-Winged Angel energy.
        # E harmonic minor, 132 BPM, electric guitar + brass, choir + strings.
        bpm=132,
        scale_name="harmonic_minor",
        root="E",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["ff8_electric_guitar", "brass"],
        accompaniment=["choir", "ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "rock_ballad_epic": _StyleDef(
        # Emotional rock ballad with orchestral strings — Noctis's Theme meets rock.
        # D natural minor, 76 BPM, guitar + piano over sweeping strings.
        bpm=76,
        scale_name="natural_minor",
        root="D",
        octave=4,
        progression_name="i_bVI_bVII_i",
        instruments=["ff8_electric_guitar", "piano"],
        accompaniment=["ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "electronic_epic": _StyleDef(
        # Electronic / EDM fused with orchestral depth — synth leads over strings and choir.
        # F natural minor, 128 BPM, driving electronic energy with FF emotion.
        bpm=128,
        scale_name="natural_minor",
        root="F",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["synth_lead_bright", "ff7_lead"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="synth_bass_punch",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="four_on_the_floor",
        ostinato_instrument="crystal_synth",
        bars=8,
    ),

    "synthwave_epic": _StyleDef(
        # Retrowave / synthwave with nostalgic FF energy — crystal synths over warm strings.
        # A natural minor, 110 BPM, shimmering retro atmosphere.
        bpm=110,
        scale_name="natural_minor",
        root="A",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["synth_lead_bright", "crystal_synth"],
        accompaniment=["synth_pad", "ff7_strings"],
        bass_instrument="synth_bass_punch",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        ostinato_instrument="crystal_synth",
        bars=8,
    ),

    "metal_epic": _StyleDef(
        # Heavy metal with choral orchestral backing — the rage and majesty of FF16.
        # E Phrygian, 160 BPM, brutal guitar fury underpinned by choir and brass grandeur.
        bpm=160,
        scale_name="phrygian",
        root="E",
        octave=3,
        progression_name="i_bII_i_bVII",
        instruments=["ff8_electric_guitar", "brass"],
        accompaniment=["choir", "ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "world_epic": _StyleDef(
        # World music with epic orchestral treatment — global flavours with FF grandeur.
        # D Dorian, 96 BPM, flute lead over choir + strings + brass.
        bpm=96,
        scale_name="dorian",
        root="D",
        octave=3,
        progression_name="i_bVII_bVI_bVII",
        instruments=["flute", "strings"],
        accompaniment=["choir", "ff7_strings", "brass"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        bars=8,
    ),

    "latin_epic": _StyleDef(
        # Latin rhythms with FF cinematic grandeur — piano + brass over flowing strings.
        # A Dorian, 116 BPM, syncopated Latin energy with orchestral sweep.
        bpm=116,
        scale_name="dorian",
        root="A",
        octave=3,
        progression_name="i_bVII_bVI_bVII",
        instruments=["piano", "brass"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="four_on_the_floor",
        bars=8,
    ),

    "acoustic_epic": _StyleDef(
        # Acoustic / folk with emotional FF depth — intimate piano + flute over warm strings.
        # G major, 84 BPM, organic textures with cinematic emotional arc.
        bpm=84,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano", "flute"],
        accompaniment=["strings"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),

    "country_epic": _StyleDef(
        # Country with cinematic orchestral backing — heartland simplicity meets FF scale.
        # G pentatonic major, 100 BPM, piano + guitar over lush strings.
        bpm=100,
        scale_name="pentatonic_major",
        root="G",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["piano", "electric_guitar"],
        accompaniment=["ff7_strings"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        bars=8,
    ),

    "rnb_ballad": _StyleDef(
        # R&B / soul ballad — smooth piano over strings and choir, soulful and epic.
        # F natural minor, 70 BPM, lush and emotionally rich.
        bpm=70,
        scale_name="natural_minor",
        root="F",
        octave=4,
        progression_name="i_bVI_bVII_i",
        instruments=["piano", "synth_pad"],
        accompaniment=["ff7_strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="syncopated",
        chord_pattern="ambient",
        bars=8,
    ),

    "ambient_nature": _StyleDef(
        # Nature-inspired ambient with FF crystalline texture — like the Prelude reimagined outdoors.
        # F major, 60 BPM, flute + crystal synth over strings and pad.
        bpm=60,
        scale_name="major",
        root="F",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["flute", "crystal_synth"],
        accompaniment=["strings", "synth_pad"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        bars=8,
    ),

    "ambient_space": _StyleDef(
        # Space ambient — vast, crystalline, timeless.  Crystal synths + choir pads.
        # D major, 55 BPM, shimmering and ethereal like looking at stars.
        bpm=55,
        scale_name="major",
        root="D",
        octave=3,
        progression_name="I_vi_IV_V",
        instruments=["crystal_synth", "synth_pad"],
        accompaniment=["choir", "synth_pad"],
        bass_instrument="synth_pad",
        percussion_instrument=None,
        melody_pattern="ambient",
        chord_pattern="ambient",
        bars=8,
    ),

    "cinematic_orchestral": _StyleDef(
        # Pure cinematic orchestral — Hans Zimmer grandeur meets Uematsu emotional depth.
        # C harmonic minor, 96 BPM, full orchestra: brass + choir + strings + percussion.
        bpm=96,
        scale_name="harmonic_minor",
        root="C",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["brass", "ff7_strings"],
        accompaniment=["choir", "strings", "brass"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        bars=8,
    ),
    "hybrid_trailer": _StyleDef(
        bpm=128,
        scale_name="harmonic_minor",
        root="D",
        octave=3,
        progression_name="i_bVII_bVI_V",
        instruments=["french_horn", "trumpet"],
        accompaniment=["cello", "choir"],
        bass_instrument="ff7_bass",
        percussion_instrument="timpani",
        melody_pattern="battle",
        chord_pattern="four_on_the_floor",
        ostinato_instrument="marimba",
        bars=8,
    ),
    "neo_noir": _StyleDef(
        bpm=84,
        scale_name="dorian",
        root="C",
        octave=3,
        progression_name="ii_V_I_VI",
        instruments=["clarinet", "piano"],
        accompaniment=["strings", "synth_pad"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        ostinato_instrument="marimba",
        bars=8,
    ),
    "festival_folk": _StyleDef(
        bpm=118,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_IV_V_I",
        instruments=["acoustic_guitar", "flute"],
        accompaniment=["strings", "piano"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="syncopated",
        ostinato_instrument="marimba",
        bars=8,
    ),
    "sci_fi_pulse": _StyleDef(
        bpm=124,
        scale_name="natural_minor",
        root="E",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["synth_lead_bright", "crystal_synth"],
        accompaniment=["synth_pad", "ff7_strings"],
        bass_instrument="synth_pad",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="four_on_the_floor",
        ostinato_instrument="celesta",
        bars=8,
    ),
    "synth_house_modern": _StyleDef(
        bpm=124,
        scale_name="major",
        root="A",
        octave=4,
        progression_name="I_V_vi_IV",
        instruments=["supersaw_lead", "synth_pluck_glass"],
        accompaniment=["synth_pad", "ff7_strings"],
        bass_instrument="synth_bass_punch",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="four_on_the_floor",
        ostinato_instrument="synth_pluck_glass",
        bars=8,
    ),
    "techno_drive": _StyleDef(
        bpm=132,
        scale_name="natural_minor",
        root="E",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["synth_lead_bright", "synth_pluck_glass"],
        accompaniment=["synth_pad", "crystal_synth"],
        bass_instrument="synth_bass_punch",
        percussion_instrument="percussion",
        melody_pattern="four_on_the_floor",
        chord_pattern="four_on_the_floor",
        ostinato_instrument="synth_pluck_glass",
        bars=8,
    ),
    "trance_uplift": _StyleDef(
        bpm=136,
        scale_name="dorian",
        root="F",
        octave=4,
        progression_name="i_bVI_bVII_i",
        instruments=["supersaw_lead", "synth_lead_bright"],
        accompaniment=["synth_pad", "choir"],
        bass_instrument="synth_bass_punch",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="four_on_the_floor",
        ostinato_instrument="synth_pluck_glass",
        bars=8,
    ),
    "drum_and_bass_neuro": _StyleDef(
        bpm=172,
        scale_name="natural_minor",
        root="D",
        octave=3,
        progression_name="i_bVI_bVII_i",
        instruments=["synth_lead_bright", "synth_pluck_glass"],
        accompaniment=["synth_pad", "ff7_strings"],
        bass_instrument="synth_bass_punch",
        percussion_instrument="percussion",
        melody_pattern="battle",
        chord_pattern="syncopated",
        ostinato_instrument="synth_pluck_glass",
        bars=8,
    ),
    "future_bass_modern": _StyleDef(
        bpm=150,
        scale_name="major",
        root="G",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["supersaw_lead", "soft_epiano_ps2"],
        accompaniment=["synth_pad", "choir"],
        bass_instrument="synth_bass_punch",
        percussion_instrument="percussion",
        melody_pattern="syncopated",
        chord_pattern="half_notes",
        ostinato_instrument="synth_pluck_glass",
        bars=8,
    ),
    "waltz_orchestral": _StyleDef(
        bpm=92,
        scale_name="major",
        root="F",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["violin_solo", "oboe"],
        accompaniment=["cello", "harp"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="half_notes",
        chord_pattern="half_notes",
        ostinato_instrument="harp",
        bars=8,
    ),
}

_PROGRESSION_DEGREES: dict[str, list[list[int]]] = {
    "I_IV_V_I": [[1, 3, 5], [4, 6, 1], [5, 7, 2], [1, 3, 5]],
    "I_V_vi_IV": [[1, 3, 5], [5, 7, 2], [6, 1, 3], [4, 6, 1]],
    "ii_V_I": [[2, 4, 6], [5, 7, 2], [1, 3, 5]],
    "ii_V_I_VI": [[2, 4, 6], [5, 7, 2], [1, 3, 5], [6, 1, 3]],
    "i_bVII_bVI_bVII": [[1, 3, 5], [7, 2, 4], [6, 1, 3], [7, 2, 4]],
    "i_iv_v_i": [[1, 3, 5], [4, 6, 1], [5, 7, 2], [1, 3, 5]],
    "i_VI_III_VII": [[1, 3, 5], [6, 1, 3], [3, 5, 7], [7, 2, 4]],
    "i_bII_i_bVII": [[1, 3, 5], [2, 4, 6], [1, 3, 5], [7, 2, 4]],
    "i_v_bVI_bVII": [[1, 3, 5], [5, 7, 2], [6, 1, 3], [7, 2, 4]],
    "i_bVII_bVI_V": [[1, 3, 5], [7, 2, 4], [6, 1, 3], [5, 7, 2]],
    "I_vi_IV_V": [[1, 3, 5], [6, 1, 3], [4, 6, 1], [5, 7, 2]],
    "i_iv_bVII_bIII": [[1, 3, 5], [4, 6, 1], [7, 2, 4], [3, 5, 7]],
    "i_bVI_bVII_i": [[1, 3, 5], [6, 1, 3], [7, 2, 4], [1, 3, 5]],
}

_DEFAULT_THEORY_PROFILE = _TheoryProfile(cadence=[5, 7, 2], pre_cadence=[4, 6, 1], closure=[1, 3, 5])
_THEORY_PROFILES: dict[str, _TheoryProfile] = {
    "major": _TheoryProfile(cadence=[5, 7, 2], pre_cadence=[4, 6, 1], closure=[1, 3, 5]),
    "pentatonic_major": _TheoryProfile(cadence=[5, 7, 2], pre_cadence=[4, 6, 1], closure=[1, 3, 5]),
    "natural_minor": _TheoryProfile(cadence=[7, 2, 4], pre_cadence=[6, 1, 3], closure=[1, 3, 5]),
    "harmonic_minor": _TheoryProfile(cadence=[5, 7, 2], pre_cadence=[4, 6, 1], closure=[1, 3, 5]),
    "phrygian": _TheoryProfile(cadence=[2, 4, 6], pre_cadence=[7, 2, 4], closure=[1, 3, 5]),
    "dorian": _TheoryProfile(cadence=[5, 7, 2], pre_cadence=[4, 6, 1], closure=[1, 3, 5]),
    "blues": _TheoryProfile(cadence=[5, 7, 2], pre_cadence=[4, 6, 1], closure=[1, 3, 5]),
}

_STYLE_INTENT_OVERRIDES: dict[str, _StyleIntent] = {
    "hybrid_trailer": _StyleIntent(
        family="hybrid_trailer",
        required_any=("french_horn", "trumpet", "cello", "timpani"),
        preferred_bass=("ff7_bass", "bass"),
        require_percussion=True,
    ),
    "neo_noir": _StyleIntent(
        family="neo_noir",
        required_any=("clarinet", "piano", "strings"),
        preferred_bass=("bass",),
        disallow_percussion=True,
    ),
    "festival_folk": _StyleIntent(
        family="festival_folk",
        required_any=("acoustic_guitar", "flute", "piano"),
        preferred_bass=("bass",),
        require_percussion=True,
    ),
    "sci_fi_pulse": _StyleIntent(
        family="sci_fi_pulse",
        required_any=("synth_lead_bright", "synth_pad", "crystal_synth"),
        preferred_bass=("synth_pad", "bass"),
        require_percussion=True,
    ),
    "waltz_orchestral": _StyleIntent(
        family="waltz_orchestral",
        required_any=("violin_solo", "oboe", "cello", "harp"),
        preferred_bass=("bass", "cello"),
        disallow_percussion=True,
    ),
}


# ---------------------------------------------------------------------------
# Markov chain melody generator
# ---------------------------------------------------------------------------

# Transition probabilities for melodic intervals (in scale degrees).
# The key is the last interval taken; value is weighted choices for next.
_MARKOV_TRANSITIONS: dict[int, list[tuple[int, float]]] = {
    0:  [(1, 0.35), (2, 0.25), (-1, 0.2), (3, 0.1), (-2, 0.1)],
    1:  [(1, 0.3), (2, 0.2), (-1, 0.25), (0, 0.15), (3, 0.1)],
    2:  [(1, 0.25), (-1, 0.3), (-2, 0.2), (2, 0.15), (0, 0.1)],
    3:  [(-1, 0.3), (-2, 0.25), (1, 0.2), (-3, 0.15), (0, 0.1)],
    -1: [(-1, 0.3), (1, 0.25), (-2, 0.2), (0, 0.15), (2, 0.1)],
    -2: [(-1, 0.35), (1, 0.25), (-3, 0.15), (0, 0.15), (2, 0.1)],
    -3: [(1, 0.35), (-1, 0.25), (2, 0.2), (-2, 0.1), (0, 0.1)],
}
_DEFAULT_TRANSITIONS: list[tuple[int, float]] = [
    (1, 0.3), (-1, 0.25), (2, 0.2), (-2, 0.15), (0, 0.1),
]
_BARS_HASH_MULTIPLIER = 7919


def _markov_melody(
    scale: Scale,
    num_notes: int,
    start_degree: int = 1,
    rng: random.Random | None = None,
    octave_range: int = 2,
) -> list[float]:
    """Generate a melody as a list of frequencies using a Markov chain.

    Parameters
    ----------
    scale:
        Source scale.
    num_notes:
        Number of notes to generate.
    start_degree:
        Scale degree (1-indexed) to begin on.
    rng:
        Random instance for reproducibility.
    octave_range:
        Number of octaves to span.
    """
    if rng is None:
        rng = random.Random()

    scale_size = len(scale.intervals)
    total_degrees = scale_size * octave_range

    degree = start_degree
    last_interval = 0
    melody: list[float] = []

    for _ in range(num_notes):
        melody.append(scale.degree(degree))
        transitions = _MARKOV_TRANSITIONS.get(last_interval, _DEFAULT_TRANSITIONS)
        choices, weights = zip(*transitions)
        raw = rng.choices(list(choices), list(weights))[0]
        new_degree = degree + raw
        # Clamp to valid range
        new_degree = max(1, min(new_degree, total_degrees))
        last_interval = new_degree - degree
        degree = new_degree

    return melody


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------

class MusicGenerator:
    """AI-assisted procedural music generator.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    seed:
        Random seed for reproducibility (``None`` = non-deterministic).
    """

    def __init__(self, sample_rate: int = 44100, seed: int | None = None) -> None:
        self.sample_rate = sample_rate
        # Keep seed=None distinct from seed=0 by capturing a random base seed per generator instance.
        self._seed = resolve_base_seed(seed)
        MusicGenerator.verify_style_library_alignment()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        style: TrackStyle = "battle",
        duration: float | None = None,
        bars: int | None = None,
    ) -> Sequencer:
        """Generate a complete multi-track :class:`~audio_engine.composer.Sequencer`.

        Parameters
        ----------
        style:
            Musical style preset.
        duration:
            Override total length in seconds (ignored if *bars* is set).
        bars:
            Override number of bars to generate.

        Returns
        -------
        :class:`~audio_engine.composer.Sequencer`
            Fully populated sequencer, ready to call ``.render()``.
        """
        if style not in _STYLE_DEFS:
            available = ", ".join(sorted(_STYLE_DEFS))
            raise ValueError(f"Unknown style '{style}'. Available: {available}")

        sdef = _STYLE_DEFS[style]
        if style.startswith("studio_custom_"):
            self._validate_style_alignment(style, sdef)
        effective_bars = bars if bars is not None else sdef.bars
        rng = self._rng_for_call(style, effective_bars)
        scale_name = self._resolve_scale_name(style, sdef.scale_name)
        scale = ScaleLibrary.get(scale_name, sdef.root, sdef.octave)

        seq = Sequencer(bpm=sdef.bpm, sample_rate=self.sample_rate)
        self._configure_tracks(seq, sdef)

        planner = SectionPlanner(style=style, total_bars=effective_bars, seed=self._seed)
        blocks = planner.plan()
        motif_bank = MotifBank(scale_degree_count=len(scale.intervals), seed=self._seed)
        motif_seed = motif_bank.seed_motif()
        cadence_target = 1
        bar_duration = seq.bar_duration

        for block in blocks:
            for rel_bar in range(block.bar_length):
                bar_index = block.bar_start + rel_bar
                if bar_index >= effective_bars:
                    break
                bar_onset = bar_index * bar_duration
                is_phrase_end = rel_bar == block.bar_length - 1
                motif = self._vary_motif(motif_bank, motif_seed, block.motif_variation, rel_bar)
                if is_phrase_end:
                    motif[-1] = cadence_target

                chord_degrees = self._chord_for_bar(style, sdef, bar_index)
                chord_freqs = [scale.degree(d) for d in chord_degrees]
                root_freq = chord_freqs[0]
                density_steps = max(2, int(round(2 + 6 * block.melody_density)))
                note_len = bar_duration / density_steps

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
                        seq.add_note(
                            "lead_melody",
                            freq,
                            bar_onset + step * note_len,
                            note_len * 0.92,
                            velocity=0.55 + 0.4 * block.arrangement_density,
                        )

                if block.arrangement_density > 0.56 and block.role in {PhraseRole.A_VAR, PhraseRole.B_PHRASE, PhraseRole.CLIMAX}:
                    counter = motif_bank.sequence_down(motif, steps=1 if block.role != PhraseRole.CLIMAX else 2)
                    for step in range(max(2, density_steps // 2)):
                        degree = counter[step % len(counter)]
                        seq.add_note(
                            "counter_melody",
                            scale.degree(degree + 6),
                            bar_onset + (step + 0.5) * (bar_duration / max(2, density_steps // 2)),
                            max(0.08, note_len * 0.8),
                            velocity=0.35 + 0.32 * block.arrangement_density,
                        )

                if block.arrangement_density > 0.45 and rng.random() > 0.08:
                    for chord_freq in chord_freqs:
                        seq.add_note(
                            "harmony_pad",
                            chord_freq * 0.5,
                            bar_onset,
                            bar_duration * 0.96,
                            velocity=0.28 + 0.25 * block.arrangement_density,
                        )

                if block.arrangement_density > 0.38 and rng.random() > 0.12:
                    for hit in (0.0, 0.5):
                        for chord_freq in chord_freqs:
                            seq.add_note(
                                "chord_support",
                                chord_freq,
                                bar_onset + hit * bar_duration,
                                bar_duration * 0.46,
                                velocity=0.3 + 0.28 * block.arrangement_density,
                            )

                if block.arrangement_density > 0.5:
                    ostinato_steps = 8 if block.role in {PhraseRole.B_PHRASE, PhraseRole.CLIMAX} else 4
                    ost_len = bar_duration / ostinato_steps
                    tones = [chord_degrees[0], chord_degrees[-1], motif[0]]
                    for step in range(ostinato_steps):
                        degree = tones[step % len(tones)] + 12
                        seq.add_note(
                            "high_ostinato",
                            scale.degree(degree),
                            bar_onset + step * ost_len,
                            ost_len * 0.8,
                            velocity=0.24 + 0.2 * block.arrangement_density,
                        )

                for hit in (0.0, 0.5):
                    seq.add_note(
                        "bass_line",
                        root_freq * 0.25,
                        bar_onset + hit * bar_duration,
                        bar_duration * 0.44,
                        velocity=0.52 + 0.32 * block.arrangement_density,
                    )

                if "perc_low" in seq._tracks:
                    perc_strength = 0.35 + 0.55 * block.arrangement_density
                    for beat in (0.0, 0.5):
                        seq.add_note(
                            "perc_low",
                            80.0,
                            bar_onset + beat * bar_duration,
                            min(0.15, bar_duration * 0.2),
                            velocity=perc_strength,
                        )
                    if block.arrangement_density > 0.52:
                        for beat in (0.25, 0.75):
                            seq.add_note(
                                "perc_texture",
                                220.0,
                                bar_onset + beat * bar_duration,
                                min(0.12, bar_duration * 0.18),
                                velocity=0.28 + 0.42 * block.arrangement_density,
                            )

        pickup_onset = max(0.0, effective_bars * bar_duration - seq.beat_duration * 0.5)
        seq.add_note(
            "lead_melody",
            scale.degree(motif_seed[0] + 7),
            pickup_onset,
            min(seq.beat_duration * 0.4, 0.24),
            velocity=0.35,
        )
        return seq

    # ------------------------------------------------------------------
    # Convenience: generate + render
    # ------------------------------------------------------------------

    def generate_audio(
        self,
        style: TrackStyle = "battle",
        bars: int | None = None,
    ) -> np.ndarray:
        """Generate and render audio as a stereo float32 NumPy array.

        Parameters
        ----------
        style:
            Musical style preset.
        bars:
            Number of bars (defaults to the style's default).

        Returns
        -------
        np.ndarray
            Shape ``(N, 2)`` stereo float32 array.
        """
        seq = self.generate(style=style, bars=bars)
        return seq.render()

    @staticmethod
    def available_styles() -> list[str]:
        """Return sorted list of available style names."""
        return sorted(_STYLE_DEFS.keys())

    @staticmethod
    def available_style_metadata() -> dict[str, dict[str, object]]:
        """Return public style metadata for UI and CLI consumers."""
        return {
            name: {
                "bpm": style.bpm,
                "scale_name": style.scale_name,
                "root": style.root,
                "bars": style.bars,
                "progression_name": style.progression_name,
                "instruments": [*style.instruments],
                "accompaniment": [*style.accompaniment],
                "bass_instrument": style.bass_instrument,
                "percussion_instrument": style.percussion_instrument,
            }
            for name, style in _STYLE_DEFS.items()
        }

    @staticmethod
    def style_intent_metadata() -> dict[str, dict[str, object]]:
        """Return style-intent metadata used for alignment validation."""
        data: dict[str, dict[str, object]] = {}
        for name, sdef in _STYLE_DEFS.items():
            intent = MusicGenerator._infer_style_intent(name, sdef)
            data[name] = {
                "family": intent.family,
                "required_any": [*intent.required_any],
                "preferred_bass": [*intent.preferred_bass],
                "require_percussion": intent.require_percussion,
                "disallow_percussion": intent.disallow_percussion,
            }
        return data

    @staticmethod
    def validate_style_library_alignment() -> dict[str, list[str]]:
        """Return style-name/synth-alignment issues keyed by style."""
        issues: dict[str, list[str]] = {}
        for name, sdef in _STYLE_DEFS.items():
            style_issues = MusicGenerator._style_validation_errors(name, sdef)
            if style_issues:
                issues[name] = style_issues
        return issues

    @staticmethod
    def verify_style_library_alignment() -> None:
        """Raise when any style-intent alignment issue exists."""
        issues = MusicGenerator.validate_style_library_alignment()
        if not issues:
            return
        summary = "; ".join(f"{name}: {messages[0]}" for name, messages in sorted(issues.items()))
        raise ValueError(f"style/synth alignment failed during initialization: {summary}")

    def _rng_for_call(self, style: str, bars: int) -> random.Random:
        style_hash = sum((idx + 1) * ord(ch) for idx, ch in enumerate(style))
        return random.Random(self._seed + style_hash + bars * _BARS_HASH_MULTIPLIER)

    def _resolve_scale_name(self, style: str, default: str) -> str:
        family = style.lower()
        if family == "battle":
            return "harmonic_minor"
        if family == "exploration":
            return "major"
        if family == "ambient":
            return "dorian"
        if family == "boss":
            return "phrygian"
        if family == "victory":
            return "major"
        if family == "menu":
            return "dorian"
        return default

    def _configure_tracks(self, seq: Sequencer, sdef: _StyleDef) -> None:
        lead_name = sdef.instruments[0] if sdef.instruments else "strings"
        counter_name = sdef.instruments[1] if len(sdef.instruments) > 1 else "flute"
        ostinato_name = sdef.ostinato_instrument
        pad_name = sdef.accompaniment[0] if sdef.accompaniment else "synth_pad"
        chord_name = sdef.accompaniment[1] if len(sdef.accompaniment) > 1 else "strings"
        bass_name = sdef.bass_instrument or "bass"

        seq.add_track("lead_melody", InstrumentLibrary.get(lead_name, self.sample_rate), pan=-0.08, volume=0.9, priority=100, role="melody")
        seq.add_track("counter_melody", InstrumentLibrary.get(counter_name, self.sample_rate), pan=0.14, volume=0.58, priority=90, role="counter")
        seq.add_track("high_ostinato", InstrumentLibrary.get(ostinato_name, self.sample_rate), pan=0.26, volume=0.45, priority=50, role="texture")
        seq.add_track("harmony_pad", InstrumentLibrary.get(pad_name, self.sample_rate), pan=-0.16, volume=0.5, priority=70, role="harmony")
        seq.add_track("chord_support", InstrumentLibrary.get(chord_name, self.sample_rate), pan=0.04, volume=0.5, priority=60, role="harmony")
        seq.add_track("bass_line", InstrumentLibrary.get(bass_name, self.sample_rate), pan=0.0, volume=0.86, priority=95, role="bass")

        if sdef.percussion_instrument:
            perc_inst = InstrumentLibrary.get(sdef.percussion_instrument, self.sample_rate)
            seq.add_track("perc_low", perc_inst, pan=0.0, volume=0.78, priority=85, role="percussion")
            seq.add_track("perc_texture", perc_inst, pan=0.32, volume=0.42, priority=40, role="texture")

    def _vary_motif(self, bank: MotifBank, motif: list[int], mode: str, offset: int) -> list[int]:
        if mode == "sequence_up":
            return bank.sequence_up(motif, steps=1 + (offset % 2))
        if mode == "sequence_down":
            return bank.sequence_down(motif, steps=1 + (offset % 2))
        if mode == "invert":
            return bank.invert(motif)
        if mode == "rhythmic_augment":
            return bank.rhythmic_augment(motif)
        if mode == "rhythmic_diminish":
            return bank.rhythmic_diminish(motif)
        return motif[:]

    def _chord_for_bar(self, style: str, sdef: _StyleDef, bar_index: int) -> list[int]:
        progression = _PROGRESSION_DEGREES.get(sdef.progression_name)
        if not progression:
            style_family = style.lower()
            if style_family == "ambient":
                progression = [[1, 4, 5], [2, 5, 6], [1, 4, 6], [2, 5, 7]]
            elif style_family in {"boss", "battle"}:
                progression = [[1, 3, 5], [5, 7, 2], [6, 1, 3], [5, 7, 2]]
            else:
                progression = [[1, 3, 5], [4, 6, 1], [5, 7, 2], [1, 3, 5]]
        chord = progression[bar_index % len(progression)]
        profile = _THEORY_PROFILES.get(sdef.scale_name, _DEFAULT_THEORY_PROFILE)
        if bar_index % 8 == 7:
            return profile.closure
        if bar_index % 4 == 3:
            return profile.cadence
        if bar_index % 8 == 6:
            return profile.pre_cadence
        return chord

    def _validate_style_alignment(self, style: str, sdef: _StyleDef) -> None:
        issues = self._style_validation_errors(style, sdef)
        if issues:
            joined = "; ".join(issues)
            raise ValueError(f"style/synth alignment failed for '{style}': {joined}")

    @staticmethod
    def _style_validation_errors(style: str, sdef: _StyleDef) -> list[str]:
        intent = MusicGenerator._infer_style_intent(style, sdef)
        voices = [*sdef.instruments, *sdef.accompaniment, sdef.bass_instrument]
        if sdef.ostinato_instrument:
            voices.append(sdef.ostinato_instrument)
        issues: list[str] = []
        required = set(intent.required_any)
        if required and not any(voice in required for voice in voices):
            issues.append(
                f"expected at least one of {sorted(required)} in instruments/accompaniment"
            )
        if intent.preferred_bass and sdef.bass_instrument not in intent.preferred_bass:
            issues.append(
                f"bass instrument '{sdef.bass_instrument}' should be one of {sorted(intent.preferred_bass)}"
            )
        if intent.require_percussion and not sdef.percussion_instrument:
            issues.append("percussion is required for this style family")
        if intent.disallow_percussion and sdef.percussion_instrument:
            issues.append("percussion should be disabled for this style family")
        return issues

    @staticmethod
    def _infer_style_intent(style: str, sdef: _StyleDef) -> _StyleIntent:
        if style in _STYLE_INTENT_OVERRIDES:
            return _STYLE_INTENT_OVERRIDES[style]
        name = style.lower()
        if "ambient" in name:
            return _StyleIntent(
                family="ambient",
                required_any=("synth_pad", "crystal_synth", "choir", "strings"),
                preferred_bass=("synth_pad", "bass", "ff7_bass"),
                disallow_percussion=True,
            )
        if "battle" in name or "boss" in name or "epic" in name:
            return _StyleIntent(
                family="combat",
                required_any=(
                    "brass",
                    "ff8_electric_guitar",
                    "ff7_strings",
                    "french_horn",
                    "timpani",
                    "ff7_lead",
                    "piano",
                    "flute",
                    "synth_pad",
                ),
                preferred_bass=("ff7_bass", "bass", "synth_pad"),
                require_percussion=bool(sdef.percussion_instrument),
            )
        if "ballad" in name or "menu" in name or "memorial" in name:
            return _StyleIntent(
                family="ballad",
                required_any=("piano", "strings", "cello", "flute", "violin_solo"),
                preferred_bass=("bass", "ff7_bass", "synth_pad"),
                disallow_percussion=True,
            )
        required_any = tuple(sorted(set([*sdef.instruments, *sdef.accompaniment]))) or ("strings",)
        return _StyleIntent(
            family="general",
            required_any=required_any,
            preferred_bass=(sdef.bass_instrument,),
            require_percussion=bool(sdef.percussion_instrument),
            disallow_percussion=not bool(sdef.percussion_instrument),
        )
