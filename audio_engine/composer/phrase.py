"""Phrase/section planning utilities for structured procedural composition."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import random

__all__ = ["PhraseRole", "PhraseBlock", "SectionPlanner", "MotifBank"]

_BAR_HASH_MULTIPLIER = 97


class PhraseRole(Enum):
    INTRO = auto()
    A_PHRASE = auto()
    A_VAR = auto()
    B_PHRASE = auto()
    CLIMAX = auto()
    CADENCE = auto()
    OUTRO = auto()


@dataclass(frozen=True)
class PhraseBlock:
    role: PhraseRole
    bar_start: int
    bar_length: int
    melody_density: float
    arrangement_density: float
    motif_variation: str


class SectionPlanner:
    """Create deterministic phrase blocks for a style and bar count."""

    def __init__(self, style: str, total_bars: int, seed: int | None = None) -> None:
        self.style = style
        self.total_bars = max(4, total_bars)
        self._seed = seed if seed is not None else random.SystemRandom().randrange(0, 2**31)
        style_hash = sum((idx + 1) * ord(ch) for idx, ch in enumerate(style))
        # Mix style and bar count into the seed to keep repeatable section plans per request shape.
        self._rng = random.Random(self._seed + style_hash + self.total_bars * _BAR_HASH_MULTIPLIER)

    def plan(self) -> list[PhraseBlock]:
        if self.total_bars <= 4:
            names = [
                PhraseRole.INTRO,
                PhraseRole.A_PHRASE,
                PhraseRole.CLIMAX,
                PhraseRole.CADENCE,
            ]
        elif self.total_bars == 5:
            names = [
                PhraseRole.INTRO,
                PhraseRole.A_PHRASE,
                PhraseRole.B_PHRASE,
                PhraseRole.CLIMAX,
                PhraseRole.CADENCE,
            ]
        else:
            names = [
                PhraseRole.INTRO,
                PhraseRole.A_PHRASE,
                PhraseRole.A_VAR,
                PhraseRole.B_PHRASE,
                PhraseRole.CLIMAX,
                PhraseRole.CADENCE,
            ]
        if self.total_bars >= 20:
            names.append(PhraseRole.OUTRO)

        weight_templates = {
            PhraseRole.INTRO: 0.12,
            PhraseRole.A_PHRASE: 0.2,
            PhraseRole.A_VAR: 0.18,
            PhraseRole.B_PHRASE: 0.2,
            PhraseRole.CLIMAX: 0.18,
            PhraseRole.CADENCE: 0.12,
            PhraseRole.OUTRO: 0.08,
        }
        raw = [weight_templates[r] for r in names]
        total = sum(raw)
        bars = [max(1, round(self.total_bars * (w / total))) for w in raw]

        while sum(bars) > self.total_bars:
            idx = max(range(len(bars)), key=bars.__getitem__)
            if bars[idx] > 1:
                bars[idx] -= 1
            else:
                break
        while sum(bars) < self.total_bars:
            idx = min(range(len(bars)), key=bars.__getitem__)
            bars[idx] += 1

        densities = {
            PhraseRole.INTRO: (0.25, 0.25, "repeat"),
            PhraseRole.A_PHRASE: (0.55, 0.45, "repeat"),
            PhraseRole.A_VAR: (0.65, 0.58, "rhythmic_diminish"),
            PhraseRole.B_PHRASE: (0.7, 0.62, "invert"),
            PhraseRole.CLIMAX: (0.95, 0.9, "sequence_up"),
            PhraseRole.CADENCE: (0.45, 0.52, "sequence_down"),
            PhraseRole.OUTRO: (0.3, 0.25, "rhythmic_augment"),
        }

        blocks: list[PhraseBlock] = []
        start = 0
        for role, length in zip(names, bars):
            m, a, v = densities[role]
            m = max(0.1, min(1.0, m + self._rng.uniform(-0.05, 0.05)))
            a = max(0.1, min(1.0, a + self._rng.uniform(-0.06, 0.06)))
            blocks.append(
                PhraseBlock(
                    role=role,
                    bar_start=start,
                    bar_length=length,
                    melody_density=m,
                    arrangement_density=a,
                    motif_variation=v,
                )
            )
            start += length
        return blocks


class MotifBank:
    """Create and transform compact motifs as scale-degree sequences."""

    def __init__(self, scale_degree_count: int = 7, seed: int | None = None) -> None:
        self.scale_degree_count = max(5, scale_degree_count)
        self._rng = random.Random(seed)

    def seed_motif(self) -> list[int]:
        size = self._rng.randint(3, 5)
        degrees = [self._rng.randint(1, self.scale_degree_count) for _ in range(size)]
        if all(d == degrees[0] for d in degrees):
            degrees[-1] = min(self.scale_degree_count, degrees[-1] + 1)
        return degrees

    def sequence_up(self, motif: list[int], steps: int = 1) -> list[int]:
        return [self._clamp(deg + steps) for deg in motif]

    def sequence_down(self, motif: list[int], steps: int = 1) -> list[int]:
        return [self._clamp(deg - steps) for deg in motif]

    def invert(self, motif: list[int]) -> list[int]:
        pivot = motif[0] if motif else 1
        return [self._clamp(pivot - (deg - pivot)) for deg in motif]

    def rhythmic_augment(self, motif: list[int]) -> list[int]:
        expanded: list[int] = []
        for degree in motif:
            expanded.extend([degree, degree])
        return expanded

    def rhythmic_diminish(self, motif: list[int]) -> list[int]:
        if len(motif) <= 2:
            return motif[:]
        return motif[::2] + [motif[-1]]

    def _clamp(self, degree: int) -> int:
        return max(1, min(self.scale_degree_count, degree))
