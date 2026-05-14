# Codebase Map

> Quick locator for future agents. This map uses real repository paths and focuses on where to make changes for each responsibility.

## Repository root landmarks

- Python package: `audio_engine/`
- Tests: `tests/`
- Asset-manifest schema + examples: `assets/schema/`, `assets/examples/`
- Utility scripts: `tools/`
- AI-factory continuity docs: `docs/AI_FACTORY/`
- CI workflow (manifest validation): `.github/workflows/validate-assets.yml`

## Core entrypoints

| Responsibility | Primary files | Notes |
|---|---|---|
| Package entry | `audio_engine/__init__.py` | Exposes top-level `AudioEngine`. |
| Main facade API | `audio_engine/engine.py` | High-level generation/export helpers. |
| CLI entrypoint | `audio_engine/cli.py` | `audio-engine` command and all subcommands. |
| Install/console script wiring | `pyproject.toml` (`[project.scripts]`) | Maps `audio-engine` to `audio_engine.cli:main`. |

## Generation subsystems

| Area | Primary files | What lives there |
|---|---|---|
| Music generation | `audio_engine/ai/generator.py`, `audio_engine/ai/music_gen.py`, `audio_engine/composer/*` | Style-based generation, prompt-driven generation, sequencing/music theory helpers. |
| SFX generation | `audio_engine/ai/sfx_gen.py`, `audio_engine/ai/sfx_synth.py` | Prompt parsing to procedural SFX synthesis. |
| Voice generation (low priority) | `audio_engine/ai/voice_gen.py`, `audio_engine/ai/voice_synth.py` | Local/prototype-grade voice synthesis pipeline. |
| Backend abstraction | `audio_engine/ai/backend.py`, `audio_engine/ai/prompt.py` | Backend and prompt interpretation surfaces. |

## Audio quality, mastering, and export

| Area | Primary files | What lives there |
|---|---|---|
| DSP processing | `audio_engine/dsp/*` | EQ, compression, limiter, reverb, resampling, dithering. |
| Mastering/render | `audio_engine/render/offline_bounce.py`, `audio_engine/render/stem_renderer.py` | Offline bounce/mastering and stem export. |
| QA checks | `audio_engine/qa/*` | Loudness, clipping, and loop analyses. |
| Export layer | `audio_engine/export/audio_exporter.py` | WAV (and optional OGG) writing and loop metadata. |

## Integration / asset pipeline

| Responsibility | Primary files | Notes |
|---|---|---|
| Fixed-map generation pipeline | `audio_engine/integration/asset_pipeline.py` | Generates `music/`, `sfx/`, `voice/` sets and writes manifest. |
| Canonical event/state mapping | `audio_engine/integration/game_state_map.py` | Music/SFX/voice manifest tuples and prompts. |
| Integration docs for consumer repo | `docs/AI_FACTORY/INTEGRATION/GAMEREWRITTEN.md` | Path/naming direction for `GameRewritten`. |

## Tests by area

| Area | Main test files |
|---|---|
| CLI behavior | `tests/test_engine_cli.py`, `tests/test_new_cli.py` |
| Integration pipeline | `tests/test_integration.py` |
| Music/composer/generator | `tests/test_generator.py`, `tests/test_pattern.py`, `tests/test_scale.py`, `tests/test_chord.py`, `tests/test_sequencer.py` |
| DSP/render/QA/export | `tests/test_dsp.py`, `tests/test_effects.py`, `tests/test_filter.py`, `tests/test_render.py`, `tests/test_qa.py`, `tests/test_exporter.py` |
| AI pipeline end-to-end | `tests/test_ai_pipeline.py` |

## Docs and machine-guidance surfaces

| Need | Primary files |
|---|---|
| Mission/state/handoff | `docs/AI_FACTORY/PROJECT_MISSION.md`, `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md` |
| Implementation truth table | `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md` |
| Mechanical build order | `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md` |
| Known constraints | `docs/AI_FACTORY/KNOWN_ISSUES.md` |
| Refactor/stability guardrails | `docs/AI_FACTORY/STABILITY_RULES.md` |
| Example plan/request artifacts | `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/*` |
