# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a stronger machine-guidance layer (implementation matrix, codebase map, next PR sequence, and committed example artifacts). The next priority is to implement plan/request ingestion in code.

## Now

- [x] Establish AI-first mission/state/handoff docs
- [x] Add explicit operating instructions for future agents
- [x] Document current implementation, gaps, and roadmap
- [x] Define a committed `GameRewritten`-oriented audio plan example
- [x] Commit generation request + review/provenance example artifacts
- [x] Add implementation matrix + codebase map + next-PR sequence docs
- [ ] Implement code-side loading of plan/request artifacts
- [ ] Add approval/review workflow for generated assets

## Recommended next PRs

1. **Implement plan/request loaders in integration layer**
   - Parse committed example artifacts into typed runtime structures.
2. **Add request-batch generation path**
   - Generate music/SFX from request files with deterministic seed handling.
3. **Persist provenance + review status logs**
   - Capture request ID, seed, output path, and review state per generated asset.
4. **Add automated batch QA command**
   - Wrap loudness/clipping/loop checks for generated sets.
5. **Implement `GameRewritten` export profile**
   - Align generated outputs with stable downstream import paths.

## Do not deprioritize

- music usefulness
- SFX coverage
- deterministic regeneration
- downstream folder organization
- continuity docs

## Lower-priority work

- premium voice generation
- Windows-native developer ergonomics beyond basic setup
- broad UI polish
- nonessential refactors
