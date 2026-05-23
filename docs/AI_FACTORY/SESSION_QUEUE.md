# Session Queue

> Canonical next-session controller for AI agents. If a user says **"complete next session"**, execute the top-most session in this file whose status is `ready`.

## How to use this file

1. Read this file before choosing work.
2. Only execute the top-most `ready` session unless the user explicitly overrides the queue.
3. Treat `NEXT_PR_SEQUENCE.md` as the longer-range roadmap and this file as the single-session execution controller.
4. Treat `CURRENT_SESSION.json` as the detailed machine-readable companion to this file for the single active session.
5. Before marking work done, satisfy `SESSION_GATE_RULES.md` and the relevant profile in `VERIFICATION_PROFILES.md`.
6. If the current session becomes blocked or partially completed, update this file, `HANDOFF.md`, `SESSION_STATE.json`, and `CURRENT_SESSION.json` in the same PR.
7. If facts are missing, follow `BLOCKER_PROTOCOL.md` and `FAILSAFE_RULES.md` instead of improvising.

## Recently completed sessions

### SESSION-001 — Implement audio plan + request loading primitives
- **Status:** `completed`
- Typed loader code in `audio_engine/integration/factory_inputs.py`.

### SESSION-002 — Add request-batch generation command
- **Status:** `completed`
- `RequestBatchPipeline` + `generate-request-batch` CLI; 13 new tests; 334 total.

### SESSION-003 — Write provenance + review logs per request
- **Status:** `completed`
- `.provenance.json` sidecars per generated file; 5 new tests; 338 total.

### SESSION-004 — Add batch QA gate command for generated outputs
- **Status:** `completed`
- `qa-batch` CLI with JSON report; 7 new tests; 345 total.

### SESSION-005 — Implement GameRewritten export profile
- **Status:** `completed`
- `DraftExportPipeline` + `export-drafts` CLI; 10 new tests; 370 total.
- Exports `drafts/` audio to `exports/gamerewritten/Content/Audio/` using `targetImportPath` from provenance sidecars.

### SESSION-006 — Add approval workflow (promote drafts to approved/)
- **Status:** `completed`
- `ApprovalWorkflow` + `approve-draft` CLI; 13 new tests; 383 total.
- `approve-draft --factory-root <dir> --draft-file <path>` copies audio to `approved/<type>/`, updates provenance `reviewStatus` to `"approved"`, writes `approvedAt` timestamp.

### SESSION-007 — Wire qa-batch into CI
- **Status:** `completed`
- `.github/workflows/audio-qa.yml` added; triggers on push/PR to audio source and fixture files.
- Generates SFX batch from committed fixture then runs `qa-batch`; fails CI if any file fails loudness/peak/clipping checks.

### SESSION-008 — Expand full-game taxonomy coverage
- **Status:** `completed`
- Expanded committed example fixtures across music/SFX/ambience/optional voice taxonomy coverage.
- Added long-form OST request entries for key BGM loops (`field`, `town`, `dungeon`, `battle`, `boss`) plus tension/sadness music entries.

### SESSION-009 — Add plan-driven batch orchestration
- **Status:** `completed`
- Added `PlanBatchOrchestrator` + `generate-plan-batch` CLI path to drive deterministic request execution from `audio_plan.*.json` targets.
- Required plan targets now map to request batches with strict type/path/format matching, and execution routes through existing `RequestBatchPipeline` provenance/drafts surfaces.
- Removed OGG fallback-to-WAV behavior in `RequestBatchPipeline`: requested `.ogg` outputs must be produced or the request fails.

### SESSION-010 — Expand neural backend support
- **Status:** `completed`
- Request-batch generation now respects per-request `backend` for music/SFX/voice in `RequestBatchPipeline`.
- Added backend discoverability via `list-backends` CLI and backend selection flags (`--backend`) on `generate-music`, `generate-sfx`, and `generate-voice`.
- Added coverage tests for invalid-backend handling through request-batch execution paths.

