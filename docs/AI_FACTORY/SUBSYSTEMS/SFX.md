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

## Near-term goals

1. expand SFX taxonomy from current event list to full game coverage
2. expand executable tooling around the documented variation strategy beyond current validation/provenance support
3. define category-specific loudness/readability targets
