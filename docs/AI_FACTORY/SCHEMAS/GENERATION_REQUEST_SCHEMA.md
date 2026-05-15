# Generation Request Schema

> This contract is partially implemented in code via `audio_engine/integration/factory_inputs.py` for fixture-backed request-batch loading and validation. Batch execution/provenance writing remain future work.

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

## Recommended review fields

- `qa.reviewStatus`
- `qa.notes`
- `qa.loopRequired`
- `qa.acceptanceProfile`
- `replaceExisting`
- `supersedesRequestId`

## Deterministic seed rule

Every generated asset should eventually be associated with a captured seed, even if a backend later becomes less deterministic. If exact determinism is impossible, record the closest available provenance metadata.
