# Current State

> Update this file whenever implementation scope, commands, workflows, or limitations change.

## Current snapshot

The repository contains a working Python audio engine with tests, a manifest validation workflow, a stronger repo-memory plus session-autopilot and execution-safety layer for low-prompt AI execution, typed loader primitives for committed audio-plan and generation-request artifacts, deterministic request-batch generation with provenance sidecars, plan-driven batch orchestration, a batch QA gate, a GameRewritten export profile, an approval workflow that promotes drafts to `approved/`, and a CI QA gate workflow. Music-duration policy is clearly documented, taxonomy fixtures now cover ambience/fanfares/stingers/expanded SFX/tension/sadness/optional voice plus a broader 21-piece music style/mood/environment testing set (driving through grand opera), and backend evaluation plus repeated-SFX variation rules now have executable code paths. Category-specific SFX/ambience loudness-readability guidance and variant-family review/report templates are now documented for consistent manual QA decisions, review logs now have executable writer paths integrated with approval/export handoff and request-batch result JSON ingestion, and both the newer request-batch pipeline and the backward-compatible legacy request-file path now support explicit per-request duration control for music/SFX. Procedural generation quality is now substantially upgraded with structured phrase planning, motif-bank reuse/variation, cadence-aware sectioning, 8-layer arrangement/voice management, distinct per-category SFX recipes, and richer deterministic voice synthesis. Studio workflow tooling is now expanded with preset save/load JSON controls, in-studio mastering-profile selection, one-click batch generation, and retry-last-error UX. Request-driven music workflows now also support deterministic dual-path delivery (`musicDeliveryMode: dual_vocal_instrumental`) with paired `__instrumental` + `__vocal_ready` outputs and explicit provenance linkage metadata. Music style coverage now also includes dedicated narrative/world presets (`stealth`, `memorial`, `mystery`, `underscore`, `ending`, regional exploration variants, and `transition_sting`) plus region-aware prompt shaping and optional adaptive layer-bundle export metadata from `MusicGen.generate_to_file(..., layer_output_dir=...)`. Windows one-click bootstrap files now exist (`setup.bat`, `run.bat`) with an idempotent model downloader (`tools/download_models.py`) and optional local-files-only neural backend adapters under `audio_engine/ai/backends/`. Backend preflight verification (`audio-engine verify-backends`) is now implemented. A `vocal_mix` mastering profile is now available in `OfflineBounce` and selectable via `--profile` on `generate-music`. WAV sample-folder ingestion contract, license inventory, commercial eligibility matrix, and autopilot command contracts are now documented. Deterministic sample-note scanning (`samples/orchestral`), DSP pitch-shifting, event-driven remastering (`audio-engine remaster --events-json`), and deterministic `audio-engine remaster-batch` result reporting are now implemented.

## What is implemented today

### Confirmed working subsystems

