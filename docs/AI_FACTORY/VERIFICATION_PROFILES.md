# Verification Profiles

> Map each session/task type to the minimum acceptable verification for this repository. Use these profiles before marking a session done.

## Global rules

1. Run the smallest profile that truthfully matches the task.
2. If a task touches executable behavior, add targeted tests before relying on manual confidence.
3. Reuse the committed example artifacts under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` as canonical fixtures whenever they fit the task.
4. Record the commands run and the observed result in `HANDOFF.md`.

## Profile table

| Task type | Minimum verification | Stronger verification when feasible | Evidence to record in handoff |
|---|---|---|---|
| `docs_only` | Manual doc consistency review; parse any new/edited JSON with `python -m json.tool <file>` | Re-run repo baseline commands if repo entrypoint instructions or verification policy changed materially | Which docs changed, which JSON files were parsed, and whether baseline repo commands were already known-good in the session |
| `loader_parsing` | `pytest`; at least one success path and one invalid-input path through tests | Focused loader smoke check against committed example artifacts if a CLI/API hook was added | Test file names or command summary, example artifacts used, invalid-input path covered |
| `cli` | `pytest`; targeted CLI tests; one `audio-engine ... --help` or command smoke check if command surface changed | Smoke run writing to `/tmp` using committed examples or small generated assets | Changed command/flags, help or smoke output summary, preserved compatibility notes |
| `batch_generation` | `pytest`; one deterministic smoke run to `/tmp` using committed request fixtures | Verify expected output files and stable seeds/paths in emitted metadata | Output directory checked, request IDs used, seed/path determinism evidence |
| `provenance` | `pytest`; one reproducible provenance/log generation check | Validate log contents against example schema/fixture shape | Log path, required fields present, request-to-output linkage confirmed |
| `qa` | `pytest`; one passing input and one failing input or reproducible failure mode | Batch QA run over a small generated set in `/tmp` | Pass/fail evidence, actionable failure reason example |
| `integration_export` | `pytest`; one export smoke check to `/tmp`; verify expected files or mapping records exist | Downstream-path verification against documented export layout | Output paths verified, overwrite/naming behavior noted |
| `taxonomy` | Manual checklist review against `FULL_GAME_AUDIO_CHECKLIST.md` and affected examples/docs | Add or update fixture/example artifacts that close a coverage gap | Which coverage areas were added or confirmed |

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
