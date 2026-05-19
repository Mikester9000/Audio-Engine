# Completion-State Handoff

> Final handoff and maintenance instructions for the Audio-Engine factory baseline.
> Written in SESSION-045 after all required commercial readiness gates were evidenced.
> Future additive work may continue; this document describes the stable baseline state.

## Baseline completion declaration

The Audio-Engine factory baseline is **complete** as of SESSION-045. All required commercial readiness gates are satisfied (see `COMMERCIAL_READINESS_AUDIT.md`).

This declaration is **reversible**: if any gate regresses, update `COMMERCIAL_READINESS_AUDIT.md` and open a follow-up session to restore compliance.

## What "complete" means here

- All planned code sessions through SESSION-045 that have executable scope are implemented and tested.
- The factory can generate, QA, approve, and package professional WAV audio assets for game import using the procedural backend.
- All session-control, continuity, and state docs are synchronized.
- The regression harness (`tests/test_regression.py`) enforces baseline determinism.

## What "complete" does NOT mean

- Neural backends (MusicGen, orchestral remaster) are optional and depend on local model availability.
- Sessions SESSION-028b, 028c, 029b, 031, 032 are planned but not blocking the baseline.
- The factory is a production tool; ongoing game-specific work (new prompts, seeds, reviews) is always expected.

## Stable baseline capabilities

| Capability | Command |
|---|---|
| Generate music | `audio-engine generate-music --prompt "..." --duration 60 --output out.wav --seed 42` |
| Generate SFX | `audio-engine generate-sfx --prompt "..." --output out.wav --seed 42` |
| Generate voice | `audio-engine generate-voice --text "..." --output out.wav` |
| Batch generation from requests | `audio-engine generate-request-batch --batch-file requests.json --output-dir ./drafts` |
| Plan-driven batch generation | `audio-engine generate-plan-batch --plan-file plan.json --batch-file requests.json --output-dir ./drafts` |
| QA check (single file) | `audio-engine qa --input file.wav` |
| QA batch with JSON report | `audio-engine qa-batch --input-dir ./drafts/sfx --output-report qa.json --recursive` |
| Approve draft | `audio-engine approve-draft --factory-root ./factory --draft-file ./factory/drafts/sfx/file.wav` |
| Export to GameRewritten | `audio-engine export-drafts --factory-root ./factory` |
| Commercial WAV delivery | `audio-engine export-wav-delivery --factory-root ./factory --delivery-dir ./delivery/v1` |
| Backend preflight | `audio-engine verify-backends --smoke --output-report preflight.json` |
| Studio UI | `audio-engine studio` |

## Maintenance instructions for future work

### Adding a new asset type

1. Add the type to the taxonomy fixtures in `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/`.
2. Add generation requests to the appropriate batch JSON.
3. Update `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`.

### Adding a new QA gate

1. Add the check to `audio_engine/qa/` (new module or extend existing).
2. Update `_cmd_qa` and `_cmd_qa_batch` in `audio_engine/cli.py` to include the new check.
3. Update `docs/AI_FACTORY/QA/QUALITY_BARS.md`.
4. Add regression tests in `tests/test_qa.py` or `tests/test_regression.py`.

### Adding a new backend

1. Implement adapter in `audio_engine/ai/backends/`.
2. Register in `audio_engine/ai/backend.py`.
3. Update `docs/AI_FACTORY/LICENSE_INVENTORY.md` and `docs/AI_FACTORY/COMMERCIAL_ELIGIBILITY_MATRIX.md`.
4. Verify with `audio-engine verify-backends`.

### Adding a new session

1. Add to `SESSION_QUEUE.md` with a `planned` status.
2. Update `NEXT_PR_SEQUENCE.md` if it changes the ordered roadmap.
3. Set `CURRENT_SESSION.json` when the session becomes `ready`.

## Files a future agent should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`
5. `docs/AI_FACTORY/HANDOFF.md`
6. `docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md`
7. `docs/AI_FACTORY/SEED_POLICY.md`
