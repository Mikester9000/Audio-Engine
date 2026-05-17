# Known Issues and Practical Limitations

> Focused list of current limitations that matter for agent planning and execution.

## Current high-impact gaps

1. **Procedural-first backend ceiling**
   - Procedural generation remains the most reliable default path.
   - Result: quality/style consistency can still vary and may require manual curation.

2. **Optional neural backends require local dependencies + model files**
   - Neural adapters are available but dependency/model-gated by local setup.
   - Result: runs can fall back to procedural behavior or report unavailable adapters when models are missing.

3. **No dedicated backend preflight/readiness command yet**
   - Backend discovery exists (`list-backends`), but there is no single deterministic preflight command that emits a machine-readable readiness report.
   - Result: neural-readiness handoff still requires manual command assembly.

4. **Voice is lower priority and lower fidelity**
   - Voice synthesis exists but is prototype-grade relative to music and SFX.
   - Result: treat voice as optional/placeholder; prioritize music/SFX coverage first.

5. **Plan-driven orchestration requires explicit request coverage**
   - `generate-plan-batch` requires matching request records for required plan targets and fails fast when coverage is missing.
   - Result: plan execution depends on maintaining complete request fixtures.

6. **Neural quality/performance benchmarking is not yet standardized**
   - The repository has adapters and optional model bootstrap but no stabilized benchmark rubric tied to automated pass/fail gates.
   - Result: neural quality/performance evaluation remains mostly manual.

## Temporary workarounds

- Use committed examples under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` as the default fixtures.
- Use deterministic seeds and provenance sidecars/review logs for reproducibility and handoff continuity.
- Run `pytest` and `python tools/validate-assets.py assets/examples/ --verbose` for substantial executable changes.

## Exit criteria for this file

This file should shrink over time as gaps become implemented behavior, with each resolved issue moved into `IMPLEMENTATION_MATRIX.md` as `implemented` or `partial`.
