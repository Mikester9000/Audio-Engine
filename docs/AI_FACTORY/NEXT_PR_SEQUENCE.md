# Next PR Sequence

> Mechanical build order for future agents. `SESSION_QUEUE.md` remains canonical for the single next executable session.

## PR-7 — Consolidate to MusicGen Medium + sample folder structure

- **Suggested title:** `Consolidate neural model baseline to MusicGen Medium and add sample drop-in scaffold`
- **Objective:** Keep one optional neural model path (`musicgen-medium`) and add committed sample folder scaffolding for orchestral drop-ins.
- **Why it matters:** Reduces setup complexity while preparing deterministic sample-remaster workflows.
- **Likely files to change:** `tools/download_models.py`, `audio_engine/ai/backends/__init__.py`, `audio_engine/ai/backends/musicgen_backend.py`, `WINDOWS_QUICKSTART.md`, `models/README.md`, `.gitignore`, `samples/*`
- **Verification commands:** `python -m pytest tests/test_ai_pipeline.py tests/test_musicgen_backend.py`
- **Definition of done:** Only MusicGen Medium is downloaded/registered by default, and sample scaffold + docs are committed.

## PR-8 — Synth quality upgrade (chorus/reverb/stereo/mastering profiles)

- **Suggested title:** `Upgrade procedural synth and mastering quality for standalone listening`
- **Objective:** Improve instrument voicing, add optional DSP modules, add mastering profiles, and loop crossfade baking.
- **Why it matters:** Raises procedural output quality toward OST/YouTube usability.
- **Likely files to change:** `audio_engine/synthesizer/instrument.py`, `audio_engine/dsp/chorus.py`, `audio_engine/dsp/reverb.py`, `audio_engine/dsp/stereo.py`, `audio_engine/render/offline_bounce.py`, `audio_engine/render/loop_exporter.py`, `audio_engine/ai/music_gen.py`, tests
- **Verification commands:** `python -m pytest tests/test_instrument.py tests/test_dsp.py tests/test_dsp_chorus.py tests/test_dsp_reverb.py tests/test_dsp_stereo.py tests/test_render.py tests/test_loop_exporter.py`
- **Definition of done:** New DSP/profile code paths are additive, tested, and default behavior remains backward compatible.

## PR-9 — Sample library scanner + pitch-shift engine (completed)

- **Suggested title:** `Add sample library scanning and deterministic pitch shifting`
- **Objective:** Implement `audio_engine/integration/sample_library.py` and `audio_engine/dsp/pitch_shift.py`.
- **Why it matters:** Enables note-aligned sample substitution for orchestral remastering.
- **Likely files to change:** `audio_engine/integration/sample_library.py`, `audio_engine/dsp/pitch_shift.py`, tests
- **Verification commands:** `python -m pytest tests/test_sample_library.py tests/test_pitch_shift.py`
- **Definition of done:** ✅ Completed — engine now indexes `samples/orchestral` note files and pitch-shifts source notes to requested targets reproducibly.

## PR-10 — Remaster pipeline + CLI command (completed)

- **Suggested title:** `Add remaster pipeline and additive remaster CLI`
- **Objective:** Implement `audio_engine/render/remaster.py` and `audio-engine remaster` command.
- **Why it matters:** Turns synth-first outputs into higher-fidelity sample-based renders from provenance events.
- **Likely files to change:** `audio_engine/render/remaster.py`, `audio_engine/cli.py`, integration tests
- **Verification commands:** `python -m pytest tests/test_remaster.py tests/test_engine_cli.py -k remaster`
- **Definition of done:** ✅ Completed — CLI remaster path works with event-driven sample substitution and synth fallback per instrument.

## PR-11 — Backend preflight verify command (SESSION-028)

- **Suggested title:** `Add verify-backends readiness command`
- **Objective:** Add `audio-engine verify-backends` with deterministic report output.
- **Why it matters:** Improves local/offline neural readiness checks before long generation runs.
- **Likely files to change:** `audio_engine/cli.py`, `audio_engine/ai/backend.py`, tests
- **Verification commands:** `python -m pytest tests/test_engine_cli.py tests/test_ai_pipeline.py`
- **Definition of done:** Command reports availability/dependency status and optional smoke outcomes.

## PR-12 — Procedural quality-overhaul implementation (SESSION-029, completed)

- **Suggested title:** `Implement procedural phrase/SFX/voice quality overhaul`
- **Objective:** Land executable PS2-era procedural quality upgrades across music/SFX/voice/sequencing and add a local studio launch surface.
- **Why it matters:** Improves default offline output quality without requiring neural dependencies.
- **Likely files to change:** `audio_engine/ai/generator.py`, `audio_engine/composer/phrase.py`, `audio_engine/ai/sfx_synth.py`, `audio_engine/ai/voice_synth.py`, `audio_engine/composer/sequencer.py`, `audio_engine/synthesizer/effects.py`, `audio_engine/ui/*`, tests/docs
- **Verification commands:** targeted pytest slices for generator/sfx/voice/sequencer/CLI/studio + relevant regression slices
- **Definition of done:** Structured deterministic procedural outputs and additive studio entrypoint are implemented and tested.

## PR-13 — Studio creation-tooling follow-up (SESSION-029b)

