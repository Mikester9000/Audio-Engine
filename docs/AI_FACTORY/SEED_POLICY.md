# Seed Policy — Baseline Reproducibility

> Canonical seed-capture and regeneration rules for all generation, QA, export, and remaster surfaces.
> Locked in SESSION-043. Update this file only when seed behavior changes in code.

## Policy statement

Every generated audio asset must carry a deterministic seed that allows exact reproduction of that generation run when all other inputs remain the same (prompt, backend, duration, profile, sample rate).

## Rules

### 1. Seed capture is mandatory for all generation commands

All generation commands (`generate-music`, `generate-sfx`, `generate-voice`, `generate-request-batch`, `generate-plan-batch`) must record the seed used in the generation in the provenance sidecar. The `seed` field in `.provenance.json` is the canonical record.

### 2. Seed defaults

When no `--seed` flag is provided, a seed is derived from the current UTC timestamp (millisecond resolution). The derived seed must still be written to provenance so the run can be regenerated later.

### 3. Seed precedence

| Source | Precedence | Notes |
|---|---|---|
| Explicit `--seed` flag | Highest | Always used when provided |
| Request-level `seed` field in batch JSON | Middle | Overrides timestamp default for that request |
| Timestamp-derived seed | Lowest | Used when no explicit seed is present |

### 4. Seed format

Seeds are stored as plain integers in provenance JSON. Zero-padded display strings (e.g., `seed0042`) are for delivery filenames only and must not be stored in provenance as strings.

### 5. Reproducibility guarantee scope

The procedural backend guarantees bit-identical audio for the same seed, prompt, duration, sample rate, and profile on the same software version. Neural backends (MusicGen Medium) provide best-effort reproducibility subject to model version and hardware precision.

### 6. Delivery naming uses seed

The deterministic commercial delivery filename format (`export-wav-delivery`) embeds the seed as `seed<NNNN>` (zero-padded 4 digits, or longer if the seed exceeds 9999). This makes the delivery package self-documenting without requiring manifest lookup.

### 7. Regression testing

`tests/test_regression.py` enforces seed-stability contracts for the procedural backend. Any change that breaks seed determinism is a regression and must be fixed before merging.

## Enforcement status

| Surface | Seed captured | Seed written to provenance | Notes |
|---|---|---|---|
| `generate-music` | ✅ | ✅ | `--seed` flag |
| `generate-sfx` | ✅ | ✅ | `--seed` flag |
| `generate-voice` | ✅ | ✅ | `--seed` flag |
| `generate-request-batch` (batch-file path) | ✅ | ✅ | per-request seed in JSON |
| `generate-request-batch` (request-file path) | ✅ | Optional (--write-provenance) | legacy path |
| `generate-plan-batch` | ✅ | ✅ | inherited from request-batch |
| `export-wav-delivery` | N/A | N/A | reads from provenance; does not generate |
| `remaster` | N/A | N/A | sample-substitution; no generation seed |

## Change log

- SESSION-043: Policy written and locked as part of baseline reproducibility freeze.
