# Handoff

> Update this file at the end of every PR. Treat it as the "what changed last" file.

## Last completed change

This PR completes `SESSION-004` by adding a `qa-batch` CLI command that runs quality-assurance checks on all WAV files in a directory and writes a machine-readable JSON report. 7 new tests were added; total test count is 345.

## Verified in this session

```bash
pip install -e ".[dev]"
python -m pytest
# 345 passed (was 338 before SESSION-004)
python tools/validate-assets.py assets/examples/ --verbose
# PASS — all manifests are valid
audio-engine qa-batch \
  --input-dir /tmp/session003_smoke/drafts/sfx \
  --output-report /tmp/session004_qa_report.json
# 5 files checked: 4 pass, 1 fail (sfx_ui_cancel.wav at -6.37 LUFS exceeds -9.0 ceiling)
```

## QA report format

```json
{
  "qaBatchVersion": "1.0.0",
  "inputDir": "/tmp/session003_smoke/drafts/sfx",
  "generatedAt": "2026-05-14T22:59:11.584885+00:00",
  "summary": {"total": 5, "passed": 4, "failed": 1},
  "results": [
    {
      "file": "...",
      "status": "pass",
      "checks": {
        "loudness_lufs": -12.57,
        "true_peak_dbfs": -3.0,
        "loudness_range_lu": 0.0,
        "has_clipping": false,
        "clipped_samples": 0,
        "loudness_ok": true,
        "peak_ok": true,
        "clipping_ok": true
      }
    }
  ]
}
```

## QA batch command options

```
audio-engine qa-batch --input-dir <dir> [--output-report <path>] [--check-loop] [--recursive] [--quiet]
```

- `--check-loop`: also run `LoopAnalyzer` per file (adds `loop_is_seamless`, `loop_amplitude_jump_db`, `loop_ok` to checks)
- `--recursive`: recurse into subdirectories when searching for WAV files
- `--quiet`: suppress per-file output lines (summary is still printed)
- Returns non-zero exit code if any file fails

## Loudness bars used

- `loudness_ok`: `-30.0 ≤ integrated_lufs ≤ -9.0`
- `peak_ok`: `true_peak_dbfs ≤ -0.1`
- `clipping_ok`: no clipped samples detected

## Immediate next best task

Execute `SESSION-005` from `docs/AI_FACTORY/SESSION_QUEUE.md`: implement the GameRewritten export profile — copy approved draft assets into the `exports/gamerewritten/Content/Audio/` layout.

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/SESSION_QUEUE.md`
4. `docs/AI_FACTORY/CURRENT_SESSION.json`
5. `docs/AI_FACTORY/HANDOFF.md`
6. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
7. `docs/AI_FACTORY/FAILSAFE_RULES.md`
8. relevant subsystem/style/schema docs

## Handoff checklist

- [x] Mission and non-goals documented
- [x] Current state documented
- [x] Roadmap documented
- [x] Agent workflow documented
- [x] Troubleshooting documented
- [x] Style-family safety guidance documented
- [x] Integration direction for `GameRewritten` documented
- [x] Project-level audio plan example implemented in repo
- [x] Generation request examples with seeds/output/review fields implemented in repo
- [x] Implementation matrix + codebase map + next PR sequence implemented in repo
- [x] Session queue + template added
- [x] Done criteria, no-decision zones, task-output contracts, file-touch matrix, and failsafe rules added
- [x] PR autopilot checklist + session history + machine-readable session state added
- [x] Final execution-safety hardening layer added
- [x] Audio plan and music/SFX generation-request fixtures load through typed integration code and tests
- [x] Request-batch generation command implemented (`generate-request-batch` CLI + `RequestBatchPipeline`)
- [x] Per-request provenance sidecar files written alongside every generated audio file
- [x] Batch QA gate command implemented (`qa-batch` CLI with JSON report)
- [ ] Approval/replacement workflow (drafts → approved promotion)
- [ ] GameRewritten export profile (copy approved to `exports/gamerewritten/Content/Audio/`)
