# Failsafe Rules

> Use these rules when the current session is unclear, partially blocked, or riskier than expected.

## 1) Do not invent missing working behavior

- If code does not exist, do not describe it as working.
- If a downstream contract is missing, document the missing fact instead of hallucinating it.

## 2) Choose the smallest additive step that still moves the session forward

- If the full session cannot be completed exactly, implement the smallest compatible sub-step that preserves future progress.
- Then update `SESSION_QUEUE.md` so the remainder becomes the next explicit session.

## 3) Preserve current example contracts when details are missing

- Prefer the committed example plan/request/review artifacts over newly invented formats.
- Keep current target paths, request IDs, and seed fields stable unless the session explicitly changes them.

## 4) Debug the current scope before expanding the task

- If verification fails, fix the failing scope first.
- Do not compensate for a local failure by expanding into a large unrelated rewrite.

## 5) Prefer the least disruptive compatible change

- If multiple implementation paths are possible, choose the one that preserves existing CLI/API behavior.
- Avoid module moves/renames unless the session explicitly calls for them.

## 6) Record blockers in repo memory immediately

When blocked, update at least:

- `docs/AI_FACTORY/HANDOFF.md`
- `docs/AI_FACTORY/SESSION_QUEUE.md`
- `docs/AI_FACTORY/SESSION_STATE.json`

Add the blocker, what was verified, and the smallest next step.

## 7) One session means one session

- A request like **"complete next session"** means complete the current queue item, not the entire roadmap.
- Do not silently consume multiple queued sessions in one PR unless the user explicitly asks for that.
