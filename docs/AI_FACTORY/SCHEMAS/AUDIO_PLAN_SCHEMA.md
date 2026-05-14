# Project Audio Plan Schema

> This is a documentation contract for future work. It is not yet implemented in code.

## Purpose

A project audio plan describes the full set of desired assets for a game or game slice before generation begins.

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

Future implementation should read from a plan like this rather than relying only on ad hoc prompts.
