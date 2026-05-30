# Music Subsystem Status

## What exists now

- style-based generation through `AudioEngine.generate_track()`
- prompt-driven generation through `MusicGen`
- expanded narrative/region style presets (`stealth`, `memorial`, `mystery`, `underscore`, `ending`, and regional exploration variants) in `audio_engine/ai/generator.py`
- region-aware prompt shaping and optional adaptive layer bundle export (`layer_output_dir`) in `MusicGen.generate_to_file()`
- structured phrase planning + motif variation via `audio_engine/composer/phrase.py` (`SectionPlanner`, `MotifBank`)
- cadence-aware, loop-friendly 8-layer procedural arrangement in `audio_engine/ai/generator.py`
- mastering through `OfflineBounce`
- CLI access through `generate` and `generate-music`
- backend selection/discovery surfaces through `generate-music --backend` and `list-backends`
- studio-side music mastering-profile selection plus preset save/load, backend/sample controls, one-click batch generation, and play/stop preview browser in `audio_engine/ui/studio.py`
- studio-side full-edit controls for prompt/format/region/adaptive intensity plus procedural custom arrangement instrument overrides and new-file template output authoring
- request-driven dual-path delivery mode for paired instrumental and vocal-ready outputs (`musicDeliveryMode: dual_vocal_instrumental`)
- full-piece generation now auto-writes instrumental companion files whenever a rendered track includes vocals (`*__instrumental.wav|ogg`) across `compose-piece`, `generate-track`, `generate-radio-playlist`, and `generate-album`
- existing integration mapping for multiple game states in `audio_engine/integration/game_state_map.py`
- style-intent metadata and executable style/synth alignment validation via `MusicGenerator.validate_style_library_alignment()`
- release-gate generation now enforces and reports style/synth alignment results in `release_gate_report.json` (`gates.generation.styleAlignment`)
- standalone `audio-engine check-style-alignment` CLI command: calls `validate_style_library_alignment()`, prints human-readable summary, writes machine-readable JSON report to `--output-report` (or stdout), exits 1 when any issue is found
- expanded style families: `hybrid_trailer`, `neo_noir`, `festival_folk`, `sci_fi_pulse`, `waltz_orchestral`
- expanded timbres: `violin_solo`, `trumpet`, `acoustic_guitar`, `synth_lead_bright`
- expanded PS2-era realism timbres: `legato_strings_ps2`, `nylon_guitar_ps2`, `soft_epiano_ps2`
- global all-instrument PS2 realism voicing pass in `Instrument.render()` (console-era bandwidth shaping, gentle bus compression, subtle room glue)
- SESSION-051 timbre identity refinement: `piano`, `electric_guitar`, `ff8_electric_guitar`, and `acoustic_guitar` now have stronger instrument-name alignment under PS2-era FF8/FF10-style tonal constraints
- additive realism refinement for `violin_solo` + `trumpet` synthesis and vocal post-processing polish in `voice_synth`
- deterministic vocal post-processing chain remains enabled in `voice_synth` (cleanup/presence/de-ess/saturation/early reflections) so voice realism improvements preserve reproducible outputs
- FF7/FF8/FF10 presets now incorporate the new PS2-era timbres for broader arrangement variety while preserving deterministic style intent

## Style/synth alignment: check and remediation flow

### Quick check (standalone, no full gate)

```bash
audio-engine check-style-alignment
# writes JSON to stdout; exits 0 = all pass, exits 1 = issues found

audio-engine check-style-alignment --output-report reports/style_alignment.json --quiet
# writes report file, no console output
```

### Report schema

```json
{
  "compliant": true,
  "styleCount": 0,
  "issueCount": 0,
  "issues": {}
}
```

When issues are present `compliant` is `false`, `styleCount` is the number of affected styles, `issueCount` is the total number of issue messages, and `issues` is a mapping of style-name → list of issue strings.

### Release-gate integration

`audio-engine run-release-gate` calls `validate_style_library_alignment()` as the first check inside Gate 1 (Generation). If any issues are found, the gate records them in `release_gate_report.json` under `gates.generation.styleAlignment` and halts execution.

### Remediation steps when a style fails alignment