- **Suggested title:** `Expand studio creation tooling presets and workflow UX`
- **Objective:** Add preset save/load, quick batch generation controls, and improved failure recovery to `audio-engine studio`.
- **Why it matters:** Lowers iterative content-creation friction for non-CLI users.
- **Likely files to change:** `audio_engine/ui/studio.py`, `audio_engine/cli.py`, docs, tests
- **Verification commands:** `python -m pytest tests/test_engine_cli.py tests/test_procedural_overhaul.py -k studio`
- **Definition of done:** Studio retains compatibility and offers repeatable creation tooling primitives for routine asset generation.

## PR-14 — WAV sample folder ingestion contract (SESSION-030)

- **Suggested title:** `Define strict WAV ingestion contract for sample folders`
- **Objective:** Publish deterministic layout/naming/metadata/rejection rules.
- **Why it matters:** Keeps sample ingestion deterministic for weak local agents.
- **Likely files to change:** `docs/AI_FACTORY/*` schema and subsystem pages
- **Verification commands:** manual doc review + JSON parse checks
- **Definition of done:** Ingestion contract is explicit enough for no-ambiguity automation.

## PR-15 — Batch remaster pipeline wiring (SESSION-031, completed)

- **Suggested title:** `Wire deterministic batch remaster execution`
- **Objective:** Add batch remaster execution and machine-readable outcomes.
- **Why it matters:** Scales remastering beyond one-off CLI usage.
- **Likely files to change:** `audio_engine/integration/asset_pipeline.py`, `audio_engine/cli.py`, tests
- **Verification commands:** `python -m pytest tests/test_integration.py tests/test_engine_cli.py -k remaster`
- **Definition of done:** ✅ Completed — batch remaster pipeline runs deterministically with machine-readable result manifests.

## PR-16 — License compliance CI gate (SESSION-032/033/034)

- **Suggested title:** `Add license compliance gate and policy matrix`
- **Objective:** Implement CI/license checks plus inventory and allow/conditional/block matrix.
- **Why it matters:** Required for commercial-readiness claims.
- **Likely files to change:** compliance tooling, workflow files, docs matrix/inventory pages
- **Verification commands:** targeted compliance tests + workflow dry-run checks
- **Definition of done:** CI fails on unknown/disallowed licenses with machine-readable reports.

## PR-17 — Mastering profile presets: game mix / OST / YouTube (SESSION-035)

- **Suggested title:** `Finalize mastering profile selection contracts`
- **Objective:** Stabilize profile selection and parameter capture across generation/export paths.
- **Why it matters:** Ensures repeatable delivery for game vs OST vs streaming output.
- **Likely files to change:** `audio_engine/render/offline_bounce.py`, CLI/profile docs, tests
- **Verification commands:** `python -m pytest tests/test_render.py tests/test_engine_cli.py -k profile`
- **Definition of done:** Profiles are selectable, deterministic, documented, and backward compatible.

## PR-18 — Professional QA gates (SESSION-036)

- **Suggested title:** `Expand professional release QA gates`
- **Objective:** Add true-peak, spectral balance, and loop-integrity checks.
- **Why it matters:** Turns subjective quality goals into enforceable release gates.
- **Likely files to change:** `audio_engine/qa/*`, CLI QA commands, tests
- **Verification commands:** `python -m pytest tests/test_qa.py tests/test_engine_cli.py -k qa`
- **Definition of done:** New QA checks are actionable, machine-readable, and integrated into existing gates.

## PR-19 — Commercial WAV export contract (SESSION-037)

- **Suggested title:** `Add commercial WAV-first export contract`
- **Objective:** Define deterministic naming/layout/manifests for commercial delivery.
- **Why it matters:** Prevents export drift between game import and distribution workflows.
- **Likely files to change:** export pipeline code/docs/tests
- **Verification commands:** `python -m pytest tests/test_exporter.py tests/test_integration.py -k export`
- **Definition of done:** Export outputs follow stable contracts with manifest evidence.

## PR-20 — Vocals + instrumental production path (SESSION-038)

- **Suggested title:** `Complete dual-path vocal and instrumental workflow`
- **Objective:** Support generation/export of instrumental and vocal-production-ready variants.
- **Why it matters:** Expands utility for general music production workflows.
- **Likely files to change:** generation pipeline, voice integration docs, tests
- **Verification commands:** `python -m pytest tests/test_ai_pipeline.py tests/test_integration.py -k voice`
- **Definition of done:** Deterministic dual-path outputs with clear provenance.

## PR-21 — End-to-end vertical slice release gate automation (SESSION-041)

- **Suggested title:** `Automate full vertical-slice release gate`
- **Objective:** One deterministic command from requests → QA/compliance/export outputs.
- **Why it matters:** Lowers operational burden for full factory runs.
- **Likely files to change:** orchestration CLI/pipeline and docs
- **Verification commands:** deterministic `/tmp` end-to-end smoke run + targeted tests
- **Definition of done:** Full vertical-slice automation runs with machine-readable gate artifacts.

## PR-22 — Final commercial readiness audit + closure (SESSION-044/045)

- **Suggested title:** `Run final readiness audit and publish closure handoff`
- **Objective:** Audit all capability/quality/licensing/automation gates and close baseline factory scope.
- **Why it matters:** Ensures completion claims are evidence-based and reversible.
- **Likely files to change:** `docs/AI_FACTORY/HANDOFF.md`, `CURRENT_STATE.md`, `SESSION_HISTORY.md`, session-control docs
- **Verification commands:** required JSON parse checks + referenced verification command replay summaries
- **Definition of done:** Final audit evidence is documented and session-control files reflect closure state.
