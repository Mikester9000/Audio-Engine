# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-006 + SESSION-007 (combined PR): Added `ApprovalWorkflow` and `approve-draft` CLI (SESSION-006); wired `qa-batch` into CI via `.github/workflows/audio-qa.yml` (SESSION-007); updated music-duration policy across all relevant docs. 13 new tests; 383 total pass.

## Verified in this session

```bash
pip install -e ".[dev]"
python -m pytest  # 383 passed
python tools/validate-assets.py assets/examples/ --verbose  # PASS
python -m json.tool docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json  # PASS

# Smoke run: generate SFX batch then approve one draft
audio-engine generate-request-batch \
  --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json \
  --output-dir /tmp/session006_smoke --quiet
audio-engine approve-draft \
  --factory-root /tmp/session006_smoke \
  --draft-file /tmp/session006_smoke/drafts/sfx/req_sfx_ui_confirm_v1.wav \
  --output-report /tmp/session006_smoke/approval_report.json
# 1 file copied to approved/sfx/; provenance reviewStatus=approved; report written
```

Observed result:
- `383 passed` in pytest (up from 370 before this PR)
- 1 SFX draft approved; `approved/sfx/req_sfx_ui_confirm_v1.wav` created
- provenance `reviewStatus` updated to `"approved"` with `approvedAt` timestamp in both draft and approved copies
- CI workflow `.github/workflows/audio-qa.yml` created; triggers on push/PR to audio source and fixtures

## Immediate next best task

Execute `SESSION-008` from `docs/AI_FACTORY/SESSION_QUEUE.md`: expand full-game taxonomy coverage — add committed backlog for all audio families beyond the vertical slice and add OST variant request entries for key BGM tracks.

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`
5. `docs/AI_FACTORY/HANDOFF.md`
6. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
7. `docs/AI_FACTORY/FAILSAFE_RULES.md`

## Handoff checklist

- [x] Request-batch generation command (`generate-request-batch`)
- [x] Per-request provenance sidecar files (`.provenance.json`)
- [x] Batch QA gate command (`qa-batch` with JSON report)
- [x] GameRewritten export profile (`export-drafts` to `Content/Audio/`)
- [x] Approval workflow (`approve-draft` → `approved/<type>/`, updates provenance)
- [x] QA gate wired into CI (`.github/workflows/audio-qa.yml`)
- [x] Music-duration policy documented and encoded in checklist, layout, music subsystem, and example plan
- [ ] Full-game taxonomy coverage expansion (SESSION-008)
