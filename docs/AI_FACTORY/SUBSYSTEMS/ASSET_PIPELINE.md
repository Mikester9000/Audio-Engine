# Asset Pipeline Status

## What exists now

- Legacy fixed-map generation remains available via `AssetPipeline.generate_*` and CLI:
  - `generate-game-assets`
  - `verify-game-assets`
- Request-driven generation is implemented via `RequestBatchPipeline` and CLI:
  - `generate-request-batch --batch-file ...`
- Plan-driven orchestration is implemented via `PlanBatchOrchestrator` and CLI:
  - `generate-plan-batch --plan-file ... --request-file ...`
  - plan targets select and order executable requests; missing required plan targets fail execution
- Per-request provenance sidecars are written for successful draft outputs:
  - `<stem>.provenance.json` with request ID, asset ID, backend, seed, prompt, output path, import path, review status, and timestamp
- QA/export/approval workflow is implemented end-to-end:
  - `qa-batch`
  - `export-drafts`
  - `approve-draft`
- Deterministic remaster workflows are now executable:
  - `audio-engine remaster --input <wav> --samples-dir <dir> --events-json <events.json> --output <wav>`
  - `audio-engine remaster-batch --input-dir <dir> --output-dir <dir> --samples-dir <dir>`
  - `RemasterBatchPipeline` writes machine-readable `remaster_batch_result.json`
- Machine-readable review-log writing is executable:
  - `write-review-log`
  - optional review-log update flags on `approve-draft` and `export-drafts`
  - review entries are sourced from provenance sidecars and can optionally include `qa-batch` snapshot fields
  - `write-review-log --from-result <request_batch_result.json>` can source entries from legacy request-file execution results
- Legacy request-file execution now writes additive manifest parity output:
  - `generate-request-batch --request-file ...` writes `<output_dir>/batch_manifest.json`
  - manifest records keep deterministic per-request metadata (`request_id`, `asset_id`, `type`, `seed`, `file`, `status`)
  - existing `request_batch_result.json` output behavior is unchanged and remains optional via `--write-result`
- Request format behavior is strict:
  - requested `.ogg` outputs must be produced as `.ogg`
  - no silent OGG→WAV fallback in request-batch execution paths

## Current constraints

- Plan-driven execution requires request batches that contain executable entries for all required plan targets.
- Plan-driven execution now enforces per-target plan durations (`durationTargetSeconds`) by forwarding them as per-request duration overrides in request execution.
- Both request-batch execution entrypoints now support additive optional request-level `durationSeconds` for explicit music/SFX durations without requiring a plan file:
  - `generate-request-batch --batch-file` (`RequestBatchPipeline`)
  - backward-compatible `generate-request-batch --request-file` (`AssetPipeline.execute_request_batch`)
- On the legacy `--request-file` path, `--music-duration` and `--sfx-duration` remain fallback defaults for requests that omit `durationSeconds`.
- On the legacy `--request-file` path, provenance sidecars are now additive/optional via `generate-request-batch --write-provenance`; result records include `provenance_path` when written.
- On the legacy `--request-file` path, manifest parity is now additive and always written to `<output_dir>/batch_manifest.json`.
- OGG export depends on `soundfile`; if unavailable, requests that specify `.ogg` fail.
- Event-driven remaster note substitution requires instrument note files under `samples/orchestral/<instrument>/` that include note names in filenames (for example `violin_C4.wav`).

## Near-term goal

Add the license compliance CI gate (SESSION-032) while preserving additive compatibility across existing generation and remaster command surfaces.
