# Change Journal

> Append a short entry for every substantial PR. Keep entries brief and factual.

## 2026-05-14 — Add AI-first documentation system for GitHub-native audio asset factory

- Added `docs/AI_FACTORY/` as the persistent mission/state/roadmap/handoff memory tree.
- Added subsystem, style, schema, QA, troubleshooting, Windows, and integration docs.
- Added `.github/copilot-instructions.md` to direct future AI contributors.
- Updated root README to point readers and agents at the new docs-first operating model.
- Confirmed repository baseline remained healthy with `pytest` and asset-manifest validation.

## Baseline before this PR

- Python package and CLI already existed.
- Procedural generation existed for music, SFX, and voice.
- Asset pipeline existed for `Game Engine for Teaching`.
- Asset-manifest documentation and validation workflow already existed.

## 2026-05-14 — Add implementation matrix, PR build sequence, codebase map, and factory input examples

- Added machine-guidance docs: `IMPLEMENTATION_MATRIX.md`, `NEXT_PR_SEQUENCE.md`, `CODEBASE_MAP.md`, `KNOWN_ISSUES.md`, and `STABILITY_RULES.md`.
- Added committed example artifacts for `GameRewritten` vertical-slice planning and request-driven workflows under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/`.
- Added machine-friendly continuity snapshot `FACTORY_STATUS.json`.
- Updated AI-factory indexes and continuity docs so future agents can distinguish implemented code from docs-only contracts and planned work.

## 2026-05-14 — Add session queue and autopilot control layer for AI agents

- Added `SESSION_QUEUE.md` as the canonical “what should I do next?” file for low-prompt continuation.
- Added `SESSION_TEMPLATE.md`, `DONE_CRITERIA.md`, `NO_DECISION_ZONES.md`, `TASK_OUTPUT_CONTRACTS.md`, `FILE_TOUCH_MATRIX.md`, `FAILSAFE_RULES.md`, and `PR_AUTOPILOT_CHECKLIST.md`.
- Added continuity tracking artifacts `SESSION_HISTORY.md` and `SESSION_STATE.json`.
- Updated repo entrypoints and workflow docs so future agents can execute one explicit session with less ambiguity and less improvisation.

## 2026-05-14 — Add final hardening layer for low-prompt AI execution

- Added `CURRENT_SESSION.json` so future agents can read the single active session contract mechanically without scraping markdown.
- Added `SESSION_GATE_RULES.md`, `BLOCKER_PROTOCOL.md`, `VERIFICATION_PROFILES.md`, and `MINIMUM_TEST_EXPANSION_RULES.md` to reduce false completion, under-testing, and blocker ambiguity.
- Added `CANONICAL_OUTPUT_LAYOUT.md`, `FULL_GAME_AUDIO_CHECKLIST.md`, and `HUMAN_COMMANDS.md` so future sessions target a stable output shape, full game-audio coverage, and a simple low-prompt interaction model.
- Updated AI-factory indexes, status JSON, session-control docs, and handoff/state docs to integrate the new hardening layer cleanly into the existing `docs/AI_FACTORY` system.

## 2026-05-14 — Complete SESSION-001 with typed audio-plan and request loaders

- Added `audio_engine/integration/factory_inputs.py` with typed dataclasses and JSON loaders for the committed audio-plan and generation-request example artifacts.
- Exported the new loader API from `audio_engine.integration` without changing existing CLI behavior.
- Added fixture-driven integration tests for successful plan/request ingestion plus an invalid-input failure path.
- Updated AI-factory continuity docs and session-control files to mark `SESSION-001` complete and advance the queue to `SESSION-002`.

## 2026-05-14 — Complete SESSION-002 with request-batch generation command

- Added `RequestBatchPipeline` class to `audio_engine/integration/asset_pipeline.py` with per-request seed execution, channel conversion, WAV/OGG export, and `batch_manifest.json` output.
- Added `generate-request-batch --batch-file <json> --output-dir <dir>` CLI command to `audio_engine/cli.py`.
- Exported `RequestBatchPipeline` from `audio_engine.integration`.
- Added 7 integration tests for `RequestBatchPipeline` (SFX smoke, manifest fields, seed verification, skip_existing, manifest JSON, music batch, progress callback).
- Added 5 CLI tests for `generate-request-batch` (subcommand presence, SFX smoke, missing file, quiet, manifest written).
- Smoke-ran both committed fixtures: 5 SFX and 4 music files produced with seeds 305001–305045 and 204801–204834 respectively.
- Test count: 334 passed (up from 321).

## 2026-05-14 — Complete SESSION-003 with per-request provenance sidecar files

- Added `_write_provenance()` method to `RequestBatchPipeline` in `audio_engine/integration/asset_pipeline.py`.
- Each successful generation now writes a `<stem>.provenance.json` sidecar alongside the audio file, containing: `provenanceVersion`, `requestId`, `assetId`, `type`, `backend`, `seed`, `prompt`, `styleFamily`, `generatedOutputPath`, `targetImportPath`, `reviewStatus`, `generatedAt`.
- Added 5 new tests: provenance files written, required fields present, seed matches request, not written for skipped files.
- Test count: 338 passed (up from 334).



## 2026-05-14 — Complete SESSION-004 with batch QA gate command

- Extracted `_load_wav_array()` helper from `_cmd_qa` in `audio_engine/cli.py` to avoid duplication.
- Added `qa-batch --input-dir <dir> [--output-report <path>] [--check-loop] [--recursive] [--quiet]` CLI command that runs `LoudnessMeter`, `ClippingDetector`, and optionally `LoopAnalyzer` on all WAV files in a directory.
- The command writes a machine-readable JSON report with `qaBatchVersion`, `inputDir`, `generatedAt`, `summary` (total/passed/failed), and per-file `results` with `file`, `status`, and `checks`.
- Returns non-zero if any file fails QA checks; returns 0 if all pass.
- Added 7 new CLI tests covering: subcommand presence, valid audio pass, silent audio fail, JSON report output, required check keys, missing directory, quiet flag.
- Smoke run: 5 SFX files checked; 4 pass, 1 fail (`sfx_ui_cancel.wav` at −6.37 LUFS exceeds −9.0 ceiling).
- Test count: 345 passed (up from 338).
