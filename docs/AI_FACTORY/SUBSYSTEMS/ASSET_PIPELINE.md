# Asset Pipeline Status

## What exists now

- `AssetPipeline` can generate `music/`, `sfx/`, and `voice/` directories plus `manifest.json`
- current generation map is defined in `audio_engine/integration/game_state_map.py`
- CLI supports `generate-game-assets` and `verify-game-assets`
- committed plan/request/review example artifacts now exist under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/`
- the canonical current execution target is `SESSION-001` in `docs/AI_FACTORY/SESSION_QUEUE.md`

## Current constraint

The existing pipeline is specialized toward the current integration target and is not yet a general asset-factory orchestration system.

## Missing capabilities

- request-manifest ingestion
- project-plan ingestion
- provenance capture per output asset
- approval/replacement workflow
- generalized export targets for `GameRewritten`

## Near-term goal

Evolve the current `AssetPipeline` from a fixed mapping generator into a plan-driven batch system without losing the existing simple CLI path. The session-control docs should remain the execution guide while this transition happens.
