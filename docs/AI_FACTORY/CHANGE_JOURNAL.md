# Change Journal

> Append a short entry for every substantial PR. Keep entries brief and factual.

## 2026-05-14 — Add AI-first documentation system for GitHub-native audio asset factory

- Added `docs/AI_FACTORY/` as the persistent mission/state/roadmap/handoff memory tree.
- Added subsystem, style, schema, QA, troubleshooting, Windows, and integration docs.
- Added `.github/copilot-instructions.md` to direct future AI contributors.
- Updated root README to point readers and agents at the new docs-first operating model.
- Confirmed repository baseline remained healthy with `pytest` and asset-manifest validation.

## Baseline before this PR

- Python package and CLI already existed.
- Procedural generation existed for music, SFX, and voice.
- Asset pipeline existed for `Game Engine for Teaching`.
- Asset-manifest documentation and validation workflow already existed.

## 2026-05-14 — Add implementation matrix, PR build sequence, codebase map, and factory input examples

- Added machine-guidance docs: `IMPLEMENTATION_MATRIX.md`, `NEXT_PR_SEQUENCE.md`, `CODEBASE_MAP.md`, `KNOWN_ISSUES.md`, and `STABILITY_RULES.md`.
- Added committed example artifacts for `GameRewritten` vertical-slice planning and request-driven workflows under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/`.
- Added machine-friendly continuity snapshot `FACTORY_STATUS.json`.
- Updated AI-factory indexes and continuity docs so future agents can distinguish implemented code from docs-only contracts and planned work.

## 2026-05-14 — Add session queue and autopilot control layer for AI agents

- Added `SESSION_QUEUE.md` as the canonical “what should I do next?” file for low-prompt continuation.
- Added `SESSION_TEMPLATE.md`, `DONE_CRITERIA.md`, `NO_DECISION_ZONES.md`, `TASK_OUTPUT_CONTRACTS.md`, `FILE_TOUCH_MATRIX.md`, `FAILSAFE_RULES.md`, and `PR_AUTOPILOT_CHECKLIST.md`.
- Added continuity tracking artifacts `SESSION_HISTORY.md` and `SESSION_STATE.json`.
- Updated repo entrypoints and workflow docs so future agents can execute one explicit session with less ambiguity and less improvisation.
