# Handoff

> Update this file at the end of every PR. Treat it as the "what changed last" file.

## Last completed change

This PR completes `SESSION-002` by adding a `RequestBatchPipeline` class to `audio_engine/integration/asset_pipeline.py` and a `generate-request-batch` CLI command that executes the committed music and SFX generation-request batch fixtures deterministically, with per-request seeds captured in a machine-readable `batch_manifest.json`, and 13 new tests covering the batch pipeline and CLI path.

## Verified in this session

```bash
pip install -e ".[dev]"
python -m pytest
# 334 passed (was 321 before SESSION-002)
python tools/validate-assets.py assets/examples/ --verbose
# PASS — all manifests are valid
audio-engine generate-request-batch \
  --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json \
  --output-dir /tmp/session002_smoke
# 5 SFX WAV files written; seeds 305001–305045 captured in batch_manifest.json
audio-engine generate-request-batch \
  --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json \
  --output-dir /tmp/session002_smoke
# 4 music WAV files written; seeds 204801–204834 captured in batch_manifest.json
```

## Smoke run output layout

```
/tmp/session002_smoke/
└── drafts/
    ├── music/
    │   ├── bgm_battle_standard.wav
    │   ├── bgm_field_day.wav
    │   ├── bgm_town_evening.wav
    │   └── stinger_victory_short.wav
    ├── sfx/
    │   ├── amb_wind_ruins_loop.wav
    │   ├── sfx_attack_light.wav
    │   ├── sfx_spell_fire_small.wav
    │   ├── sfx_ui_cancel.wav
    │   └── sfx_ui_confirm.wav
    └── batch_manifest.json   ← request_id, asset_id, seed, file, status per record
```

OGG requests (music BGMs in the committed fixture) fell back to WAV because the optional `soundfile` dependency is not installed in this environment. The `[warn]` message is intentional and documented.

## Seed and request-id usage

- Each `GenerationRequest.seed` is passed directly to the constructor of `MusicGen` or `SFXGen` for that request. No global pipeline seed is used.
- `request_id` and `seed` appear verbatim in each `batch_manifest.json` record.
- Determinism: re-running with the same batch file and `--force` regenerates identical audio.

## Immediate next best task

Execute `SESSION-003` from `docs/AI_FACTORY/SESSION_QUEUE.md`: write per-request provenance + review logs so each generated file is traceable to its request ID, seed, output path, and review state.

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`
5. `docs/AI_FACTORY/HANDOFF.md`
6. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
7. `docs/AI_FACTORY/FAILSAFE_RULES.md`
8. relevant subsystem/style/schema docs

## Handoff checklist

- [x] Mission and non-goals documented
- [x] Current state documented
- [x] Roadmap documented
- [x] Agent workflow documented
- [x] Troubleshooting documented
- [x] Style-family safety guidance documented
- [x] Integration direction for `GameRewritten` documented
- [x] Project-level audio plan example implemented in repo
- [x] Generation request examples with seeds/output/review fields implemented in repo
- [x] Implementation matrix + codebase map + next PR sequence implemented in repo
- [x] Session queue + template added
- [x] Done criteria, no-decision zones, task-output contracts, file-touch matrix, and failsafe rules added
- [x] PR autopilot checklist + session history + machine-readable session state added
- [x] Final execution-safety hardening layer added (current-session JSON, session gates, blocker protocol, verification profiles, canonical output layout, full game-audio checklist, minimum test-expansion rules, human command guide)
- [x] Audio plan and music/SFX generation-request fixtures load through typed integration code and tests
- [x] Request-batch generation command implemented (`generate-request-batch` CLI + `RequestBatchPipeline`)
- [ ] Per-request provenance/review log writing
- [ ] Audio QA/review automation added
