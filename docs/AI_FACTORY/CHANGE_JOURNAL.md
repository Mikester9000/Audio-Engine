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
