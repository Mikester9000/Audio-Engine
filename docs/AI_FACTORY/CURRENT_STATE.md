# Current State

> Update this file whenever implementation scope, commands, workflows, or limitations change.

## Current snapshot

The repository contains a working Python audio engine with tests, a manifest validation workflow, a stronger repo-memory plus session-autopilot and execution-safety layer for low-prompt AI execution, typed loader primitives for committed audio-plan and generation-request artifacts, deterministic request-batch generation with provenance sidecars, plan-driven batch orchestration, a batch QA gate, a GameRewritten export profile, an approval workflow that promotes drafts to `approved/`, and a CI QA gate workflow. Music-duration policy is clearly documented, taxonomy fixtures now cover ambience/fanfares/stingers/expanded SFX/tension/sadness/optional voice, and backend evaluation plus repeated-SFX variation rules now have executable code paths. Category-specific SFX/ambience loudness-readability guidance and variant-family review/report templates are now documented for consistent manual QA decisions, review logs now have an executable writer path integrated with approval/export handoff, and both the newer request-batch pipeline and the backward-compatible legacy request-file path now support explicit per-request duration control for music/SFX.

## What is implemented today

### Confirmed working subsystems

| Subsystem | Status | Evidence |
|---|---|---|
| Python package install | Implemented | `pyproject.toml` |
| Top-level `AudioEngine` façade | Implemented | `audio_engine/engine.py` |
| CLI for music/SFX/voice/QA | Implemented | `audio_engine/cli.py` |
| Procedural music generation | Implemented | `audio_engine/ai/generator.py`, `audio_engine/ai/music_gen.py` |
| Procedural SFX generation | Implemented | `audio_engine/ai/sfx_gen.py`, `audio_engine/ai/sfx_synth.py` |
| Basic local voice synthesis | Implemented | `audio_engine/ai/voice_gen.py`, `audio_engine/ai/voice_synth.py` |
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
| Repeated SFX variation strategy guidance | Implemented (factory-side) | `audio_engine/integration/factory_inputs.py` (variant-family validation), `audio_engine/integration/asset_pipeline.py` (variant provenance fields) |
| Category-specific SFX loudness/readability guidance | Implemented (docs) | `docs/AI_FACTORY/SUBSYSTEMS/SFX.md`, `docs/AI_FACTORY/QA/QUALITY_BARS.md` |
| Variant-family QA review/report templates | Implemented (docs-contract) | `docs/AI_FACTORY/QA/REVIEW_WORKFLOW.md`, `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json` |
| Machine-readable review-log writer + handoff integration | Implemented | `audio_engine/integration/asset_pipeline.py` (`ReviewLogWriter`), `audio_engine/cli.py` (`write-review-log`, review-log flags on `approve-draft`/`export-drafts`) |
| Optional request-level duration field for both request-batch entrypoints | Implemented | `audio_engine/integration/factory_inputs.py` (`durationSeconds` parsing), `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline` and `AssetPipeline.execute_request_batch` duration resolution), `tests/test_integration.py`, `tests/test_engine_cli.py` |
| Automated test suite | Implemented | `tests/` |

### Commands verified in this session

```bash
python -m pytest tests/test_integration.py -k "request_duration_seconds or legacy-duration-tests or execute_request_batch_prefers_request_duration_seconds"
python -m pytest tests/test_engine_cli.py -k "request_duration_seconds or via_request_file"
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
python -m audio_engine.cli generate-request-batch --request-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json --output-dir /tmp/session021_legacy_smoke --sfx-duration 0.1 --quiet
```

Observed result in this session:

- legacy `AssetPipeline.execute_request_batch()` now honors request-level `durationSeconds` for music/SFX while preserving CLI duration flags as fallback defaults
- targeted integration tests passed (`2` selected tests) and targeted CLI tests passed (`3` selected tests)
- full repo test suite passed (`419`) and asset-manifest validation passed
- legacy CLI smoke run succeeded for the committed SFX fixture (`10` requests OK to `/tmp/session021_legacy_smoke`)

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

## Current limitations

1. The default backend is still primarily procedural rather than modern neural generation.
2. The current asset pipeline is aimed at `Game Engine for Teaching`, not yet fully generalized for `GameRewritten`.
3. Voice generation exists but should be treated as lower priority and lower fidelity than music/SFX.
4. Plan-driven orchestration currently requires explicit request-batch files that provide prompts/seeds/backends for all required plan targets; missing required requests are treated as execution errors.
5. The backward-compatible `--request-file` path still writes legacy outputs without the newer drafts/provenance sidecars by default, so downstream review/export automation is still richer on the `--batch-file` / plan-driven path.
6. OGG export depends on `soundfile`; `.ogg` requests fail (no fallback-to-WAV) when encoder support is unavailable.

## Current blockers

None blocking the next session.

## Existing GitHub Actions state

- `Validate Asset Manifests` in `.github/workflows/validate-assets.yml`
- `Audio QA Gate` in `.github/workflows/audio-qa.yml` (added this session)

## Immediate interpretation

This repo now has a complete draft-to-approved pipeline on the newer request-driven (`generate-request-batch --batch-file`) and plan-driven (`generate-plan-batch`) entrypoints: provenance sidecars → `qa-batch` → `export-drafts` → `approve-draft` → `approved/<type>/`. Requested `.ogg` outputs are strict in request-batch execution paths (no silent WAV fallback), backend selection/discovery includes executable backend evaluation metadata, repeated-SFX variation strategy has executable request-validation and provenance tracking support, review logs have executable generation/update surfaces (`write-review-log`, plus optional integration into approval/export commands), plan-driven orchestration enforces `durationTargetSeconds` on matched requests during execution, and the backward-compatible legacy `--request-file` path now matches explicit-duration behavior for music/SFX while remaining a lighter-weight surface.
