# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a complete draft-to-export pipeline: `generate-request-batch` → provenance sidecars → `qa-batch` → `export-drafts` → GameRewritten `Content/Audio/` layout. The next executable session is `SESSION-006` in `docs/AI_FACTORY/SESSION_QUEUE.md`: add an approval workflow that promotes drafts to `approved/`.

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
- [ ] Execute `SESSION-006` — add approval workflow (promote drafts to approved/)
- [ ] Add approval/review workflow for generated assets

## Recommended next PRs

1. **Execute `SESSION-006` — add approval workflow (promote drafts to approved/)**
   - Mark a draft asset as `approved` (update provenance `reviewStatus`) and copy it to `approved/<type>/`.
2. **Wire `qa-batch` into CI**
   - Run QA gate on generated outputs in GitHub Actions.
3. **Expand full-game taxonomy**
   - Add ambience, fanfares, UI, and combat audio coverage beyond the vertical slice.

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
