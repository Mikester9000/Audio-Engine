# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-017 + SESSION-018: Refreshed the queue and completed executable plan-duration enforcement so `generate-plan-batch` now applies plan `durationTargetSeconds` as per-request duration overrides during request execution.

## Verified in this session

```bash
python -m pytest tests/test_integration.py -k "duration_override or applies_duration_overrides or passes_duration_overrides_from_plan_targets"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
```

Observed result:
- targeted duration-override tests passed (`2` selected tests)
- full repo test suite passed (`415`) and asset-manifest validation passed
- SESSION-017 and SESSION-018 completed; queue advanced to SESSION-019

## Immediate next best task

Execute `SESSION-019` from `docs/AI_FACTORY/SESSION_QUEUE.md`: add additive optional per-request duration support for direct request-batch execution (`generate-request-batch --batch-file` / `RequestBatchPipeline`).

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
