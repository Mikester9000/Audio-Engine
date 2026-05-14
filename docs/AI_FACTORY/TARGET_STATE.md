# Target State

> Update this file whenever the long-term product direction changes.

## Desired future identity

This repository should evolve into the canonical place where `GameRewritten`-style projects define, generate, review, organize, and regenerate all needed audio assets.

## Long-term coverage target

The target factory should eventually generate or coordinate generation for:

- field themes
- town themes
- dungeon themes
- battle themes
- boss themes
- menu/shop/save/victory fanfares
- UI sounds
- combat SFX
- spell/magic SFX
- traversal/footstep/environmental SFX
- ambient loops
- cinematic stingers
- optional voice generation

Voice is valuable, but **lower priority** than music and SFX.

## Target operational characteristics

The mature system should provide:

1. project-level audio plans
2. batch generation requests
3. deterministic seed handling
4. clear acceptance criteria per asset type
5. review logs and replace/override workflow
6. downstream import guidance for `GameRewritten`
7. explicit tracking of what is generated, approved, rejected, or pending
8. backend abstraction for procedural and model-based generation

## Desired output model

```text
factory-output/
├── manifests/
│   ├── project-audio-plan.json
│   ├── generation-requests/
│   └── review-reports/
├── music/
├── sfx/
├── ambience/
├── ui/
├── voice/
├── variants/
└── export/
```

## Architectural target

### Current reality
- procedural backend first
- direct CLI and Python usage
- one batch pipeline aimed at a known consumer

### Target architecture
- input plans and requests
- generator orchestration layer
- seed + provenance tracking
- asset review layer
- QA layer
- export/publish layer
- consuming-repo integration layer

## Definition of success

A future AI agent should be able to enter the repository and, with minimal prompting:

- identify missing game audio coverage
- generate or regenerate a bounded set of assets
- verify outputs against documented quality bars
- update project memory docs
- prepare a clean handoff for the next agent