| Subsystem | Status | Evidence |
|---|---|---|
| Python package install | Implemented | `pyproject.toml` |
| Top-level `AudioEngine` façade | Implemented | `audio_engine/engine.py` |
| CLI for music/SFX/voice/QA | Implemented | `audio_engine/cli.py` |
| Procedural music generation (structured phrases + motif reuse) | Implemented | `audio_engine/ai/generator.py`, `audio_engine/composer/phrase.py`, `audio_engine/ai/music_gen.py` |
| Procedural SFX generation (distinct recipe families) | Implemented | `audio_engine/ai/sfx_gen.py`, `audio_engine/ai/sfx_synth.py` |
| Local voice synthesis (phoneme-aware voiced/unvoiced + prosody) | Implemented | `audio_engine/ai/voice_gen.py`, `audio_engine/ai/voice_synth.py` |
| Local Tkinter studio UI (`audio-engine studio`) | Implemented | `audio_engine/ui/studio.py`, `audio_engine/cli.py` |
| Studio creation-tooling preset/profile/batch/retry workflow | Implemented | `audio_engine/ui/studio.py`, `tests/test_studio_ui.py` |
| DSP/mastering/QA | Implemented | `audio_engine/dsp/*`, `audio_engine/render/*`, `audio_engine/qa/*` |
| Export to WAV / optional OGG | Implemented | `audio_engine/export/audio_exporter.py` |
| Batch game asset generation | Implemented | `audio_engine/integration/asset_pipeline.py` |
| Typed audio plan + generation request loading | Implemented | `audio_engine/integration/factory_inputs.py`, `tests/test_integration.py` |
| Request-batch generation pipeline | Implemented | `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline`, `AssetPipeline.execute_request_batch`), `audio_engine/cli.py` (`generate-request-batch`) |
| Plan-driven batch orchestration | Implemented | `audio_engine/integration/asset_pipeline.py` (`PlanBatchOrchestrator`), `audio_engine/cli.py` (`generate-plan-batch`) |
| Per-request provenance sidecar files | Implemented | `audio_engine/integration/asset_pipeline.py` (`_write_provenance`) |
| Batch QA gate command | Implemented | `audio_engine/cli.py` (`qa-batch`) |
| GameRewritten export profile | Implemented | `audio_engine/integration/asset_pipeline.py` (`DraftExportPipeline`), `audio_engine/cli.py` (`export-drafts`) |
| Approval workflow (draft → approved) | Implemented | `audio_engine/integration/asset_pipeline.py` (`ApprovalWorkflow`), `audio_engine/cli.py` (`approve-draft`) |
| QA gate wired into CI | Implemented | `.github/workflows/audio-qa.yml` |
| Music duration policy documented | Implemented (docs) | `docs/AI_FACTORY/SUBSYSTEMS/MUSIC.md` |
| Manifest validation docs + CI | Implemented | `docs/asset-manifest.md`, `.github/workflows/validate-assets.yml` |
| Implementation matrix / codebase map / next PR sequence | Implemented (docs layer) | `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`, `docs/AI_FACTORY/CODEBASE_MAP.md`, `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md` |
| Example plan/request/review artifacts | Implemented (docs contracts) | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/*` |
| Session queue / autopilot control docs | Implemented (docs layer) | `docs/AI_FACTORY/SESSION_QUEUE.md`, `docs/AI_FACTORY/SESSION_STATE.json`, `docs/AI_FACTORY/CURRENT_SESSION.json` |
| Final execution-safety hardening docs | Implemented (docs layer) | `docs/AI_FACTORY/SESSION_GATE_RULES.md`, `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`, `docs/AI_FACTORY/VERIFICATION_PROFILES.md`, `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md` |
| Full-game taxonomy fixture coverage | Implemented (docs fixtures) | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` |
| Backend discoverability, selection, and preflight verification | Implemented | `audio_engine/ai/backend.py` (`BackendRegistry.evaluate_backends`), `audio_engine/cli.py` (`list-backends`, `verify-backends`, `--backend` flags) |
| MusicGen Medium backend (single AI model) | Implemented | `audio_engine/ai/backends/musicgen_backend.py` |
| Optional neural backend adapters (local files only) | Implemented (optional runtime) | `audio_engine/ai/backends/*`, `tests/test_ai_pipeline.py` |
| Windows offline bootstrap workflow | Implemented | `setup.bat`, `run.bat`, `tools/download_models.py`, `WINDOWS_QUICKSTART.md` |
| Orchestral sample drop-in folder structure | Implemented (folder) | `samples/orchestral/*`, `samples/README.md` |
| Orchestral sample-note scanner + pitch-shift primitives | Implemented | `audio_engine/integration/sample_library.py`, `audio_engine/dsp/pitch_shift.py`, `tests/test_sample_library.py`, `tests/test_pitch_shift.py` |
| Deterministic remaster and remaster-batch workflows | Implemented | `audio_engine/render/remaster.py`, `audio_engine/integration/asset_pipeline.py` (`RemasterBatchPipeline`), `audio_engine/cli.py` (`remaster`, `remaster-batch`) |
| Synth chorus/reverb/stereo DSP modules | Implemented | `audio_engine/dsp/chorus.py`, `audio_engine/dsp/reverb.py`, `audio_engine/dsp/stereo.py` |
| Mastering profile presets (game, ost, youtube, vocal_mix, procedural_neutral) | Implemented | `audio_engine/render/offline_bounce.py` (`OfflineBounce`, `VALID_PROFILES`) |
| Mastering profile CLI flag (`--profile` on `generate-music`) | Implemented | `audio_engine/cli.py`, `audio_engine/ai/music_gen.py` (`mastering_profile` param) |
| Crossfade loop baking | Implemented | `audio_engine/render/loop_exporter.py` |
| Machine-readable review-log writer + handoff integration | Implemented | `audio_engine/integration/asset_pipeline.py` (`ReviewLogWriter`), `audio_engine/cli.py` (`write-review-log`) |
| Optional request-level duration field for both request-batch entrypoints | Implemented | `audio_engine/integration/factory_inputs.py`, `audio_engine/integration/asset_pipeline.py` |
| Optional dual-path music request delivery mode with provenance linkage | Implemented | `audio_engine/integration/factory_inputs.py` (`musicDeliveryMode`), `audio_engine/integration/asset_pipeline.py` (paired outputs + linked sidecars), `tests/test_integration.py` |
| Legacy request-file provenance sidecars + result-driven review-log sourcing + manifest parity | Implemented | `audio_engine/integration/asset_pipeline.py`, `audio_engine/cli.py` |
| WAV sample-folder ingestion contract (docs) | Implemented | `docs/AI_FACTORY/SCHEMAS/WAV_INGESTION_CONTRACT.md` |
| License inventory (docs) | Implemented | `docs/AI_FACTORY/LICENSE_INVENTORY.md` |
| Commercial eligibility matrix (docs) | Implemented | `docs/AI_FACTORY/COMMERCIAL_ELIGIBILITY_MATRIX.md` |
| Autopilot command contracts (docs) | Implemented | `docs/AI_FACTORY/AUTOPILOT_COMMAND_CONTRACTS.md` |
| Automated test suite | Implemented | `tests/` |

### Commands verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_ai_pipeline.py tests/test_integration.py -k "voice or dual_path or music_delivery_mode"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
```

Observed result in this session:

- baseline repo verification passed (full `pytest` 1048 passed + asset-manifest validation)
- targeted dual-path/voice integration tests passed (28 selected tests)
- session-control JSON files parse cleanly


## What is implemented today

### Confirmed working subsystems

| Subsystem | Status | Evidence |
|---|---|---|
| Python package install | Implemented | `pyproject.toml` |
| Top-level `AudioEngine` façade | Implemented | `audio_engine/engine.py` |
| CLI for music/SFX/voice/QA | Implemented | `audio_engine/cli.py` |
| Procedural music generation (structured phrases + motif reuse) | Implemented | `audio_engine/ai/generator.py`, `audio_engine/composer/phrase.py`, `audio_engine/ai/music_gen.py` |
| Procedural SFX generation (distinct recipe families) | Implemented | `audio_engine/ai/sfx_gen.py`, `audio_engine/ai/sfx_synth.py` |
| Local voice synthesis (phoneme-aware voiced/unvoiced + prosody) | Implemented | `audio_engine/ai/voice_gen.py`, `audio_engine/ai/voice_synth.py` |
| Local Tkinter studio UI (`audio-engine studio`) | Implemented | `audio_engine/ui/studio.py`, `audio_engine/cli.py` |
| DSP/mastering/QA | Implemented | `audio_engine/dsp/*`, `audio_engine/render/*`, `audio_engine/qa/*` |
| Export to WAV / optional OGG | Implemented | `audio_engine/export/audio_exporter.py` |
| Batch game asset generation | Implemented | `audio_engine/integration/asset_pipeline.py` |
| Typed audio plan + generation request loading | Implemented | `audio_engine/integration/factory_inputs.py`, `tests/test_integration.py` |
| Request-batch generation pipeline | Implemented | `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline`, `AssetPipeline.execute_request_batch`), `audio_engine/cli.py` (`generate-request-batch`) |
| Plan-driven batch orchestration | Implemented | `audio_engine/integration/asset_pipeline.py` (`PlanBatchOrchestrator`), `audio_engine/cli.py` (`generate-plan-batch`) |
| Per-request provenance sidecar files | Implemented | `audio_engine/integration/asset_pipeline.py` (`_write_provenance`) |
| Batch QA gate command | Implemented | `audio_engine/cli.py` (`qa-batch`) |
| GameRewritten export profile | Implemented | `audio_engine/integration/asset_pipeline.py` (`DraftExportPipeline`), `audio_engine/cli.py` (`export-drafts`) |
| Approval workflow (draft → approved) | Implemented | `audio_engine/integration/asset_pipeline.py` (`ApprovalWorkflow`), `audio_engine/cli.py` (`approve-draft`) |
| QA gate wired into CI | Implemented | `.github/workflows/audio-qa.yml` |
| Music duration policy documented | Implemented (docs) | `docs/AI_FACTORY/SUBSYSTEMS/MUSIC.md`, `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`, `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md` |
| Manifest validation docs + CI | Implemented | `docs/asset-manifest.md`, `.github/workflows/validate-assets.yml` |
| Implementation matrix / codebase map / next PR sequence | Implemented (docs layer) | `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`, `docs/AI_FACTORY/CODEBASE_MAP.md`, `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md` |
| Example plan/request/review artifacts | Implemented (docs contracts) | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/*` |
| Session queue / autopilot control docs | Implemented (docs layer) | `docs/AI_FACTORY/SESSION_QUEUE.md`, `docs/AI_FACTORY/SESSION_STATE.json`, `docs/AI_FACTORY/CURRENT_SESSION.json` |
| Final execution-safety hardening docs | Implemented (docs layer) | `docs/AI_FACTORY/SESSION_GATE_RULES.md`, `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`, `docs/AI_FACTORY/VERIFICATION_PROFILES.md`, `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`, `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`, `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md` |
| Full-game taxonomy fixture coverage | Implemented (docs fixtures) | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json`, `generation_requests.music.v1.json`, `generation_requests.sfx.v1.json`, `generation_requests.voice.v1.json`, `docs/AI_FACTORY/TASKS/BACKLOG.md` |
| Backend discoverability and selection CLI | Implemented | `audio_engine/cli.py` (`list-backends`, `--backend` on `generate-music`/`generate-sfx`/`generate-voice`) |
| Backend evaluation and availability guidance | Implemented | `audio_engine/ai/backend.py` (`BackendRegistry.evaluate_backends`), `audio_engine/cli.py` (`list-backends`) |
| MusicGen Medium backend (single AI model) | Implemented | `audio_engine/ai/backends/musicgen_backend.py` |
| Optional neural backend adapters (local files only) | Implemented (optional runtime) | `audio_engine/ai/backends/*`, `tests/test_ai_pipeline.py` |
| Windows offline bootstrap workflow | Implemented | `setup.bat`, `run.bat`, `tools/download_models.py`, `WINDOWS_QUICKSTART.md`, `models/README.md` |
| Orchestral sample drop-in folder structure | Implemented (folder) | `samples/orchestral/*`, `samples/README.md` |
| Synth chorus/reverb/stereo DSP modules | Implemented | `audio_engine/dsp/chorus.py`, `audio_engine/dsp/reverb.py`, `audio_engine/dsp/stereo.py` |
| Mastering profile presets | Implemented | `audio_engine/render/offline_bounce.py` |
| Crossfade loop baking | Implemented | `audio_engine/render/loop_exporter.py` |
| Duration stitching in MusicGen backend | Implemented | `audio_engine/ai/backends/musicgen_backend.py` |
| Repeated SFX variation strategy guidance | Implemented (factory-side) | `audio_engine/integration/factory_inputs.py` (variant-family validation), `audio_engine/integration/asset_pipeline.py` (variant provenance fields) |
| Category-specific SFX loudness/readability guidance | Implemented (docs) | `docs/AI_FACTORY/SUBSYSTEMS/SFX.md`, `docs/AI_FACTORY/QA/QUALITY_BARS.md` |
| Variant-family QA review/report templates | Implemented (docs-contract) | `docs/AI_FACTORY/QA/REVIEW_WORKFLOW.md`, `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json` |
| Machine-readable review-log writer + handoff integration | Implemented | `audio_engine/integration/asset_pipeline.py` (`ReviewLogWriter`), `audio_engine/cli.py` (`write-review-log`, review-log flags on `approve-draft`/`export-drafts`) |
| Optional request-level duration field for both request-batch entrypoints | Implemented | `audio_engine/integration/factory_inputs.py` (`durationSeconds` parsing), `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline` and `AssetPipeline.execute_request_batch` duration resolution), `tests/test_integration.py`, `tests/test_engine_cli.py` |
| Legacy request-file provenance sidecars + result-driven review-log sourcing + manifest parity | Implemented | `audio_engine/integration/asset_pipeline.py` (`AssetPipeline.execute_request_batch(write_provenance)` legacy `batch_manifest.json` writer, `ReviewLogWriter.append_from_result_json`), `audio_engine/cli.py` (`generate-request-batch --write-provenance`, `write-review-log --from-result`), `tests/test_integration.py`, `tests/test_engine_cli.py` |
| Spectral balance + intelligibility QA gate | Implemented | `audio_engine/qa/spectral_analyzer.py` (`SpectralAnalyzer`), `audio_engine/cli.py` (`qa`, `qa-batch`) |
| Deterministic commercial WAV delivery | Implemented | `audio_engine/integration/export_contract.py` (`WavDeliveryPipeline`), `audio_engine/cli.py` (`export-wav-delivery`) |
| Deterministic regression harness | Implemented | `tests/test_regression.py` |
| Seed policy (docs) | Implemented | `docs/AI_FACTORY/SEED_POLICY.md` |
| Commercial readiness audit (docs) | Implemented | `docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md` |
| Completion-state handoff (docs) | Implemented | `docs/AI_FACTORY/COMPLETION_HANDOFF.md` |
| Automated test suite | Implemented | `tests/` |

### Commands verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m pytest tests/test_integration.py -k "writes_batch_manifest_json and execute_request_batch"
python -m pytest tests/test_engine_cli.py -k "request_file_writes_batch_manifest_json"
```

Observed result in this session:

- baseline repo verification passed (full `pytest` + asset-manifest validation)
- legacy request-file batch-manifest parity targeted integration/CLI tests passed

## Current repository structure

```text
/home/runner/work/Audio-Engine/Audio-Engine/
├── README.md
├── pyproject.toml
├── audio_engine/
├── tests/
├── assets/
├── docs/
├── tools/
└── .github/workflows/
    ├── validate-assets.yml
    └── audio-qa.yml         ← NEW (SESSION-007)
```

## Current strengths

1. Real code already exists for music, SFX, and voice generation.
2. The CLI supports one-off generation, game-asset batch generation, request-batch generation, QA, export, and now approval.
3. The approval workflow allows explicit draft → approved promotion with provenance tracking.
4. The QA gate is now wired into CI; QA failures block the PR.
5. Music-duration policy is clearly documented: long-form up to 5 minutes for major themes, loopable 60–120 s for gameplay BGM, OST variants planned for key tracks.
6. Request-batch generation is deterministic: each request's seed is passed explicitly per-request.
7. Single AI model (MusicGen Medium) covers music and SFX with no model-switching overhead.
8. Orchestral sample drop-in folder structure is ready for user-provided WAV libraries.
9. Procedural mastering now includes a `youtube` profile for broadcast/streaming-targeted output.

## Current limitations

1. Neural backend use is optional and gated by local dependency/model availability; procedural remains default fallback and voice uses built-in synthesis by default.
2. The current asset pipeline is aimed at `Game Engine for Teaching`, not yet fully generalized for `GameRewritten`.
3. Voice generation exists but should be treated as lower priority and lower fidelity than music/SFX.
4. Plan-driven orchestration currently requires explicit request-batch files that provide prompts/seeds/backends for all required plan targets; missing required requests are treated as execution errors.
5. The backward-compatible `--request-file` path now writes additive `batch_manifest.json` parity by default, while richer sidecar/result artifacts remain opt-in via `--write-provenance` and `--write-result`.
6. OGG export depends on `soundfile`; `.ogg` requests fail (no fallback-to-WAV) when encoder support is unavailable.

## Current blockers

None blocking the next session.

## Existing GitHub Actions state

- `Validate Asset Manifests` in `.github/workflows/validate-assets.yml`
- `Audio QA Gate` in `.github/workflows/audio-qa.yml` (added this session)

## Immediate interpretation

This repo now has a complete draft-to-approved pipeline on the newer request-driven (`generate-request-batch --batch-file`) and plan-driven (`generate-plan-batch`) entrypoints: provenance sidecars → `qa-batch` → `export-drafts` → `approve-draft` → `approved/<type>/`. Requested `.ogg` outputs are strict in request-batch execution paths (no silent WAV fallback), backend selection/discovery includes executable backend evaluation metadata, repeated-SFX variation strategy has executable request-validation and provenance tracking support, review logs have executable generation/update surfaces (`write-review-log`, optional integration into approval/export commands, and result-JSON sourcing via `--from-result`), plan-driven orchestration enforces `durationTargetSeconds` on matched requests during execution, and the backward-compatible legacy `--request-file` path now supports explicit-duration behavior plus optional provenance sidecars plus additive `batch_manifest.json` parity output while remaining compatibility-safe. Additional deterministic remaster capability is now implemented through an orchestral sample-note scanner, event-driven `remaster`, and machine-readable `remaster-batch` outcomes. Session-control continuity is synchronized with SESSION-032 queued as the active next implementation session (license compliance CI gate).
