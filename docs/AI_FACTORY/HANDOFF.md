# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-013 + SESSION-014: Added docs-only quality-contract updates for SFX QA consistency: category-specific loudness/readability guidance aligned with existing `qa`/`qa-batch` outputs, plus variant-family review/report template updates in workflow guidance and committed review-log example artifacts.

## Verified in this session

```bash
python -m json.tool docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
```

Observed result:
- edited review-log/session JSON files parse successfully
- docs-only consistency review completed across SFX/QA/review/schema continuity docs
- SESSION-013 and SESSION-014 completed and queue advanced to SESSION-015

## Immediate next best task

Execute `SESSION-015` from `docs/AI_FACTORY/SESSION_QUEUE.md`: add a machine-readable review-log writer aligned with provenance and existing QA/report surfaces.

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
