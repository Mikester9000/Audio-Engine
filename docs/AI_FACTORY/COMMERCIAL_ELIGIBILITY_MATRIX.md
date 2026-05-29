# Commercial Eligibility Matrix

> **SESSION-034** — docs_only.
> Explicit allow / conditional / block commercial-use matrix for each backend +
> model combination used by generation commands.
>
> Do **not** claim commercial eligibility where license terms are unknown or
> where the model license explicitly restricts commercial use.
>
> Cross-reference: `LICENSE_INVENTORY.md` for per-dependency license details.

---

## Matrix legend

| Symbol | Meaning |
|--------|---------|
| ✅ Allow | Commercial use confirmed permitted by the applicable license(s) |
| ⚠️ Conditional | Commercial use is allowed under specific conditions stated in the Notes column |
| ❌ Block | Commercial use is NOT permitted; do not ship outputs in commercial products |
| ❓ Unknown | License terms not yet fully reviewed; treat as ❌ Block until confirmed |

---

## Backend × model commercial eligibility

| Backend | Model weights used | Backend library license | Model license | Commercial eligibility | Notes |
|---------|-------------------|------------------------|--------------|------------------------|-------|
| `procedural` | None | N/A (bundled code) | N/A | ✅ **Allow** | Pure algorithmic synthesis; no model weights. Outputs are fully commercially usable. |
| `ps1` | None | N/A (bundled code) | N/A | ✅ **Allow** | PS1-style DSP on top of procedural. No model weights. |
| `synth_orchestral` | None | N/A (bundled code) | N/A | ✅ **Allow** | Orchestral synthesis on top of procedural. No model weights. |
| `sample` (no model) | User-provided WAV files | N/A | Depends on WAV files | ⚠️ **Conditional** | Commercial eligibility depends entirely on the license of user-provided WAV samples. Verify each sample's license before commercial use. |
| `musicgen-small` (MusicGen Small) | `facebook/musicgen-small` | Apache-2.0 | CC BY-NC 4.0 | ❌ **Block** | CC BY-NC 4.0 prohibits commercial use. Outputs generated with this backend **may not** be used commercially. |
| `musicgen` (MusicGen Medium) | `facebook/musicgen-medium` | Apache-2.0 | CC BY-NC 4.0 | ❌ **Block** | CC BY-NC 4.0 prohibits commercial use. Outputs generated with this backend **may not** be used commercially. |
| `audiogen` (AudioGen Medium) | `facebook/audiogen-medium` | Apache-2.0 | CC BY-NC 4.0 | ❌ **Block** | Same restriction as MusicGen. |
| `kokoro` (Kokoro TTS) | `kokoro-82M` | Apache-2.0 | Apache-2.0 | ✅ **Allow** | Both backend library and model weights are Apache-2.0. Commercial use is permitted. |

---

## Audio output eligibility by workflow

| Workflow command | Default backend | Commercial eligibility | Required condition |
|-----------------|----------------|----------------------|-------------------|
| `generate-music` (default) | `procedural` | ✅ Allow | Use default backend or explicitly select a commercially-clear backend |
| `generate-sfx` (default) | `procedural` | ✅ Allow | Same |
| `generate-voice` (default) | `procedural` | ✅ Allow | Same |
| `remaster` with user WAVs | `sample` | ⚠️ Conditional | User WAV samples must have commercially-permissive licenses |
| Any command with `--backend musicgen-small` | `musicgen-small` | ❌ Block | Do not use for commercial products |
| Any command with `--backend musicgen` | `musicgen` | ❌ Block | Do not use for commercial products |
| Any command with `--backend audiogen` | `audiogen` | ❌ Block | Do not use for commercial products |
| `generate-voice` with `--backend kokoro` | `kokoro` | ✅ Allow | Verify kokoro model version is Apache-2.0 |

---

## Safe default workflow for commercial use

To ensure all outputs are commercially eligible:

1. **Do not** pass `--backend musicgen-small`, `--backend musicgen`, or `--backend audiogen` to any command.
2. **Do not** use the `musicgen-small`, `musicgen`, or `audiogen` backends in generation-request batch files.
3. **Do** use the default `procedural` backend, or explicitly set `--backend procedural`.
4. **Do** verify the license of any user-provided WAV sample files before commercial distribution.
5. Run `audio-engine verify-backends` to confirm which backends are active.

---

## Unresolved items

None at this time. All currently registered backends have been reviewed.

Any new backend added to `BackendRegistry` must be added to this matrix before it
can be cleared for commercial use in factory outputs.

---

## Related files

- `docs/AI_FACTORY/LICENSE_INVENTORY.md` — per-dependency license details
- `audio_engine/ai/backend.py` — BackendRegistry
- `docs/AI_FACTORY/SESSION_GATE_RULES.md` — gate rules for session completion
