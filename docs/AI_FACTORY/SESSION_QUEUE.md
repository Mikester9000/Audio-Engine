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
- **Task type:** `loader_parsing`
- **Result summary:** Typed loader code for the committed audio plan and music/SFX request fixtures now exists in `audio_engine/integration/factory_inputs.py`, with tests covering successful ingestion and an invalid-input failure path.

### SESSION-002 — Add request-batch generation command

- **Status:** `completed`
- **Task type:** `batch_generation`
- **Result summary:** `RequestBatchPipeline` added to `audio_engine/integration/asset_pipeline.py`; `generate-request-batch` CLI command added. Both committed music (4) and SFX (5) fixtures execute deterministically with per-request seeds captured in `batch_manifest.json`. 13 new tests added; 334 total passed.

### SESSION-003 — Write provenance + review logs per request

- **Status:** `completed`
- **Task type:** `provenance`
- **Result summary:** `_write_provenance()` method added to `RequestBatchPipeline`. Every successful generation writes a `<stem>.provenance.json` sidecar containing `provenanceVersion`, `requestId`, `assetId`, `type`, `backend`, `seed`, `prompt`, `styleFamily`, `generatedOutputPath`, `targetImportPath`, `reviewStatus`, `generatedAt`. 5 new tests added; 338 total passed.

## Current next session

### SESSION-004 — Add batch QA gate command for generated outputs

- **Status:** `ready`
- **Task type:** `qa`
- **Objective:** Wrap the existing loudness, clipping, and loop QA primitives in a batch CLI command that reports pass/fail per asset and writes a machine-readable QA report.
- **Why it matters:** Without a batch QA gate, generated assets have no automated first-pass acceptance check before they are promoted to `approved/`. The existing `audio-engine qa` command works on individual files only.
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
  12. `docs/AI_FACTORY/QA/QUALITY_BARS.md`
  13. `docs/AI_FACTORY/QA/REVIEW_WORKFLOW.md`
  14. `audio_engine/qa/` (existing QA primitives)
  15. `audio_engine/cli.py` (existing `qa` command)
  16. `audio_engine/integration/asset_pipeline.py`
  17. `tests/test_integration.py`
- **Exact or likely files to modify:**
  - `audio_engine/cli.py`
  - `tests/test_integration.py`
  - optionally `audio_engine/integration/asset_pipeline.py` if a batch QA helper fits there
- **Files not to modify unless absolutely necessary:**
  - `audio_engine/dsp/*`
  - `audio_engine/render/*`
  - `audio_engine/composer/*`
  - `assets/schema/*`
- **Verification commands:**
  - `pip install -e ".[dev]"`
  - `python -m pytest`
  - `python tools/validate-assets.py assets/examples/ --verbose`
  - one `/tmp` smoke run confirming QA report is written for a committed batch output
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
  1. A `qa-batch` (or `qa-request-batch`) CLI command accepts a directory of generated audio files and reports pass/fail per file.
  2. The command writes a machine-readable QA report (JSON) with at minimum: `file`, `status` (pass/fail), `checks` (per-check results).
  3. Tests cover at least one passing case (synthetic or generated audio that meets bars) and one failing case (silent/clipping file).
  4. The existing `audio-engine qa` single-file command is preserved.
  5. Docs reflect the new command truthfully.
- **Enqueue next session after completion:** `SESSION-005 — Implement GameRewritten export profile`
- **If uncertain or blocked:**
  - follow `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  - do not change the existing `qa` command signature
  - emit JSONL or JSON QA report — do not create a binary format

## Upcoming queued sessions

### SESSION-005 — Implement GameRewritten export profile

- **Status:** `queued-after-SESSION-004`
- **Task type:** `export`
- **Short objective:** Copy approved draft assets into the `exports/gamerewritten/Content/Audio/` layout expected by the downstream game.
