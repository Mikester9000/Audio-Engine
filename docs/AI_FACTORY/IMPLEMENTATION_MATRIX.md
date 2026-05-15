# Implementation Matrix

> Canonical implementation-status matrix for AI agents. Update this file when implementation state, verification evidence, or source-of-truth paths change.

## Status legend

- `implemented` = real code path exists now
- `partial` = code exists but scope is limited
- `docs-contract` = documented contract only, not implemented in code
- `planned` = intended future work with no active code path
- `blocked` = cannot proceed without external dependency or prerequisite

## A. Implemented code or operational control layer

| Capability | State | Source of truth | Last verified | Verification command | Notes / next step |
|---|---|---|---|---|---|
| Python package + CLI install path | implemented | `pyproject.toml`, `audio_engine/cli.py` | 2026-05-14 | `pip install -e ".[dev]"` | Keep as baseline for all future work. |
| Music generation (style + prompt) | implemented | `audio_engine/engine.py`, `audio_engine/ai/generator.py`, `audio_engine/ai/music_gen.py` | 2026-05-15 | `pytest` | CLI now supports backend selection via `generate-music --backend <name>`. |
| SFX generation (prompt/procedural) | implemented | `audio_engine/ai/sfx_gen.py`, `audio_engine/ai/sfx_synth.py` | 2026-05-15 | `pytest` | CLI now supports backend selection via `generate-sfx --backend <name>`. |
| Voice generation (prototype-grade) | partial | `audio_engine/ai/voice_gen.py`, `audio_engine/ai/voice_synth.py` | 2026-05-15 | `pytest` | CLI now supports backend selection via `generate-voice --backend <name>`; voice remains lower priority than music/SFX. |
| DSP / mastering | implemented | `audio_engine/dsp/*`, `audio_engine/render/offline_bounce.py` | 2026-05-14 | `pytest` | Use as current quality floor before backend expansion. |
| Audio QA primitives | implemented | `audio_engine/qa/*`, `audio_engine/cli.py` (`qa`, `qa-batch`) | 2026-05-15 | `pytest` | Single-file `qa` and batch `qa-batch` commands; JSON report with per-file loudness/clipping/loop results. |
| Fixed-map batch generation pipeline | implemented | `audio_engine/integration/asset_pipeline.py`, `audio_engine/integration/game_state_map.py` | 2026-05-14 | `pytest` | Works for current integration map; not plan-driven. |
| Request-batch generation pipeline | implemented | `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline`), `audio_engine/cli.py` (`generate-request-batch`) | 2026-05-15 | `pytest`, smoke run | Executes any `GenerationRequestBatch` deterministically with per-request seeds and per-request backend selection; requested format is strict (no OGG→WAV fallback). |
| Plan-driven batch orchestration | implemented | `audio_engine/integration/asset_pipeline.py` (`PlanBatchOrchestrator`), `audio_engine/cli.py` (`generate-plan-batch`) | 2026-05-15 | `pytest`, `/tmp` smoke run | Uses `audio_plan.*.json` targets to select/order requests from one or more request batches; missing required targets fail fast. |
| Backend registry discovery in CLI | implemented | `audio_engine/ai/backend.py`, `audio_engine/cli.py` (`list-backends`) | 2026-05-15 | `pytest` | Backends are listable via CLI for explicit availability/discovery before generation runs; evaluation guidance is documented in `SUBSYSTEMS/MUSIC.md` and `SCHEMAS/GENERATION_REQUEST_SCHEMA.md`. |
| Draft approval workflow | implemented | `audio_engine/integration/asset_pipeline.py` (`ApprovalWorkflow`), `audio_engine/cli.py` (`approve-draft`) | 2026-05-15 | `pytest`, smoke run | `approve-draft --factory-root <dir> --draft-file <path>` copies audio to `approved/<type>/`, updates provenance `reviewStatus` to `"approved"`, writes `approvedAt` timestamp. |
| QA gate wired into CI | implemented | `.github/workflows/audio-qa.yml` | 2026-05-15 | GitHub Actions | Generates SFX batch and runs `qa-batch` on pushes/PRs touching audio source, tests, example fixtures, or the workflow file (path-filtered); fails CI if any file fails loudness/peak/clipping. |
| Music-duration policy | implemented (docs) | `docs/AI_FACTORY/SUBSYSTEMS/MUSIC.md`, `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`, `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md` | 2026-05-15 | Manual doc review | Long-form up to 5 min for major themes; 60–120 s gameplay loops; 90–180 s boss loops; OST variants now represented in committed request fixtures for key BGM tracks. |
| Asset-manifest schema validation | implemented | `tools/validate-assets.py`, `.github/workflows/validate-assets.yml`, `assets/schema/*` | 2026-05-14 | `python tools/validate-assets.py assets/examples/ --verbose` | Extend idea to future audio-plan/request validation when implemented. |
| Session-control / autopilot docs layer | implemented | `docs/AI_FACTORY/SESSION_QUEUE.md`, `docs/AI_FACTORY/CURRENT_SESSION.json`, `docs/AI_FACTORY/DONE_CRITERIA.md`, `docs/AI_FACTORY/SESSION_GATE_RULES.md`, `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`, `docs/AI_FACTORY/NO_DECISION_ZONES.md`, `docs/AI_FACTORY/FAILSAFE_RULES.md`, `docs/AI_FACTORY/VERIFICATION_PROFILES.md`, `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md`, `docs/AI_FACTORY/PR_AUTOPILOT_CHECKLIST.md`, `docs/AI_FACTORY/SESSION_STATE.json` | 2026-05-14 | Manual doc review | Treat `SESSION_QUEUE.md` as the canonical single-session controller and `CURRENT_SESSION.json` as the detailed machine-readable session contract. |
| Canonical output-layout + full-game coverage docs | implemented | `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`, `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`, `docs/AI_FACTORY/HUMAN_COMMANDS.md` | 2026-05-14 | Manual doc review | Keeps future agents aligned on output targets, coverage expectations, and low-prompt interaction model before code-side implementation expands. |

