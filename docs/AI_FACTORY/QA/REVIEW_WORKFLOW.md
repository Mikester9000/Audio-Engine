# Asset Review Workflow

> Update this file whenever review states or review expectations change.

## Purpose

Generated assets should not move from draft output to downstream import by accident. Review must be explicit.

## Recommended review states

| State | Meaning |
|---|---|
| `draft` | generated but not reviewed |
| `approved` | acceptable for downstream use |
| `revise` | promising but needs another pass |
| `rejected` | wrong direction; do not ship |
| `overridden` | replaced by a manual or alternate asset |

## Review checklist

### Music

- gameplay role is correct
- loop behavior is correct when required
- no obvious clipping or bad seam
- emotional target fits the scene
- output does not feel like a direct copyrighted imitation

### SFX

- transient/readability fits gameplay
- category identity is clear
- tail length is appropriate
- repetition fatigue risk is acceptable

### Voice

- intelligibility is acceptable
- timing fits gameplay use
- quality is good enough for the current milestone

## Rule

If an asset is not `approved`, it should not be treated as final downstream content even if it is technically usable.
