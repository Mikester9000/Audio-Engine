# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-011 + SESSION-012: Implemented executable backend evaluation metadata (`BackendRegistry.evaluate_backends` + enriched `list-backends` output), and implemented repeated-SFX variation execution rules (variant-family validation with `_varNN` + distinct seeds + contiguous indices) plus SFX variant provenance fields (`variationFamily`, `variationIndex`).

## Verified in this session

```bash
pip install -e ".[dev]"
python -m pytest  # 404 passed
python tools/validate-assets.py assets/examples/ --verbose  # PASS
```

Observed result:
- `404 passed` in pytest
- all asset-manifest examples passed validation
- edited continuity/session JSON files parse successfully
- SESSION-011 and SESSION-012 completed and queue advanced to SESSION-013

## Immediate next best task

Execute `SESSION-013` from `docs/AI_FACTORY/SESSION_QUEUE.md`: define category-specific SFX loudness/readability targets and align that guidance with existing QA/reporting surfaces.

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