## B. Documentation-driven capabilities with partial or docs-only implementation

| Capability | State | Source of truth doc | Last verified | Verification command | Notes / next step |
|---|---|---|---|---|---|
| Project-level audio plan format | implemented | `docs/AI_FACTORY/SCHEMAS/AUDIO_PLAN_SCHEMA.md`, `audio_engine/integration/factory_inputs.py`, `audio_engine/integration/asset_pipeline.py` | 2026-05-15 | `pytest`, `/tmp` smoke run | Typed plan loading now drives batch orchestration via `PlanBatchOrchestrator` and `generate-plan-batch`. |
| Generation request format with seed/provenance fields | implemented | `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md`, `audio_engine/integration/factory_inputs.py`, `audio_engine/integration/asset_pipeline.py` | 2026-05-14 | `pytest` | Typed batch/request loading, execution, and per-request `.provenance.json` sidecar writing all implemented. |
| Backend evaluation + dependency/availability guidance | docs-contract | `docs/AI_FACTORY/SUBSYSTEMS/MUSIC.md`, `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md` | 2026-05-15 | Manual doc review | Documents truthful current backend state (`procedural`) plus additive future-adapter evaluation guidance without overclaiming model quality. |
| Repeated-SFX variation strategy guidance | docs-contract | `docs/AI_FACTORY/SUBSYSTEMS/SFX.md`, `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md` | 2026-05-15 | Manual doc review | Documents deterministic variant-per-request guidance (stable naming + seed capture); runtime variation selection remains unimplemented. |
| AI factory review-state workflow | docs-contract | `docs/AI_FACTORY/QA/REVIEW_WORKFLOW.md` | 2026-05-14 | Manual doc review | Add machine-readable review log writer. |
| `GameRewritten` vertical-slice examples | docs-contract | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/*` | 2026-05-15 | `pytest`, JSON parse checks | Expanded taxonomy fixtures now include ambience, fanfares/stingers, expanded UI/combat/spell SFX, tension/sadness music, optional voice placeholders, and key BGM OST request entries. |

## C. Planned / blocked work

| Capability | State | Source of truth | Last verified | Verification command | Notes / next step |
|---|---|---|---|---|---|
| Plan-driven batch orchestration | implemented | `audio_engine/integration/asset_pipeline.py` (`PlanBatchOrchestrator`), `audio_engine/cli.py` (`generate-plan-batch`), `audio_engine/integration/factory_inputs.py` | 2026-05-15 | `pytest`, `/tmp` smoke run | Direct audio-plan-driven orchestration is implemented and routes through provenance-enabled request-batch execution; requested `.ogg` must be produced when specified. |
| Deterministic provenance capture per generated asset | implemented | `audio_engine/integration/asset_pipeline.py` (`_write_provenance`) | 2026-05-14 | `pytest`, smoke run | `.provenance.json` sidecar per generated file; fields: requestId, seed, backend, reviewStatus, generatedAt. |
| Automated QA gate for generated outputs in CI | implemented | `.github/workflows/audio-qa.yml` | 2026-05-15 | GitHub Actions | Generates SFX batch and runs `qa-batch`; fails CI if any file fails QA. |
| `GameRewritten` import automation | implemented | `audio_engine/integration/asset_pipeline.py` (`DraftExportPipeline`), `audio_engine/cli.py` (`export-drafts`) | 2026-05-14 | `pytest`, smoke run | Copies drafts to `exports/gamerewritten/Content/Audio/` using `targetImportPath` from provenance sidecars; writes export manifest. Approval workflow (`approve-draft`) also implemented. |
| Full game-audio coverage tracking (music + SFX + ambience + fanfares + optional voice) | partial | `docs/AI_FACTORY/TARGET_STATE.md`, `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md`, `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/*`, `docs/AI_FACTORY/TASKS/BACKLOG.md` | 2026-05-15 | Manual taxonomy checklist review, JSON parse checks | Committed fixture taxonomy now covers major families; executable plan-driven orchestration remains pending. |