### SESSION-011 — Add backend evaluation notes
- **Status:** `completed`
- **Task type:** `cli`
- Added executable backend evaluation metadata in `BackendRegistry.evaluate_backends()` and surfaced dependency/modality evaluation output in `audio-engine list-backends`.
- Preserved truthful current backend reality (`procedural` implemented) while keeping future adapter-family quality claims out of runtime behavior.

### SESSION-012 — Add variation strategy for repeated SFX categories
- **Status:** `completed`
- **Task type:** `loader_parsing + provenance`
- Added executable repeated-SFX variant-family validation in generation-request parsing (`_varNN` naming, deterministic distinct seeds, contiguous variant indices).
- Added per-asset variant provenance fields (`variationFamily`, `variationIndex`) for SFX variant requests in `RequestBatchPipeline`.
- Runtime in-game variant selection remains downstream/out of scope; factory-side deterministic variant generation/tracking is now implemented.

### SESSION-013 — Define category-specific SFX loudness/readability targets
- **Status:** `completed`
- **Task type:** `docs_only`
- Added category-specific SFX/ambience loudness-readability target guidance in `docs/AI_FACTORY/SUBSYSTEMS/SFX.md` and `docs/AI_FACTORY/QA/QUALITY_BARS.md`.
- Kept guidance additive to existing QA surfaces (`qa`, `qa-batch`) without claiming automated per-category enforcement.

### SESSION-014 — Add review/report template updates for variant-family QA decisions
- **Status:** `completed`
- **Task type:** `docs_only`
- Updated review workflow guidance and committed review-log example template for variant-family QA decisions.
- Added explicit family-level decision tracking guidance while preserving truthful docs-contract boundaries.

### SESSION-015 — Add machine-readable review-log writer for QA decisions
- **Status:** `completed`
- **Task type:** `provenance`
- Added executable `ReviewLogWriter` path and `write-review-log` CLI command that writes stable machine-readable review logs from provenance sidecars.
- Added optional QA snapshot alignment from `qa-batch` JSON report fields and optional `variationFamilyDecisions` ingestion.

### SESSION-016 — Integrate review-log output with approval/export handoff flow
- **Status:** `completed`
- **Task type:** `integration_export + provenance`
- Added additive review-log integration flags to `approve-draft` and `export-drafts`.
- Approval/export flows can now update review-log entries without changing default behavior when flags are omitted.

### SESSION-017 — Define the next executable implementation session
- **Status:** `completed`
- **Task type:** `docs_only`
- Refreshed queue priority and defined SESSION-018 as the next concrete executable implementation session.
- Updated continuity/session-control docs to keep queue/state/current-session synchronized.

### SESSION-018 — Enforce plan-target duration overrides in plan-driven execution
- **Status:** `completed`
- **Task type:** `batch_generation`
- Plan-driven execution now forwards `durationTargetSeconds` to request execution as explicit per-request duration overrides for matched plan targets.
- Added tests covering duration-override behavior in `RequestBatchPipeline` and `PlanBatchOrchestrator`.

### SESSION-019 — Add optional per-request duration field for direct request-batch execution
- **Status:** `completed`
- **Task type:** `loader_parsing + batch_generation`
- Added additive optional `durationSeconds` parsing on generation requests.
- `RequestBatchPipeline` now applies request-level `durationSeconds` for music/SFX in direct request-batch execution, with plan-driven per-request overrides still taking precedence.
- Added integration coverage for parsing validation and execution precedence/behavior.

### SESSION-020 — Define and queue the next executable implementation session
- **Status:** `completed`
- **Task type:** `docs_only`
- Refreshed continuity/session-control docs to mark SESSION-019 complete and advance the queue.
- Defined SESSION-021 as the next concrete executable implementation session.

### SESSION-021 — Unify explicit-duration behavior for legacy request-file execution path
- **Status:** `completed`
- **Task type:** `cli + batch_generation`
- Legacy `generate-request-batch --request-file` / `AssetPipeline.execute_request_batch` now honors request-level `durationSeconds` for music/SFX while preserving `--music-duration` / `--sfx-duration` as fallback defaults.
- Added regression coverage for legacy integration execution and CLI behavior so duration precedence is explicit and stable.

