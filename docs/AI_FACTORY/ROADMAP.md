# Roadmap

> Update this file whenever phase sequencing changes.

## Phase overview

| Phase | Name | Goal | Status |
|---|---|---|---|
| 0 | Documentation foundation | Make the repo resumable by AI agents | Completed |
| 1 | Planning + taxonomy | Define complete asset universe and request schemas | In progress |
| 2 | Deterministic batch generation | Generate from manifests/plans with reproducible seeds | Planned |
| 3 | QA + review loop | Add acceptance checks and review workflow | Planned |
| 4 | `GameRewritten` integration | Align names, folders, and import contracts | Planned |
| 5 | Backend expansion | Improve quality with local/open backends | Planned |
| 6 | Optional voice expansion | Upgrade voice only after music/SFX are strong | Low priority |

## Phase details

### Phase 0 — Documentation foundation
Definition of done:

- AI-first docs exist
- root README points to docs
- handoff and active-work files exist
- Copilot instructions exist

### Phase 1 — Planning + taxonomy
Definition of done:

- canonical audio categories are documented
- project-level audio plan format is documented
- generation request schema is documented
- backlog is organized by asset family and dependency

### Phase 2 — Deterministic batch generation
Definition of done:

- requests can carry seed, style family, output path, and QA expectations
- generator can process batches repeatably
- manifest/provenance output is captured

### Phase 3 — QA + review loop
Definition of done:

- acceptance criteria exist per asset type
- loop seams, clipping, and loudness checks are scriptable
- review outcomes are trackable: approved / revise / rejected

### Phase 4 — `GameRewritten` integration
Definition of done:

- consuming repo target paths are documented
- replacement/override workflow is documented
- generated files match expected naming or include mapping manifest

### Phase 5 — Backend expansion
Definition of done:

- documented backend strategy exists for local/open models
- procedural backend remains fallback
- install/availability checks are explicit

### Phase 6 — Optional voice expansion
Definition of done:

- voice requirements are explicitly scoped
- narrator/NPC utility quality is acceptable
- voice is still isolated from higher-priority music/SFX work

## Scope rule

Do not jump to large backend or voice work before planning, taxonomy, and QA are documented well enough that future agents can extend them predictably.
