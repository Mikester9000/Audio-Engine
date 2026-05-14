# Done Criteria

> Central definition of what `done` means for common work types in this repository. Use this file to reduce over-building and under-building. For the final mark-complete gate, also use `SESSION_GATE_RULES.md`.

## Global done rules for every substantial session

A session is not done until all of the following are true:

1. The requested change exists in the repo diff, not only in planning text.
2. The smallest relevant verification commands were run and recorded.
3. `CURRENT_STATE.md`, `HANDOFF.md`, and any directly affected AI_FACTORY tracking docs were reviewed and updated.
4. New behavior is described as implemented only if it is real and verified.
5. The next session is either queued explicitly or the blocker is documented explicitly.

## Docs-only change

**Done when:**

- the new docs are present, concrete, and internally consistent
- no doc claims code behavior that does not exist
- the relevant continuity docs are updated (`ACTIVE_WORK.md`, `HANDOFF.md`, `CHANGE_JOURNAL.md`, and session docs if sequencing changed)
- any new JSON metadata files parse successfully

## Loader / parsing task

**Done when:**

- parser/loader code exists in the repository
- the committed example artifacts load successfully through tested code paths
- at least one invalid-input or missing-field failure path is tested
- existing CLI/API compatibility is preserved unless the session explicitly permits additive CLI changes
- implementation docs are updated from `docs-contract` to `partial` or `implemented` where appropriate

## CLI task

**Done when:**

- the command is wired into the existing CLI entrypoint
- `--help`/usage behavior is consistent with the rest of the CLI
- tests cover the new command or changed flags
- the command has a documented output path/contract and verification command

## Batch generation task

**Done when:**

- one command or API path can execute the targeted batch deterministically
- request IDs, seeds, and output paths remain explicit
- at least one smoke test or automated test covers the path
- existing one-off generation commands still work unless the session explicitly replaces them

## QA task

**Done when:**

- pass/fail behavior is explicit and machine-readable or scriptable
- the command reports actionable failure reasons
- at least one good input and one failing input path are covered by tests or reproducible verification
- docs explain when a failed QA result should block asset promotion

## Integration / export task

**Done when:**

- outputs land in stable documented target paths or mapping metadata is generated
- overwrite behavior and naming behavior are explicit
- a verification step confirms expected files or mapping records exist
- integration docs are updated with the exact target contract

## Provenance / review logging task

**Done when:**

- machine-readable logs are produced for each targeted asset or request
- logs contain the minimum identity fields documented by the session contract
- tests or a reproducible smoke check confirm the log format
- docs explain where the log lives and how future agents should use it
