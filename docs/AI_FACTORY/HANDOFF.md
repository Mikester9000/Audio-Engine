# Handoff

> Update this file at the end of every PR.

## Last completed change

Implemented **SESSION-051**: PS2 instrument identity refinement (piano + guitar families).

- Refined `audio_engine/synthesizer/instrument.py` core timbres:
  - upgraded `piano` synthesis with detuned-string layering, hammer/key transients, and controlled body resonance
  - upgraded `electric_guitar` and `ff8_electric_guitar` with pick transients + cabinet-like post-EQ shaping
  - upgraded `acoustic_guitar` with stronger pluck/body resonance behavior and natural high-frequency decay
- Preserved PS2-era JRPG design target (FF8/FF10-like tonal aesthetic) by keeping constrained bandwidth, modest ambience, and deterministic synth behavior.
- Added regression checks in `tests/test_instrument.py`:
  - transient decay profile for piano
  - pick-brightness decay for acoustic guitar
  - midrange-presence guardrail for ff8 electric guitar

## Verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_instrument.py tests/test_ps1_era.py -k "instrument or guitar or piano"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
```

Observed result:
- Targeted instrument + PS-era slices pass (111 selected tests)
- Full test suite passes (1129 tests)
- Asset manifest validation passes

## Immediate next best task

Execute SESSION-050 to surface style/synth alignment validation in release-gate artifacts, then continue instrument-identity refinement for additional named timbres.

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
