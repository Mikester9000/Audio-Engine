# Agent Workflow Playbook

> Update this file whenever the expected AI-agent process changes.

## Required workflow

Every AI agent working in this repository should follow this sequence unless a task explicitly requires a different order:

1. Read `docs/AI_FACTORY/README.md`
2. Read `CURRENT_STATE.md`, `SESSION_QUEUE.md`, `ACTIVE_WORK.md`, and `HANDOFF.md`
3. Read `NO_DECISION_ZONES.md` and `FAILSAFE_RULES.md`
4. Read the relevant subsystem/style/schema docs
5. Inspect the real code before changing docs about implementation
6. Run existing verification commands before editing code
7. Make the smallest useful change set that fully addresses the current session
8. Re-run targeted verification
9. Update persistent memory docs and session-state docs
10. Leave a clean handoff

## Mandatory doc-sync rule

If your PR changes any of the following, update the matching docs:

| Change type | Docs to review/update |
|---|---|
| Repo purpose or priorities | `PROJECT_MISSION.md`, `ROADMAP.md` |
| Implemented functionality | `CURRENT_STATE.md`, relevant `SUBSYSTEMS/*.md` |
| Next steps or sequencing | `SESSION_QUEUE.md`, `ACTIVE_WORK.md`, `TASKS/*` |
| Latest session summary | `HANDOFF.md`, `CHANGE_JOURNAL.md`, `SESSION_HISTORY.md`, `SESSION_STATE.json` |
| Style policy | `STYLES/*`, relevant ADR |
| QA/acceptance rules | `QA/QUALITY_BARS.md`, `PLAYBOOKS/TROUBLESHOOTING.md` |
| Integration behavior | `INTEGRATION/GAMEREWRITTEN.md`, relevant subsystem page |

## Planning rules

- Prefer small PRs that change one coherent area.
- If a task is larger than one coherent area, split it into explicit phases inside the PR description or backlog docs.
- Use checklists and stable headings.
- Do not rely on memory outside the repo when repo memory can be updated instead.

## Naming rules for AI retrieval

1. Prefer descriptive filenames over clever names.
2. Put critical concepts in headings exactly as they appear in code or prompts.
3. Use repeated canonical terms: `audio plan`, `generation request`, `style family`, `handoff`, `review status`, `seed`.
4. Avoid inventing synonyms unless they are added to the glossary.

## Anti-drift rules

1. Never describe an implementation as existing unless it exists in code or a verified script today.
2. Label future ideas as `planned`, `target`, or `documentation contract`.
3. If a doc becomes stale during your PR, fix it in the same PR.
4. If you cannot confirm a capability, write it as an open question or blocker.

## Handoff checklist for every substantial PR

- [ ] update `ACTIVE_WORK.md`
- [ ] update `HANDOFF.md`
- [ ] append `CHANGE_JOURNAL.md`
- [ ] advance `SESSION_QUEUE.md` if session state changed
- [ ] append `SESSION_HISTORY.md` for completed sessions
- [ ] update `SESSION_STATE.json`
- [ ] update at least one relevant subsystem page
- [ ] update one quality/style/schema doc if the behavior changed
- [ ] mention exact verification commands used

## Escalation rule

If the next logical task requires information from `GameRewritten` or another repo that is not present here, document the dependency clearly instead of guessing.
