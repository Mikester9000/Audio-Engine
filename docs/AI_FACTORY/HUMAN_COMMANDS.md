# Human Commands

> Intended low-prompt interaction model for future agents.

## Canonical commands

### `complete next session`

- Read `docs/AI_FACTORY/SESSION_QUEUE.md`
- Execute the top-most session whose status is `ready`
- Use `docs/AI_FACTORY/CURRENT_SESSION.json` for the detailed machine-readable session contract

### `complete SESSION-XYZ only`

- Execute only that named session
- Do not silently consume later queued sessions

### `continue until blocked`

- Complete the current ready session
- Stop at the first truthful blocker
- Follow `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`

### `finish current PR and hand off`

- Stop adding scope
- run required verification
- update continuity docs
- leave the next step explicit

### `what is the current session`

- Read `docs/AI_FACTORY/SESSION_QUEUE.md`, `docs/AI_FACTORY/SESSION_STATE.json`, and `docs/AI_FACTORY/CURRENT_SESSION.json`

## Important rule

Low-prompt does **not** mean low-verification. Future agents should use these commands to reduce ambiguity, not to skip gates or tests.
