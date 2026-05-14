# PR Autopilot Checklist

> Checklist for every substantial implementation or process PR in this repository.

## Before changing files

- [ ] Read `docs/AI_FACTORY/SESSION_QUEUE.md`
- [ ] Read `docs/AI_FACTORY/CURRENT_SESSION.json`
- [ ] Read `docs/AI_FACTORY/SESSION_GATE_RULES.md`
- [ ] Read `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
- [ ] Read `docs/AI_FACTORY/CURRENT_STATE.md`
- [ ] Read `docs/AI_FACTORY/HANDOFF.md`
- [ ] Read `docs/AI_FACTORY/NO_DECISION_ZONES.md`
- [ ] Read `docs/AI_FACTORY/FAILSAFE_RULES.md`
- [ ] Read `docs/AI_FACTORY/VERIFICATION_PROFILES.md`
- [ ] Read `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md`
- [ ] Read task-specific subsystem/style/schema docs
- [ ] Run the existing verification commands appropriate for the scope before editing code

## While doing the work

- [ ] Stay inside the current session scope
- [ ] Prefer additive change over broad refactor
- [ ] Use committed example artifacts as fixtures where possible
- [ ] Add targeted tests for changed executable behavior
- [ ] Keep implementation claims aligned with reality

## Before marking the PR/session done

- [ ] Targeted code/tests/docs are added and reviewed
- [ ] Verification commands were run and recorded
- [ ] `CURRENT_STATE.md` reviewed/updated if implementation or workflow changed
- [ ] `ACTIVE_WORK.md` reviewed/updated if priorities or sequencing changed
- [ ] `HANDOFF.md` updated
- [ ] `CHANGE_JOURNAL.md` appended for substantial PRs
- [ ] `SESSION_QUEUE.md` advanced if the active session was completed or blocked
- [ ] `SESSION_HISTORY.md` appended for completed sessions
- [ ] `SESSION_STATE.json` and `CURRENT_SESSION.json` updated to reflect the new current/next session
- [ ] Relevant subsystem/schema/QA/integration docs updated
