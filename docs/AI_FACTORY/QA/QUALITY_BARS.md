# Quality Bars and Asset Rules

> Update this file whenever naming, export, review, or acceptance criteria change.

## Current export reality

Current code supports WAV export by default and optional OGG export with extra dependency support.

## File organization rule

Generated assets should be organized by gameplay function first, not by implementation detail.

### Current batch layout

```text
<output_dir>/
├── music/
├── sfx/
├── voice/
└── manifest.json
```

### Target extended layout

```text
<output_dir>/
├── music/
├── sfx/
├── ambience/
├── ui/
├── voice/
├── manifests/
└── reviews/
```

## Naming conventions

### Current canonical integration names

When interoperating with existing integration code, preserve canonical filenames defined in `audio_engine/integration/game_state_map.py`.

### Future naming rule for broader factory work

Use stable, searchable names:

```text
<category>/<asset_id>__<variant>__seed<seed>.<ext>
```

Example:

```text
music/bgm_field_day__base__seed0042.ogg
sfx/spell_fire_cast__variant_a__seed1337.wav
```

## Export format rules

| Asset type | Preferred format | Notes |
|---|---|---|
| Music loops | `ogg` or `wav` depending downstream need | capture loop requirements explicitly |
| Short SFX | `wav` | easy iteration and exact transient handling |
| Voice | `wav` during iteration | convert later only if downstream requires |

## Acceptance criteria by asset type

### Music

- emotionally matches gameplay role
- avoids obvious clipping
- loopable when marked loopable
- no abrupt stop unless intentionally a sting/fanfare
- sufficiently distinct from other core categories

### SFX

- immediately readable in gameplay context
- attack/transient is present when required
- tail length fits the event
- category variants are meaningfully different when multiple variants exist

### Voice

- intelligible
- acceptable timing for gameplay use
- treat as lower-priority polish target

## Regeneration rules

Regenerate an asset when any of these change:

- prompt or style family
- backend
- seed
- duration/loop requirement
- target format/sample rate
- review notes requiring revision

## Replacement/override workflow

1. generate draft asset
2. review and mark `approved` or `revise`
3. if a manual replacement is preferred, keep provenance linking replacement to original request
4. document override in the future review/provenance manifest

## Loudness and QA targets

This repo already has QA utilities. Future automation should define explicit profiles such as:

- `music-loop`
- `music-sting`
- `ui-short`
- `combat-sfx`
- `ambient-loop`

Until those profiles are scripted, use the existing QA tools plus human listening review.
