# Music Subsystem Status

## What exists now

- style-based generation through `AudioEngine.generate_track()`
- prompt-driven generation through `MusicGen`
- mastering through `OfflineBounce`
- CLI access through `generate` and `generate-music`
- backend selection/discovery surfaces through `generate-music --backend` and `list-backends`
- existing integration mapping for multiple game states in `audio_engine/integration/game_state_map.py`

## What is missing

- per-target duration enforcement from plan metadata in execution paths
- richer style-preset registry beyond current built-in styles
- verified non-procedural backend quality benchmarks using real downloaded model weights

## Backend evaluation notes (SESSION-011 + optional neural scaffolding)

- **Current implemented backend reality:** `procedural` remains the default backend, with optional local-files-only neural adapters now available in `audio_engine/ai/backends/` (`musicgen`, `audiogen`, `kokoro`) when dependencies and local model folders are present.
- **Current selection/discovery surfaces:** users can list registered backends with `audio-engine list-backends` and select one with `--backend` on music/SFX/voice generation commands.
- **Current executable evaluation surface:** `BackendRegistry.evaluate_backends()` now reports backend availability, availability reason, dependency summary, and supported modalities; `audio-engine list-backends` prints this metadata.
- **Availability behavior:** backend availability is dependency-driven (`is_available()`); missing runtime dependencies should be treated as unavailable/failing execution rather than as quality regressions.
- **Future local/open backend guidance (docs, not implementation):**
  - acceptable adapter families include local ONNX-runtime wrappers, ggml/llama.cpp-style local wrappers, or local-files-only Hugging Face adapters
  - evaluate by deterministic reproducibility, dependency footprint, and command-line operability first
  - do not claim production quality or parity with commercial systems until implemented and verified in this repo

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
  `--music-duration 180` (or higher, up to 300 s / 5 min), or use
  plan-driven orchestration where `durationTargetSeconds` is enforced per
  target. The `--batch-file` path still does not consume an explicit
  per-request duration field.

## Near-term goals

1. define canonical music categories for downstream projects
2. capture prompt + seed + target path in request manifests
3. define loop and loudness acceptance profiles per category
4. add long-form OST variant support to example request fixtures
