# Dependency and Model License Inventory

> **SESSION-033** — docs_only.
> Machine-readable baseline inventory of runtime dependencies and optional AI model
> weights, each mapped to a license and a commercial-eligibility policy category.
>
> Keep this file synchronized with `COMMERCIAL_ELIGIBILITY_MATRIX.md` and the
> outputs of `audio-engine verify-backends`.
>
> **Policy categories used in this file:**
> - `allow` — license is permissive and commercial use is confirmed allowed
> - `conditional` — commercial use is allowed under specific conditions (attribution, etc.)
> - `block` — commercial use is not permitted; do not ship in commercial products
> - `unknown` — license terms not yet verified; treat as `block` until confirmed

---

## Core runtime dependencies

| Package | Version range | SPDX License | Policy | Notes |
|---------|--------------|--------------|--------|-------|
| `numpy` | ≥1.24 | BSD-3-Clause | `allow` | Core numeric engine |
| `scipy` | ≥1.10 | BSD-3-Clause | `allow` | DSP / resampling |
| `soundfile` | ≥0.12 | BSD-3-Clause | `allow` | OGG export (optional) |
| `sounddevice` | ≥0.4 | MIT | `allow` | Playback (optional / UI) |
| `tkinter` | stdlib | PSF-2.0 | `allow` | Studio UI (bundled with CPython) |

---

## Optional neural backend dependencies

These packages are **not** required for the default procedural pipeline.
They are only needed if a specific neural backend is selected at runtime.

| Package | Version range | SPDX License | Policy | Notes |
|---------|--------------|--------------|--------|-------|
| `transformers` | ≥4.38 | Apache-2.0 | `allow` | MusicGen / AudioGen backend |
| `torch` | ≥2.0 | BSD-3-Clause | `allow` | Required by transformers-based backends |
| `torchaudio` | ≥2.0 | BSD-3-Clause | `allow` | Audio utilities for torch backends |
| `onnxruntime` | ≥1.16 | MIT | `allow` | ONNX inference (future backend) |
| `kokoro` | ≥0.9 | Apache-2.0 | `allow` | Kokoro TTS backend |

---

## Optional AI model weights

Model weights are **not** bundled in this repository.
Users must download them separately via `tools/download_models.py` or manually.

| Model | Publisher | Model License | Policy | Notes |
|-------|-----------|--------------|--------|-------|
| `facebook/musicgen-medium` | Meta AI | CC BY-NC 4.0 | `block` | **Non-commercial only.** Do not use in commercial products. |
| `facebook/audiogen-medium` | Meta AI | CC BY-NC 4.0 | `block` | **Non-commercial only.** |
| `kokoro-82M` | Kokoro team | Apache-2.0 | `allow` | Commercial use permitted |

> **Warning:** `musicgen-medium` and `audiogen-medium` are licensed CC BY-NC 4.0,
> which explicitly prohibits commercial use.  All factory outputs generated using
> these models inherit this restriction.
> The default `procedural` backend uses zero licensed model weights; outputs from
> the procedural backend are not subject to model license restrictions.

---

## Development-only dependencies

These packages are used for testing and development only and are not shipped in
production builds.

| Package | Version range | SPDX License | Policy | Notes |
|---------|--------------|--------------|--------|-------|
| `pytest` | ≥7.0 | MIT | `allow` | Test runner |
| `pytest-cov` | any | MIT | `allow` | Coverage reporting |

---

## Inventory maintenance rules

1. Add a new row whenever a new dependency is introduced in `pyproject.toml` or
   in any `audio_engine/ai/backends/` module.
2. Set `Policy` to `unknown` for any new entry until the license has been
   reviewed.
3. Run `python tools/validate-assets.py` and `audio-engine verify-backends`
   after updating this file to confirm the inventory reflects current behavior.
4. Cross-check `COMMERCIAL_ELIGIBILITY_MATRIX.md` whenever a row changes.
