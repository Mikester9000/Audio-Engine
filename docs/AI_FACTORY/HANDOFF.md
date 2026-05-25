# Handoff

> Update this file at the end of every PR.

## Last completed change

Implemented additive PS2-era instrument-variety and realism expansion:

- Added three new PS2-oriented instrument timbres in `audio_engine/synthesizer/instrument.py`:
  - `legato_strings_ps2`
  - `nylon_guitar_ps2`
  - `soft_epiano_ps2`
- Tuned **all instruments** via a shared PS2-era realism voicing pass in `Instrument.render()`:
  - console-style bandwidth contour
  - gentle bus compression
  - subtle room glue
- Expanded FF-era style variety and realism by integrating new timbres into core presets:
  - `ff7_overworld`, `ff7_sad`, `ff8_ballad`, `ff10_calm`, `ff10_battle`, `ff10_zanarkand`
- Added/updated regression coverage in:
  - `tests/test_instrument.py` (new bow-bloom, nylon attack-decay, and soft-epiano tine-presence checks)

## Verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_instrument.py tests/test_generator.py -k "legato_strings_ps2 or nylon_guitar_ps2 or soft_epiano_ps2 or style_alignment"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
```

Observed result:
- Targeted instrument/style-alignment slices pass
- Full test suite passes
- Asset manifest validation passes

## Immediate next best task

Continue iterative FF-era instrument realism refinement for remaining families (woodwinds/brass/percussion) while preserving deterministic generation and style-alignment gate guarantees.

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
- [x] **Vertical-slice release gate automation** (`run-release-gate` CLI + `VerticalSliceGatePipeline`, SESSION-041)
- [x] **Studio full-edit + style/synth alignment expansion** (`audio_engine studio` advanced controls, new styles/instruments/SFX, SESSION-049)
- [x] **PS2 instrument identity refinement** (`piano` + guitar-family timbre updates, SESSION-051)
