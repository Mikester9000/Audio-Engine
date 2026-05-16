# Project Audio Plan Schema

> This contract is implemented in code via `audio_engine/integration/factory_inputs.py` for typed loading/validation and `audio_engine/integration/asset_pipeline.py` (`PlanBatchOrchestrator`) for plan-driven request orchestration.

## Purpose

A project audio plan describes the full set of desired assets for a game or game slice before generation begins.

Committed example:

- `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json`

## Suggested shape

```json
{
  "planVersion": "1.0.0",
  "project": "GameRewritten",
  "scope": "vertical-slice",
  "priorities": {
    "music": "high",
    "sfx": "high",
    "voice": "low"
  },
  "styleFamilies": [
    "heroic-sci-fantasy",
    "melancholic-techno-fantasy",
    "mythic-space-opera"
  ],
  "assetGroups": [
    {
      "groupId": "music-field",
      "type": "music",
      "required": true,
      "targets": [
        {
          "assetId": "bgm_field_day",
          "gameplayRole": "field exploration",
          "loop": true,
          "durationTargetSeconds": 90,
          "mood": ["adventure", "wonder", "forward-motion"]
        }
      ]
    }
  ]
}
```

## Required fields

| Field | Meaning |
|---|---|
| `planVersion` | Version of the plan format |
| `project` | Consuming project name |
| `scope` | Whole game, chapter, milestone, or vertical slice |
| `priorities` | Priority split across music, SFX, voice |
| `styleFamilies` | Allowed style buckets |
| `assetGroups` | Grouped desired assets |

## Recommended per-asset fields

- `assetId`
- `type`
- `gameplayRole`
- `targetPath`
- `loop`
- `durationTargetSeconds`
- `mood`
- `reviewPriority`
- `notes`

## Rule

Plan-driven execution should continue using this schema as the canonical selection contract, with executable prompt/seed/backend details supplied by generation-request batches, and `durationTargetSeconds` forwarded as per-request duration overrides for matched plan targets.
