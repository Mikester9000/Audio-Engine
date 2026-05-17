# Handoff

> Update this file at the end of every PR.

## Last completed change

Completed MusicGen-medium consolidation + synth-quality/doc roadmap update PR scope:

- Consolidated default offline neural path to MusicGen Medium only (`download_models.py`, backend registration, MusicGen backend model path).
- Added sample drop-in scaffold under `samples/` with committed `.gitkeep` structure and documentation.
- Added additive DSP quality modules (`chorus`, Schroeder `reverb` helper, stereo imaging), loop crossfade baking, and mastering profile presets.
- Upgraded core procedural instrument voicing for strings/brass/piano/choir/flute/bass/synth-pad/percussion.
- Refreshed roadmap/state docs (`NEXT_PR_SEQUENCE.md`, `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `SESSION_QUEUE.md`).

## Verified in this session

```bash
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m pytest tests/test_musicgen_backend.py tests/test_dsp_chorus.py tests/test_dsp_reverb.py tests/test_dsp_stereo.py tests/test_loop_exporter.py
```

Observed result:
- baseline tests and asset-manifest validation passed before changes
- focused tests for new MusicGen backend + DSP/loop modules pass
- docs/roadmap updates reflect MusicGen-medium single-model direction and inserted SESSION-028b/028c planning

## Immediate next best task

Execute `SESSION-028` from `docs/AI_FACTORY/SESSION_QUEUE.md` to add `audio-engine verify-backends` preflight reporting for optional neural backend readiness.

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
- [x] Optional provenance sidecars for legacy request-file execution path (SESSION-023)
- [x] Result-JSON sourced review-log writing for legacy request-file workflow (SESSION-024)
- [x] Queue advancement and next executable session definition (SESSION-025)
- [x] Legacy request-file batch-manifest parity without result-json breakage (SESSION-026)
- [x] Queue advancement and next executable session definition (SESSION-027)