### SESSION-022 — Define and queue the next executable implementation session
- **Status:** `completed`
- **Task type:** `docs_only`
- Refreshed continuity/session-control docs to mark SESSION-021 complete and advance the queue.
- Defined SESSION-023 as the next concrete executable implementation session.

### SESSION-023 — Add optional provenance sidecars for legacy request-file execution path

- **Status:** `completed`
- **Task type:** `provenance + cli`
- Added optional provenance sidecar writing for legacy `generate-request-batch --request-file` via additive `--write-provenance`.
- Legacy `request_batch_result.json` records now include `provenance_path` when sidecars are written.

### SESSION-024 — Add result-JSON sourcing path for review-log writing

- **Status:** `completed`
- **Task type:** `provenance + cli`
- Added `ReviewLogWriter.append_from_result_json()` and `write-review-log --from-result` / `--include-skipped`.
- Result-driven review-log writes now preserve request metadata from result records when sidecars are missing, resolve relative output paths against the result context, and support `--project` / `--scope` overrides.

### SESSION-025 — Define and queue the next executable implementation session

- **Status:** `completed`
- **Task type:** `docs_only`
- Refreshed continuity/session-control docs to reflect SESSION-023/024 completion.
- Defined SESSION-026 as the next concrete executable implementation session.

### SESSION-026 — Add legacy request-file batch-manifest parity

- **Status:** `completed`
- **Task type:** `provenance + cli`
- Added additive legacy `batch_manifest.json` writing for `generate-request-batch --request-file` / `AssetPipeline.execute_request_batch` with deterministic per-request records aligned to existing request/result metadata.
- Preserved compatibility by leaving `request_batch_result.json` behavior unchanged and added focused integration/CLI coverage for the new legacy manifest output.

## Recently completed priority sessions

### SESSION-027 — Define and queue the next executable implementation session

- **Status:** `completed`
- **Task type:** `docs_only`
- **Objective:** Refresh continuity/session-control docs to reflect SESSION-026 completion and define the next concrete executable implementation task.
- **Notes:** Keep queue/state/current-session/history synchronized and avoid claiming unverified implementation scope.

### SESSION-028 — Add backend preflight verification command for optional neural workflows

- **Status:** `completed`
- **Task type:** `cli`
- **Objective:** Add an additive `audio-engine verify-backends` command that runs deterministic backend availability/preflight checks, optionally executes bounded fixture smoke runs when local models are present, and emits a machine-readable report to support neural-readiness handoff decisions.
- **Notes:** Implemented `_cmd_verify_backends` in `audio_engine/cli.py`; exits 0 (all available) or 2 (some unavailable); smoke run produces per-modality pass/fail entries; 6 focused tests added.

### SESSION-028b — Sample library scanner and pitch-shift engine

- **Status:** `completed`
- **Task type:** `integration_export`
- **Objective:** Add executable sample-library scanning and note pitch-shift primitives for orchestral remaster workflows.
- **Notes:** Added `audio_engine/integration/sample_library.py` (`OrchestralSampleLibrary`, note parsing/resolution) for deterministic instrument→note→filepath scanning over `samples/orchestral/`; added `audio_engine/dsp/pitch_shift.py` and integrated it into `audio_engine/samples/sample_library.py`; added focused tests in `tests/test_sample_library.py` and `tests/test_pitch_shift.py`.

### SESSION-028c — Remaster pipeline and CLI command

- **Status:** `completed`
- **Task type:** `integration_export`
- **Objective:** Add a deterministic remaster pipeline that replays provenance note events and substitutes available orchestral samples with synth fallback.
- **Notes:** Added `audio_engine/render/remaster.py` (`RemasterPipeline`, `RemasterEvent`) with deterministic event-driven sample substitution plus synth fallback; wired `audio-engine remaster` to this pipeline and added `--events-json`; added focused tests in `tests/test_remaster.py`.

### SESSION-029 — Finalize dual synth profile targets (PS1/PS2-era + orchestral)

