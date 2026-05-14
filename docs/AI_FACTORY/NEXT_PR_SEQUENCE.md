# Next PR Sequence

> Mechanical build order for future agents. Goal: evolve this repository into a GitHub-native factory that can generate all audio files needed by a game (music, fanfares/stingers, UI/combat/spell SFX, ambience, optional low-priority voice).
>
> `SESSION_QUEUE.md` is the canonical file for **the single next session**. This file remains the longer-range ordered sequence behind that queue.

## PR-1 — Implement audio plan + request loading primitives

- **Suggested title:** `Implement plan/request loaders for factory inputs`
- **Objective:** Add code-side dataclasses/loaders for project audio plans and generation requests.
- **Why it matters:** Converts docs-only contracts into executable inputs.
- **Likely files to change:**
  - `audio_engine/integration/*` (new loader module)
  - `audio_engine/cli.py` (new validation/listing command if needed)
  - `tests/test_integration.py`
- **Files that should probably not change:**
  - `audio_engine/dsp/*`, `audio_engine/synthesizer/*`
- **Verification commands:**
  - `pytest`
  - `python tools/validate-assets.py assets/examples/ --verbose`
- **Docs to update:**
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/SUBSYSTEMS/ASSET_PIPELINE.md`
  - `docs/AI_FACTORY/HANDOFF.md`
- **Definition of done:** Loader code can parse committed example plan/request artifacts and expose them as typed objects.

## PR-2 — Add request-batch generation command

- **Suggested title:** `Add request-batch generation CLI for music and SFX`
- **Objective:** Add a CLI/API path that executes a batch of generation requests.
- **Why it matters:** Enables low-prompt, deterministic, mechanical generation from committed inputs.
- **Likely files to change:**
  - `audio_engine/cli.py`
  - `audio_engine/integration/asset_pipeline.py`
  - `tests/test_engine_cli.py`, `tests/test_integration.py`
- **Files that should probably not change:**
  - `audio_engine/composer/*` unless bugfix required
- **Verification commands:**
  - `pytest`
  - One CLI smoke run against example requests to `/tmp`
- **Docs to update:**
  - `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/HANDOFF.md`
- **Definition of done:** Batch command produces expected output files for at least music + SFX example requests.

## PR-3 — Write provenance + review logs per request

- **Suggested title:** `Capture provenance and review status for generated assets`
- **Objective:** Persist request ID, seed, output path, and review status in machine-readable logs.
- **Why it matters:** Supports repeatability and handoff continuity.
- **Likely files to change:**
  - `audio_engine/integration/*` (manifest/provenance writer)
  - `tests/test_integration.py`
- **Files that should probably not change:**
  - `audio_engine/dsp/*`
- **Verification commands:**
  - `pytest`
- **Docs to update:**
  - `docs/AI_FACTORY/QA/REVIEW_WORKFLOW.md`
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/HANDOFF.md`
- **Definition of done:** Each generated asset has machine-readable provenance linked to its request.

## PR-4 — Add batch QA gate command for generated outputs

- **Suggested title:** `Add batch QA gate command for generated asset sets`
- **Objective:** Wrap existing QA checks into a command that validates many generated outputs at once.
- **Why it matters:** Reduces manual review load and catches weak outputs early.
- **Likely files to change:**
  - `audio_engine/cli.py`
  - `audio_engine/qa/*` (if helper needed)
  - `tests/test_qa.py`, `tests/test_engine_cli.py`
- **Files that should probably not change:**
  - `audio_engine/ai/*` generation logic
- **Verification commands:**
  - `pytest`
- **Docs to update:**
  - `docs/AI_FACTORY/QA/QUALITY_BARS.md`
  - `docs/AI_FACTORY/KNOWN_ISSUES.md`
  - `docs/AI_FACTORY/HANDOFF.md`
- **Definition of done:** Command returns pass/fail status and per-file reasons for music and SFX outputs.

## PR-5 — Implement `GameRewritten` export profile and mapping outputs

- **Suggested title:** `Add GameRewritten export profile with stable target paths`
- **Objective:** Emit outputs and mapping metadata aligned with `Content/Audio/*` expectations.
- **Why it matters:** Directly supports import into the consuming game repository.
- **Likely files to change:**
  - `audio_engine/integration/game_state_map.py`
  - `audio_engine/integration/asset_pipeline.py`
  - `tests/test_integration.py`
- **Files that should probably not change:**
  - `audio_engine/synthesizer/*`
- **Verification commands:**
  - `pytest`
  - generation smoke test to `/tmp` + verify expected paths exist
- **Docs to update:**
  - `docs/AI_FACTORY/INTEGRATION/GAMEREWRITTEN.md`
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/HANDOFF.md`
- **Definition of done:** Generated outputs include a stable mapping for downstream import with clear overwrite behavior.

## PR-6 — Expand taxonomy toward full game coverage

- **Suggested title:** `Expand factory taxonomy for full game-audio coverage`
- **Objective:** Add committed taxonomy/backlog coverage for all needed audio families (music states, fanfares/stingers, UI, combat/spell SFX, ambience, optional voice).
- **Why it matters:** Prevents hidden gaps as scope scales from vertical slice to full game.
- **Likely files to change:**
  - `docs/AI_FACTORY/TASKS/BACKLOG.md`
  - `docs/AI_FACTORY/EXAMPLES/*`
  - `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`
- **Files that should probably not change:**
  - production code, unless tied to taxonomy implementation
- **Verification commands:**
  - Manual review + any schema validation added by prior PRs
- **Docs to update:**
  - `docs/AI_FACTORY/ACTIVE_WORK.md`
  - `docs/AI_FACTORY/HANDOFF.md`
- **Definition of done:** No major asset family required for a game is missing from tracked plan/taxonomy docs.
