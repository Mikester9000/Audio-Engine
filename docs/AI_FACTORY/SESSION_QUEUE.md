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
- **Task type:** `docs_only`
- Added explicit backend evaluation notes and dependency/availability guidance aligned with backend registry/selection CLI surfaces.
- Documented current backend reality (`procedural` implemented) and future local/open adapter families without claiming unimplemented quality.

### SESSION-012 — Add variation strategy for repeated SFX categories
- **Status:** `completed`
- **Task type:** `docs_only`
- Added deterministic request-level SFX variation strategy guidance (stable naming, explicit seed capture, variant-per-request flow).
- Clarified this is currently docs-contract guidance and not implemented runtime variation selection logic.

## Current next session

### SESSION-013 — Define category-specific SFX loudness/readability targets

- **Status:** `ready`
- **Task type:** `docs_only`
- **Objective:** Define category-specific SFX loudness/readability target guidance and align it with existing QA/reporting surfaces so repeated-category variant assets can be reviewed consistently.
- **Enqueue next session after completion:** `SESSION-014 — Add review/report template updates for variant-family QA decisions`
- **Notes:** Keep guidance additive and truthful to existing checks (`qa`, `qa-batch`) without claiming new automated per-category enforcement.
