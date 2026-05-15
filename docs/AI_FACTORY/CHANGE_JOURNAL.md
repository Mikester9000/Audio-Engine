# Change Journal

> Append a short entry for every substantial PR. Keep entries brief and factual.

## 2026-05-14 — SESSION-002: Add request-batch generation command

- Added `RequestBatchRecord` and `RequestBatchResult` dataclasses to `audio_engine/integration/asset_pipeline.py`.
- Added `AssetPipeline.execute_request_batch()` with private helpers `_execute_music_request()`, `_execute_sfx_request()`, and `_execute_voice_request()` that pass per-request seeds explicitly.
- Added `generate-request-batch` CLI command (`audio_engine/cli.py`) with `--request-file`, `--output-dir`, `--force`, `--quiet`, `--music-duration`, `--sfx-duration`, `--write-result` flags.
- Exported `RequestBatchRecord` and `RequestBatchResult` from `audio_engine/integration/__init__.py`.
- Added `TestRequestBatchExecution` class (7 tests) to `tests/test_integration.py` using committed vertical-slice fixtures.
- Added 4 CLI tests for `generate-request-batch` to `tests/test_engine_cli.py`.
- Smoke run: SFX fixture 5/5 OK (seeds 305001–305045 explicit in result JSON); WAV music stinger OK; OGG music requests report graceful errors (optional `soundfile` dep not installed in this environment).
- Test suite: 332 passed (up from 321).



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

## 2026-05-14 — Complete SESSION-005 with GameRewritten export profile

- Added `DraftExportPipeline` class to `audio_engine/integration/asset_pipeline.py` that copies draft audio files to `<factory_root>/exports/gamerewritten/Content/Audio/` using `targetImportPath` from `.provenance.json` sidecars as the downstream filename.
- Exported `DraftExportPipeline` from `audio_engine.integration`.
- Added `export-drafts --output-dir <factory_root>` CLI command to `audio_engine/cli.py`.
- Added 7 integration tests for `DraftExportPipeline` (files created, provenance names used, manifest written, manifest fields, drafts not modified, ValueError on empty drafts, fallback without provenance).
- Added 3 CLI tests for `export-drafts` (subcommand registered, missing dir fails, smoke).
- Smoke run: 5 SFX files from `/tmp/session003_smoke/drafts/sfx/` exported to `/tmp/session003_smoke/exports/gamerewritten/Content/Audio/` using stable `targetImportPath` filenames.
- Test count: 355 passed (up from 345).

## 2026-05-15 — Complete SESSION-006 (approval workflow) + SESSION-007 (CI QA gate) + music-duration policy

### SESSION-006 — Add approval workflow

- Added `ApprovalWorkflow` class to `audio_engine/integration/asset_pipeline.py` with `approve()` (single file) and `approve_batch()` (multiple files) methods.
- `approve()` copies the audio file to `<factory_root>/approved/<type>/`, reads or synthesises the `.provenance.json` sidecar, updates `reviewStatus` to `"approved"`, adds `approvedAt` timestamp and `approvedPath`, and writes updated provenance to both the approved directory and the original draft location.
- Added `approve-draft --factory-root <dir> --draft-file <path> [--output-report <path>] [--quiet]` CLI command.
- Exported `ApprovalWorkflow` from `audio_engine.integration`.
- Added 13 new integration tests covering: file copy, approved directory placement, provenance update in approved and draft locations, required record fields, FileNotFoundError on missing file, ValueError on unsupported extension, fallback without provenance sidecar, `approve_batch` multi-file, `approve_batch` error recording, CLI approval, CLI report output, CLI missing file.
- Test count: 383 passed (up from 370).

### SESSION-007 — Wire qa-batch into CI

- Added `.github/workflows/audio-qa.yml` that triggers on push/PR to `audio_engine/**`, `tests/**`, `docs/AI_FACTORY/EXAMPLES/**`, and the workflow file itself.
- The workflow: installs the package, runs `pytest`, generates the committed SFX fixture to `/tmp/ci_qa_batch`, and runs `qa-batch` over the output; fails the CI step if any file fails loudness/peak/clipping checks.

