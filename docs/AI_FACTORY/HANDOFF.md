# Handoff

> Update this file at the end of every PR.

## Last completed change

Completed procedural audio quality-overhaul implementation scope:

- Replaced Markov-only melody behavior with structured phrase planning (`intro → A → A-var → B → climax → cadence`) using new `audio_engine/composer/phrase.py` (`SectionPlanner`, `MotifBank`).
- Upgraded procedural music arrangement to layered orchestration with cadence-aware phrase endings and loop pickup continuity while keeping deterministic seed behavior.
- Rewrote SFX recipes to category-specific synthesis strategies (explosion, footstep, hit/impact, whoosh/swing, laser, coin/pickup, jump, magic elemental spells, cure/summon, progression/UI cues, sword/slash).
- Rebuilt procedural voice synthesis with phoneme-class voiced/unvoiced handling, plosive/fricative treatment, sentence-level prosody arcs, and deterministic seed support.
- Added 8-voice active-layer management plus role-aware mixing/EQ in `Sequencer`; vectorized `Effects.chorus` to remove per-sample Python loops.
- Added local Tkinter studio workflow module and additive `audio-engine studio` CLI command.
- Updated continuity docs to mark SESSION-029 implemented (user override) and queued SESSION-029b UI/tooling follow-up.
- Follow-up QA Gate fix: SFX prompt parsing now recognizes `parry`/`block` explicitly and routes them to a dedicated metallic parry recipe so the committed combat-parry fixture clears the CI loudness floor.

## Verified in this session

```bash
python -m pytest
python tools/validate-assets.py assets/examples/ --verbose
audio-engine generate-request-batch --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json --output-dir /tmp/ci_qa_batch_local --quiet
audio-engine qa-batch --input-dir /tmp/ci_qa_batch_local/drafts/sfx --output-report /tmp/ci_qa_batch_local/qa_report.json --recursive
audio-engine generate-request-batch --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json --output-dir /tmp/ci_qa_music_local --quiet
audio-engine qa-batch --input-dir /tmp/ci_qa_music_local/drafts/music --output-report /tmp/ci_qa_music_local/qa_report.json --recursive
audio-engine generate-request-batch --batch-file docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.voice.v1.json --output-dir /tmp/ci_qa_voice_local --quiet
audio-engine qa-batch --input-dir /tmp/ci_qa_voice_local/drafts/voice --output-report /tmp/ci_qa_voice_local/qa_report.json --recursive
python -m pytest tests/test_procedural_overhaul.py tests/test_generator.py tests/test_sequencer.py tests/test_effects.py tests/test_ai_pipeline.py -k "not OptionalNeuralBackends"
python -m pytest tests/test_ps1_era.py -k "FF7StylePresets or FF7SFXTypes"
python -m pytest tests/test_engine_cli.py -k "list_styles or generate or studio"
```

Observed result:
- procedural-overhaul focused tests pass (phrase planner, SFX spectral differentiation, deterministic music/voice generation, sequencer 8-layer limit, studio wiring)
- PS1/FF-style regression slices pass for style presets + expanded SFX aliases
- CLI regression slice passes with additive `studio` command coverage
- full pytest passes (914 tests)
- asset manifest validation passes
- local reproduction of the Audio QA Gate workflow now passes for SFX, music, and voice fixtures; `req_sfx_combat_parry_v1.wav` now clears QA at -18.19 LUFS

## Immediate next best task

Execute `SESSION-028` (`verify-backends`) next, then follow SESSION-029b for iterative studio tooling UX improvements.

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`
5. `docs/AI_FACTORY/HANDOFF.md`
6. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
7. `docs/AI_FACTORY/FAILSAFE_RULES.md`

## Handoff checklist

- [x] Request-batch generation command (`generate-request-batch`)
- [x] Per-request provenance sidecar files (`.provenance.json`)
- [x] Batch QA gate command (`qa-batch` with JSON report)
- [x] GameRewritten export profile (`export-drafts` to `Content/Audio/`)
- [x] Approval workflow (`approve-draft` → `approved/<type>/`, updates provenance)
- [x] QA gate wired into CI (`.github/workflows/audio-qa.yml`)
- [x] Music-duration policy documented and encoded in checklist, layout, music subsystem, and example plan
- [x] Full-game taxonomy coverage expansion (SESSION-008)
- [x] Plan-driven batch orchestration (SESSION-009, including required `.ogg` output production)
- [x] Backend support surface expansion (SESSION-010)
- [x] Backend evaluation metadata in code and CLI output (SESSION-011)
- [x] Repeated-SFX variation validation + provenance metadata in code (SESSION-012)
- [x] Category-specific SFX loudness/readability guidance (SESSION-013, docs-only)
- [x] Variant-family review/report template updates (SESSION-014, docs-only)
- [x] Machine-readable review-log writer (`ReviewLogWriter` + `write-review-log`, SESSION-015)
- [x] Review-log handoff integration for approval/export (`approve-draft`/`export-drafts` flags, SESSION-016)
- [x] Session queue refresh to define next executable implementation session (SESSION-017)
- [x] Plan target duration enforcement in plan-driven execution (SESSION-018)
- [x] Optional request-level `durationSeconds` parsing + direct request-batch execution support (SESSION-019)
- [x] Queue advancement and next executable session definition (SESSION-020)
- [x] Legacy request-file explicit-duration parity (SESSION-021)
- [x] Queue advancement and next executable session definition (SESSION-022)
- [x] Optional provenance sidecars for legacy request-file execution path (SESSION-023)
- [x] Result-JSON sourced review-log writing for legacy request-file workflow (SESSION-024)
- [x] Queue advancement and next executable session definition (SESSION-025)
- [x] Legacy request-file batch-manifest parity without result-json breakage (SESSION-026)
- [x] Queue advancement and next executable session definition (SESSION-027)
