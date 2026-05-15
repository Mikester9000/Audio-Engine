# Music Subsystem Status

## What exists now

- style-based generation through `AudioEngine.generate_track()`
- prompt-driven generation through `MusicGen`
- mastering through `OfflineBounce`
- CLI access through `generate` and `generate-music`
- existing integration mapping for multiple game states in `audio_engine/integration/game_state_map.py`

## What is missing

- project-level plan-driven music generation
- explicit review status tracking per music asset
- richer style-preset registry beyond current built-in styles
- `GameRewritten`-specific music backlog committed in this repo

## Music duration policy

Different music asset categories have different appropriate duration targets.
This table is the canonical reference for agents and contributors:

| Category | Loop required | Duration target | Notes |
|---|---|---|---|
| Major themes (title, ending, credits) | optional | 120–300 s (up to 5 min) | Full-length game-ready pieces; may also have a shorter in-game loop variant |
| Gameplay BGM (field, town, dungeon, combat) | yes | 60–120 s | Loopable at a natural loop point |
| Boss battle | yes | 90–180 s | Complex structure; longer loop is preferred |
| Story cutscene / underscore | no | 30–120 s | Matches scene length; no loop point required |
| Tension / stealth | yes | 30–90 s | Minimal, atmospheric |
| Stingers and fanfares | no | 2–12 s | Short, punchy; must not be loopable |
| Save / level-up cues | no | 2–8 s | Very short reward signals |
| UI / system cues | no | 0.1–2 s | As short as possible |

### Long-form OST support policy

For shorter in-game gameplay tracks (BGM loops of 60–120 s), the factory
**should plan or generate a corresponding longer OST-style version** (120–300 s)
when that asset is important enough for a soundtrack release.  The OST version:

- is not required for game functionality
- is stored alongside the in-game loop under a clear `_ost` suffix (e.g.
  `bgm_field_day_ost.ogg`)
- may be generated from the same seed and prompt with a longer `duration`
  parameter
- should be noted in the `audio_plan.*.json` alongside the in-game request

### Default generation-request durations

When generating via `generate-request-batch`:

- Music requests with no explicit duration default to **30 s**.
- The `--music-duration` CLI flag only applies to the `--request-file` /
  `execute_request_batch` path; it is **ignored** by the `--batch-file` /
  `RequestBatchPipeline` path, which calls `MusicGen.generate()` directly
  without a duration override.
- For long-form OST variants, use the `--request-file` path with
  `--music-duration 180` (or higher, up to 300 s / 5 min), or embed
  `durationTargetSeconds` in a future plan-driven pipeline.  The `--batch-file`
  path does not yet consume this option.

## Near-term goals

1. define canonical music categories for downstream projects
2. capture prompt + seed + target path in request manifests
3. define loop and loudness acceptance profiles per category
4. add long-form OST variant support to example request fixtures
