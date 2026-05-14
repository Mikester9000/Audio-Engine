# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has typed plan/request loader primitives in code alongside the machine-guidance, **session-autopilot, and execution-safety** layer. The canonical next executable session is `SESSION-002` in `docs/AI_FACTORY/SESSION_QUEUE.md`: add request-batch generation using those loaders.

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
- [ ] Execute `SESSION-002` from `docs/AI_FACTORY/SESSION_QUEUE.md`
- [ ] Add approval/review workflow for generated assets

## Recommended next PRs

1. **Execute `SESSION-002` — add request-batch generation path**
   - Generate music/SFX from request files with deterministic seed handling.
2. **Execute `SESSION-003` — persist provenance + review status logs**
   - Capture request ID, seed, output path, and review state per generated asset.
3. **Execute `SESSION-004` — add automated batch QA command**
   - Wrap loudness/clipping/loop checks for generated sets.
4. **Implement `GameRewritten` export profile**
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
