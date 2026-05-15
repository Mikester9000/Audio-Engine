# GameRewritten Vertical Slice Example Artifacts

These artifacts are committed examples/contracts for future plan-driven factory workflows.

- They are intentionally explicit and repetitive for AI-agent consumption.
- They are **not yet wired into code-level orchestration**.
- They model a realistic RPG-style slice and align with the long-term goal of full game audio coverage.

## Files

- `audio_plan.vertical_slice.v1.json` — project-level audio plan example
- `generation_requests.music.v1.json` — music request examples
- `generation_requests.sfx.v1.json` — SFX request examples
- `generation_requests.voice.v1.json` — optional placeholder voice request examples
- `review_log.example.v1.json` — simple provenance/review status example

## Intended usage in future PRs

1. parse these artifacts in code
2. execute request batches deterministically
3. persist generation + review provenance
4. map approved assets to stable `GameRewritten` import paths
