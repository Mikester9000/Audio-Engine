# No Decision Zones

> Areas where future agents should **not improvise**. When a session touches one of these areas, follow existing policy or the active session instructions exactly.

## 1) CLI compatibility is a policy surface

- Preserve existing CLI commands and flags unless the active session explicitly permits a change.
- Prefer additive commands/options over renaming or removing behavior.
- If a breaking CLI change seems necessary, stop and document why instead of making the change casually.

## 2) Persistent-memory docs must stay synchronized

- When session state changes, update `SESSION_QUEUE.md`, `HANDOFF.md`, and `SESSION_STATE.json` together.
- When repo priorities or next steps change, update `ACTIVE_WORK.md` in the same PR.
- When a substantial PR lands, append `CHANGE_JOURNAL.md` and add an entry to `SESSION_HISTORY.md`.

## 3) Prefer additive change over broad refactor

- Do not wander into unrelated refactors while completing a session.
- Do not move or rename major modules unless the session explicitly says to do so.
- If a refactor seems required, take the least disruptive compatible path first.

## 4) Use committed examples as fixtures when possible

- The example artifacts under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` are the default fixtures for early plan/request work.
- Do not invent alternate examples when the committed ones already cover the target workflow.
- If the examples are insufficient, add the smallest missing example explicitly instead of silently changing contracts.

## 5) Docs-only contracts are not implemented behavior

- Schema docs, examples, and workflow docs are source-of-truth contracts.
- They must not be described as executable code until code and verification exist.
- If a session only updates docs, keep implementation status labeled as docs-only, planned, or partial as appropriate.

## 6) Priority order is fixed unless the session is explicit

- Prioritize music and SFX over voice.
- Treat voice as optional/lower-priority unless the session is voice-specific.
- Optimize for usable game-audio output and continuity, not elegant internals.

## 7) Stable names and paths should not drift casually

- Preserve canonical terms: `audio plan`, `generation request`, `review status`, `seed`, `handoff`, `session`.
- Prefer stable file paths under `docs/AI_FACTORY/` so future agents can rely on retrieval by name.
- Do not create duplicate “better” control docs when an existing canonical doc can be updated instead.

## 8) Do not guess external repo contracts

- If `GameRewritten` or another downstream repo is missing concrete details, document the dependency.
- Do not hallucinate import paths, metadata fields, or workflow guarantees that are not verified in this repo.
