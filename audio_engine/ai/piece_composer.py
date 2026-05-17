"""
PieceComposer — structured multi-section musical piece generator.

Produces a complete musical piece by assembling multiple sections (intro,
verse, chorus, bridge, outro), crossfading between them, and optionally
layering a sung vocal melody over the arrangement.

This is the module that enables producing full pieces like "Eyes on Me" from
FF8 — a slow ballad with a piano intro, string-led verse, full orchestral
chorus, and a wordless soprano vocal melody above the arrangement.

Quick start
-----------
Generate a full "Eyes on Me"-style piece with vocals::

    from audio_engine.ai.piece_composer import PieceComposer

    composer = PieceComposer(sample_rate=44100, seed=42)
    audio = composer.compose_eyes_on_me(duration=120.0)
    # Returns stereo float32 (N, 2) array

Generate any structured piece::

    audio = composer.compose(
        style="ff8_ballad",
        sections=["intro", "verse", "chorus", "bridge", "chorus", "outro"],
        with_vocals=True,
        duration=90.0,
    )

CLI
---
    audio-engine compose-piece --style ff8_ballad --with-vocals --output eyes_on_me.wav --duration 90
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

__all__ = ["PieceComposer", "SectionDef", "SECTION_TEMPLATES"]

SectionType = Literal["intro", "verse", "pre_chorus", "chorus", "bridge", "outro"]

# ---------------------------------------------------------------------------
# Section template definitions
# Per section: bar multiplier (relative to the base style's default bars)
# and per-track volume modifiers for orchestration variety between sections.
# ---------------------------------------------------------------------------

@dataclass
class SectionDef:
    """Defines how to render one section of a structured musical piece.

    Attributes
    ----------
    name:
        Human-readable section label.
    bar_multiplier:
        Scale the style's default bar count by this factor.
    melody_volume:
        Volume scalar applied to the melody layer (0–1).
    chord_volume:
        Volume scalar applied to the chord/accompaniment layer (0–1).
    bass_volume:
        Volume scalar applied to the bass layer (0–1).
    percussion_volume:
        Volume scalar applied to percussion (0 = mute).
    vocal_volume:
        Volume scalar for the vocal layer in this section (0 = no vocal).
    vocal_vowel:
        Vowel used for the vocal line in this section.
    crossfade_ms:
        Crossfade duration in milliseconds to the *next* section.
    """
    name: str
    bar_multiplier: float = 1.0
    melody_volume: float = 1.0
    chord_volume: float = 1.0
    bass_volume: float = 1.0
    percussion_volume: float = 1.0
    vocal_volume: float = 0.0       # 0 = no vocal by default
    vocal_vowel: str = "ah"
    crossfade_ms: float = 80.0      # crossfade to next section


# Default section templates for ballad / orchestral styles
SECTION_TEMPLATES: dict[str, SectionDef] = {
    "intro":      SectionDef("intro",      bar_multiplier=0.5, melody_volume=0.8,
                             chord_volume=0.7, bass_volume=0.6, percussion_volume=0.0,
                             vocal_volume=0.0, crossfade_ms=100.0),
    "verse":      SectionDef("verse",      bar_multiplier=1.0, melody_volume=1.0,
                             chord_volume=0.8, bass_volume=0.8, percussion_volume=0.5,
                             vocal_volume=0.70, vocal_vowel="ah", crossfade_ms=80.0),
    "pre_chorus": SectionDef("pre_chorus", bar_multiplier=0.5, melody_volume=0.9,
                             chord_volume=1.0, bass_volume=0.9, percussion_volume=0.6,
                             vocal_volume=0.50, vocal_vowel="oh", crossfade_ms=60.0),
    "chorus":     SectionDef("chorus",     bar_multiplier=1.0, melody_volume=1.0,
                             chord_volume=1.0, bass_volume=1.0, percussion_volume=0.8,
                             vocal_volume=0.85, vocal_vowel="ah", crossfade_ms=80.0),
    "bridge":     SectionDef("bridge",     bar_multiplier=0.5, melody_volume=0.75,
                             chord_volume=0.9, bass_volume=0.75, percussion_volume=0.3,
                             vocal_volume=0.55, vocal_vowel="mm", crossfade_ms=100.0),
    "outro":      SectionDef("outro",      bar_multiplier=0.75, melody_volume=0.7,
                             chord_volume=0.6, bass_volume=0.5, percussion_volume=0.0,
                             vocal_volume=0.35, vocal_vowel="oh", crossfade_ms=0.0),
}

# "Eyes on Me" specific section sequence
_EYES_ON_ME_SECTIONS: list[str] = [
    "intro", "verse", "pre_chorus", "chorus",
    "verse", "pre_chorus", "chorus", "bridge",
    "chorus", "outro",
]


class PieceComposer:
    """Generate structured multi-section musical pieces with optional vocals.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz.
    seed:
        RNG seed for reproducibility.
    backend:
        Backend identifier for music generation.  Defaults to
        ``"synth_orchestral"`` for the cleanest output; use ``"ps1"``
        for the retro-degraded flavour.
    vocal_preset:
        Voice preset for VocalMelodySynth
        (``"soprano"`` | ``"alto"`` | ``"tenor"`` | ``"choir_ah"``).
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        seed: int | None = None,
        backend: str = "synth_orchestral",
        vocal_preset: str = "soprano",
        backend_kwargs: dict[str, object] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self._seed = seed
        self._backend_name = backend
        self._vocal_preset = vocal_preset
        self._backend_kwargs = dict(backend_kwargs or {})
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    def compose_eyes_on_me(
        self,
        duration: float = 90.0,
        with_vocals: bool = True,
        backend: str | None = None,
    ) -> np.ndarray:
        """Generate a complete "Eyes on Me" (FF8) style piece.

        Parameters
        ----------
        duration:
            Target total duration in seconds.  Sections are scaled to fit.
        with_vocals:
            If ``True``, overlays a soprano "ah"/"oh" vocal melody line.
        backend:
            Override the instance backend for this call.

        Returns
        -------
        np.ndarray
            Stereo float32 audio ``(N, 2)``.
        """
        return self.compose(
            style="ff8_ballad",
            sections=_EYES_ON_ME_SECTIONS,
            with_vocals=with_vocals,
            duration=duration,
            backend=backend,
        )

    def compose(
        self,
        style: str = "ff8_ballad",
        sections: list[str] | None = None,
        with_vocals: bool = True,
        duration: float = 90.0,
        backend: str | None = None,
        quiet: bool = False,
    ) -> np.ndarray:
        """Generate a multi-section musical piece.

        Parameters
        ----------
        style:
            Base music style for all sections.
        sections:
            Ordered list of section type names from
            :data:`SECTION_TEMPLATES`.  Defaults to
            ``["intro", "verse", "chorus", "bridge", "chorus", "outro"]``.
        with_vocals:
            If ``True``, overlay a VocalMelodySynth vocal line.
        duration:
            Target total duration in seconds.
        backend:
            Override backend for this call.

        Returns
        -------
        np.ndarray
            Stereo float32 audio ``(N, 2)``.
        """
        if sections is None:
            sections = ["intro", "verse", "chorus", "bridge", "chorus", "outro"]

        effective_backend = backend or self._backend_name

        # Resolve section defs
        sec_defs = [SECTION_TEMPLATES.get(s, SECTION_TEMPLATES["verse"]) for s in sections]

        # Calculate per-section target duration
        total_weight = sum(sd.bar_multiplier for sd in sec_defs)
        sec_durations = [sd.bar_multiplier / total_weight * duration for sd in sec_defs]

        # Generate each section
        section_audios: list[np.ndarray] = []
        for i, (sec_def, sec_dur) in enumerate(zip(sec_defs, sec_durations)):
            audio = self._generate_section(
                style=style,
                sec_def=sec_def,
                duration=sec_dur,
                backend_name=effective_backend,
                with_vocal=with_vocals,
                rng=self._rng,
            )
            section_audios.append(audio)
            if not quiet:
                print(f"  [{i+1}/{len(sec_defs)}] {sec_def.name}: {sec_dur:.1f}s", flush=True)

        # Assemble with crossfades
        assembled = self._crossfade_sections(section_audios, sec_defs)

        # Final mastering pass
        assembled = self._master(assembled)

        return assembled

    # ------------------------------------------------------------------
    # Section generation
    # ------------------------------------------------------------------

    def _generate_section(
        self,
        style: str,
        sec_def: SectionDef,
        duration: float,
        backend_name: str,
        with_vocal: bool,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Generate audio for one section, with optional vocal overlay."""
        # Instrumental backing
        instrumental = self._generate_instrumental(style, duration, backend_name)

        if not with_vocal or sec_def.vocal_volume < 0.01:
            return self._to_stereo(instrumental)

        # Generate vocal melody
        vocal_audio = self._generate_vocal_melody(
            style=style,
            duration=duration,
            vowel=sec_def.vocal_vowel,
            rng=rng,
        )

        # Mix
        stereo_inst = self._to_stereo(instrumental)
        stereo_vocal = self._to_stereo(vocal_audio)

        n = min(len(stereo_inst), len(stereo_vocal))
        mixed = (
            stereo_inst[:n] * (1.0 - sec_def.vocal_volume * 0.3)
            + stereo_vocal[:n] * sec_def.vocal_volume
        )
        if len(stereo_inst) > n:
            mixed = np.concatenate([mixed, stereo_inst[n:]])

        return mixed.astype(np.float32)

    def _generate_instrumental(
        self,
        style: str,
        duration: float,
        backend_name: str,
    ) -> np.ndarray:
        """Generate the instrumental backing for a section."""
        from audio_engine.ai.backend import BackendRegistry
        from audio_engine.ai.ps1_backend import PS1Backend
        from audio_engine.ai.synth_orchestral_backend import SynthOrchestralBackend

        try:
            if backend_name == "ps1":
                backend = PS1Backend(sample_rate=self.sample_rate, seed=self._seed)
            elif backend_name == "synth_orchestral":
                backend = SynthOrchestralBackend(sample_rate=self.sample_rate, seed=self._seed)
            else:
                backend = BackendRegistry.get(
                    backend_name,
                    sample_rate=self.sample_rate,
                    seed=self._seed,
                    **self._backend_kwargs,
                )
            audio = backend.generate_music_audio(style=style, duration=duration)
        except Exception:
            # Fallback to procedural
            from audio_engine.ai.backend import ProceduralBackend
            backend = ProceduralBackend(sample_rate=self.sample_rate, seed=self._seed)
            audio = backend.generate_music_audio(style=style, duration=duration)

        return audio

    def _generate_vocal_melody(
        self,
        style: str,
        duration: float,
        vowel: str,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Generate a sung vocal melody line for the given style and duration."""
        from audio_engine.ai.vocal_melody_synth import VocalMelodySynth
        from audio_engine.composer.scale import ScaleLibrary, midi_to_freq

        synth = VocalMelodySynth(
            sample_rate=self.sample_rate,
            voice_preset=self._vocal_preset,
        )

        # Build a scale-aware melody
        notes = self._build_vocal_melody_notes(style, duration, vowel, rng)
        return synth.synthesize(notes, rng=rng)

    def _build_vocal_melody_notes(
        self,
        style: str,
        duration: float,
        vowel: str,
        rng: np.random.Generator,
    ) -> list[tuple[float, float, str]]:
        """Build a sequence of (freq, dur, vowel) notes for the vocal line."""
        from audio_engine.ai.generator import _STYLE_DEFS
        from audio_engine.composer.scale import ScaleLibrary, midi_to_freq

        style_def = _STYLE_DEFS.get(style, _STYLE_DEFS.get("ff8_ballad", list(_STYLE_DEFS.values())[0]))
        scale = ScaleLibrary.get(style_def.scale_name, root=style_def.root, octave=style_def.octave)
        bpm = style_def.bpm

        # Build a melodic line using scale degrees — stepwise motion with occasional leaps
        # For ff8_ballad (Eyes on Me feel): mostly 5th, 6th, 7th, 8th, 1st, 2nd, 3rd
        # Typical pattern: high degree → stepwise descent → climb
        degree_patterns = [5, 6, 7, 8, 7, 6, 5, 4, 3, 4, 5, 6, 7, 6, 5]
        beat_dur = 60.0 / bpm  # quarter-note duration

        notes: list[tuple[float, float, str]] = []
        elapsed = 0.0
        degree_idx = 0

        # Vary note durations: mix of half-notes and quarter-notes for melodic feel
        durations_pattern = [2.0, 1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 4.0,
                             2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 4.0]
        dur_idx = 0

        while elapsed < duration:
            degree = degree_patterns[degree_idx % len(degree_patterns)]
            freq = scale.degree(degree)
            note_dur_beats = durations_pattern[dur_idx % len(durations_pattern)]
            note_dur_sec = note_dur_beats * beat_dur
            remaining = duration - elapsed
            if note_dur_sec > remaining:
                note_dur_sec = remaining

            # Alternate vowels: "ah" for longer notes, "oh" for short
            v = "ah" if note_dur_sec >= beat_dur * 1.5 else "oh"
            if vowel == "mm":
                v = "mm"  # Bridge sections use hum throughout

            notes.append((freq, note_dur_sec, v))
            elapsed += note_dur_sec
            degree_idx += 1
            dur_idx += 1

        return notes

    # ------------------------------------------------------------------
    # Assembly helpers
    # ------------------------------------------------------------------

    def _crossfade_sections(
        self,
        sections: list[np.ndarray],
        sec_defs: list[SectionDef],
    ) -> np.ndarray:
        """Join stereo section arrays with crossfades."""
        if not sections:
            return np.zeros((0, 2), dtype=np.float32)
        if len(sections) == 1:
            return sections[0]

        result = sections[0]
        for i, (seg, sec_def) in enumerate(zip(sections[1:], sec_defs[:-1])):
            xfade_n = max(1, int(sec_def.crossfade_ms * self.sample_rate / 1000.0))
            result = self._crossfade_pair(result, seg, xfade_n)

        return result

    def _crossfade_pair(
        self,
        a: np.ndarray,
        b: np.ndarray,
        xfade_n: int,
    ) -> np.ndarray:
        """Overlap-add crossfade between two stereo arrays."""
        xfade_n = min(xfade_n, len(a), len(b))
        fade_out = np.linspace(1.0, 0.0, xfade_n, dtype=np.float32).reshape(-1, 1)
        fade_in  = np.linspace(0.0, 1.0, xfade_n, dtype=np.float32).reshape(-1, 1)

        blended = a[-xfade_n:] * fade_out + b[:xfade_n] * fade_in
        return np.concatenate([a[:-xfade_n], blended, b[xfade_n:]], axis=0).astype(np.float32)

    def _to_stereo(self, audio: np.ndarray) -> np.ndarray:
        """Convert mono to stereo if needed."""
        if audio.ndim == 2 and audio.shape[1] == 2:
            return audio.astype(np.float32)
        if audio.ndim == 1:
            return np.stack([audio, audio], axis=1).astype(np.float32)
        return audio.astype(np.float32)

    def _master(self, audio: np.ndarray) -> np.ndarray:
        """Light mastering: normalise + gentle limiter."""
        # Normalise to -3 dBFS peak
        peak = np.max(np.abs(audio))
        if peak > 1e-9:
            audio = audio * (0.70 / peak)
        return audio.astype(np.float32)
