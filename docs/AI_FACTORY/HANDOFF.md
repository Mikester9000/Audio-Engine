# Handoff

> Update this file at the end of every PR.

## Last completed change

SESSION-005: Added `DraftExportPipeline` and `export-drafts` CLI command. 10 new tests; 355 total pass.

## Verified in this session

```bash
pip install -e ".[dev]"
python -m pytest  # 355 passed
python tools/validate-assets.py assets/examples/ --verbose  # PASS
audio-engine export-drafts --output-dir /tmp/session003_smoke
# 5 SFX files → exports/gamerewritten/Content/Audio/ using targetImportPath names
```

## Immediate next best task

Execute `SESSION-006` from `docs/AI_FACTORY/SESSION_QUEUE.md`: add an approval workflow that marks draft assets as `approved`, updates provenance `reviewStatus`, and copies them to `approved/<type>/`.

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
- [ ] Approval workflow (drafts → approved/)
- [ ] QA gate wired into CI
