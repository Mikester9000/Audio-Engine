# AI Factory Documentation Index

> Update this file whenever the documentation tree changes or a new persistent-memory document is added.

## What this repository is for

This repository is a **GitHub-native audio asset factory**. Its primary job is to generate usable audio assets that can be imported into another repository such as `GameRewritten`. It is **not** primarily a shipped end-user product. The main optimization target is therefore:

1. AI comprehension
2. reproducible asset generation
3. clean handoff between agents
4. reliable game-asset output
5. incremental extension without architectural drift

If you are a future AI agent, start here, then read the files below in order.

## Mandatory read order for agents

1. [`PROJECT_MISSION.md`](./PROJECT_MISSION.md)
2. [`CURRENT_STATE.md`](./CURRENT_STATE.md)
3. [`SESSION_QUEUE.md`](./SESSION_QUEUE.md)
4. [`ACTIVE_WORK.md`](./ACTIVE_WORK.md)
5. [`HANDOFF.md`](./HANDOFF.md)
6. [`IMPLEMENTATION_MATRIX.md`](./IMPLEMENTATION_MATRIX.md)
7. [`NEXT_PR_SEQUENCE.md`](./NEXT_PR_SEQUENCE.md)
8. [`NO_DECISION_ZONES.md`](./NO_DECISION_ZONES.md)
9. [`FAILSAFE_RULES.md`](./FAILSAFE_RULES.md)
10. [`CODEBASE_MAP.md`](./CODEBASE_MAP.md)
11. [`PR_AUTOPILOT_CHECKLIST.md`](./PR_AUTOPILOT_CHECKLIST.md)
12. Relevant subsystem/style/schema docs for the task you are about to change

## Fast answers

| Question | Where to look |
|---|---|
| What is this repo for? | [`PROJECT_MISSION.md`](./PROJECT_MISSION.md) |
| What exists today? | [`CURRENT_STATE.md`](./CURRENT_STATE.md) |
| What should happen next? | [`SESSION_QUEUE.md`](./SESSION_QUEUE.md), [`ACTIVE_WORK.md`](./ACTIVE_WORK.md), [`ROADMAP.md`](./ROADMAP.md) |
| What is implemented vs docs-only vs planned? | [`IMPLEMENTATION_MATRIX.md`](./IMPLEMENTATION_MATRIX.md), [`FACTORY_STATUS.json`](./FACTORY_STATUS.json) |
| What session should I execute right now? | [`SESSION_QUEUE.md`](./SESSION_QUEUE.md), [`SESSION_STATE.json`](./SESSION_STATE.json) |
| What PR should I do next after the current session? | [`NEXT_PR_SEQUENCE.md`](./NEXT_PR_SEQUENCE.md) |
| Where is the code for each subsystem? | [`CODEBASE_MAP.md`](./CODEBASE_MAP.md) |
| How do I build/test/run it? | [`PLAYBOOKS/BUILD_AND_RUN.md`](./PLAYBOOKS/BUILD_AND_RUN.md) |
| What should I avoid deciding myself? | [`NO_DECISION_ZONES.md`](./NO_DECISION_ZONES.md), [`FAILSAFE_RULES.md`](./FAILSAFE_RULES.md) |
| How do I avoid drift? | [`PLAYBOOKS/AGENT_WORKFLOW.md`](./PLAYBOOKS/AGENT_WORKFLOW.md), [`PR_AUTOPILOT_CHECKLIST.md`](./PR_AUTOPILOT_CHECKLIST.md) |
| How should assets be named/organized? | [`QA/QUALITY_BARS.md`](./QA/QUALITY_BARS.md), [`INTEGRATION/GAMEREWRITTEN.md`](./INTEGRATION/GAMEREWRITTEN.md) |
| Which style targets are allowed? | [`STYLES/STYLE_FAMILIES.md`](./STYLES/STYLE_FAMILIES.md) |
| How do I hand off? | [`HANDOFF.md`](./HANDOFF.md), [`TEMPLATES/PR_TEMPLATE.md`](./TEMPLATES/PR_TEMPLATE.md) |

## Document map

### Mission, state, roadmap, continuity
- [`PROJECT_MISSION.md`](./PROJECT_MISSION.md)
- [`CURRENT_STATE.md`](./CURRENT_STATE.md)
- [`TARGET_STATE.md`](./TARGET_STATE.md)
- [`ROADMAP.md`](./ROADMAP.md)
- [`ACTIVE_WORK.md`](./ACTIVE_WORK.md)
- [`HANDOFF.md`](./HANDOFF.md)
- [`CHANGE_JOURNAL.md`](./CHANGE_JOURNAL.md)
- [`GLOSSARY.md`](./GLOSSARY.md)
- [`IMPLEMENTATION_MATRIX.md`](./IMPLEMENTATION_MATRIX.md)
- [`NEXT_PR_SEQUENCE.md`](./NEXT_PR_SEQUENCE.md)
- [`SESSION_QUEUE.md`](./SESSION_QUEUE.md)
- [`SESSION_TEMPLATE.md`](./SESSION_TEMPLATE.md)
- [`SESSION_HISTORY.md`](./SESSION_HISTORY.md)
- [`DONE_CRITERIA.md`](./DONE_CRITERIA.md)
- [`NO_DECISION_ZONES.md`](./NO_DECISION_ZONES.md)
- [`TASK_OUTPUT_CONTRACTS.md`](./TASK_OUTPUT_CONTRACTS.md)
- [`FILE_TOUCH_MATRIX.md`](./FILE_TOUCH_MATRIX.md)
- [`FAILSAFE_RULES.md`](./FAILSAFE_RULES.md)
- [`PR_AUTOPILOT_CHECKLIST.md`](./PR_AUTOPILOT_CHECKLIST.md)
- [`CODEBASE_MAP.md`](./CODEBASE_MAP.md)
- [`KNOWN_ISSUES.md`](./KNOWN_ISSUES.md)
- [`STABILITY_RULES.md`](./STABILITY_RULES.md)
- [`FACTORY_STATUS.json`](./FACTORY_STATUS.json)
- [`SESSION_STATE.json`](./SESSION_STATE.json)

