# Session Gate Rules

> Final hard gate for marking a session `completed`, `blocked`, or `partially-complete`. Use this file together with `DONE_CRITERIA.md`, not instead of it.

## Purpose

This file exists to reduce false completion. A session is not done because work was attempted. A session is done only when the correct repo diff, verification evidence, and continuity updates all exist.

## Completion gate for every substantial session

Do **not** mark a session `completed` until all gates below are satisfied:

1. **Requested scope exists in the repo diff**
   - The required docs/code/tests are actually present.
   - Do not count planning text or TODO notes as completion.
2. **The correct verification profile was executed**
   - Use `VERIFICATION_PROFILES.md` for the active task type.
   - Record what ran and the observed result in `HANDOFF.md`.
3. **Test expectations expanded correctly**
   - Follow `MINIMUM_TEST_EXPANSION_RULES.md`.
   - If executable behavior changed and no new tests were added, explain why in `HANDOFF.md`.
4. **Implementation claims match reality**
   - Do not relabel something as implemented unless it is real and verified.
   - Keep docs-only contracts clearly labeled as docs-only, planned, or partial when code is still missing.
5. **Required continuity docs were updated**
   - Always review/update `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, and `CHANGE_JOURNAL.md` when they are affected.
   - Update relevant subsystem/schema/QA/integration docs when behavior or workflow changed.
6. **Session-control files are synchronized**
   - If the active session status changed, update `SESSION_QUEUE.md`, `SESSION_STATE.json`, and `CURRENT_SESSION.json` together.
   - If the session completed, append `SESSION_HISTORY.md`.
7. **The next step is explicit**
   - Queue the next session or explicitly record the blocker.
   - Never leave the repo in an ambiguous “something changed, figure it out” state.

## Allowed terminal states

### `completed`

Use only when every required gate passed.

### `blocked`

Use when the session cannot be completed exactly as written because of a real dependency, missing fact, failing prerequisite, or external constraint. Follow `BLOCKER_PROTOCOL.md`.

### `partially-complete`

Use only when:

- a meaningful additive sub-step landed,
- the original full objective was **not** achieved,
- the remaining work is written as the next explicit session/blocker,
- and the diff does not pretend the entire session is finished.

Do not use `partially-complete` as a softer spelling of `completed`.

## Minimum file updates by terminal state

| Session result | Required file updates |
|---|---|
| `completed` | `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, `CHANGE_JOURNAL.md`, `SESSION_QUEUE.md`, `SESSION_HISTORY.md`, `SESSION_STATE.json`, `CURRENT_SESSION.json`, affected implementation/subsystem docs |
| `blocked` | `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, `SESSION_QUEUE.md`, `SESSION_STATE.json`, `CURRENT_SESSION.json`, plus any affected state docs |
| `partially-complete` | `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, `SESSION_QUEUE.md`, `SESSION_STATE.json`, `CURRENT_SESSION.json`, and any docs that would otherwise misstate implementation status |

## Hard stop rules

- Do not mark a session complete just because the main command “looks like it should work.”
- Do not mark a session complete if required docs were skipped.
- Do not mark a session complete if a required verification command failed or was not run.
- Do not silently carry unfinished work into the next PR without writing it down.
