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
| Music generation (style + prompt) | implemented | `audio_engine/engine.py`, `audio_engine/ai/generator.py`, `audio_engine/ai/music_gen.py` | 2026-05-14 | `pytest` | Extend with plan/request ingestion later, do not break existing commands. |
| SFX generation (prompt/procedural) | implemented | `audio_engine/ai/sfx_gen.py`, `audio_engine/ai/sfx_synth.py` | 2026-05-14 | `pytest` | Add broader variation control in later PRs. |
| Voice generation (prototype-grade) | partial | `audio_engine/ai/voice_gen.py`, `audio_engine/ai/voice_synth.py` | 2026-05-14 | `pytest` | Keep low priority; useful for placeholders only. |
| DSP / mastering | implemented | `audio_engine/dsp/*`, `audio_engine/render/offline_bounce.py` | 2026-05-14 | `pytest` | Use as current quality floor before backend expansion. |
| Audio QA primitives | implemented | `audio_engine/qa/*`, `audio_engine/cli.py` (`qa`) | 2026-05-14 | `pytest` | Missing batch QA gate workflow over generated sets. |
| Fixed-map batch generation pipeline | implemented | `audio_engine/integration/asset_pipeline.py`, `audio_engine/integration/game_state_map.py` | 2026-05-14 | `pytest` | Works for current integration map; not plan-driven. |
| Request-batch generation pipeline | implemented | `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline`), `audio_engine/cli.py` (`generate-request-batch`) | 2026-05-14 | `pytest`, smoke run | Executes any `GenerationRequestBatch` deterministically with per-request seeds; outputs in `<output_dir>/drafts/<type>/`. |
| Asset-manifest schema validation | implemented | `tools/validate-assets.py`, `.github/workflows/validate-assets.yml`, `assets/schema/*` | 2026-05-14 | `python tools/validate-assets.py assets/examples/ --verbose` | Extend idea to future audio-plan/request validation when implemented. |
| Session-control / autopilot docs layer | implemented | `docs/AI_FACTORY/SESSION_QUEUE.md`, `docs/AI_FACTORY/CURRENT_SESSION.json`, `docs/AI_FACTORY/DONE_CRITERIA.md`, `docs/AI_FACTORY/SESSION_GATE_RULES.md`, `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`, `docs/AI_FACTORY/NO_DECISION_ZONES.md`, `docs/AI_FACTORY/FAILSAFE_RULES.md`, `docs/AI_FACTORY/VERIFICATION_PROFILES.md`, `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md`, `docs/AI_FACTORY/PR_AUTOPILOT_CHECKLIST.md`, `docs/AI_FACTORY/SESSION_STATE.json` | 2026-05-14 | Manual doc review | Treat `SESSION_QUEUE.md` as the canonical single-session controller and `CURRENT_SESSION.json` as the detailed machine-readable session contract. |
| Canonical output-layout + full-game coverage docs | implemented | `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`, `docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`, `docs/AI_FACTORY/HUMAN_COMMANDS.md` | 2026-05-14 | Manual doc review | Keeps future agents aligned on output targets, coverage expectations, and low-prompt interaction model before code-side implementation expands. |

## B. Documentation-driven capabilities with partial or docs-only implementation

| Capability | State | Source of truth doc | Last verified | Verification command | Notes / next step |
|---|---|---|---|---|---|
| Project-level audio plan format | partial | `docs/AI_FACTORY/SCHEMAS/AUDIO_PLAN_SCHEMA.md`, `audio_engine/integration/factory_inputs.py` | 2026-05-14 | `pytest` | Typed loader exists for the committed example artifact; batch execution and broader validation are still future work. |
| Generation request format with seed/provenance fields | partial | `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md`, `audio_engine/integration/factory_inputs.py`, `audio_engine/integration/asset_pipeline.py` | 2026-05-14 | `pytest` | Typed batch/request loading and execution both exist; per-request provenance logs (beyond batch_manifest.json) remain future work. |
| AI factory review-state workflow | docs-contract | `docs/AI_FACTORY/QA/REVIEW_WORKFLOW.md` | 2026-05-14 | Manual doc review | Add machine-readable review log writer. |
| `GameRewritten` vertical-slice examples | docs-contract | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/*` | 2026-05-14 | `pytest` | The committed examples now serve as canonical loader fixtures; broader orchestration still needs follow-up sessions. |

## C. Planned / blocked work

| Capability | State | Source of truth | Last verified | Verification command | Notes / next step |
|---|---|---|---|---|---|
| Plan-driven batch orchestration | planned | `docs/AI_FACTORY/ROADMAP.md`, `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md` | 2026-05-14 | N/A | Implement as small PRs that preserve existing CLI compatibility. |
| Deterministic provenance capture per generated asset | planned | `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md`, `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json` | 2026-05-14 | N/A | Persist request ID, seed, output path, review status. |
| Automated QA gate for generated outputs in CI | planned | `docs/AI_FACTORY/QA/QUALITY_BARS.md`, `docs/AI_FACTORY/KNOWN_ISSUES.md` | 2026-05-14 | N/A | Add command first, then CI workflow wiring. |
| `GameRewritten` import automation | blocked | `docs/AI_FACTORY/INTEGRATION/GAMEREWRITTEN.md`, `docs/AI_FACTORY/KNOWN_ISSUES.md` | 2026-05-14 | N/A | Blocked on concrete import contract from consuming repo. |
| Full game-audio coverage tracking (music + SFX + ambience + fanfares + optional voice) | planned | `docs/AI_FACTORY/TARGET_STATE.md`, `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md` | 2026-05-14 | N/A | Expand from vertical slice toward full game asset taxonomy. |
