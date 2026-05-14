# Copilot Instructions for Audio-Engine

This repository is an **AI-first audio asset factory**, not just a code library.

## Read these first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/ACTIVE_WORK.md`
5. `docs/AI_FACTORY/HANDOFF.md`
6. `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`
7. `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md`
8. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
9. `docs/AI_FACTORY/FAILSAFE_RULES.md`
10. `docs/AI_FACTORY/CODEBASE_MAP.md`
11. relevant subsystem/style/schema docs

## Core rules

- Optimize for usable game-audio assets and clean handoff, not elegant internals.
- Update persistent memory docs in the same PR when behavior, priorities, or workflow changes.
- Treat inspiration targets as style families, not requests to copy copyrighted material.
- Keep music and SFX higher priority than voice unless the task is explicitly voice-focused.
- Windows/Visual Studio support is desirable but lower priority than Python/Linux workflows.
- Prefer stable names, explicit schemas, and deterministic seed capture.

## Minimum doc updates for substantial changes

Review and update as needed:

- `docs/AI_FACTORY/CURRENT_STATE.md`
- `docs/AI_FACTORY/ACTIVE_WORK.md`
- `docs/AI_FACTORY/HANDOFF.md`
- `docs/AI_FACTORY/SESSION_QUEUE.md` when session order or status changes
- `docs/AI_FACTORY/SESSION_HISTORY.md` and `docs/AI_FACTORY/SESSION_STATE.json` when a session is completed or blocked
- one relevant subsystem page
- one relevant QA/style/schema page if behavior changed
