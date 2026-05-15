# Canonical Output Layout

> Target output contract for the audio factory as it matures. This file defines the desired destination layout for practical game-audio production. It is a planning/control document, not a claim that the full layout already exists in code.

## Why this file exists

Future agents need one stable answer to: “where should generated audio, approved audio, and provenance/review data live?”

## Output layout goals

1. separate draft generation from approved downstream-ready assets
2. keep provenance and review state machine-readable
3. use stable asset-family-first paths
4. support practical game formats such as WAV and OGG
5. preserve deterministic seed/request identity when assets are regenerated

## Canonical factory layout

```text
<factory_output_root>/
├── drafts/
│   ├── music/
│   ├── fanfares_stingers/
│   ├── sfx/
│   ├── ambience/
│   └── voice/
├── approved/
│   ├── music/
│   ├── fanfares_stingers/
│   ├── sfx/
│   ├── ambience/
│   └── voice/
├── provenance/
│   ├── requests/
│   ├── generation_logs/
│   └── review_logs/
└── exports/
    └── gamerewritten/
        └── Content/
            └── Audio/
```

## Directory meanings

### `drafts/`

- first-pass generated outputs
- safe place for iterative regeneration
- should not be treated as final downstream content automatically

### `approved/`

- assets explicitly marked acceptable for downstream use
- may still be regenerated later, but current approved selection should stay stable

### `provenance/requests/`

- input audio plans and generation request manifests used to create outputs

### `provenance/generation_logs/`

- machine-readable request ID, seed, backend, output path, and timestamp linkage

### `provenance/review_logs/`

- machine-readable review status such as `draft`, `approved`, `revise`, or `rejected`

### `exports/gamerewritten/Content/Audio/`

- downstream-ready export surface for `GameRewritten`
- preserve any required downstream filenames even if internal draft/provenance paths are richer

## Naming rules

Use stable searchable names:

```text
<family>/<asset_id>__<variant>__seed<seed>.<ext>
```

Examples:

```text
music/bgm_field_day__base__seed0042.ogg
fanfares_stingers/fanfare_victory_short__base__seed0042.ogg
sfx/ui_confirm__base__seed1337.wav
ambience/amb_forest_day__loop_a__seed0210.ogg
voice/npc_shopkeeper_greeting__take01__seed0007.wav
```

## Family layout expectations

| Family | Typical contents | Preferred working format | Common downstream format |
|---|---|---|---|
| `music/` | loops, state themes, layered BGM, long-form OST variants | `wav` or `ogg` | often `ogg`, sometimes `wav` |
| `fanfares_stingers/` | victory, level-up, save, discovery cues | `wav` or `ogg` | `ogg` or `wav` |
| `sfx/` | UI, combat, spells, pickups, impacts, footsteps | `wav` | usually `wav` |
| `ambience/` | weather, room tone, biome loops, transitions | `wav` or `ogg` | often `ogg` |
| `voice/` | placeholder narration, barks, callouts | `wav` | format depends on downstream need |

## Music duration expectations

Different music sub-types have different appropriate durations.  This is the
canonical reference for agents generating or reviewing music assets:

| Music sub-type | Loop | Target duration | Notes |
|---|---|---|---|
| Major themes (title, ending, credits) | optional | 120–300 s | Full-length pieces; qualify as long-form game audio |
| Gameplay BGM (field, town, dungeon, combat) | **yes** | 60–120 s | Must loop cleanly at a natural loop point |
| Boss battle BGM | **yes** | 90–180 s | Longer loops preferred for sustained engagement |
| Story cutscene underscore | no | 30–120 s | Non-loopable; matches scene length |
| Stingers and fanfares | no | 2–12 s | Short punchy reward / event cues |
| Save / level-up cues | no | 2–8 s | Very short; a few seconds maximum |
| UI / system cues | no | 0.1–2 s | As short as possible; never loopable |

### Long-form OST variants

For key in-game BGM loops, a corresponding longer **OST-style variant** may be
generated or planned alongside the gameplay loop.  The OST variant:

- uses an `_ost` suffix (e.g. `bgm_field_day_ost.ogg`) and is stored in the
  same `music/` sub-directory
- targets 120–300 s (up to 5 minutes) from the same seed and prompt
- is not required for game functionality but supports soundtrack releases
- should be noted in the `audio_plan.*.json` with
  `"gameplayRole": "ost-variant"` and `"loop": false`

## Practical format rules

1. **WAV is the safe default working/master format.**
2. **OGG is preferred when looped music/ambience size matters and downstream supports it.**
3. Keep sample-rate/channel/export requirements explicit in request/provenance data once those paths are implemented.
4. Do not assume voice deserves the same polish priority as music/SFX unless a session is explicitly voice-focused.

## Current implementation note

Current code already exports WAV and optional OGG and already emits organized asset batches, but it does **not** yet implement this full draft/approved/provenance/export directory contract end-to-end.
