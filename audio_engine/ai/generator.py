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

from audio_engine.composer.scale import Scale, ScaleLibrary
from audio_engine.composer.chord import ChordProgression
from audio_engine.composer.pattern import RhythmPattern
from audio_engine.composer.sequencer import Note, Sequencer
from audio_engine.synthesizer.instrument import InstrumentLibrary

__all__ = ["TrackStyle", "MusicGenerator"]

TrackStyle = Literal[
    "battle", "exploration", "ambient", "boss", "victory", "menu",
    # FF7 / FF8 era styles
    "ff7_battle", "ff7_overworld", "ff7_boss", "ff7_sad", "ff7_town",
    "ff8_battle", "ff8_ballad",
    # Shared retro-RPG styles
    "prelude", "world_map", "dungeon", "healing", "tension",
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
        instruments=["flute", "strings"],
        accompaniment=["strings", "choir"],
        bass_instrument="bass",
        percussion_instrument=None,
        melody_pattern="eighth_notes",
        chord_pattern="half_notes",
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
        melody_pattern="eight_notes",
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
        instruments=["ff7_lead", "flute"],
        accompaniment=["ff7_strings", "choir"],
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
        instruments=["piano", "ff7_strings"],
        accompaniment=["ff7_strings", "choir"],
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

    "ff8_ballad": _StyleDef(
        # "Eyes on Me" — slow romantic ballad, the signature FF8 vocal piece.
        # F major, 74 BPM, piano-led with strings + choir.  Designed for
        # use with VocalMelodySynth overlay to create a full vocal arrangement.
        bpm=74,
        scale_name="major",
        root="F",
        octave=4,
        progression_name="I_vi_IV_V",
        instruments=["piano", "flute"],
        accompaniment=["ff7_strings", "choir"],
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
        instruments=["piano"],
        accompaniment=["ff7_strings"],
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
        accompaniment=["ff7_strings", "brass"],
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
        instruments=["piano"],
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
        melody_pattern="eight_notes",
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
        instruments=["brass", "ff7_strings"],
        accompaniment=["choir", "ff7_strings"],
        bass_instrument="ff7_bass",
        percussion_instrument="percussion",
        melody_pattern="half_notes",
        chord_pattern="half_notes",
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
        instruments=["flute", "piano"],
        accompaniment=["ff7_strings"],
        bass_instrument="bass",
        percussion_instrument="percussion",
        melody_pattern="eighth_notes",
        chord_pattern="four_on_the_floor",
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
        self._rng = random.Random(seed)

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
        effective_bars = bars if bars is not None else sdef.bars

        seq = Sequencer(bpm=sdef.bpm, sample_rate=self.sample_rate)
        scale = ScaleLibrary.get(sdef.scale_name, sdef.root, sdef.octave)

        bar_dur = seq.bar_duration

        # --- Build chord progression ---
        prog = ChordProgression(scale, sdef.progression_name)
        chords = prog.chords  # list of Chord objects (one per chord change)

        # --- Add instrument tracks ---
        chord_patt = getattr(RhythmPattern, sdef.chord_pattern, RhythmPattern.half_notes)()
        melody_patt = getattr(RhythmPattern, sdef.melody_pattern, RhythmPattern.eighth_notes)()

        for inst_name in sdef.instruments:
            inst = InstrumentLibrary.get(inst_name, self.sample_rate)
            pan = self._rng.uniform(-0.3, 0.3)
            seq.add_track(f"melody_{inst_name}", inst, pan=pan, volume=0.8)

        for inst_name in sdef.accompaniment:
            inst = InstrumentLibrary.get(inst_name, self.sample_rate)
            pan = self._rng.uniform(-0.5, 0.5)
            seq.add_track(f"chord_{inst_name}", inst, pan=pan, volume=0.6)

        bass_inst = InstrumentLibrary.get(sdef.bass_instrument, self.sample_rate)
        seq.add_track("bass", bass_inst, pan=0.0, volume=0.85)

        if sdef.percussion_instrument:
            perc_inst = InstrumentLibrary.get(sdef.percussion_instrument, self.sample_rate)
            seq.add_track("percussion", perc_inst, pan=0.0, volume=0.9)

        # --- Populate notes bar by bar ---
        for bar_idx in range(effective_bars):
            bar_onset = bar_idx * bar_dur
            chord = chords[bar_idx % len(chords)]

            # Melody layer
            mel_triggers = melody_patt.note_durations(bar_dur)
            num_mel_notes = len(mel_triggers)
            mel_freqs = _markov_melody(
                scale, num_mel_notes, start_degree=1, rng=self._rng, octave_range=2
            )

            for track_name_suffix in sdef.instruments:
                for (rel_onset, note_dur), freq in zip(mel_triggers, mel_freqs):
                    vel = self._rng.uniform(0.6, 1.0)
                    seq.add_note(
                        f"melody_{track_name_suffix}",
                        freq,
                        bar_onset + rel_onset,
                        note_dur * 0.9,
                        velocity=vel,
                    )

            # Chord layer
            chord_triggers = chord_patt.note_durations(bar_dur)
            for inst_name in sdef.accompaniment:
                for rel_onset, note_dur in chord_triggers:
                    for chord_freq in chord.frequencies:
                        # Drop chord tones by one octave for richness
                        seq.add_note(
                            f"chord_{inst_name}",
                            chord_freq * 0.5,
                            bar_onset + rel_onset,
                            note_dur * 0.85,
                            velocity=0.55,
                        )

            # Bass – root note of current chord
            bass_freq = chord.frequencies[0] * 0.25   # two octaves below
            for rel_onset, note_dur in chord_patt.note_durations(bar_dur):
                seq.add_note("bass", bass_freq, bar_onset + rel_onset, note_dur * 0.9, velocity=0.8)

            # Percussion
            if sdef.percussion_instrument:
                perc_patt = RhythmPattern.four_on_the_floor()
                for rel_onset, note_dur in perc_patt.note_durations(bar_dur):
                    # Use a fixed pitched 'hit' frequency for the drum voice
                    seq.add_note(
                        "percussion",
                        80.0,   # low thud
                        bar_onset + rel_onset,
                        min(note_dur, 0.15),
                        velocity=self._rng.uniform(0.7, 1.0),
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
