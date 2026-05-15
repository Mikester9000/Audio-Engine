# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a complete draft-to-approved pipeline with both request-driven and plan-driven execution: `generate-request-batch` or `generate-plan-batch` → provenance sidecars → `qa-batch` → `export-drafts` → `approve-draft` → `approved/<type>/`. SESSION-009 added plan-driven orchestration with strict requested-format behavior (requested `.ogg` must be produced; no WAV fallback), and SESSION-010 expanded backend surfaces (`RequestBatchPipeline` now honors request backend and CLI now supports backend selection/discovery). The next executable session is `SESSION-011` in `docs/AI_FACTORY/SESSION_QUEUE.md`: add backend evaluation notes and dependency/availability guidance.

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
- [ ] Execute `SESSION-011` — add backend evaluation notes and dependency guidance

## Recommended next PRs

1. **Add backend evaluation notes (SESSION-011)**
   - Document backend strategy, availability checks, and realistic quality expectations for local/open model adapters.
2. **Add variation strategy for repeated SFX categories (SESSION-012)**
   - Define deterministic variation controls for repeated gameplay-triggered SFX families.

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
