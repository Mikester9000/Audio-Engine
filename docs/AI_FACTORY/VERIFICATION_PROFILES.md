# Verification Profiles

> Map each session/task type to the minimum acceptable verification for this repository. Use these profiles before marking a session done.

## Global rules

1. Run the smallest profile that truthfully matches the task.
2. If a task touches executable behavior, add targeted tests before relying on manual confidence.
3. Reuse the committed example artifacts under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` as canonical fixtures whenever they fit the task.
4. Record the commands run and the observed result in `HANDOFF.md`.

## Profile summary

| Task type | Minimum bar |
|---|---|
| `docs_only` | Manual consistency review plus JSON parsing for new/edited machine-readable files |
| `loader_parsing` | `pytest` with success-path and invalid-input coverage |
| `cli` | `pytest` plus targeted CLI help/smoke verification when command surface changes |
| `batch_generation` | `pytest` plus one deterministic `/tmp` smoke run using committed request fixtures |
| `provenance` | `pytest` plus one reproducible log-generation check |
| `qa` | `pytest` plus one passing and one failing/reproducible-failure verification path |
| `integration_export` | `pytest` plus one export smoke check to `/tmp` and output-path verification |
| `taxonomy` | Manual checklist review against `FULL_GAME_AUDIO_CHECKLIST.md` and affected examples/docs |

## Profile details

### `docs_only`

- **Minimum verification:** Manual doc consistency review; parse any new/edited JSON with `python -m json.tool <file>`.
- **Stronger verification when feasible:** Re-run repo baseline commands if repo entrypoint instructions or verification policy changed materially.
- **Evidence to record in handoff:** Which docs changed, which JSON files were parsed, and whether baseline repo commands were already known-good in the session.

### `loader_parsing`

- **Minimum verification:** `pytest`; at least one success path and one invalid-input path through tests.
- **Stronger verification when feasible:** Focused loader smoke check against committed example artifacts if a CLI/API hook was added.
- **Evidence to record in handoff:** Test file names or command summary, example artifacts used, and the invalid-input path covered.

### `cli`

- **Minimum verification:** `pytest`; targeted CLI tests; one `audio-engine ... --help` or command smoke check if the command surface changed.
- **Stronger verification when feasible:** Smoke run writing to `/tmp` using committed examples or small generated assets.
- **Evidence to record in handoff:** Changed command/flags, help or smoke output summary, and preserved compatibility notes.

### `batch_generation`

- **Minimum verification:** `pytest`; one deterministic smoke run to `/tmp` using committed request fixtures.
- **Stronger verification when feasible:** Verify expected output files and stable seeds/paths in emitted metadata.
- **Evidence to record in handoff:** Output directory checked, request IDs used, and seed/path determinism evidence.

### `provenance`

- **Minimum verification:** `pytest`; one reproducible provenance/log generation check.
- **Stronger verification when feasible:** Validate log contents against example schema/fixture shape.
- **Evidence to record in handoff:** Log path, required fields present, and request-to-output linkage confirmation.

### `qa`

- **Minimum verification:** `pytest`; one passing input and one failing input or reproducible failure mode.
- **Stronger verification when feasible:** Batch QA run over a small generated set in `/tmp`.
- **Evidence to record in handoff:** Pass/fail evidence and at least one actionable failure-reason example.

### `integration_export`

- **Minimum verification:** `pytest`; one export smoke check to `/tmp`; verify expected files or mapping records exist.
- **Stronger verification when feasible:** Downstream-path verification against documented export layout.
- **Evidence to record in handoff:** Output paths verified and overwrite/naming behavior notes.

### `taxonomy`

- **Minimum verification:** Manual checklist review against `FULL_GAME_AUDIO_CHECKLIST.md` and affected examples/docs.
- **Stronger verification when feasible:** Add or update fixture/example artifacts that close a coverage gap.
- **Evidence to record in handoff:** Which coverage areas were added or confirmed.

## Docs-only profile details

For docs/control-layer PRs like this one, the minimum bar is:

1. cross-check new docs against existing `AI_FACTORY` files
2. parse every new or edited JSON file
3. ensure no doc claims code behavior that does not exist
4. keep continuity docs synchronized

## Evidence expectations

Do not write “verified” without evidence. Record one of:

- exact commands and summarized results
- named tests and summarized result
- manual checks with the specific file(s) or output paths inspected
