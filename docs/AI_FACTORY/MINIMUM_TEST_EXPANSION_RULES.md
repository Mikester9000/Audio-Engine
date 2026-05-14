# Minimum Test Expansion Rules

> Rules for how test expectations expand when executable behavior changes.

## Core rule

If code changes, test expectations usually expand. If they do not, explain why in `HANDOFF.md`.

## Fixture rule

Use the committed example artifacts under `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/` as canonical fixtures whenever they cover the target workflow.

- Prefer reusing committed examples over inventing ad hoc fixtures.
- If the committed examples are insufficient, add the smallest missing example explicitly.
- Keep new fixture files stable and machine-readable.

## Expansion rules by change type

### Docs-only changes

- No new production-code tests required.
- Still validate any new/edited JSON control files parse successfully.
- Still check docs for consistency with implemented behavior.

### Parsing / loader changes

- Add parsing tests for the committed example artifacts.
- Add at least one invalid-input or missing-field failure-path test.
- If parsing behavior affects error messages or normalization, test that observable behavior too.

### CLI changes

- Add or update CLI tests covering the changed command/flags.
- Preserve existing command compatibility unless the session explicitly allows a breaking change.
- Include at least one help/usage or smoke-path check when command surface changes.

### Output manifest / provenance behavior

- Add fixture-driven tests for expected machine-readable output.
- Verify required fields such as request ID, seed, output path, and review state when applicable.

### Batch generation behavior

- Add at least one deterministic smoke or integration-style test for the new path when practical.
- Prefer checking file existence, manifest content, and stable request identity over subjective audio-quality assertions.

### QA / validation behavior

- Cover at least one passing case and one failing case.
- Ensure failure output is actionable rather than silent.

### Export / integration behavior

- Verify expected output paths or mapping files are created.
- Test overwrite/naming behavior when that contract changes.

## Explanation rule when no new tests are added

If executable code changed and you did not add tests, `HANDOFF.md` must explain:

1. why the change is still safe,
2. which existing tests already cover it,
3. and why adding new tests was unnecessary or infeasible in that PR.
