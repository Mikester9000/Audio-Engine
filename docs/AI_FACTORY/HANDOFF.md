# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-019 + SESSION-020: Added optional request-level `durationSeconds` parsing/execution for direct request-batch runs and advanced session-control docs to queue SESSION-021.

## Verified in this session

```bash
python -m pytest tests/test_integration.py -k "duration or generation_request_loader"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
```

Observed result:
- targeted duration/parsing integration tests passed (`12` selected tests)
- full repo test suite passed (`417`) and asset-manifest validation passed
- SESSION-019 and SESSION-020 completed; queue advanced to SESSION-021

## Immediate next best task

Execute `SESSION-021` from `docs/AI_FACTORY/SESSION_QUEUE.md`: unify explicit-duration behavior for backward-compat `generate-request-batch --request-file` (`AssetPipeline.execute_request_batch`) while preserving additive compatibility.

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`
5. `docs/AI_FACTORY/HANDOFF.md`
6. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
7. `docs/AI_FACTORY/FAILSAFE_RULES.md`

## Handoff checklist

- [x] Request-batch generation command (`generate-request-batch`)
- [x] Per-request provenance sidecar files (`.provenance.json`)
- [x] Batch QA gate command (`qa-batch` with JSON report)
- [x] GameRewritten export profile (`export-drafts` to `Content/Audio/`)
- [x] Approval workflow (`approve-draft` → `approved/<type>/`, updates provenance)
- [x] QA gate wired into CI (`.github/workflows/audio-qa.yml`)
- [x] Music-duration policy documented and encoded in checklist, layout, music subsystem, and example plan
- [x] Full-game taxonomy coverage expansion (SESSION-008)
- [x] Plan-driven batch orchestration (SESSION-009, including required `.ogg` output production)
- [x] Backend support surface expansion (SESSION-010)
- [x] Backend evaluation metadata in code and CLI output (SESSION-011)
- [x] Repeated-SFX variation validation + provenance metadata in code (SESSION-012)
- [x] Category-specific SFX loudness/readability guidance (SESSION-013, docs-only)
- [x] Variant-family review/report template updates (SESSION-014, docs-only)
- [x] Machine-readable review-log writer (`ReviewLogWriter` + `write-review-log`, SESSION-015)
- [x] Review-log handoff integration for approval/export (`approve-draft`/`export-drafts` flags, SESSION-016)
- [x] Session queue refresh to define next executable implementation session (SESSION-017)
- [x] Plan target duration enforcement in plan-driven execution (SESSION-018)
- [x] Optional request-level `durationSeconds` parsing + direct request-batch execution support (SESSION-019)
- [x] Queue advancement and next executable session definition (SESSION-020)