- **Status:** `completed` (implemented by user override)
- **Task type:** `implementation + tests`
- **Objective:** Implement procedural quality-overhaul code paths for PS2-era JRPG-targeted output: structured phrase planning, motif reuse/variation, 8-layer arrangement management, recipe-specific SFX synthesis, and upgraded voice synthesis.
- **Notes:** Includes additive `audio-engine studio` GUI tooling surface and deterministic seed-preserving behavior across music/SFX/voice.

### SESSION-029b — Expand creation tooling / studio workflow

- **Status:** `completed`
- **Task type:** `cli + ui`
- **Objective:** Add post-MVP creation tooling improvements for the local studio workflow (presets, profile loading, batch generation shortcuts, and error-recovery UX).
- **Notes:** Added studio preset save/load JSON controls, music mastering-profile selection in studio, one-click "Generate All" shortcut, and retry-last-error recovery button while preserving CLI compatibility.

### SESSION-030 — Add strict WAV sample-folder ingestion contract

- **Status:** `completed`
- **Task type:** `docs_only`
- **Objective:** Define deterministic folder/layout, naming, metadata, and rejection rules for user-provided WAV sample folders consumed by remaster workflows.
- **Notes:** Published `docs/AI_FACTORY/SCHEMAS/WAV_INGESTION_CONTRACT.md` with explicit layout, file format, naming, pitch-shift behavior, and rejection rules.

### SESSION-031 — Complete batch remaster pipeline wiring

- **Status:** `completed`
- **Task type:** `integration_export`
- **Objective:** Add deterministic remaster-batch execution over ingestion-contract sample folders with machine-readable per-file outcomes.
- **Notes:** Added additive `RemasterBatchPipeline` + `RemasterBatchResult` in `audio_engine/integration/asset_pipeline.py`, exported via `audio_engine.integration`, and added additive `audio-engine remaster-batch` CLI command with deterministic ordering and `remaster_batch_result.json` output; covered with CLI + pipeline tests.

### SESSION-032 — Add license compliance CI gate

- **Status:** `planned`
- **Task type:** `cli`
- **Objective:** Fail CI on unknown or disallowed dependency/model licenses and emit a machine-readable compliance report for auditability.
- **Notes:** Keep policy config explicit and version-controlled.

### SESSION-033 — Build dependency/model license inventory baseline

- **Status:** `completed`
- **Task type:** `docs_only`
- **Objective:** Capture machine-readable dependency/model license inventory and map each entry to commercial-eligibility policy categories.
- **Notes:** Published `docs/AI_FACTORY/LICENSE_INVENTORY.md` with all core, optional neural, and model-weight entries mapped to allow/conditional/block/unknown policy.

### SESSION-034 — Define commercial eligibility matrix by backend/model combination

- **Status:** `completed`
- **Task type:** `docs_only`
- **Objective:** Publish explicit allow/conditional/block commercial-use matrix for backend + model combinations used by generation commands.
- **Notes:** Published `docs/AI_FACTORY/COMMERCIAL_ELIGIBILITY_MATRIX.md` with allow/conditional/block rows for all registered backends and safe commercial-use workflow.

### SESSION-035 — Finalize mastering profile presets (game mix / OST / vocal mix)

- **Status:** `completed`
- **Task type:** `cli`
- **Objective:** Add stable mastering profile selection for game mix, OST, and vocal-centric workflows with deterministic parameter capture.
- **Notes:** Added `vocal_mix` profile to `OfflineBounce`; exported `VALID_PROFILES` constant; added `mastering_profile` parameter to `MusicGen`; exposed `--profile` flag on `generate-music` CLI command; 3 new CLI profile tests and 1 new render test.

### SESSION-036 — Expand QA gates for professional WAV release quality

- **Status:** `completed`
- **Task type:** `qa`
- **Objective:** Add enforceable QA checks for loudness, true peak, clipping, loop integrity, spectral balance, and intelligibility expectations.
- **Notes:** Added `audio_engine/qa/spectral_analyzer.py` (`SpectralAnalyzer`, `SpectralReport`); wired spectral balance checks into `qa` and `qa-batch` CLI commands; added `spectral_balance_ok`, `spectral_centroid_hz`, `high_freq_ratio` fields to `qa-batch` JSON reports; 13 new QA tests + 1 CLI test. Updated `docs/AI_FACTORY/QA/QUALITY_BARS.md`.

