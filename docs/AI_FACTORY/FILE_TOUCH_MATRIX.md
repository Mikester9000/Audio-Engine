# File Touch Matrix

> Where agents should usually work for each session type, and where they should avoid wandering unless the active session explicitly requires it.

| Task/session type | Commonly safe or expected files to change | Avoid unless necessary |
|---|---|---|
| `docs_only` | `docs/AI_FACTORY/*`, `README.md`, `.github/copilot-instructions.md`, `docs/AI_FACTORY/FACTORY_STATUS.json`, `docs/AI_FACTORY/SESSION_STATE.json` | `audio_engine/*` production code, `tests/*` unless docs/testing instructions truly need it |
| `loader_parsing` | `audio_engine/integration/*`, `tests/test_integration.py`, `tests/test_engine_cli.py`, `tests/test_new_cli.py`, relevant schema/subsystem docs | `audio_engine/dsp/*`, `audio_engine/render/*`, broad composer changes |
| `cli` | `audio_engine/cli.py`, CLI tests, relevant subsystem docs | unrelated AI generation internals, broad path renames |
| `batch_generation` | `audio_engine/cli.py`, `audio_engine/integration/asset_pipeline.py`, integration tests, `docs/AI_FACTORY/INTEGRATION/*` | DSP internals unless a verified bug blocks the task |
| `provenance` | `audio_engine/integration/*`, tests, schema/QA docs | synthesizer/composer internals |
| `qa` | `audio_engine/qa/*`, `audio_engine/cli.py`, `tests/test_qa.py`, QA docs | unrelated music/SFX generation internals |
| `integration_export` | `audio_engine/integration/*`, `tests/test_integration.py`, `docs/AI_FACTORY/INTEGRATION/*` | unrelated CLI refactors, style docs |
| `taxonomy` | `docs/AI_FACTORY/EXAMPLES/*`, `docs/AI_FACTORY/TASKS/*`, `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`, `docs/AI_FACTORY/ACTIVE_WORK.md` | production code unless tied directly to the taxonomy change |

## Default rule

If a file is outside the expected area for the active session, pause and ask: **is this required to complete the current session, or am I drifting into an unrelated refactor?**
