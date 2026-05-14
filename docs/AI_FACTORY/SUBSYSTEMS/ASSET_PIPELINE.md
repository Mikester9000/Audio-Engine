# Asset Pipeline Status

## What exists now

- `AssetPipeline` can generate `music/`, `sfx/`, and `voice/` directories plus `manifest.json` from the fixed game-state map.
- `AssetPipeline.execute_request_batch()` executes a `GenerationRequestBatch` (loaded from a factory JSON fixture) using per-request seeds explicitly, writing outputs to `output_dir / request.output.targetPath`.
- `RequestBatchRecord` and `RequestBatchResult` provide machine-readable per-request execution records with status, seed, and output path.
- CLI supports `generate-game-assets`, `verify-game-assets`, and `generate-request-batch`.
- `generate-request-batch` flags: `--request-file`, `--output-dir`, `--force`, `--quiet`, `--music-duration`, `--sfx-duration`, `--write-result`.
- Committed plan/request/review example artifacts exist under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/`.
- Typed loader code for the committed audio plan and music/SFX request fixtures exists in `audio_engine/integration/factory_inputs.py`.

## Request-batch execution details

- Each request carries its own `seed` field; this is passed explicitly to the generator (not inherited from pipeline-level defaults).
- Output path: `output_dir / request.output.targetPath` — parent directories created automatically.
- Duration defaults: 30 s for music, 2 s for SFX (overridable via `--music-duration`, `--sfx-duration`).
- OGG export requires the optional `soundfile` dep (`pip install audio-engine[ogg]`); graceful per-request errors without it.
- `--write-result` writes `request_batch_result.json` to `output_dir` for downstream provenance use.

## Remaining gaps

- No provenance log persisted per output asset (planned for SESSION-003).
- No automated QA gate over generated outputs (planned for SESSION-004).
- No generalized export targets for `GameRewritten`.
- No approval/replacement workflow.

## Near-term goal

Add per-request provenance log writing (SESSION-003) so each generated asset has a machine-readable record linking it to its request ID, seed, output path, and review status.
