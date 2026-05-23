# Active Work

> Update this file in every PR that changes priorities, in-progress work, or recommended next tasks.

## Current headline

The repository now has a complete draft-to-approved pipeline, a MusicGen-Medium-only offline neural path, sample drop-in folder scaffolding, upgraded synth/mastering/DSP quality surfaces, and an implemented procedural quality-overhaul pass (structured composition + recipe-driven SFX + improved voice + expanded studio UI with preview playback controls). Latest additive work (SESSION-049/051) expands full-edit studio controls and new-file workflow templates, adds style/instrument/SFX coverage + alignment validation, and refines piano/guitar timbral identity toward PS2-era FF8/FF10 aesthetics.

Latest additive work extended procedural music coverage with new narrative/region presets and added region-aware + adaptive layer-bundle output options in `MusicGen`.

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
- [x] Execute `SESSION-017` — define next implementation session after review-log integration
- [x] Execute `SESSION-018` — enforce plan-target duration overrides in plan-driven execution
- [x] Execute `SESSION-019` — add optional per-request duration field for direct request-batch execution
- [x] Execute `SESSION-020` — define and queue the next executable implementation session
- [x] Execute `SESSION-021` — unify explicit-duration behavior for legacy request-file execution path
- [x] Execute `SESSION-022` — define and queue the next executable implementation session
- [x] Execute `SESSION-023` — add optional provenance sidecars for legacy request-file execution path
- [x] Execute `SESSION-024` — add result-JSON sourcing path for review-log writing
- [x] Execute `SESSION-025` — define and queue the next executable implementation session
- [x] Execute `SESSION-026` — add legacy request-file batch-manifest parity
- [x] Execute `SESSION-027` — define and queue the next executable implementation session
- [x] Execute `SESSION-028` — add backend preflight verification command for optional neural workflows
- [x] Consolidate optional model download/registration to MusicGen Medium only
- [x] Add committed sample folder scaffold for orchestral remaster drop-ins
- [x] Add additive chorus/reverb/stereo DSP modules and loop crossfade baking
- [x] Add additive mastering profile presets (`game`, `ost`, `youtube`, `vocal_mix`, `procedural_neutral`)
- [x] Upgrade procedural instrument voicing toward higher-quality standalone listening output
- [x] Execute SESSION-029 implementation override — procedural quality overhaul + phrase planner + studio UI entrypoint
- [x] Execute SESSION-030 — WAV sample-folder ingestion contract (docs)
- [x] Execute SESSION-033 — license inventory (docs)
- [x] Execute SESSION-034 — commercial eligibility matrix (docs)
- [x] Execute SESSION-035 — vocal_mix mastering profile + `--profile` flag on `generate-music`
- [x] Execute SESSION-039 — autopilot command contracts (docs)
- [x] Execute SESSION-036 — expand QA gates for professional WAV release quality (`SpectralAnalyzer`, spectral balance/intelligibility in `qa-batch` JSON)
- [x] Execute SESSION-037 — deterministic commercial WAV delivery contract (`WavDeliveryPipeline`, `export-wav-delivery` CLI)
- [x] Execute SESSION-040 — deterministic regression harness (`tests/test_regression.py`)
- [x] Execute SESSION-043 — freeze seed policy (`docs/AI_FACTORY/SEED_POLICY.md`)
- [x] Execute SESSION-044 — final commercial readiness audit (`docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md`)
- [x] Execute SESSION-045 — completion-state handoff (`docs/AI_FACTORY/COMPLETION_HANDOFF.md`)
- [x] Execute SESSION-028b — sample-library scanner + pitch-shift engine (`audio_engine/integration/sample_library.py`, `audio_engine/dsp/pitch_shift.py`)
- [x] Execute SESSION-028c — deterministic remaster pipeline + CLI wiring (`audio_engine/render/remaster.py`, `audio-engine remaster --events-json`)
- [x] Execute SESSION-031 — deterministic remaster-batch pipeline (`RemasterBatchPipeline`, `audio-engine remaster-batch`)
- [x] Execute SESSION-046 — expand music testing fixture style coverage (`generation_requests.music.v1.json`, `tests/test_integration.py`)
- [x] Execute SESSION-047 — synchronize continuity/session-control docs after SESSION-046
- [x] Execute SESSION-029b — expand studio creation tooling with presets/profile loading/batch shortcut/retry UX
- [x] Execute SESSION-038 — stabilize dual-path vocal/instrumental production outputs with provenance linkage
- [x] Complete ordered task-list batch continuation: Task 04 (music style preset expansion) + Task 05 (region-aware/adaptive `MusicGen` output options)
- [x] Execute SESSION-041 — end-to-end vertical-slice release gate automation (`VerticalSliceGatePipeline`, `run-release-gate` CLI)
- [x] Execute SESSION-049 — studio full-edit workflow + synthesis/theory alignment expansion
- [x] Execute SESSION-051 — PS2 instrument identity refinement (piano + guitar families)

## Recommended next PRs

1. Execute SESSION-050 release-gate integration for style/synth intent validation output.
2. Continue iterative named-instrument identity refinement for additional timbres while preserving deterministic style profiles.

## Do not deprioritize

- music usefulness
- SFX coverage
- deterministic regeneration
- downstream folder organization
- continuity docs
- session queue clarity

## Lower-priority work

- premium voice generation
- Windows-native developer ergonomics beyond the current setup/run bootstrap scripts
- broad UI polish
- nonessential refactors
