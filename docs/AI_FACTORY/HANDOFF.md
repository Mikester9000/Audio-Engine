# Handoff

> Update this file at the end of every PR. Treat it as the "what changed last" file.

## Last completed change

This PR completes `SESSION-003` by adding per-request provenance sidecar files (`<stem>.provenance.json`) to `RequestBatchPipeline`. Every successfully generated audio file now has an independent machine-readable provenance record beside it containing request ID, seed, backend, review status, and generation timestamp. 5 new tests were added; total test count is 338.

## Verified in this session

```bash
pip install -e ".[dev]"
python -m pytest
# 338 passed (was 334 before SESSION-003)
python tools/validate-assets.py assets/examples/ --verbose
# PASS — all manifests are valid
audio-engine generate-request-batch \
  --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json \
  --output-dir /tmp/session003_smoke
# 5 SFX WAV files + 5 .provenance.json sidecars written
# seeds and request IDs confirmed in provenance files
```

## Smoke run provenance example

```json
{
  "provenanceVersion": "1.0.0",
  "requestId": "req_sfx_ui_confirm_v1",
  "assetId": "sfx_ui_confirm",
  "type": "sfx",
  "backend": "procedural",
  "seed": 305001,
  "prompt": "clean menu confirm click, short and readable",
  "styleFamily": "heroic-sci-fantasy",
  "generatedOutputPath": "/tmp/session003_smoke/drafts/sfx/sfx_ui_confirm.wav",
  "targetImportPath": "Content/Audio/sfx_ui_confirm.wav",
  "reviewStatus": "draft",
  "generatedAt": "2026-05-14T22:45:41.734635+00:00"
}
```

## Provenance sidecar behavior

- File name: `<audio_stem>.provenance.json` beside the generated audio file.
- Written for every successfully generated request; not written for skipped requests.
- `reviewStatus` is copied from `qa.reviewStatus` in the request (initially `"draft"`).
- `generatedAt` is the UTC ISO 8601 timestamp at write time.

## Immediate next best task

Execute `SESSION-004` from `docs/AI_FACTORY/SESSION_QUEUE.md`: add a batch QA gate command that checks generated audio files for loudness, clipping, and loop boundary compliance.

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
- [x] Final execution-safety hardening layer added
- [x] Audio plan and music/SFX generation-request fixtures load through typed integration code and tests
- [x] Request-batch generation command implemented (`generate-request-batch` CLI + `RequestBatchPipeline`)
- [x] Per-request provenance sidecar files written alongside every generated audio file
- [ ] Audio QA/review automation (batch gate command)
- [ ] Approval/replacement workflow (drafts → approved promotion)
