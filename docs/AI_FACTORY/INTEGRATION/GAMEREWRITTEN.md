# `GameRewritten` Integration Direction

> Update this file when downstream import expectations become more concrete.

## Why this matters

The long-term purpose of this repository is to generate assets that another game repository can import. `GameRewritten` is the clearest downstream target described so far.

## Integration goals

1. generate assets with stable target paths
2. keep naming conventions machine-readable
3. preserve provenance so assets can be regenerated or replaced
4. separate draft generation from approved import assets

## Recommended downstream categories

- `Content/Audio/` music loops and stingers
- `Content/Audio/` combat and UI SFX
- optional voice/narration assets kept clearly separated

## Suggested mapping strategy

1. define gameplay states/events in an audio plan
2. map each state/event to one or more generation requests
3. export to canonical downstream paths
4. record overrides where manual replacement beats generated output

## Important rule

If `GameRewritten` expects a specific filename, keep that filename stable even if the factory stores additional provenance or draft variants elsewhere.
