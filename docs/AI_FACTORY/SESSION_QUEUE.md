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

## Current next session

### SESSION-005 — Implement GameRewritten export profile

- **Status:** `ready`
- **Task type:** `export`
- **Objective:** Copy all approved draft assets from `<output_dir>/drafts/` into `<output_dir>/exports/gamerewritten/Content/Audio/<type>/`, following the `targetImportPath` in each `.provenance.json` sidecar as the canonical destination name.
- **Why it matters:** Generated assets currently live in `drafts/` only. The GameRewritten consuming repo needs them placed in `Content/Audio/` by stable name. Without an export step, the factory cannot produce a deployable deliverable.
- **Read first docs/files:**
  1. `docs/AI_FACTORY/SESSION_QUEUE.md`
  2. `docs/AI_FACTORY/CURRENT_STATE.md`
  3. `docs/AI_FACTORY/HANDOFF.md`
  4. `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md`
  5. `docs/AI_FACTORY/CURRENT_SESSION.json`
  6. `docs/AI_FACTORY/SESSION_GATE_RULES.md`
  7. `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  8. `docs/AI_FACTORY/VERIFICATION_PROFILES.md`
  9. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
  10. `docs/AI_FACTORY/FAILSAFE_RULES.md`
  11. `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md`
  12. `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`
  13. `docs/AI_FACTORY/INTEGRATION/GAMEREWRITTEN.md`
  14. `audio_engine/integration/asset_pipeline.py`
  15. `audio_engine/cli.py`
  16. `tests/test_integration.py`
- **Exact or likely files to modify:**
  - `audio_engine/integration/asset_pipeline.py` (add export helper/class)
  - `audio_engine/cli.py` (add `export-drafts` or `export-gamerewritten` command)
  - `tests/test_integration.py`
- **Files not to modify unless absolutely necessary:**
  - `audio_engine/dsp/*`
  - `audio_engine/render/*`
  - `audio_engine/composer/*`
  - `assets/schema/*`
  - `audio_engine/integration/factory_inputs.py`
- **Verification commands:**
  - `pip install -e ".[dev]"`
  - `python -m pytest`
  - `python tools/validate-assets.py assets/examples/ --verbose`
  - one `/tmp` smoke run confirming export files land in `Content/Audio/<type>/` by `targetImportPath` name
- **Docs that must be updated:**
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/ACTIVE_WORK.md`
  - `docs/AI_FACTORY/HANDOFF.md`
  - `docs/AI_FACTORY/CHANGE_JOURNAL.md`
  - `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`
  - `docs/AI_FACTORY/SUBSYSTEMS/ASSET_PIPELINE.md`
  - `docs/AI_FACTORY/SESSION_QUEUE.md`
  - `docs/AI_FACTORY/SESSION_HISTORY.md`
  - `docs/AI_FACTORY/CURRENT_SESSION.json`
  - `docs/AI_FACTORY/SESSION_STATE.json`
- **Explicit done criteria:**
  1. A CLI command (`export-drafts` or `export-gamerewritten`) copies files from `drafts/<type>/` to `exports/gamerewritten/Content/Audio/<type>/`, using the `targetImportPath` filename from provenance sidecars where available.
  2. The command writes an export manifest listing source and destination paths.
  3. Existing `drafts/` content is not modified or deleted.
  4. Tests verify: files are copied, destination names match provenance `targetImportPath`, export manifest is written.
  5. Command returns non-zero if no drafts exist to export.
  6. Docs describe the export behavior truthfully.
- **Enqueue next session after completion:** `SESSION-006 — Add approval workflow (promote drafts to approved/)`
- **If uncertain or blocked:**
  - follow `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  - if `docs/AI_FACTORY/INTEGRATION/GAMEREWRITTEN.md` is absent or incomplete, read the KNOWN_ISSUES.md and use `Content/Audio/<type>/` as the conservative target path

## Upcoming queued sessions

### SESSION-006 — Add approval workflow (promote drafts to approved/)

- **Status:** `queued-after-SESSION-005`
- **Task type:** `workflow`
- **Short objective:** Let an agent or human mark a draft asset as `approved` (updating its `.provenance.json` `reviewStatus`) and copy it to `approved/<type>/`.
