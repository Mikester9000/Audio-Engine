# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-008: Expanded committed taxonomy coverage across AI-factory fixtures and backlog docs. Added ambience/fanfare/UI/combat/spell/tension/sadness/optional-voice coverage in the committed vertical-slice plan and request artifacts, plus long-form OST request entries for key BGM tracks marked `+ost`.

## Verified in this session

```bash
pip install -e ".[dev]"
python -m pytest  # 385 passed
python tools/validate-assets.py assets/examples/ --verbose  # PASS
python -m json.tool docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json  # PASS
python -m json.tool docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json  # PASS
python -m json.tool docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json  # PASS
python -m json.tool docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.voice.v1.json  # PASS
```

Observed result:
- `385 passed` in pytest
- all asset-manifest examples passed validation
- all edited AI-factory JSON fixtures parsed successfully
- committed taxonomy coverage now includes ambience, fanfares/stingers, expanded UI/combat/spell SFX, tension/sadness music, optional voice placeholders, and OST request entries for `field`, `town`, `dungeon`, `battle`, and `boss` BGM tracks

## Immediate next best task

Execute `SESSION-009` from `docs/AI_FACTORY/SESSION_QUEUE.md`: add plan-driven batch orchestration by wiring audio-plan artifacts into deterministic batch execution while preserving current CLI compatibility.

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
- [x] Full-game taxonomy coverage expansion (SESSION-008)
- [ ] Plan-driven batch orchestration (SESSION-009)
