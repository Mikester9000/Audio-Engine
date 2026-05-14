# Session Template

> Copy this template when adding a new session to `SESSION_QUEUE.md` or when documenting a one-off session in another AI_FACTORY file.

## SESSION-XXX — Replace with title

- **Status:** `ready | in-progress | blocked | partially-complete | completed | queued-after-SESSION-YYY`
- **Task type:** `docs_only | loader_parsing | cli | batch_generation | provenance | qa | integration_export | taxonomy`
- **Objective:** One sentence describing the exact output expected from this session.
- **Why it matters:** One sentence linking the session to the long-term audio-factory goal.
- **Read first docs/files:**
  1. `docs/AI_FACTORY/SESSION_QUEUE.md`
  2. `docs/AI_FACTORY/CURRENT_STATE.md`
  3. `docs/AI_FACTORY/HANDOFF.md`
  4. `docs/AI_FACTORY/CURRENT_SESSION.json`
  5. `docs/AI_FACTORY/SESSION_GATE_RULES.md`
  6. `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  7. `docs/AI_FACTORY/VERIFICATION_PROFILES.md`
  8. add task-specific docs/code/tests here
- **Exact or likely files to modify:**
  - `path/to/file`
  - `path/to/test`
- **Files not to modify unless absolutely necessary:**
  - `path/to/stable/file`
- **Verification commands:**
  - `pytest`
  - add any task-specific commands here
- **Verification profile:** `docs/AI_FACTORY/VERIFICATION_PROFILES.md#pick-the-right-profile`
- **Minimum test-expansion rules:** `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md`
- **Docs that must be updated:**
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/ACTIVE_WORK.md`
  - `docs/AI_FACTORY/HANDOFF.md`
  - `docs/AI_FACTORY/CHANGE_JOURNAL.md`
  - `docs/AI_FACTORY/CURRENT_SESSION.json` if the active session status/details changed
  - add task-specific docs here
- **Explicit done criteria:**
  1. list concrete observable outcomes
  2. list tests/verification expectations
  3. list required doc/state updates
- **Completion gate:** `docs/AI_FACTORY/SESSION_GATE_RULES.md`
- **Enqueue next session after completion:** `SESSION-YYY — Replace with next title`
- **If uncertain or blocked:**
  - reference `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  - reference `docs/AI_FACTORY/FAILSAFE_RULES.md`
  - write blocker notes instead of guessing

## Template usage rules

- Keep filenames and headings explicit for retrieval.
- Use real repository paths.
- Do not mark a session `completed` until verification commands have run.
- If a session changes priority or cannot finish, update `SESSION_QUEUE.md`, `HANDOFF.md`, `SESSION_STATE.json`, and `CURRENT_SESSION.json` together.
