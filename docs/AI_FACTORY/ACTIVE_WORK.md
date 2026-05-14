# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a working request-batch generation command (`generate-request-batch`) that executes any committed generation-request batch deterministically, using per-request seeds, through the `RequestBatchPipeline`. The next executable session is `SESSION-003` in `docs/AI_FACTORY/SESSION_QUEUE.md`: persist provenance + review logs per generated request.

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
- [ ] Execute `SESSION-003` — persist provenance + review logs per request
- [ ] Add approval/review workflow for generated assets

## Recommended next PRs

1. **Execute `SESSION-003` — persist provenance + review status logs**
   - Capture request ID, seed, output path, and review state per generated asset.
2. **Execute `SESSION-004` — add automated batch QA command**
   - Wrap loudness/clipping/loop checks for generated sets.
3. **Implement `GameRewritten` export profile**
   - Align generated outputs with stable downstream import paths.

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
