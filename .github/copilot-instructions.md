# Copilot Instructions for Audio-Engine

This repository is an **AI-first audio asset factory**, not just a code library.

## Read these first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/ACTIVE_WORK.md`
4. `docs/AI_FACTORY/HANDOFF.md`
5. `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`
6. `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md`
7. `docs/AI_FACTORY/CODEBASE_MAP.md`
8. `docs/AI_FACTORY/STABILITY_RULES.md`
9. relevant subsystem/style/schema docs

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
- one relevant subsystem page
- one relevant QA/style/schema page if behavior changed
