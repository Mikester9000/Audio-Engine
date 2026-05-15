# SFX Subsystem Status

## What exists now

- prompt-driven SFX generation via `SFXGen`
- procedural synthesis helpers in `audio_engine/ai/sfx_synth.py`
- CLI access through `generate-sfx`
- current game integration map covers combat, magic, world, quest, and UI events

## What is missing

- formal taxonomy for material-dependent footsteps and environment variants
- automatic variation-generation workflow for repeated gameplay events
- broader request/review manifest coverage for additional SFX families beyond the current committed fixture set

## Variation strategy for repeated categories (SESSION-012)

This strategy is now **partially executable** in the factory pipeline for deterministic request authoring (validation + provenance metadata), while still not implementing automatic runtime randomization.

1. Define repeated-event families explicitly (e.g., `ui_confirm`, `footstep_stone`, `sword_hit_light`).
2. Pre-generate multiple variants per family as separate generation requests.
3. Use stable naming with explicit variant suffixes (`_var01`, `_var02`, ...).
4. Capture deterministic but distinct seeds for each variant and keep those seeds committed.
5. Keep prompts stylistically coherent within a family while varying micro-phrasing to avoid near-duplicates.
6. Route each variant through normal provenance/QA/export/approval paths; do not bypass existing review gates.

### Current execution boundary

- Request parsing now enforces repeated-family `_varNN` variant naming, distinct deterministic seeds per family, and contiguous variant index sequences.
- Request-batch provenance sidecars now include `variationFamily` and `variationIndex` for SFX variant requests.
- Variant selection at gameplay runtime is out of scope for the current codebase.
- The implemented factory responsibility is to generate and track variant assets reproducibly so downstream systems can pick among them.

## Category-specific loudness/readability targets (SESSION-013)

These are **review guidance targets** for SFX/ambience categories and variant families.
They align to existing QA outputs (`qa`, `qa-batch`) and do **not** imply new automated per-category gates.

### Existing executable QA floor (already implemented)

- `qa` and `qa-batch` currently enforce global loudness acceptance at **-30.0 to -9.0 LUFS**.
- True peak acceptance remains **≤ -0.1 dBFS**.
- Optional loop checks remain opt-in via `--check-loop`.

### Category guidance for manual review consistency

| Acceptance profile | Recommended loudness focus | Readability focus |
|---|---|---|
| `sfx-ui` | Aim near the quieter half of current QA pass band (typically around `-22` to `-14` LUFS) | Clear attack, minimal tail masking, no harsh spike fatigue in repeated menu use |
| `sfx-combat` | Aim near the stronger half of current QA pass band (typically around `-18` to `-10` LUFS) | Fast transient recognition during dense mixes; tails should not mask follow-up hits |
| `sfx-magic` | Mid-band guidance (typically around `-20` to `-12` LUFS) | Identity should remain readable over music; spectral tail should support element identity without clutter |
| `ambience-loop` | Lower-energy guidance inside pass band (typically around `-28` to `-18` LUFS) | Loop continuity and texture clarity should support scene mood without competing with foreground SFX/voice |

Use these ranges as review anchors, not as hard CLI thresholds. Continue using `qa-batch` JSON fields (`loudness_lufs`, `true_peak_dbfs`, `has_clipping`, `clipped_samples`, `loudness_ok`, `peak_ok`, `clipping_ok`, optional `loop_ok`) plus listening notes for final approval decisions.

## Near-term goals

1. expand SFX taxonomy from current event list to full game coverage
2. expand executable tooling around the documented variation strategy beyond current validation/provenance support
3. operationalize machine-readable review logging for per-asset and variant-family QA decisions
