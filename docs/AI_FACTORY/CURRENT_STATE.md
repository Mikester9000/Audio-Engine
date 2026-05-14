# Current State

> Update this file whenever implementation scope, commands, workflows, or limitations change.

## Current snapshot

The repository contains a working Python audio engine with tests, a manifest validation workflow, a stronger repo-memory plus session-autopilot and execution-safety layer for low-prompt AI execution, typed loader primitives for committed audio-plan and generation-request artifacts, and now a request-batch generation command that executes those artifacts deterministically.

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
| Request-batch generation pipeline | Implemented | `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline`), `audio_engine/cli.py` (`generate-request-batch`) |
| Per-request provenance sidecar files | Implemented | `audio_engine/integration/asset_pipeline.py` (`_write_provenance`) | 2026-05-14 | `pytest`, smoke run | Each successfully generated audio file now has a `<stem>.provenance.json` sidecar with requestId, seed, backend, reviewStatus, generatedAt, and output paths. |
| Batch QA gate command | Implemented | `audio_engine/cli.py` (`qa-batch`) | 2026-05-14 | `pytest`, smoke run | `qa-batch --input-dir <dir>` runs LoudnessMeter, ClippingDetector, optional LoopAnalyzer on all WAVs; writes JSON report; non-zero exit on failure. |
| Manifest validation docs + CI | Implemented | `docs/asset-manifest.md`, `.github/workflows/validate-assets.yml` |
| Implementation matrix / codebase map / next PR sequence | Implemented (docs layer) | `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`, `docs/AI_FACTORY/CODEBASE_MAP.md`, `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md` |
| Example plan/request/review artifacts | Implemented (docs contracts) | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/*` |
| Session queue / autopilot control docs | Implemented (docs layer) | `docs/AI_FACTORY/SESSION_QUEUE.md`, `docs/AI_FACTORY/SESSION_STATE.json`, `docs/AI_FACTORY/CURRENT_SESSION.json` |
| Final execution-safety hardening docs | Implemented (docs layer) | `docs/AI_FACTORY/SESSION_GATE_RULES.md`, `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`, `docs/AI_FACTORY/VERIFICATION_PROFILES.md`, `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`, `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`, `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md` |
| Automated test suite | Implemented | `tests/` |

### Commands verified in this session

```bash
pip install -e ".[dev]"
python -m pytest
# 338 passed (was 334 before SESSION-003)
python tools/validate-assets.py assets/examples/ --verbose
# SFX batch smoke run (also writes provenance sidecars)
audio-engine generate-request-batch \
  --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json \
  --output-dir /tmp/session003_smoke
```

Observed result in this session:

- `338 passed` in pytest (up from 334 before SESSION-003)
- asset example manifests passed validation
- SFX batch smoke run produced 5 WAV files + 5 `.provenance.json` sidecars in `/tmp/session003_smoke/drafts/sfx/`
- each provenance file contained `requestId`, `seed`, `backend`, `reviewStatus`, `generatedAt`, `generatedOutputPath`, and `targetImportPath`
- QA batch smoke run (SESSION-004): 5 SFX files checked; 4 pass, 1 fail (sfx_ui_cancel.wav at -6.37 LUFS)
- test count: 345 passed (up from 338)

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
└── .github/workflows/validate-assets.yml
```

## Current strengths

1. Real code already exists for music, SFX, and voice generation.
2. The CLI already supports one-off generation, game-asset batch generation, and request-batch generation.
3. The integration layer already knows how to produce organized `music/`, `sfx/`, and `voice/` outputs.
4. The repository already has broad automated test coverage.
5. The backend system is already extensible enough to support future local model integrations.
6. Request-batch generation is now deterministic: each request's seed is passed explicitly per-request.

## Current limitations

1. The default backend is still primarily procedural rather than modern neural generation.
2. The current asset pipeline is aimed at `Game Engine for Teaching`, not yet fully generalized for `GameRewritten`.
3. Voice generation exists but should be treated as lower priority and lower fidelity than music/SFX.
4. There is now a committed `GameRewritten`-oriented vertical-slice example plan and request set, but there is not yet full-game taxonomy coverage in executable code.
7. The repo now has a session queue/autopilot layer; queued execution continues with SESSION-005.
8. OGG export requires the optional `soundfile` dependency; the pipeline falls back to WAV when it is not installed.
9. Per-request provenance sidecars are written with `reviewStatus: "draft"` from the request; there is not yet an approval/promotion workflow.
10. The `qa-batch` command provides batch QA reports but is not yet wired into CI.
11. Generated assets currently live in `drafts/` only; there is not yet an export step to place them in the downstream game's `Content/Audio/` layout.

## Current blockers

| Blocker | Why it matters | Suggested next move |
|---|---|---|
| No export step to game layout | Factory cannot produce a deployable deliverable | Implement GameRewritten export profile (SESSION-005) |
| No approval/promotion workflow | Provenance reviews remain at `"draft"` with no path to `approved/` | Add approval command after export profile exists |
| No QA gate wired into CI | QA is manual/local only | Wire `qa-batch` into CI workflow after export is established |

## Existing GitHub Actions state

Current workflow found:

- `Validate Asset Manifests` in `.github/workflows/validate-assets.yml`

That workflow validates manifests, but there is currently no workflow that validates the new AI-factory docs or audio outputs.

## Immediate interpretation

This repo is now a capable **procedural audio generation toolkit** with typed loading for committed factory-input artifacts, a working deterministic request-batch generation command, per-request provenance sidecar files, and a batch QA gate command. The next gap is an export step that places approved assets into the downstream game's `Content/Audio/` layout (SESSION-005).
