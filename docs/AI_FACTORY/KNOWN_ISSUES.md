# Known Issues and Practical Limitations

> Focused list of current limitations that matter for agent planning and execution.

## Current high-impact gaps

1. **Procedural-first backend ceiling**
   - The default generator stack is still primarily procedural.
   - Result: quality/style consistency can vary and may need human curation.

2. **Plan-driven factory flow is not implemented in code yet**
   - Audio-plan and generation-request formats exist as docs/contracts plus examples, not executable orchestration.
   - Result: generation is still mostly command-driven or fixed-map pipeline driven.

3. **Asset pipeline is not yet generalized for full `GameRewritten` import automation**
   - Existing `AssetPipeline` is oriented to the current fixed manifest map.
   - Result: a complete import-ready mapping workflow for all `GameRewritten` needs is still pending.

4. **Voice is lower priority and lower fidelity**
   - Voice synthesis exists but is prototype-grade relative to music and SFX.
   - Result: treat voice as optional/placeholder; prioritize music/SFX coverage first.

5. **No full QA automation gate for generated outputs in CI**
   - QA primitives exist (`qa` command, loudness/clipping/loop analyzers), but no CI gate for generated libraries.
   - Result: review burden is still partly manual.

6. **No code-level provenance/review manifest per request yet**
   - Seeds and review fields are documented and exemplified, but not enforced by generation pipeline code.
   - Result: deterministic regeneration and approval tracking can drift without discipline.

## Temporary workarounds

- Use committed examples under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` as manual source-of-truth contracts.
- Capture seeds/prompts/output paths explicitly in PR descriptions until provenance logging is implemented.
- Run `pytest` and `python tools/validate-assets.py assets/examples/ --verbose` for every substantial change.

## Exit criteria for this file

This file should shrink over time as gaps become implemented behavior, with each resolved issue moved into `IMPLEMENTATION_MATRIX.md` as `implemented` or `partial`.
