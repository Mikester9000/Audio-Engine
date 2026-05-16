# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a complete draft-to-approved pipeline with both request-driven and plan-driven execution: `generate-request-batch` or `generate-plan-batch` → provenance sidecars → `qa-batch` → `export-drafts` → `approve-draft` → `approved/<type>/`. SESSION-015 and SESSION-016 are now complete: machine-readable review-log writing is executable and can be integrated directly during approval/export handoff. The next executable work item is queue refresh/planning for `SESSION-017`.

## Now

- [x] Establish AI-first mission/state/handoff docs
- [x] Add explicit operating instructions for future agents
- [x] Document current implementation, gaps, and roadmap
- [x] Define a committed `GameRewritten`-oriented audio plan example
- [x] Commit generation request + review/provenance example artifacts
- [x] Add implementation matrix + codebase map + next-PR sequence docs
- [x] Add session queue/autopilot control docs for low-prompt execution
- [x] Add final execution-safety hardening docs and machine-readable current-session contract
- [x] Execute `SESSION-001` from `docs/AI_FACTORY/SESSION_QUEUE.md`
- [x] Execute `SESSION-002` from `docs/AI_FACTORY/SESSION_QUEUE.md`
- [x] Execute `SESSION-003` from `docs/AI_FACTORY/SESSION_QUEUE.md`
- [x] Execute `SESSION-004` from `docs/AI_FACTORY/SESSION_QUEUE.md`
- [x] Execute `SESSION-005` from `docs/AI_FACTORY/SESSION_QUEUE.md`
- [x] Execute `SESSION-006` — add approval workflow (promote drafts to approved/)
- [x] Execute `SESSION-007` — wire qa-batch into CI
- [x] Update music-duration policy across docs, checklist, layout, and example plan
- [x] Execute `SESSION-008` — expand full-game taxonomy coverage
- [x] Execute `SESSION-009` — add plan-driven batch orchestration with required requested `.ogg` + `.wav` outputs
- [x] Execute `SESSION-010` — expand neural/backend support surfaces
- [x] Execute `SESSION-011` — implement backend evaluation metadata in backend registry/CLI
- [x] Execute `SESSION-012` — implement repeated-SFX variation validation and provenance metadata
- [x] Execute `SESSION-013` — define category-specific SFX loudness/readability targets
- [x] Execute `SESSION-014` — add review/report template updates for variant-family QA decisions
- [x] Execute `SESSION-015` — add machine-readable review-log writer for QA decisions
- [x] Execute `SESSION-016` — integrate review-log output with approval/export handoff flow
- [ ] Execute `SESSION-017` — define next implementation session after review-log integration

## Recommended next PRs

1. **Define and queue next executable session (SESSION-017)**
   - Refresh queue order against current implementation state and roadmap.

## Do not deprioritize

- music usefulness
- SFX coverage
- deterministic regeneration
- downstream folder organization
- continuity docs
- session queue clarity

## Lower-priority work

- premium voice generation
- Windows-native developer ergonomics beyond basic setup
- broad UI polish
- nonessential refactors
