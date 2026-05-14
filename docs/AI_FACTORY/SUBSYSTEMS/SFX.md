# SFX Subsystem Status

## What exists now

- prompt-driven SFX generation via `SFXGen`
- procedural synthesis helpers in `audio_engine/ai/sfx_synth.py`
- CLI access through `generate-sfx`
- current game integration map covers combat, magic, world, quest, and UI events

## What is missing

- formal taxonomy for material-dependent footsteps and environment variants
- variation-generation workflow for repeated gameplay events
- request/review manifests for individual SFX families

## Near-term goals

1. expand SFX taxonomy from current event list to full game coverage
2. document variation strategy for repetitive sounds
3. define category-specific loudness/readability targets
