# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-021 + SESSION-022: Added explicit `durationSeconds` parity for legacy `generate-request-batch --request-file` runs and advanced session-control docs to queue SESSION-023.

## Verified in this session

```bash
python -m pytest tests/test_integration.py -k "request_duration_seconds or legacy-duration-tests or execute_request_batch_prefers_request_duration_seconds"
python -m pytest tests/test_engine_cli.py -k "request_duration_seconds or via_request_file"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m audio_engine.cli generate-request-batch --request-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json --output-dir /tmp/session021_legacy_smoke --sfx-duration 0.1 --quiet
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
```

Observed result:
- targeted legacy-duration integration tests passed (`2` selected tests)
- targeted legacy-duration CLI tests passed (`3` selected tests)
- full repo test suite passed (`419`), asset-manifest validation passed, and legacy CLI smoke run succeeded (`10` requests OK)
- updated session-control JSON files parsed successfully
- SESSION-021 and SESSION-022 completed; queue advanced to SESSION-023

## Immediate next best task

Execute `SESSION-023` from `docs/AI_FACTORY/SESSION_QUEUE.md`: add optional provenance sidecars for backward-compatible `generate-request-batch --request-file` runs while preserving legacy output layout/default behavior.

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
- [x] Legacy request-file explicit-duration parity (SESSION-021)
- [x] Queue advancement and next executable session definition (SESSION-022)