1. Run `audio-engine check-style-alignment` and read the `issues` map to identify the affected style(s).
2. Open `audio_engine/ai/generator.py` and find the `_StyleDef` entry for the failing style.
3. For each issue message:
   - **"instrument '…' not found"** — add the instrument to `audio_engine/synthesizer/instrument.py` or change the style's `instruments` list to use an existing instrument name.
   - **"tempo out of range"** — adjust the `bpm` field to be within the allowed range for that style category.
   - **"scale not recognised"** — correct the `scale` field to match a key defined in `_SCALE_INTERVALS`.
4. Re-run `audio-engine check-style-alignment` to confirm exit 0.
5. Run `python -m pytest tests/test_generator.py tests/test_release_gate.py` to confirm no regressions.

## What is missing

- broader style-keyword resolver coverage for every advanced preset family
- verified non-procedural backend quality benchmarks using real downloaded model weights
- full release-gate orchestration that consumes dual-path outputs end-to-end (SESSION-041 completed; style-alignment gate reporting now integrated)

## Backend evaluation notes (SESSION-011 + optional neural scaffolding)

- **Current implemented backend reality:** `procedural` remains the default backend, with optional local-files-only MusicGen adapter (`musicgen`) available when dependencies and local model folder are present.
- **Current selection/discovery surfaces:** users can list registered backends with `audio-engine list-backends` and select one with `--backend` on music/SFX/voice generation commands.
- **Current executable evaluation surface:** `BackendRegistry.evaluate_backends()` now reports backend availability, availability reason, dependency summary, and supported modalities; `audio-engine list-backends` prints this metadata.
- **Availability behavior:** backend availability is dependency-driven (`is_available()`); missing runtime dependencies should be treated as unavailable/failing execution rather than as quality regressions.
- **Future local/open backend guidance (docs, not implementation):**
  - acceptable adapter families include local ONNX-runtime wrappers, ggml/llama.cpp-style local wrappers, or local-files-only Hugging Face adapters
  - evaluate by deterministic reproducibility, dependency footprint, and command-line operability first
  - do not claim production quality or parity with commercial systems until implemented and verified in this repo

## Music duration policy

Different music asset categories have different appropriate duration targets.
This table is the canonical reference for agents and contributors:

| Category | Loop required | Duration target | Notes |
|---|---|---|---|
| Major themes (title, ending, credits) | optional | 120–300 s (up to 5 min) | Full-length game-ready pieces; may also have a shorter in-game loop variant |
| Gameplay BGM (field, town, dungeon, combat) | yes | 60–120 s | Loopable at a natural loop point |
| Boss battle | yes | 90–180 s | Complex structure; longer loop is preferred |
| Story cutscene / underscore | no | 30–120 s | Matches scene length; no loop point required |
| Tension / stealth | yes | 30–90 s | Minimal, atmospheric |
| Stingers and fanfares | no | 2–12 s | Short, punchy; must not be loopable |
| Save / level-up cues | no | 2–8 s | Very short reward signals |
| UI / system cues | no | 0.1–2 s | As short as possible |

### Long-form OST support policy

For shorter in-game gameplay tracks (BGM loops of 60–120 s), the factory
**should plan or generate a corresponding longer OST-style version** (120–300 s)
when that asset is important enough for a soundtrack release.  The OST version:

- is not required for game functionality
- is stored alongside the in-game loop under a clear `_ost` suffix (e.g.
  `bgm_field_day_ost.ogg`)
- may be generated from the same seed and prompt with a longer `duration`
  parameter
- should be noted in the `audio_plan.*.json` alongside the in-game request

### Default generation-request durations

When generating via `generate-request-batch`:

- Music requests with no explicit duration default to **30 s**.
- The `--music-duration` CLI flag only applies to the `--request-file` /
  `execute_request_batch` path; it is **ignored** by the `--batch-file` /
  `RequestBatchPipeline` path.
- The `--batch-file` / `RequestBatchPipeline` path now supports per-request
  `durationSeconds`; when provided, it is used as the explicit generation
  duration for music requests.
- For long-form OST variants, use the `--request-file` path with
  `--music-duration 180` (or higher, up to 300 s / 5 min), or use
  plan-driven orchestration where `durationTargetSeconds` is enforced per
  target.

## Near-term goals

1. define canonical music categories for downstream projects
2. capture prompt + seed + target path in request manifests
3. define loop and loudness acceptance profiles per category
4. add long-form OST variant support to example request fixtures
5. keep expanding committed style/mood/environment fixture prompts for
   deterministic broad-coverage testing