### SESSION-037 — Add deterministic export contract for commercial WAV-first delivery

- **Status:** `completed`
- **Task type:** `integration_export`
- **Objective:** Define and enforce deterministic export naming/layout/manifests for game-import and direct commercial distribution workflows.
- **Notes:** Added `audio_engine/integration/export_contract.py` (`WavDeliveryPipeline`, `_deterministic_delivery_name`); added additive `audio-engine export-wav-delivery` CLI command; delivery filenames use `<category>__<asset_id>__seed<N>.wav` contract; `delivery_manifest.json` written with full per-file records; 6 focused CLI tests.

### SESSION-040 — Add deterministic regression harness for factory workflows

- **Status:** `completed`
- **Task type:** `qa`
- **Objective:** Add reproducibility regression checks that validate stable outputs/manifests from fixed seeds and committed fixtures.
- **Notes:** Created `tests/test_regression.py` with 13 tests covering QA metric stability (`LoudnessMeter`, `ClippingDetector`, `SpectralAnalyzer`), music/SFX fixed-seed reproducibility, and delivery manifest schema/naming determinism.

### SESSION-043 — Freeze final baseline reproducibility + seed policy

- **Status:** `completed`
- **Task type:** `docs_only`
- **Objective:** Lock deterministic seed capture/regeneration rules across generation, remaster, QA, and export surfaces.
- **Notes:** Published `docs/AI_FACTORY/SEED_POLICY.md` with explicit seed precedence, format, delivery naming, and enforcement status table across all commands.

### SESSION-044 — Final commercial readiness audit session

- **Status:** `completed`
- **Task type:** `docs_only`
- **Objective:** Run a final evidence-driven audit that capability, quality, licensing, automation, and reproducibility gates are all satisfied.
- **Notes:** Published `docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md` with per-gate pass/fail evidence and open-items table for non-blocking planned sessions.

### SESSION-046 — Expand music testing fixture style coverage

- **Status:** `completed`
- **Task type:** `taxonomy`
- **Objective:** Expand committed music request fixtures with broader style/mood/environment testing coverage.
- **Notes:** Added 21 additive music test-piece requests in `generation_requests.music.v1.json` (driving/hopeful/romance/love/sailing/beach/snowy mountains/hot desert/high-tech city/elevator/guitar solo/piano solo/cyberpunk/country/rock/emo/lo-fi/synth-pop/synth-rock/synth-wave/grand opera) with deterministic IDs/seeds and explicit `durationSeconds`.

### SESSION-047 — Synchronize continuity docs after fixture expansion

