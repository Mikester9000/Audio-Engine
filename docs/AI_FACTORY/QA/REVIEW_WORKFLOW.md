# Asset Review Workflow

> Update this file whenever review states or review expectations change.

## Purpose

Generated assets should not move from draft output to downstream import by accident. Review must be explicit.

## Recommended review states

| State | Meaning |
|---|---|
| `draft` | generated but not reviewed |
| `approved` | acceptable for downstream use |
| `revise` | promising but needs another pass |
| `rejected` | wrong direction; do not ship |
| `overridden` | replaced by a manual or alternate asset |

## Review checklist

### Music

- gameplay role is correct
- loop behavior is correct when required
- no obvious clipping or bad seam
- emotional target fits the scene
- output does not feel like a direct copyrighted imitation

### SFX

- transient/readability fits gameplay
- category identity is clear
- tail length is appropriate
- repetition fatigue risk is acceptable

### Voice

- intelligibility is acceptable
- timing fits gameplay use
- quality is good enough for the current milestone

## Variant-family review/report template updates (SESSION-014)

Use a two-level review model for repeated SFX families:

1. **Per-asset review entry** (normal review state per generated file)
2. **Per-family decision entry** (one summary decision for the `_varNN` family)

### Per-asset review entry fields (recommended)

- `assetId`, `requestId`, `seed`
- `generatedOutputPath`, `targetImportPath`
- `reviewStatus`, `reviewer`, `reviewedAt`, `notes`
- `qaSnapshot` (optional): `loudnessLufs`, `truePeakDbfs`, `loudnessOk`, `peakOk`, `clippingOk`, optional `loopOk`
  - If the reviewed asset is stored as `.ogg`, capture `qaSnapshot` from the analyzed WAV input (for example pre-encode analysis or a decode-to-WAV verification step), since current `qa` / `qa-batch` execution loads WAV inputs.
- `variationFamily`, `variationIndex` (for `_varNN` SFX variants)

### Variant-family decision fields (recommended)

- Top-level collection name: `variationFamilyDecisions`
- `variationFamily`
- `assetType` (`sfx`)
- `acceptanceProfile` (for example `sfx-ui`, `sfx-combat`, `sfx-magic`)
- `decision` (`approved-family` | `partial-revise` | `revise-family`)
- `approvedVariantIds` and `reviseVariantIds`
- `notes` describing readability separation and repetition-fatigue risk

These fields now have executable writing paths:

- `audio-engine write-review-log` can write/update per-asset entries and optional `variationFamilyDecisions`.
- `audio-engine approve-draft --review-log ...` can update review logs during approval handoff.
- `audio-engine export-drafts --review-log ...` can update review logs during export handoff.

Existing per-asset approval/export behavior remains unchanged unless those additive flags are provided.

## Result-JSON sourced review-log workflow (SESSION-024)

For backward-compatible legacy request-file runs, review-log entries can be generated directly from the batch result JSON:

```bash
audio-engine generate-request-batch \
  --request-file generation_requests.sfx.v1.json \
  --output-dir /tmp/out \
  --write-result \
  --write-provenance

audio-engine write-review-log \
  --factory-root /tmp/out \
  --review-log /tmp/out/review_log.json \
  --from-result /tmp/out/request_batch_result.json
```

- `--include-skipped` includes previously generated files recorded as `skipped`.
- `--project` and `--scope` remain available as explicit overrides on this path.

## Rule

If an asset is not `approved`, it should not be treated as final downstream content even if it is technically usable.
