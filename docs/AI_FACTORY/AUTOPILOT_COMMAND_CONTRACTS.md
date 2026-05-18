# Autopilot Command Contracts

> **SESSION-039** — docs_only.
> Tightened command-contract reference for low-reasoning local LLM execution.
> Every section is an ordered, no-choice command sequence.
> Do not improvise. Do not skip steps. Do not combine steps unless explicitly stated.

---

## How to use this file

1. Identify the task type from the table below.
2. Execute the steps for that task **in the listed order**.
3. If any step fails, stop immediately and report the failure message verbatim.
4. Do not proceed to the next step after a failure.

---

## Task type index

| Task type | Section |
|-----------|---------|
| Generate music (single file) | §1 |
| Generate SFX (single file) | §2 |
| Generate voice (single file) | §3 |
| Generate request batch | §4 |
| Run QA on a batch | §5 |
| Approve a draft | §6 |
| Export drafts to game layout | §7 |
| Write a review log | §8 |
| Verify backends | §9 |
| Run full test suite | §10 |
| Validate asset manifests | §11 |

---

## §1 Generate music (single file)

```bash
audio-engine generate-music \
  --prompt "<description>" \
  --duration <seconds> \
  --output <path/to/output.wav> \
  --seed <integer> \
  --profile game
```

Flags to set:
- `--prompt` — required. Natural-language description, e.g. `"epic battle theme 140 BPM"`.
- `--duration` — required. Target duration in seconds (e.g. `60`).
- `--output` — required. Full path to the output WAV file.
- `--seed` — required for reproducibility. Use a fixed integer.
- `--profile` — one of: `game`, `ost`, `youtube`, `vocal_mix`, `procedural_neutral`. Default: `game`.

**Check:** Command exits with code 0 and the output file exists.

---

## §2 Generate SFX (single file)

```bash
audio-engine generate-sfx \
  --prompt "<description>" \
  --duration <seconds> \
  --output <path/to/output.wav> \
  --seed <integer>
```

Flags to set:
- `--prompt` — required. Category description, e.g. `"explosion impact"`.
- `--duration` — required. Target duration in seconds (e.g. `1.5`).
- `--output` — required. Full path to the output WAV file.
- `--seed` — required for reproducibility.

**Check:** Command exits with code 0 and the output file exists.

---

## §3 Generate voice (single file)

```bash
audio-engine generate-voice \
  --text "<text to speak>" \
  --voice narrator \
  --output <path/to/output.wav> \
  --seed <integer>
```

Flags to set:
- `--text` — required. Text to synthesise.
- `--voice` — one of: `narrator`, `hero`, `villain`, `announcer`, `npc`. Default: `narrator`.
- `--output` — required. Full path to the output WAV file.
- `--seed` — required for reproducibility.

**Check:** Command exits with code 0 and the output file exists.

---

## §4 Generate request batch

Step 1 — Execute the batch:

```bash
audio-engine generate-request-batch \
  --batch-file <path/to/generation_requests.json> \
  --output-dir <path/to/output_dir> \
  --quiet
```

Step 2 — Verify output directory contains WAV files:

```bash
find <path/to/output_dir>/drafts -name "*.wav" | head -20
```

**Check:** Step 1 exits with code 0. Step 2 lists at least one WAV file.

---

## §5 Run QA on a batch

```bash
audio-engine qa-batch \
  --input-dir <path/to/output_dir>/drafts \
  --output-report <path/to/qa_report.json> \
  --recursive \
  --quiet
```

**Check:** Command exits with code 0 and `qa_report.json` exists.  Open the report
and confirm `"n_failed": 0` (or review individual failures).

---

## §6 Approve a draft

```bash
audio-engine approve-draft \
  --factory-root <path/to/output_dir> \
  --draft-file <path/to/draft.wav> \
  --quiet
```

**Check:** Command exits with code 0.  The file now exists under
`<factory-root>/approved/<type>/`.

---

## §7 Export drafts to game layout

```bash
audio-engine export-drafts \
  --output-dir <path/to/output_dir> \
  --quiet
```

**Check:** Command exits with code 0.  Exported files exist under
`<output-dir>/exports/gamerewritten/Content/Audio/`.

---

## §8 Write a review log

```bash
audio-engine write-review-log \
  --factory-root <path/to/output_dir> \
  --review-log <path/to/review_log.json> \
  --reviewer "<your_name>" \
  --quiet
```

**Check:** Command exits with code 0 and `review_log.json` exists.

---

## §9 Verify backends

Step 1 — Run preflight check:

```bash
audio-engine verify-backends \
  --output-report /tmp/backend_preflight.json \
  --quiet
```

Step 2 — Print the report:

```bash
python -m json.tool /tmp/backend_preflight.json
```

**Check:** Step 1 exits with code 0 (all backends available) or code 2 (some
backends unavailable — this is expected if neural backends are not installed).
The `procedural` backend must always appear as `"available": true`.

---

## §10 Run full test suite

```bash
python -m pytest -q
```

**Check:** All tests pass with `0 failed`.

---

## §11 Validate asset manifests

```bash
python tools/validate-assets.py assets/examples/ --verbose
```

**Check:** Command exits with code 0 and no validation errors are reported.

---

## Failure handling

| Failure type | Required action |
|-------------|----------------|
| Exit code non-zero | Stop. Report the exact error message from stderr. |
| Missing output file | Stop. Report which command ran and what file was expected. |
| Test failure | Stop. Report the test name and failure message verbatim. |
| QA report `"n_failed" > 0` | Stop. Report which files failed and their failure reasons. |

**Do not** attempt to fix failures automatically unless explicitly instructed.
**Do not** skip the failure and continue to the next step.

---

## Command reference summary

| Command | Primary output | Exit code on success |
|---------|---------------|----------------------|
| `generate-music` | WAV file | 0 |
| `generate-sfx` | WAV file | 0 |
| `generate-voice` | WAV file | 0 |
| `generate-request-batch` | `drafts/` directory + manifests | 0 |
| `qa-batch` | JSON QA report | 0 |
| `approve-draft` | `approved/<type>/` copy | 0 |
| `export-drafts` | `exports/gamerewritten/` layout | 0 |
| `write-review-log` | JSON review log | 0 |
| `verify-backends` | JSON preflight report | 0 or 2 |
| `list-backends` | stdout listing | 0 |

---

## Related files

- `docs/AI_FACTORY/SESSION_GATE_RULES.md` — gate rules for session completion
- `docs/AI_FACTORY/VERIFICATION_PROFILES.md` — verification profiles by task type
- `docs/AI_FACTORY/FAILSAFE_RULES.md` — what to do when blocked
- `docs/AI_FACTORY/NO_DECISION_ZONES.md` — decisions that must not be improvised
