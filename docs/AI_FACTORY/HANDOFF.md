# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-009 + SESSION-010: Added plan-driven orchestration (`PlanBatchOrchestrator` + `generate-plan-batch`) and expanded backend support surfaces. Request-batch execution now enforces requested output formats strictly (no OGG→WAV fallback) and now honors per-request backend in `RequestBatchPipeline`; CLI now exposes backend selection flags and `list-backends`.

## Verified in this session

```bash
pip install -e ".[dev]"
pip install soundfile
python -m pytest  # 397 passed
python tools/validate-assets.py assets/examples/ --verbose  # PASS
python -m audio_engine.cli generate-plan-batch --plan-file /tmp/session009010_smoke/plan.smoke.json --request-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json --output-dir /tmp/session009010_smoke --force --quiet  # PASS
```

Observed result:
- `397 passed` in pytest
- all asset-manifest examples passed validation
- deterministic plan-driven smoke run produced requested `.ogg` output and provenance sidecar
- required fanfare requests were added to committed music request fixture to satisfy required plan targets

## Immediate next best task

Execute `SESSION-011` from `docs/AI_FACTORY/SESSION_QUEUE.md`: add backend evaluation notes and dependency/availability guidance aligned with the newly-added backend CLI surfaces.

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
