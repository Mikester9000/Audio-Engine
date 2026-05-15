# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a complete draft-to-approved pipeline: `generate-request-batch` → provenance sidecars → `qa-batch` → `export-drafts` → `approve-draft` → `approved/<type>/`. The CI QA gate (`audio-qa.yml`) validates generated outputs on pushes and PRs that touch audio engine source, tests, example fixtures, or the workflow file itself. Music-duration policy is clearly documented. The next executable session is `SESSION-008` in `docs/AI_FACTORY/SESSION_QUEUE.md`: expand full-game taxonomy coverage.

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
- [ ] Execute `SESSION-008` — expand full-game taxonomy coverage

## Recommended next PRs

1. **Execute `SESSION-008` — expand full-game taxonomy coverage**
   - Add committed backlog/request fixtures for ambience, fanfares/stingers, UI, combat/spell SFX, tension, sadness, and optional voice.
   - Add long-form OST variant request entries for the key BGM tracks already marked `+ost` in `FULL_GAME_AUDIO_CHECKLIST.md` and `audio_plan.vertical_slice.v1.json`.
2. **Add plan-driven batch orchestration (SESSION-009)**
   - Wire the audio plan loader into the batch execution path.
3. **Expand neural backend support**
   - Add a switchable backend for local model generation.

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
