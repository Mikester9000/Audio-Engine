# Asset Pipeline Status

## What exists now

- `AssetPipeline` can generate `music/`, `sfx/`, and `voice/` directories plus `manifest.json`
- current generation map is defined in `audio_engine/integration/game_state_map.py`
- CLI supports `generate-game-assets` and `verify-game-assets`
- committed plan/request/review example artifacts now exist under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/`
- typed loader code for the committed audio plan and music/SFX request fixtures now exists in `audio_engine/integration/factory_inputs.py`
- `RequestBatchPipeline` now exists in `audio_engine/integration/asset_pipeline.py`, executing any `GenerationRequestBatch` deterministically with per-request seeds; outputs land in `<output_dir>/drafts/<type>/`
- CLI supports `generate-request-batch --batch-file <json> --output-dir <dir>` for factory-driven generation

## Current constraint

The existing pipeline has two modes: the legacy fixed-map `AssetPipeline` for the Game Engine for Teaching, and the new plan/request-driven `RequestBatchPipeline`. Provenance logs beyond the `batch_manifest.json` summary are not yet written per request.

## Missing capabilities

- provenance capture per output asset (request ID + seed + review status written per file)
- approval/replacement workflow
- generalized export targets for `GameRewritten`
- automated QA gate for generated output sets

## Near-term goal

Add per-request provenance/review logs (`SESSION-003`) so every generated file is traceable to its request ID, seed, and review state.
