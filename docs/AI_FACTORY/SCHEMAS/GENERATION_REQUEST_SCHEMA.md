# Generation Request Schema

> This contract is implemented in code via `audio_engine/integration/factory_inputs.py` (typed loading/validation) and `audio_engine/integration/asset_pipeline.py` (`RequestBatchPipeline` and `PlanBatchOrchestrator`) for deterministic execution and provenance writing.

## Purpose

A generation request is one concrete instruction to create or regenerate an asset.

Committed examples:

- `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json`
- `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json`
- `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.voice.v1.json`
- `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json`

## Suggested shape

```json
{
  "requestVersion": "1.0.0",
  "requestId": "req_music_field_day_v1",
  "assetId": "bgm_field_day",
  "type": "music",
  "backend": "procedural",
  "seed": 42,
  "prompt": "uplifting exploration field theme with melancholic sci-fantasy undertone, loopable",
  "styleFamily": "heroic-sci-fantasy",
  "output": {
    "targetPath": "Content/Audio/bgm_field_day.ogg",
    "format": "ogg",
    "sampleRate": 44100,
    "channels": 2
  },
  "qa": {
    "loopRequired": true,
    "reviewStatus": "draft",
    "loudnessTarget": "music-loop",
    "notes": []
  }
}
```

## Required fields

- `requestVersion`
- `requestId`
- `assetId`
- `type`
- `backend`
- `seed`
- `prompt`
- `styleFamily`
- `output.targetPath`

## Backend field guidance (SESSION-011)

- `backend` is required and should explicitly name the intended backend.
- Today, `procedural` is the only implemented and guaranteed backend.
- Before running large batches, verify registry/availability with `audio-engine list-backends`.
- `audio-engine list-backends` now exposes executable backend-evaluation metadata (`available`, supported modalities, dependency summary, availability reason) sourced from `BackendRegistry.evaluate_backends()`.
- Requests that require an unavailable backend should fail fast; do not silently switch to a different backend unless explicitly requested in project policy.

## Recommended review fields

- `qa.reviewStatus`
- `qa.notes`
- `qa.loopRequired`
- `qa.acceptanceProfile`
- `replaceExisting`
- `supersedesRequestId`

## Repeated SFX variation strategy (SESSION-012)

Until automated variation orchestration exists, repeated SFX categories should use deterministic request-level variation records:

- model each variant as its own request in the same request batch
- keep a stable family stem in `assetId`/`requestId` and append a variant suffix (`_var01`, `_var02`, ...)
- assign deterministic but distinct seeds per variant in a stable sequence
- keep prompt/style family semantically aligned across the variant family while introducing controlled wording differences
- keep output paths explicit per variant so downstream import and QA can track each generated file independently

Current executable enforcement:

- repeated SFX families in a single request batch now require `_varNN` suffixes on `assetId`, `requestId`, and output filename stem
- variant indices must align across those fields and be contiguous (`_var01.._varNN`) per family
- seeds must be deterministic and distinct per variant family
- SFX variant provenance now includes `variationFamily` and `variationIndex`

## Acceptance-profile alignment note (SESSION-013/014)

- Existing executable QA checks remain global (`-30..-9` LUFS band, peak `<= -0.1 dBFS`) in `qa` / `qa-batch`.
- `qa.acceptanceProfile` should still be populated for category intent (`sfx-ui`, `sfx-combat`, `sfx-magic`, `ambience-loop`) so review logs can apply category-specific loudness/readability guidance consistently.
- Variant-family review decisions are tracked in review/report artifacts, not in request schema enforcement.

## Deterministic seed rule

Every generated asset should eventually be associated with a captured seed, even if a backend later becomes less deterministic. If exact determinism is impossible, record the closest available provenance metadata.
