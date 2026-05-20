"""
Deterministic orchestral sample scanner for remaster workflows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from audio_engine.dsp.pitch_shift import pitch_ratio_from_midi

__all__ = [
    "SampleMatch",
    "SampleNote",
    "OrchestralSampleLibrary",
    "note_name_to_midi",
    "midi_to_note_name",
]

_NOTE_OFFSETS: dict[str, int] = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}
_NOTE_PATTERN = re.compile(r"(?i)(?:^|[^A-G])([A-G](?:#|b)?)(-?\d)(?:[^0-9]|$)")
_CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name_to_midi(note_name: str) -> int:
    """Convert a note name like ``C4`` or ``A#3`` to MIDI note number."""
    m = re.fullmatch(r"(?i)\s*([A-G])([#b]?)(-?\d)\s*", note_name)
    if m is None:
        raise ValueError(f"invalid note name: {note_name!r}")
    root = (m.group(1).upper() + m.group(2).upper()).replace("♭", "B").replace("♯", "#")
    octave = int(m.group(3))
    if root not in _NOTE_OFFSETS:
        raise ValueError(f"invalid note root: {root!r}")
    return 12 * (octave + 1) + _NOTE_OFFSETS[root]


def midi_to_note_name(midi_note: int) -> str:
    """Convert MIDI note number to canonical sharp note name."""
    midi_note = int(midi_note)
    octave = (midi_note // 12) - 1
    return f"{_CHROMATIC[midi_note % 12]}{octave}"


@dataclass(frozen=True)
class SampleNote:
    """One discovered sample note file."""

    instrument: str
    note: str
    midi: int
    path: Path


@dataclass(frozen=True)
class SampleMatch:
    """Nearest sample match for a requested note."""

    instrument: str
    source: SampleNote
    target_midi: int
    pitch_ratio: float


class OrchestralSampleLibrary:
    """Scan a ``samples/orchestral`` tree into instrument→note mappings."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._by_instrument: dict[str, list[SampleNote]] = {}
        self._scan()

    def _scan(self) -> None:
        if not self.root.exists():
            return
        for instrument_dir in sorted(p for p in self.root.iterdir() if p.is_dir()):
            notes: list[SampleNote] = []
            for wav in sorted(p for p in instrument_dir.rglob("*") if p.suffix.lower() == ".wav"):
                parsed = self._parse_note_from_filename(wav.stem)
                if parsed is None:
                    continue
                note_name, midi_note = parsed
                notes.append(
                    SampleNote(
                        instrument=instrument_dir.name,
                        note=note_name,
                        midi=midi_note,
                        path=wav,
                    )
                )
            if notes:
                self._by_instrument[instrument_dir.name] = sorted(notes, key=lambda x: x.midi)

    @staticmethod
    def _parse_note_from_filename(stem: str) -> tuple[str, int] | None:
        m = _NOTE_PATTERN.search(f" {stem} ")
        if m is None:
            return None
        note_name = f"{m.group(1).upper()}{m.group(2)}"
        try:
            midi_note = note_name_to_midi(note_name)
        except ValueError:
            return None
        canonical = midi_to_note_name(midi_note)
        return canonical, midi_note

    def available_instruments(self) -> list[str]:
        return sorted(self._by_instrument)

    def has_instrument(self, instrument: str) -> bool:
        return instrument in self._by_instrument

    def notes_for_instrument(self, instrument: str) -> list[SampleNote]:
        return list(self._by_instrument.get(instrument, []))

    def resolve_nearest(self, instrument: str, target_note: str | int) -> SampleMatch | None:
        notes = self._by_instrument.get(instrument)
        if not notes:
            return None
        target_midi = note_name_to_midi(target_note) if isinstance(target_note, str) else int(target_note)
        source = min(notes, key=lambda n: abs(n.midi - target_midi))
        return SampleMatch(
            instrument=instrument,
            source=source,
            target_midi=target_midi,
            pitch_ratio=pitch_ratio_from_midi(source.midi, target_midi),
        )
