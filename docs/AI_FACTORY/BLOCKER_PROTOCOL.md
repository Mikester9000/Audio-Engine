# Blocker Protocol

> Exact procedure for when a session cannot be completed exactly as written.

## Core rule

When blocked, do **not** hallucinate missing implementation, pretend verification passed, or broaden scope into a large speculative rewrite.

## What counts as a blocker

A blocker is any of the following:

- a required dependency or contract is missing
- a prerequisite session was not actually finished
- verification fails and the failure is outside the current safe scope
- downstream expectations are unknown
- the committed examples do not contain enough information to continue safely

## Required blocker behavior

1. **Stop claiming the full session is complete**
   - Do not use completion wording in docs, handoff, or PR text.
2. **Prefer the smallest additive unblocker**
   - If you can land a compatible sub-step that reduces future work, do that.
   - Do not solve a local blocker by redesigning unrelated systems.
3. **Record the blocker explicitly**
   - Write the missing fact, failing command, or external dependency plainly.
   - Include what was attempted and what was verified.
4. **Keep the scope narrow**
   - Preserve current CLI/API behavior unless the session explicitly allows more.
   - Do not invent new schema fields, file layouts, or downstream contracts just to finish.
5. **Advance the queue mechanically**
   - Mark the current session `blocked` or `partially-complete`.
   - Turn the remaining work into the next explicit session or blocker note.

## Decide between blocked vs partially complete

### Mark `blocked` when:

- the main objective did not land
- the next step depends on missing information or an unmet prerequisite
- no truthful “done” statement can be written for the original session objective

### Mark `partially-complete` when:

- a useful compatible subset landed,
- that subset is verified,
- and the remaining scope is clearly described as unfinished follow-up work

## Minimum repo updates for a blocked session

Update all of the following in the same PR:

1. `docs/AI_FACTORY/HANDOFF.md`
2. `docs/AI_FACTORY/SESSION_QUEUE.md`
3. `docs/AI_FACTORY/SESSION_STATE.json`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`

Also update any state/implementation docs that would otherwise overstate the result.

## Blocker note format

Record at least:

- **Blocker:** what is missing or failing
- **Why it blocks completion:** the exact dependency on the current session goal
- **What was verified:** commands/tests/manual checks already run
- **Smallest next step:** the narrowest follow-up action that unblocks progress

## Examples of correct behavior

- If a downstream import path is unknown, document the missing contract and stop short of inventing one.
- If parsing tests pass but a broader batch command is out of scope, do not claim batch execution is implemented.
- If a new JSON control file was added but the active session remains the same, update the machine-readable state files instead of changing queue order casually.
