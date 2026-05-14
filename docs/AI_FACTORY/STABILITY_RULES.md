# Stability and Refactor Rules

> Guardrails for future agents. Optimize for working asset output, continuity, and low-prompt operability.

## 1) Stable interfaces (treat as compatibility-sensitive)

- CLI command family in `audio_engine/cli.py` (`generate`, `generate-music`, `generate-sfx`, `generate-game-assets`, `verify-game-assets`, `qa`, etc.)
- Top-level `AudioEngine` API in `audio_engine/engine.py`
- Current integration manifest concepts in `audio_engine/integration/game_state_map.py`
- Persistent memory docs in `docs/AI_FACTORY/` (especially `README`, `CURRENT_STATE`, `SESSION_QUEUE`, `ACTIVE_WORK`, `HANDOFF`)

If you need to change these, do it incrementally and update docs in the same PR.

## 2) Safe-to-change areas (lower compatibility risk)

- Internal helper decomposition inside `audio_engine/ai/*`, `audio_engine/dsp/*`, `audio_engine/render/*`
- Prompt wording/preset tuning that does not break interfaces
- Documentation expansion for clarity and machine guidance
- Additional examples/contracts under `docs/AI_FACTORY/EXAMPLES/`

## 3) Avoid heavy refactors for now

Do **not** do large architectural rewrites unless they are required to ship a working generation workflow:

- avoid broad module moves/renames that break agent path memory
- avoid replacing working procedural paths before a tested replacement exists
- avoid “clean architecture” rewrites that do not improve asset output or reproducibility

## 4) Priority rule: working output beats elegant internals

- It is acceptable for internals to be pragmatic or repetitive.
- It is not acceptable for output generation behavior to become unclear, untestable, or undocumented.

## 5) Continuity rule

When behavior changes, update these in the same PR:

1. `docs/AI_FACTORY/CURRENT_STATE.md`
2. `docs/AI_FACTORY/ACTIVE_WORK.md`
3. `docs/AI_FACTORY/HANDOFF.md`
4. `docs/AI_FACTORY/SESSION_QUEUE.md` when session order/state changes
5. one relevant subsystem doc
6. one relevant QA/style/schema doc

## 6) Full-game-audio direction rule

All major changes should improve eventual coverage for full game audio needs:

- music (field/town/dungeon/battle/boss)
- fanfares/stingers
- UI sounds
- combat/spell SFX
- ambience
- optional low-priority voice
