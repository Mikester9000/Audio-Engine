# Task Output Contracts

> Mechanical output contract for common session types. A session should produce the listed artifacts before it is marked done.

| Task/session type | Required outputs | Minimum verification | Required doc/state updates |
|---|---|---|---|
| `docs_only` | concrete doc changes, any companion JSON metadata, no false implementation claims | manual review plus JSON parse if JSON changed | `ACTIVE_WORK.md`, `HANDOFF.md`, `CHANGE_JOURNAL.md`, session docs touched by the change |
| `loader_parsing` | parser/loader code, typed runtime structures, tests for valid + invalid inputs | `pytest` plus any focused smoke check introduced by the session | `CURRENT_STATE.md`, `IMPLEMENTATION_MATRIX.md`, `HANDOFF.md`, relevant subsystem/schema docs, session docs |
| `cli` | command wiring, argument/help text, tests, any user-facing output contract | `pytest` and one CLI smoke command when practical | `CURRENT_STATE.md`, `HANDOFF.md`, relevant subsystem doc, session docs |
| `batch_generation` | command or API path that executes requests, deterministic seed handling, output path behavior | `pytest` and one batch smoke run to a temp path when practical | `CURRENT_STATE.md`, `IMPLEMENTATION_MATRIX.md`, `HANDOFF.md`, integration/subsystem docs, session docs |
| `provenance` | machine-readable log or manifest output, schema/format contract, tests | `pytest` and one reproducible log-generation check | `CURRENT_STATE.md`, `IMPLEMENTATION_MATRIX.md`, `HANDOFF.md`, QA/schema docs, session docs |
| `qa` | automation command or script, pass/fail behavior, failure reasons, tests or reproducible checks | targeted QA command verification plus `pytest` for touched code | `CURRENT_STATE.md`, `HANDOFF.md`, `QA/*`, session docs |
| `integration_export` | stable export/mapping behavior, documented target paths, tests or smoke checks | `pytest` plus path-existence or manifest verification | `CURRENT_STATE.md`, `HANDOFF.md`, `INTEGRATION/*`, relevant subsystem doc, session docs |
| `taxonomy` | expanded asset-family coverage docs/examples/checklists | manual review and any schema/example validation available | `ACTIVE_WORK.md`, `HANDOFF.md`, `IMPLEMENTATION_MATRIX.md`, session docs |

## Notes

- If the active session does not produce the minimum outputs listed here, it is not done yet.
- If the session intentionally narrows scope, update `SESSION_QUEUE.md` so the remaining work becomes the next explicit session instead of an implicit TODO.
