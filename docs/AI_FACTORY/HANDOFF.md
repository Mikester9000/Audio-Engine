# Handoff

> Update this file at the end of every PR. Treat it as the “what changed last” file.

## Last completed change

This PR adds the next repo-memory layer after the initial AI-factory docs: implementation matrix, next PR sequence, codebase map, known issues, stability rules, a machine-friendly status JSON, and committed `GameRewritten` vertical-slice plan/request/review examples.

## Verified in this session

```bash
pip install -e ".[dev]"
pytest
python tools/validate-assets.py assets/examples/ --verbose
```

Observed result:

- `314 passed`
- asset-manifest examples validated successfully

## Immediate next best task

Implement code-side loading and execution for the committed example artifacts in `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` so plan/request flows become executable rather than docs-only.

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/ACTIVE_WORK.md`
4. `docs/AI_FACTORY/PLAYBOOKS/AGENT_WORKFLOW.md`
5. relevant subsystem/style/schema docs

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
- [ ] Batch generation request format implemented in code
- [ ] Audio QA/review automation added
