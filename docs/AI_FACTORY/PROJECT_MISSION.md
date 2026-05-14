# Project Mission

> Update this file whenever the core purpose, priorities, or success criteria change.

## Mission statement

Build and maintain a **private GitHub-native audio asset factory** that generates usable game audio for downstream repositories, especially `GameRewritten`, through AI-agent-friendly workflows.

## Primary objective

Produce organized, reviewable, reproducible audio assets for game development.

## Non-goals

The repository is **not** optimized first for:

- shipping as a polished end-user application
- minimizing file count or documentation length
- elegant internals for their own sake
- direct imitation of copyrighted music or sound design
- prioritizing voice generation over music and SFX
- prioritizing Windows/Visual Studio support over Python/Linux workflows

## Definition: GitHub-native audio asset factory

A GitHub-native audio asset factory is a repository where:

1. source of truth lives in GitHub
2. progress is tracked in markdown, issues, PRs, and manifests
3. AI agents can resume work by reading repo documents instead of requiring long prompts
4. asset generation is reproducible from committed inputs, commands, and seeds
5. outputs are organized for import into a consuming game repository
6. review and QA rules are explicit enough to be followed mechanically

## AI-first repository principles

1. **Usable assets beat elegant internals.**
2. **Explicit docs beat implied knowledge.**
3. **Stable names beat clever names.**
4. **Machine-readable structure beats prose-only guidance.**
5. **Current-state truth beats aspirational marketing.**
6. **Incremental PRs beat giant rewrites.**
7. **Deterministic regeneration beats mystery output.**
8. **Music and SFX are higher priority than voice.**
9. **Safe inspiration beats direct copying.**
10. **Downstream integration beats local perfection.**

## Inspiration policy

The long-term style direction may be inspired by these franchises:

- Final Fantasy VII
- Final Fantasy VIII
- Final Fantasy X
- Final Fantasy XV
- Final Fantasy VII Remake
- Star Wars

These are **style families and mood references only**. Do not try to reproduce copyrighted melodies, sound recordings, signature motifs, or exact sound design. Aim for abstractions such as:

- melancholic sci-fi fantasy
- heroic orchestral action
- atmospheric town/field/dungeon moods
- cinematic battle escalation
- mythic space-opera scale

See [`STYLES/STYLE_FAMILIES.md`](./STYLES/STYLE_FAMILIES.md).

## Success criteria for future PRs

A good PR in this repo should make at least one of these things materially better:

- output asset usefulness
- generator coverage
- reproducibility
- QA confidence
- GameRewritten import readiness
- agent handoff quality
- documentation clarity

## Human summary

If a human asks what this repo is: it is a Python-based audio generation toolkit that should evolve into a full game-audio content factory.

## AI summary

If an AI agent asks what this repo is: it is a docs-first, continuity-first, seed-aware, asset-output-focused repository where every change should improve the ability to generate, verify, organize, and hand off game audio work.
