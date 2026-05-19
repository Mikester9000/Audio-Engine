# Handoff

> Update this file at the end of every PR.

## Last completed change

Completed SESSION-036, SESSION-037, SESSION-040, SESSION-043, SESSION-044, and SESSION-045 in a single PR:

- **SESSION-036** (expand QA gates): Added `audio_engine/qa/spectral_analyzer.py` (`SpectralAnalyzer`, `SpectralReport`) providing spectral balance and intelligibility checks. Wired into `qa` and `qa-batch` CLI commands. Added `spectral_balance_ok`, `spectral_centroid_hz`, `high_freq_ratio` fields to `qa-batch` JSON reports. Updated `docs/AI_FACTORY/QA/QUALITY_BARS.md`. 13 new QA tests + 1 CLI test.
- **SESSION-037** (WAV delivery contract): Added `audio_engine/integration/export_contract.py` (`WavDeliveryPipeline`) that reads from `approved/` and writes deterministically-named copies plus `delivery_manifest.json` to a delivery directory. Naming contract: `<category>__<asset_id>__seed<N>.wav`. Added `audio-engine export-wav-delivery` CLI command with `--factory-root`, `--delivery-dir`, `--categories`, `--quiet` flags. 6 focused CLI tests.
- **SESSION-040** (regression harness): Created `tests/test_regression.py` with 13 tests covering QA metric stability (`LoudnessMeter`, `ClippingDetector`, `SpectralAnalyzer`), fixed-seed music/SFX reproducibility, and delivery manifest schema/naming determinism.
- **SESSION-043** (seed policy): Published `docs/AI_FACTORY/SEED_POLICY.md` with explicit seed precedence rules, format, delivery naming convention, and per-command enforcement status table.
- **SESSION-044** (commercial readiness audit): Published `docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md` with per-gate pass/fail evidence table and open-items for non-blocking planned sessions.
- **SESSION-045** (completion-state handoff): Published `docs/AI_FACTORY/COMPLETION_HANDOFF.md` with stable baseline capabilities table, maintenance instructions, and reading order for future agents.

## Verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_qa.py -k "Spectral"          # 12 passed
python -m pytest tests/test_engine_cli.py -k "spectral"  # 1 passed
python -m pytest tests/test_engine_cli.py -k "export_wav_delivery"  # 6 passed
python -m pytest tests/test_regression.py                # 13 passed
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
```

Observed result:
- All targeted tests pass (32 new tests total)
- SESSION_STATE.json and CURRENT_SESSION.json parse cleanly

## Immediate next best task

Execute **SESSION-028b** (sample library scanner + pitch-shift primitives), then SESSION-028c (remaster pipeline), then SESSION-031 (batch remaster wiring).

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/COMPLETION_HANDOFF.md`
5. `docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md`
6. `docs/AI_FACTORY/SEED_POLICY.md`

## Handoff checklist

- [x] Request-batch generation command (`generate-request-batch`)
- [x] Per-request provenance sidecar files (`.provenance.json`)
- [x] Batch QA gate command (`qa-batch` with JSON report)
- [x] Spectral balance + intelligibility QA gates (`SpectralAnalyzer`, SESSION-036)
- [x] GameRewritten export profile (`export-drafts` to `Content/Audio/`)
- [x] Commercial WAV delivery (`export-wav-delivery` with deterministic naming, SESSION-037)
- [x] Approval workflow (`approve-draft` → `approved/<type>/`, updates provenance)
- [x] QA gate wired into CI (`.github/workflows/audio-qa.yml`)
- [x] Deterministic regression harness (`tests/test_regression.py`, SESSION-040)
- [x] Seed policy locked (`docs/AI_FACTORY/SEED_POLICY.md`, SESSION-043)
- [x] Commercial readiness audit evidence (`docs/AI_FACTORY/COMMERCIAL_READINESS_AUDIT.md`, SESSION-044)
- [x] Completion-state handoff (`docs/AI_FACTORY/COMPLETION_HANDOFF.md`, SESSION-045)
- [x] Session control docs synchronized (SESSION_QUEUE, SESSION_STATE, CURRENT_SESSION, ACTIVE_WORK)

- **SESSION-028** (`verify-backends`): Added `audio-engine verify-backends` CLI command with deterministic per-backend availability checks, optional 0.25 s smoke runs per modality, and a structured JSON report. Exits 0 when all backends are available; exits 2 when any are unavailable. 6 targeted tests added.
- **SESSION-035** (mastering profiles): Added `vocal_mix` profile to `OfflineBounce` (low-mid tighten + air boost + 0.12 reverb mix; reverb preset `medium_hall`). Exported `VALID_PROFILES` constant. Added `mastering_profile` parameter to `MusicGen` so CLI `--profile` wires directly to the bounce pipeline. Exposed `--profile` flag on `generate-music`. 4 new tests.
- **SESSION-030** (WAV ingestion contract): Created `docs/AI_FACTORY/SCHEMAS/WAV_INGESTION_CONTRACT.md` with explicit folder layout, accepted formats, naming rules, pitch-shift behavior, rejection rules, and CLI integration table.
- **SESSION-033** (license inventory): Created `docs/AI_FACTORY/LICENSE_INVENTORY.md` with SPDX-mapped per-package rows for all core, optional neural, and model-weight dependencies.
- **SESSION-034** (commercial eligibility matrix): Created `docs/AI_FACTORY/COMMERCIAL_ELIGIBILITY_MATRIX.md` with allow/conditional/block by backend×model combination and safe commercial-use workflow.
- **SESSION-039** (autopilot contracts): Created `docs/AI_FACTORY/AUTOPILOT_COMMAND_CONTRACTS.md` with ordered no-choice step sequences for all 11 production workflow types.

## Verified in this session

```bash
python -m pip install -e ".[dev]"
python -m pytest   # 928 passed
python tools/validate-assets.py assets/examples/ --verbose
python -m pytest tests/test_engine_cli.py -k "verify_backends"
python -m pytest tests/test_render.py -k "vocal_mix"
python -m json.tool docs/AI_FACTORY/SESSION_STATE.json
python -m json.tool docs/AI_FACTORY/CURRENT_SESSION.json
```

Observed result:
- full pytest passes (928 tests)
- asset manifest validation passes
- all `verify_backends` tests pass (6 new tests)
- all `vocal_mix` render tests pass
- SESSION_STATE.json and CURRENT_SESSION.json parse cleanly

## Immediate next best task

Execute `SESSION-036` (expand QA gates for professional WAV release quality).

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`


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