- **Status:** `completed`
- **Task type:** `docs_only`
- **Objective:** Keep session-control and continuity docs synchronized after SESSION-046 fixture/test updates.
- **Notes:** Updated `SESSION_QUEUE.md`, `SESSION_STATE.json`, `CURRENT_SESSION.json`, `SESSION_HISTORY.md`, `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, and `SUBSYSTEMS/MUSIC.md` for truthful continuity.

## Current next session

### SESSION-048 — Full Orchestral Synth (completed)

- **Status:** `completed`
- **Task type:** `synthesis + cli`
- **Objective:** Add a full orchestral synth backend and new distinct instruments to address "same sounds for everything" audio feedback.
- **Notes:**
  - Added 8 new orchestral instruments: `oboe`, `clarinet`, `french_horn`, `cello`, `harp`, `celesta`, `timpani`, `marimba`.
  - Added `full_orchestral` backend with per-section stereo panning and OST mastering.
  - Updated 6 style defs to use distinct section instruments.
  - 24 new instrument tests + 14 new backend tests.

### SESSION-032 — Add license compliance CI gate

- **Status:** `completed`
- **Task type:** `cli`
- **Objective:** Fail CI on unknown or disallowed dependency/model licenses and emit a machine-readable compliance report for auditability.
- **Notes:**
  - Added `tools/license_policy.toml` (SPDX policy with allow/conditional/block sections).
  - Added `audio_engine/compliance/license_checker.py` scoped to declared deps only.
  - Added `audio-engine check-licenses` CLI command (exits 0=compliant, 1=blocked/unknown).
  - Added `.github/workflows/license-compliance.yml` CI gate.
  - 21 new tests in `tests/test_license_compliance.py`.

## Remaining planned sessions (post-baseline)

## Current next session

### SESSION-041 — End-to-end vertical slice release gate automation

- **Status:** `completed`
- **Task type:** `orchestration`
- **Objective:** Add one deterministic command that executes vertical-slice generation, QA, compliance checks, and export handoff with machine-readable gate artifacts.
- **Notes:** Added `VerticalSliceGatePipeline` and `VerticalSliceGateReport` to `audio_engine/integration/asset_pipeline.py`; wired `audio-engine run-release-gate` CLI subcommand with `--skip-qa`, `--skip-compliance`, `--skip-export`, `--check-spectral`, `--check-loop`, `--force`, `--gate-report`, and `--qa-report` flags. 14 new tests added in `tests/test_release_gate.py`; 1108 tests pass total.

### Recently completed session context

### SESSION-038 — Stabilize dual-path vocal and instrumental workflow

- **Status:** `completed`
- **Task type:** `pipeline + voice`
- **Objective:** Support deterministic generation/export of paired instrumental and vocal-production-ready variants with explicit provenance linkage.
- **Notes:** Added additive `musicDeliveryMode: dual_vocal_instrumental` support for music requests, deterministic paired `__instrumental` + `__vocal_ready` outputs in both request-batch execution paths, and provenance linkage fields (`dualPathGroupId`, `dualPathRole`, `pairedOutputPath`).

### SESSION-028b — Sample library scanner and pitch-shift engine

- **Status:** `completed`
- **Task type:** `integration_export`
- **Objective:** Add executable sample-library scanning and note pitch-shift primitives for orchestral remaster workflows.
- **Notes:** Added `audio_engine/integration/sample_library.py` (`OrchestralSampleLibrary`, note parsing/resolution) for deterministic instrument→note→filepath scanning over `samples/orchestral/`; added `audio_engine/dsp/pitch_shift.py` and integrated it into `audio_engine/samples/sample_library.py`; added focused tests in `tests/test_sample_library.py` and `tests/test_pitch_shift.py`.

### SESSION-028c — Remaster pipeline and CLI command

- **Status:** `completed`
- **Task type:** `integration_export`
- **Objective:** Add a deterministic remaster pipeline that replays provenance note events and substitutes available orchestral samples with synth fallback.
- **Notes:** Added `audio_engine/render/remaster.py` (`RemasterPipeline`, `RemasterEvent`) with deterministic event-driven sample substitution plus synth fallback; wired `audio-engine remaster` to this pipeline and added `--events-json`; added focused tests in `tests/test_remaster.py`.

### SESSION-029b — Expand creation tooling / studio workflow

- **Status:** `completed`
- **Task type:** `cli + ui`
- **Objective:** Add post-MVP creation tooling improvements for the local studio workflow (presets, profile loading, batch generation shortcuts, and error-recovery UX).
- **Notes:** Added studio preset save/load JSON controls, music mastering-profile selection in studio, one-click "Generate All" shortcut, and retry-last-error recovery button while preserving CLI compatibility.

### SESSION-031 — Complete batch remaster pipeline wiring

- **Status:** `completed`
- **Task type:** `integration_export`
- **Objective:** Add deterministic remaster-batch execution over ingestion-contract sample folders with machine-readable per-file outcomes.
- **Notes:** Added additive `RemasterBatchPipeline` + `RemasterBatchResult` in `audio_engine/integration/asset_pipeline.py`, exported via `audio_engine.integration`, and added additive `audio-engine remaster-batch` CLI command with deterministic ordering and `remaster_batch_result.json` output; covered with CLI + pipeline tests.