### Music-duration policy

- Updated `docs/AI_FACTORY/SUBSYSTEMS/MUSIC.md` with a canonical music duration table (major themes 120–300 s, gameplay BGM 60–120 s, boss loops 90–180 s, stingers/fanfares 2–12 s, UI cues <2 s) and long-form OST support policy.
- Updated `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md` with music duration expectations table and OST variant guidance.
- Updated `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md` with a duration key and duration annotations for every music checklist item; marked key BGM tracks `+ost`.
- Updated `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json` with a `musicDurationPolicy` section and `ostVariant` entries for `bgm_field_day`, `bgm_town_evening`, `bgm_battle_standard`, and `bgm_boss_phase1`; boss target raised from 90 s to 120 s.

## 2026-05-15 — Complete SESSION-008 (taxonomy coverage expansion)

- Expanded `audio_plan.vertical_slice.v1.json` taxonomy coverage with additive groups/targets for fanfares/stingers, expanded UI/combat/spell SFX, ambience loops, tension/sadness music, and optional voice placeholders.
- Added missing `ostVariant` for `bgm_dungeon_ruins` in the committed plan to match `+ost` checklist intent for key BGM loops.
- Expanded `generation_requests.music.v1.json` from 4 to 13 requests, including base + OST entries for key BGM tracks (`field`, `town`, `dungeon`, `battle`, `boss`) plus tension/sadness cues.
- Expanded `generation_requests.sfx.v1.json` from 5 to 10 requests with additional UI/combat/spell/ambience taxonomy coverage.
- Added new optional fixture `generation_requests.voice.v1.json` with placeholder voice requests to track low-priority voice scope explicitly.
- Updated loader fixture tests in `tests/test_integration.py` to match expanded fixture counts and include the voice fixture.
- Updated continuity/session-control docs (`CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, `SESSION_QUEUE.md`, `SESSION_STATE.json`, `CURRENT_SESSION.json`, `SESSION_HISTORY.md`, `IMPLEMENTATION_MATRIX.md`, `TASKS/BACKLOG.md`) and advanced the queue to `SESSION-009`.

## 2026-05-15 — Complete SESSION-009 (plan-driven orchestration) + SESSION-010 (backend support expansion)

- Added `PlanBatchOrchestrator` to `audio_engine/integration/asset_pipeline.py` and exported it through `audio_engine.integration`.
- Added `generate-plan-batch` CLI command to execute one audio plan against one or more request-batch files while preserving existing `generate-request-batch` compatibility.
- Plan-driven orchestration now validates required-target coverage and enforces plan/request consistency for type, `targetPath`, and output format.
- Removed OGG fallback-to-WAV behavior from `RequestBatchPipeline`; requested `.ogg` outputs must be produced, otherwise the request is recorded as an error.
- Updated `RequestBatchPipeline` to honor per-request `backend` for music, SFX, and voice generation.
- Added backend discovery/selection surfaces in CLI:
  - new `list-backends` command
  - `--backend` support on `generate-music`, `generate-sfx`, and `generate-voice`
- Expanded fixture coverage by adding required fanfare requests to `generation_requests.music.v1.json` (now 15 music requests).
- Added integration and CLI tests for:
  - plan-driven orchestration
  - strict OGG failure behavior when encoder support is unavailable
  - backend handling in request-batch execution
  - new CLI subcommands/options
- Verification:
  - `python -m pytest` → 399 passed
  - `python tools/validate-assets.py assets/examples/ --verbose` → PASS
  - deterministic `/tmp` smoke run with `generate-plan-batch` produced requested `.ogg` output after installing `soundfile`.

## 2026-05-15 — Complete SESSION-011 (backend evaluation notes) + SESSION-012 (SFX variation strategy docs)

- Added backend evaluation and dependency/availability guidance in:
  - `docs/AI_FACTORY/SUBSYSTEMS/MUSIC.md`
  - `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md`
- Added deterministic repeated-SFX variation strategy guidance in:
  - `docs/AI_FACTORY/SUBSYSTEMS/SFX.md`
  - `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md`
- Clarified docs-contract boundaries (truthful current implementation vs future adapter/runtime behavior) to avoid overclaiming.
- Updated continuity and session-control docs to mark `SESSION-011` and `SESSION-012` completed and advance current session to `SESSION-013`.
- Synced queue/state/history/handoff surfaces: `SESSION_QUEUE.md`, `SESSION_STATE.json`, `CURRENT_SESSION.json`, `SESSION_HISTORY.md`, `ACTIVE_WORK.md`, `CURRENT_STATE.md`, `HANDOFF.md`, `IMPLEMENTATION_MATRIX.md`.
- Verification:
  - `pip install -e ".[dev]"` → PASS
  - `python -m pytest` → 400 passed
  - `python tools/validate-assets.py assets/examples/ --verbose` → PASS
  - `python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json` → PASS
  - `python -m json.tool docs/AI_FACTORY/SESSION_STATE.json` → PASS

## 2026-05-15 — Implement executable SESSION-011/012 behavior (backend evaluation + SFX variation enforcement)

- Implemented executable backend evaluation metadata in `audio_engine/ai/backend.py` via `BackendRegistry.evaluate_backends()`:
  - backend availability status
  - availability reason
  - dependency summary
  - supported modalities
- Updated `audio-engine list-backends` (`audio_engine/cli.py`) to surface the executable evaluation metadata in CLI output.
- Implemented repeated-SFX variation enforcement in `audio_engine/integration/factory_inputs.py`:
  - repeated family detection for SFX requests
  - required `_varNN` variant suffixes on `assetId`, `requestId`, and output filename stem
  - aligned/contiguous variant indices per family
  - distinct deterministic seeds per family
- Extended SFX provenance in `audio_engine/integration/asset_pipeline.py`:
  - `variationFamily`
  - `variationIndex`
- Added test coverage in:
  - `tests/test_ai_pipeline.py` (backend evaluation metadata)
  - `tests/test_engine_cli.py` (`list-backends` enriched output)
  - `tests/test_integration.py` (variant-family parse validation and variant provenance fields)
- Updated continuity and subsystem/schema docs to reflect that SESSION-011/012 now have executable code paths, not docs-only status.
- Verification:
  - `python -m pytest tests/test_ai_pipeline.py tests/test_engine_cli.py tests/test_integration.py` → 200 passed
  - `python -m pytest` → 404 passed
  - `python tools/validate-assets.py assets/examples/ --verbose` → PASS


## 2026-05-15 — Complete SESSION-013 + SESSION-014 (docs-only SFX QA target + variant-family review template updates)

- Updated `docs/AI_FACTORY/SUBSYSTEMS/SFX.md` with category-specific SFX/ambience loudness-readability guidance mapped to existing acceptance profiles (`sfx-ui`, `sfx-combat`, `sfx-magic`, `ambience-loop`).
- Updated `docs/AI_FACTORY/QA/QUALITY_BARS.md` to explicitly separate current executable QA checks from additive category guidance used during review.
- Updated `docs/AI_FACTORY/QA/REVIEW_WORKFLOW.md` with a two-level repeated-SFX review model (per-asset entry + per-family decision entry).
- Updated `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json` to v1.1.0 with variant-aware review entries, optional QA snapshots, and `variantFamilyDecisions` examples.
- Updated `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md` with acceptance-profile alignment notes for category guidance/review consistency.
- Synced continuity/session-control docs for SESSION-013 and SESSION-014 completion and advanced queue/state/current session to SESSION-015.
- Verification:
  - `python -m json.tool docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json` → PASS
  - `python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json` → PASS
  - `python -m json.tool docs/AI_FACTORY/SESSION_STATE.json` → PASS
