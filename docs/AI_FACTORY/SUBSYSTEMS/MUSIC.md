# Music Subsystem Status

## What exists now

- style-based generation through `AudioEngine.generate_track()`
- prompt-driven generation through `MusicGen`
- mastering through `OfflineBounce`
- CLI access through `generate` and `generate-music`
- existing integration mapping for multiple game states in `audio_engine/integration/game_state_map.py`

## What is missing

- project-level plan-driven music generation
- explicit review status tracking per music asset
- richer style-preset registry beyond current built-in styles
- `GameRewritten`-specific music backlog committed in this repo

## Near-term goals

1. define canonical music categories for downstream projects
2. capture prompt + seed + target path in request manifests
3. define loop and loudness acceptance profiles per category
