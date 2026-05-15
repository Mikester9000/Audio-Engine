# Quality Bars and Asset Rules

> Update this file whenever naming, export, review, or acceptance criteria change.

## Current export reality

Current code supports WAV export by default and optional OGG export with extra dependency support.

## File organization rule

Generated assets should be organized by gameplay function first, not by implementation detail.

For the long-term factory directory contract, use `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md` as the canonical reference.

### Current batch layout

```text
<output_dir>/
├── music/
├── sfx/
├── voice/
└── manifest.json
```

### Target extended layout

> **Superseded by `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`.** The category folders below (`music/`, `sfx/`, etc.) are still valid sub-directories; they now live inside the `drafts/`, `approved/`, `provenance/`, and `exports/` top-level layers defined in the canonical layout. Do not use this flat structure as the authoritative target; defer to `CANONICAL_OUTPUT_LAYOUT.md` instead.

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

### Current executable checks (already implemented)

- `qa` / `qa-batch` use a global loudness pass band: **-30.0 to -9.0 LUFS** (`loudness_ok`).
- True peak check is **≤ -0.1 dBFS** (`peak_ok`).
- Clipping must be absent (`clipping_ok`).
- Loop seam checks are optional and only evaluated when `--check-loop` is requested (`loop_ok`).

### Category-specific SFX/ambience guidance (SESSION-013)

These guidance ranges are for consistent review decisions and variant-family comparisons. They are **not** additional automated gates in current code.

| Acceptance profile (request `qa.acceptanceProfile`) | Guidance loudness range | Readability/review emphasis |
|---|---|---|
| `sfx-ui` | `-22` to `-14` LUFS | Immediate click/chirp readability, short tail, low fatigue under repetition |
| `sfx-combat` | `-18` to `-10` LUFS | Impact-first transient, retains cut-through in dense gameplay mix |
| `sfx-magic` | `-20` to `-12` LUFS | Element identity clarity, controlled spectral tail, avoids masking |
| `ambience-loop` | `-28` to `-18` LUFS | Stable bed texture, low distraction, seamless loop behavior |

### How to apply with existing reports

1. Run `qa` or `qa-batch` exactly as today.
2. Use report fields (`loudness_lufs`, `true_peak_dbfs`, `loudness_ok`, `peak_ok`, `clipping_ok`, optional `loop_ok`) as the objective baseline.
3. Apply category guidance and listening notes during review-log decisions (`approved`/`revise`/`rejected`).
4. For repeated-variant families, compare members against each other for readability separation and fatigue risk before approval.
