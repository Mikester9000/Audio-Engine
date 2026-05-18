from __future__ import annotations

import random

MAX_RANDOM_SEED = 2**31


def resolve_base_seed(seed: int | None) -> int:
    """Return the explicit seed or a random base seed when None is provided."""
    return seed if seed is not None else random.SystemRandom().randrange(0, MAX_RANDOM_SEED)
