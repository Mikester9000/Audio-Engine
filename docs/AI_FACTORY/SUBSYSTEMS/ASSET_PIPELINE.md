# Asset Pipeline Status

## What exists now

- `AssetPipeline` can generate `music/`, `sfx/`, and `voice/` directories plus `manifest.json`
- current generation map is defined in `audio_engine/integration/game_state_map.py`
- CLI supports `generate-game-assets` and `verify-game-assets`
- committed plan/request/review example artifacts now exist under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/`
- typed loader code for the committed audio plan and music/SFX request fixtures now exists in `audio_engine/integration/factory_inputs.py`
- the canonical current execution target is `SESSION-002` in `docs/AI_FACTORY/SESSION_QUEUE.md`

## Current constraint

The existing pipeline is still specialized toward the current integration target and is not yet a general asset-factory orchestration system that can execute the newly loaded plan/request artifacts directly.

## Missing capabilities

- request-batch execution from the committed generation-request fixtures
- provenance capture per output asset
- approval/replacement workflow
- generalized export targets for `GameRewritten`

## Near-term goal

Evolve the current `AssetPipeline` from a fixed mapping generator into a plan-driven batch system without losing the existing simple CLI path. The next step is to execute the new typed request loaders through an additive deterministic batch-generation command.
