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
3. [`ACTIVE_WORK.md`](./ACTIVE_WORK.md)
4. [`HANDOFF.md`](./HANDOFF.md)
5. [`PLAYBOOKS/AGENT_WORKFLOW.md`](./PLAYBOOKS/AGENT_WORKFLOW.md)
6. Relevant subsystem/style/schema docs for the task you are about to change

## Fast answers

| Question | Where to look |
|---|---|
| What is this repo for? | [`PROJECT_MISSION.md`](./PROJECT_MISSION.md) |
| What exists today? | [`CURRENT_STATE.md`](./CURRENT_STATE.md) |
| What should happen next? | [`ACTIVE_WORK.md`](./ACTIVE_WORK.md), [`ROADMAP.md`](./ROADMAP.md) |
| How do I build/test/run it? | [`PLAYBOOKS/BUILD_AND_RUN.md`](./PLAYBOOKS/BUILD_AND_RUN.md) |
| How do I avoid drift? | [`PLAYBOOKS/AGENT_WORKFLOW.md`](./PLAYBOOKS/AGENT_WORKFLOW.md) |
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
- one relevant subsystem page
- one relevant quality/style/schema page if behavior changed

This repository is intentionally documentation-heavy. Repetition is allowed when it reduces agent reasoning load.