### Decisions and guardrails
- [`DECISIONS/README.md`](./DECISIONS/README.md)
- [`DECISIONS/ADR-001-AI-FIRST-FACTORY.md`](./DECISIONS/ADR-001-AI-FIRST-FACTORY.md)
- [`DECISIONS/ADR-002-STYLE-FAMILIES-NOT-COPIES.md`](./DECISIONS/ADR-002-STYLE-FAMILIES-NOT-COPIES.md)

### Execution playbooks
- [`PLAYBOOKS/BUILD_AND_RUN.md`](./PLAYBOOKS/BUILD_AND_RUN.md)
- [`PLAYBOOKS/AGENT_WORKFLOW.md`](./PLAYBOOKS/AGENT_WORKFLOW.md)
- [`PLAYBOOKS/TROUBLESHOOTING.md`](./PLAYBOOKS/TROUBLESHOOTING.md)

### Schemas and request formats
- [`SCHEMAS/AUDIO_PLAN_SCHEMA.md`](./SCHEMAS/AUDIO_PLAN_SCHEMA.md)
- [`SCHEMAS/GENERATION_REQUEST_SCHEMA.md`](./SCHEMAS/GENERATION_REQUEST_SCHEMA.md)
- [`EXAMPLES/gamerewritten_vertical_slice/README.md`](./EXAMPLES/gamerewritten_vertical_slice/README.md)
- Existing asset-manifest reference: [`../asset-manifest.md`](../asset-manifest.md)

### Audio design and quality
- [`STYLES/STYLE_FAMILIES.md`](./STYLES/STYLE_FAMILIES.md)
- [`STYLES/EMOTION_MATRIX.md`](./STYLES/EMOTION_MATRIX.md)
- [`QA/QUALITY_BARS.md`](./QA/QUALITY_BARS.md)
- [`QA/REVIEW_WORKFLOW.md`](./QA/REVIEW_WORKFLOW.md)

### Subsystem status pages
- [`SUBSYSTEMS/README.md`](./SUBSYSTEMS/README.md)
- [`SUBSYSTEMS/MUSIC.md`](./SUBSYSTEMS/MUSIC.md)
- [`SUBSYSTEMS/SFX.md`](./SUBSYSTEMS/SFX.md)
- [`SUBSYSTEMS/VOICE.md`](./SUBSYSTEMS/VOICE.md)
- [`SUBSYSTEMS/ASSET_PIPELINE.md`](./SUBSYSTEMS/ASSET_PIPELINE.md)

### Session control and autopilot
- [`SESSION_QUEUE.md`](./SESSION_QUEUE.md)
- [`SESSION_TEMPLATE.md`](./SESSION_TEMPLATE.md)
- [`DONE_CRITERIA.md`](./DONE_CRITERIA.md)
- [`NO_DECISION_ZONES.md`](./NO_DECISION_ZONES.md)
- [`TASK_OUTPUT_CONTRACTS.md`](./TASK_OUTPUT_CONTRACTS.md)
- [`FILE_TOUCH_MATRIX.md`](./FILE_TOUCH_MATRIX.md)
- [`FAILSAFE_RULES.md`](./FAILSAFE_RULES.md)
- [`PR_AUTOPILOT_CHECKLIST.md`](./PR_AUTOPILOT_CHECKLIST.md)
- [`SESSION_HISTORY.md`](./SESSION_HISTORY.md)
- [`SESSION_STATE.json`](./SESSION_STATE.json)

### Tracking and templates
- [`TASKS/BACKLOG.md`](./TASKS/BACKLOG.md)
- [`TASKS/BUG_TRACKING.md`](./TASKS/BUG_TRACKING.md)
- [`TASKS/PHASE_PLAN.md`](./TASKS/PHASE_PLAN.md)
- [`TEMPLATES/AGENT_PROMPT_TEMPLATE.md`](./TEMPLATES/AGENT_PROMPT_TEMPLATE.md)
- [`TEMPLATES/PR_TEMPLATE.md`](./TEMPLATES/PR_TEMPLATE.md)

### Platform and integration docs
- [`WINDOWS/SETUP.md`](./WINDOWS/SETUP.md)
- [`INTEGRATION/GAMEREWRITTEN.md`](./INTEGRATION/GAMEREWRITTEN.md)

## Required maintenance rule

When code or process changes, update all affected docs in the same PR. At minimum, review:

- `CURRENT_STATE.md`
- `ACTIVE_WORK.md`
- `HANDOFF.md`
- `SESSION_QUEUE.md` when session order or session state changes
- `SESSION_HISTORY.md` and `SESSION_STATE.json` when a session is completed or blocked
- one relevant subsystem page
- one relevant quality/style/schema page if behavior changed

This repository is intentionally documentation-heavy. Repetition is allowed when it reduces agent reasoning load.
