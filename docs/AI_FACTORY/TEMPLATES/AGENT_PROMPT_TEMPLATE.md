# Agent Prompt Template

Use this template when opening a future AI task for this repository.

```text
Task: <short objective>

Read first:
- docs/AI_FACTORY/README.md
- docs/AI_FACTORY/CURRENT_STATE.md
- docs/AI_FACTORY/ACTIVE_WORK.md
- docs/AI_FACTORY/HANDOFF.md
- <relevant subsystem/style/schema docs>

Goal:
- <desired result>

Constraints:
- use existing commands/tests where possible
- keep generated outputs organized for downstream import
- update memory docs in the same PR
- treat inspiration targets as style families, not copying targets
- keep voice lower priority unless task is voice-specific

Verification:
- <commands to run>

Docs to update:
- <list>
```
