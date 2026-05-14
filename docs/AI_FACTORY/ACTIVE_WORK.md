# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a persistent AI-first documentation system. The next priority is to turn that documentation into machine-driven planning and generation inputs.

## Now

- [x] Establish AI-first mission/state/handoff docs
- [x] Add explicit operating instructions for future agents
- [x] Document current implementation, gaps, and roadmap
- [ ] Define a committed `GameRewritten`-oriented audio plan format
- [ ] Define batch generation request format and deterministic seed capture
- [ ] Add approval/review workflow for generated assets

## Recommended next PRs

1. **Add project audio plan example**
   - Create a machine-readable example plan for a PS2-scale RPG slice.
2. **Add request-to-output manifest flow**
   - Capture prompt, style family, seed, output path, and QA notes.
3. **Add automated audio QA command**
   - Wrap loudness/clipping/loop checks for asset batches.
4. **Add `GameRewritten` target mapping**
   - Translate game states and events into a full asset backlog.
5. **Add backend evaluation matrix**
   - Document which local/open model backends are worth integrating later.

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
