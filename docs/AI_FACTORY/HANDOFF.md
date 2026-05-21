# Handoff

> Update this file at the end of every PR.

## Last completed change

Completed **SESSION-038** (dual-path vocal/instrumental workflow stabilization):

- Added additive request schema support in `audio_engine/integration/factory_inputs.py`:
  - optional `musicDeliveryMode` field
  - currently supported value: `dual_vocal_instrumental` (music requests only)
- Implemented deterministic paired output generation in both request-batch execution paths:
  - `RequestBatchPipeline.execute(...)`
  - `AssetPipeline.execute_request_batch(...)`
- Dual-path mode now produces paired files with stable suffixes:
  - `__instrumental`
  - `__vocal_ready`
- Added explicit provenance linkage metadata for both paired outputs:
  - `dualPathGroupId`
  - `dualPathRole`
  - `pairedOutputPath`
- Added focused parser/pipeline tests in `tests/test_integration.py` for:
  - `musicDeliveryMode` parsing/validation
  - dual-path paired output generation
  - provenance linkage correctness

## Verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_ai_pipeline.py tests/test_integration.py -k "voice or dual_path or music_delivery_mode"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
```

Observed result:
- Targeted dual-path/voice integration slice passes (28 selected tests)
- Full test suite passes (1048 tests)
- Asset manifest validation passes
- Session-control JSON files parse cleanly

## Immediate next best task

Execute **SESSION-041** (end-to-end vertical-slice release gate automation).

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`
5. `docs/AI_FACTORY/ACTIVE_WORK.md`
6. `docs/AI_FACTORY/COMPLETION_HANDOFF.md`

## Handoff checklist

- [x] Request-batch generation command (`generate-request-batch`)
- [x] Per-request provenance sidecar files (`.provenance.json`)
- [x] Batch QA gate command (`qa-batch` with JSON report)
- [x] Spectral balance + intelligibility QA gates (`SpectralAnalyzer`, SESSION-036)
- [x] GameRewritten export profile (`export-drafts` to `Content/Audio/`)
- [x] Commercial WAV delivery (`export-wav-delivery` with deterministic naming, SESSION-037)
- [x] Deterministic remaster pipeline (`audio_engine/render/remaster.py`, `audio-engine remaster --events-json`, SESSION-028c)
- [x] Deterministic remaster-batch pipeline (`RemasterBatchPipeline`, `audio-engine remaster-batch`, SESSION-031)
- [x] Approval workflow (`approve-draft` → `approved/<type>/`, updates provenance)
- [x] QA gate wired into CI (`.github/workflows/audio-qa.yml`)
- [x] Deterministic regression harness (`tests/test_regression.py`, SESSION-040)
- [x] Seed policy locked (`docs/AI_FACTORY/SEED_POLICY.md`, SESSION-043)
- [x] Commercial readiness audit evidence (`docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md`, SESSION-044)
- [x] Completion-state handoff (`docs/AI_FACTORY/COMPLETION_HANDOFF.md`, SESSION-045)
- [x] Session control docs synchronized (SESSION_QUEUE, SESSION_STATE, CURRENT_SESSION, FACTORY_STATUS, ACTIVE_WORK)
