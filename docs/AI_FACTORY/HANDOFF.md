# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-052: Landed Kokoro 0.9.4 compatibility, MusicGen Small backend support, Studio ergonomics, and voice-synth intelligibility fixes:

- **`audio_engine/ai/backends/kokoro_backend.py`**: Updated the Kokoro integration for the 0.9.x `KPipeline` result shape/API while keeping graceful fallback behavior.
- **`audio_engine/ai/backends/musicgen_backend.py` / `audio_engine/ai/backends/__init__.py` / `tools/download_models.py`**: Added `musicgen-small` model-path support, a dedicated `MusicGenSmallBackend`, and downloader coverage for `facebook/musicgen-small`.
- **`audio_engine/ui/studio.py`**: Improved Studio ergonomics with a larger window, per-control value labels, browse buttons for path fields, and style metadata guidance in the Music tab.
- **`audio_engine/ai/voice_synth.py`**: Reworked procedural intelligibility with clearer word boundaries, vowel/consonant shaping, nasal/plosive handling, and post-processing presence control.

## Verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_studio_ui.py tests/test_musicgen_backend.py -v
```

Observed result:
- Focused Studio + MusicGen backend tests pass
- Continuity and inventory docs updated to match SESSION-052

## Immediate next best task

Continue iterative named-instrument identity refinement for additional timbres (woodwinds/brass/percussion) while preserving deterministic style profiles. Alternatively, add Synth Workbench quick-start presets (kick, hi-hat, bass sub, pad) for faster manual creation workflows.

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
- [x] **Windows setup fix + Synth Workbench GUI** (`setup.bat` mode selector, `tools/download_models.py` robustness, `_build_synth_patch` / `_export_synth_patch`, Synth Workbench notebook tab)
- [x] **Release-gate alignment CLI + remediation docs** (`check-style-alignment` command, 5 CLI smoke tests, `SUBSYSTEMS/MUSIC.md` remediation flow, SESSION-050)


- **`setup.bat`**: Rewrote with interactive mode selector — mode 1 (manual/procedural, instant, no AI) uses `pip install -e "."` and skips model download; mode 2 (AI workflow) retains `.[neural]`→`.[musicgen]` fallback and attempts model download as a non-blocking warning rather than a hard failure.
- **`tools/download_models.py`**: Removed deprecated `local_dir_use_symlinks=False` and `resume_download=True` arguments from `snapshot_download()`; made `huggingface_hub` import lazy so `--skip` works without AI extras; added `--skip` flag that prints manual model-placement instructions instead of downloading; `main()` now accepts `argv` parameter for testability.
- **`audio_engine/ui/studio.py`**: Added `_SYNTH_WAVEFORMS`, `_SYNTH_FILTER_TYPES` constants; added `_build_synth_patch()` (oscillator + ADSR + filter → numpy array) and `_export_synth_patch()` (write WAV) helpers; added **Synth Workbench** tab to the notebook with waveform/frequency/duration/amplitude/ADSR/filter controls and a **Generate WAV** button.
- **`audio_engine/ui/__init__.py`**: Exported `_build_synth_patch` and `_export_synth_patch`.
- **`tests/test_studio_ui.py`**: Added 24 new synth workbench helper tests.
- **`tests/test_download_models.py`**: New file, 9 tests for download helper behavior.
- **`WINDOWS_QUICKSTART.md`**: Rewritten to describe new mode selector, Synth Workbench, and `--skip` troubleshooting.
- **Continuity docs** (`CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`): Updated to reflect new subsystems.

## Verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_studio_ui.py tests/test_download_models.py -v
python -m pytest
```

Observed result:
- 33 new tests pass (24 synth workbench + 9 download_models)
- Full test suite passes

## Immediate next best task

Continue iterative named-instrument identity refinement for additional timbres (woodwinds/brass/percussion) while preserving deterministic style profiles. Alternatively, add Synth Workbench quick-start presets (kick, hi-hat, bass sub, pad) for faster manual creation workflows.

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
- [x] **Windows setup fix + Synth Workbench GUI** (`setup.bat` mode selector, `tools/download_models.py` robustness, `_build_synth_patch` / `_export_synth_patch`, Synth Workbench notebook tab)
