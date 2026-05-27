# Task Plan Order

Absolute repository paths are used intentionally in this file because the task explicitly required repository file references to use absolute paths.

Ordered one-file-at-a-time tasks to move this repository toward a full `GameRewritten` audio-delivery program.

---

## Task 01

- **Task Name:** Fix runtime music playback, looping, and cross-fade ownership
- **Coding logic of task and narrative design required:** Replace fire-and-forget music playback with managed music objects so exploration, battle, boss, and cinematic cues behave like persistent JRPG score layers instead of disposable one-shots.
- **Logic of how it functions in the program and design it must follow:** The runtime must own current/next music handles, support loop-safe playback, preserve stop/start control, and keep compatibility with the existing Lua/C++ integration surface.
- **Check to adhere to Final Fantasy aesthetics:** Ensure seamless loop continuity, graceful battle transitions, and a more cinematic PS2-era presentation instead of abrupt cuts.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **Line where code is to be edited or create:** Edit `L303-L345` (`Update`, `OnStateChange`, `PlayMusic`), `L462-L485` (`VerifyManifest` music file list), and `L562-L626` (`_TrackForState`, `_UpdateCrossfade`, member state); create new helper/state code after `L579`.

## Task 02

- **Task Name:** Expand the canonical game-audio manifest to full JRPG coverage
- **Coding logic of task and narrative design required:** Add the missing music, ambience, fanfare, transition, movement, combat, and spell families so the factory knows what the game actually needs.
- **Logic of how it functions in the program and design it must follow:** This file is the source-of-truth mapping for factory generation and downstream runtime lookup, so every new audio family must have stable identifiers, filenames, prompts, durations, and loop flags.
- **Check to adhere to Final Fantasy aesthetics:** Add exploration-region identity, mystery/dungeon moods, cinematic battle framing, readable combat verbs, and layered ambience expected from PS2-era FF presentation with modern action gameplay.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/game_state_map.py`
- **Line where code is to be edited or create:** Edit `L116-L197` (`MUSIC_MANIFEST`) and `L204-L249` (`SFX_MANIFEST`); create new manifest blocks after `L249`.

## Task 03

- **Task Name:** Add missing procedural SFX recipes and surface variation hooks
- **Coding logic of task and narrative design required:** Implement the missing low-level sound recipes for traversal, defense, damage, spell identity, interactions, and transition moments.
- **Logic of how it functions in the program and design it must follow:** Each new family needs a dedicated synthesizer function plus alias registration so prompt-driven and manifest-driven generation resolve deterministically to the right sound class.
- **Check to adhere to Final Fantasy aesthetics:** Favor crisp action readability, magical identity by element, and stylized but not overly realistic texture so the sounds sit between PS2 JRPG readability and modern action polish.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **Line where code is to be edited or create:** Extend recipe functions after `L148-L260` (starting from `_sfx_footstep` and nearby combat/spell helpers); update alias registry at `L746-L861` (`_SFX_FUNCTIONS`, `synthesise_sfx`, `available_sfx_types`).

## Task 04

- **Task Name:** Add missing music style presets for narrative and world-state gaps
- **Coding logic of task and narrative design required:** Introduce presets for stealth, memorial, mystery, underscore, ending, regional overworld variants, and short transition stings so prompts can land on stable musical behavior.
- **Logic of how it functions in the program and design it must follow:** Keep style additions additive by extending `TrackStyle` and `_STYLE_DEFS` without breaking current preset names or generator behavior.
- **Check to adhere to Final Fantasy aesthetics:** The new presets should cover melancholic, sacred, mysterious, heroic, and cinematic action states without copying franchise melodies.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/generator.py`
- **Line where code is to be edited or create:** Edit `L58-L92` (`TrackStyle`) and extend `_STYLE_DEFS` beginning at `L116`.

## Task 05

- **Task Name:** Teach the high-level music generator about region context and adaptive output
- **Coding logic of task and narrative design required:** Add region-aware prompt shaping and an optional stem/layer path so one generated cue can support open-world region identity and modern combat-intensity behavior.
- **Logic of how it functions in the program and design it must follow:** Keep the current mixed-output API intact, but add optional context fields and optional layer export behavior that downstream runtime systems can consume.
- **Check to adhere to Final Fantasy aesthetics:** Region tags should bias music toward plains, forest, coast, ruins, and arid identities while preserving the repo’s orchestral-plus-synth style families.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/music_gen.py`
- **Line where code is to be edited or create:** Edit `L55-L79` (`__init__`, `generate`) and `L97-L180` (`generate_from_plan`, `generate_to_file`, `_generate_from_plan`, `_master`).

## Task 06

- **Task Name:** Build the one-command vertical-slice release gate
- **Coding logic of task and narrative design required:** Create a deterministic pipeline that runs plan selection, request execution, QA, compliance, approval, and export in one machine-verifiable flow.
- **Logic of how it functions in the program and design it must follow:** Reuse existing batch/orchestration/provenance/export surfaces instead of inventing a parallel system, and emit one stable gate report artifact for later automation.
- **Check to adhere to Final Fantasy aesthetics:** The goal is not a style change here; it is ensuring that the repo can reliably deliver a complete JRPG-ready asset set without manual orchestration gaps.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/asset_pipeline.py`
- **Line where code is to be edited or create:** Edit `L722-L910` (`generate_all`, `generate_music_only`, `generate_sfx_only`, `generate_voice_only`) and add new orchestration code near `L1433-L1843` (`RequestBatchPipeline`, `PlanBatchOrchestrator`) before the later export/approval pipeline classes.

## Task 07

- **Task Name:** Expose the new completion flow and runtime options on the CLI
- **Coding logic of task and narrative design required:** Add command and flag surfaces for vertical-slice execution, PS2-mode routing, region-aware music generation, and any new generation entrypoints needed by the expanded factory.
- **Logic of how it functions in the program and design it must follow:** Preserve existing command compatibility and extend parser/dispatch blocks additively.
- **Check to adhere to Final Fantasy aesthetics:** The CLI should make it easy to request PS1/PS2-era color, region-specific world themes, and complete slice builds without ad hoc operator reasoning.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/cli.py`
- **Line where code is to be edited or create:** Edit `_resolve_backend` at `L88-L106`, command helpers near `L136-L223`, parser blocks at `L988-L1941`, and command dispatch at `L2210-L2214`.

## Task 08

- **Task Name:** Upgrade Lua hooks for ambience, transitions, and intensity behavior
- **Coding logic of task and narrative design required:** Add Lua-level controls for ambience playback, combat-intensity transitions, battle-intro stings, and vehicle playlist usage so the game script layer can drive the richer runtime audio system.
- **Logic of how it functions in the program and design it must follow:** Keep the nil-safe wrapper pattern, preserve current hooks, and add new ones as wrappers rather than destructive rewrites.
- **Check to adhere to Final Fantasy aesthetics:** Scripted hooks should reinforce battle start drama, ambient world presence, and vehicle/travel identity typical of modern FF presentation.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/lua/audio.lua`
- **Line where code is to be edited or create:** Edit `L54-L84` (Lua wrapper helpers) and `L94-L220` (explore/combat/camp/shop/inventory/spell hooks); create new hook wrappers after the current hook blocks.

## Task 09

- **Task Name:** Expand music request fixtures to cover the missing soundtrack families
- **Coding logic of task and narrative design required:** Add request records for regional exploration, stealth, mystery, memorial, underscore, credits, battle transitions, and additional OST variants.
- **Logic of how it functions in the program and design it must follow:** Every request needs stable `requestId`, `assetId`, prompt, seed, target path, duration, and QA shape so the batch pipeline can execute without ambiguity.
- **Check to adhere to Final Fantasy aesthetics:** Prompts should describe heroic sci-fantasy, melancholic techno-fantasy, sacred, mysterious, and cinematic action moods without asking for direct franchise copying.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json`
- **Line where code is to be edited or create:** Edit the existing request list at `L1-L520` (current music request array); append new entries after the current last request block.

## Task 10

- **Task Name:** Expand SFX request fixtures to full combat, traversal, ambience, and transition coverage
- **Coding logic of task and narrative design required:** Add deterministic requests for the missing surface footsteps, combat readability cues, spell identities, world interactions, ambience loops, and transition stings.
- **Logic of how it functions in the program and design it must follow:** Use distinct request IDs and seeds, preserve acceptance profiles, and follow the repo’s `_varNN` variant-family rules for repeated assets like footsteps.
- **Check to adhere to Final Fantasy aesthetics:** The resulting request set should support crisp action readability, stylized magic, and immersive open-world ambience instead of generic placeholder effects.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json`
- **Line where code is to be edited or create:** Edit `L1-L227` (current SFX request array); append new request families and variant entries after the current last block.

## Task 11

- **Task Name:** Expand the vertical-slice plan from a slice into a near-complete audio contract
- **Coding logic of task and narrative design required:** Add new target groups for expanded exploration music, ambience, transitions, combat states, fanfares, and any required optional voice placeholders.
- **Logic of how it functions in the program and design it must follow:** Keep the audio-plan schema stable while increasing target coverage so plan-driven orchestration can represent what the game actually needs.
- **Check to adhere to Final Fantasy aesthetics:** Target groups should reflect world travel, dungeon mystery, battle escalation, reward stingers, and environmental ambience consistent with FF-style worldbuilding.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json`
- **Line where code is to be edited or create:** Edit `L23-L305`, especially `assetGroups` and `notes`; append new groups after the current final group.

## Task 12

- **Task Name:** Wire vehicle playlist generation into the factory
- **Coding logic of task and narrative design required:** Turn the existing radio/playlist generator into a factory output that can support travel-mode playback and road-trip flavor.
- **Logic of how it functions in the program and design it must follow:** Reuse the existing preset system and emit a stable `playlist.json` contract that runtime code can parse without guessing.
- **Check to adhere to Final Fantasy aesthetics:** Playlist content should support modern-FF travel energy while staying inside the repo’s safe inspiration rules.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/radio_playlist.py`
- **Line where code is to be edited or create:** Edit preset/generator areas at `L105-L106` (`PLAYLIST_PRESETS`), `L291-L433` (`RadioPlaylistGenerator`, `generate_playlist`), and related helper code through `L542`.

## Task 13

- **Task Name:** Add PS2-era SPU2 coloration to the DSP effects chain
- **Coding logic of task and narrative design required:** Introduce a PS2-flavored reverb/profile option so FF10/FF12-style ambience and score color can be distinguished from the rougher PS1 character.
- **Logic of how it functions in the program and design it must follow:** Extend the existing mode table and effect chain additively, keeping PS1 behavior unchanged unless the new mode is requested.
- **Check to adhere to Final Fantasy aesthetics:** The target is wider, cleaner, more spacious PS2-style reverb rather than raw PS1 crunch.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/dsp/ps1_effects.py`
- **Line where code is to be edited or create:** Edit `L38-L86` (`SPUReverbMode`, `_SPU_REVERB_MODES`), constructor region `L130-L140`, and reverb processing path starting at `L207` (`spu_reverb` / `apply` behavior).

## Task 14

- **Task Name:** Expose PS2-mode behavior through the retro backend
- **Coding logic of task and narrative design required:** Teach the PS1 backend to operate in a PS2-flavored mode so higher-era presets can request cleaner bit depth and PS2-style reverb defaults.
- **Logic of how it functions in the program and design it must follow:** Preserve the current `ps1` backend behavior, but add a mode flag and routing path that CLI/runtime code can request explicitly.
- **Check to adhere to Final Fantasy aesthetics:** Use PS2 mode for FF10/FF12-style calm, sacred, and cinematic cues while keeping harsher PS1 color for FF7/FF8 presets.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/ps1_backend.py`
- **Line where code is to be edited or create:** Edit constructor and generation flow at `L54-L139` (`__init__`, `generate_music_audio`, `generate_voice_audio`).

## Task 15

- **Task Name:** Add mastering profiles for PS1 and PS2 presentation polish
- **Coding logic of task and narrative design required:** Add two new mastering targets that can shape already-generated audio toward retro-console coloration without changing higher-level composition logic.
- **Logic of how it functions in the program and design it must follow:** Extend the profile set additively, provide defaults, and keep existing profile behavior unchanged.
- **Check to adhere to Final Fantasy aesthetics:** `ps1` should sound narrower and gritier; `ps2` should sound cleaner, broader, and more cinematic.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/render/offline_bounce.py`
- **Line where code is to be edited or create:** Edit `L31-L34` (`_VALID_PROFILES`, `VALID_PROFILES`), constructor profile defaults at `L98-L131`, EQ build logic at `L150-L171`, and profile-dependent processing at `L208-L218`.

## Task 16

- **Task Name:** Turn the full-game checklist into a real completion tracker
- **Coding logic of task and narrative design required:** Keep the checklist synchronized with actual generated-and-approved coverage so “program complete” can be measured honestly.
- **Logic of how it functions in the program and design it must follow:** This file must remain a truthful completion ledger; only mark items complete when fixtures, generation, QA, approval, and export support really exist.
- **Check to adhere to Final Fantasy aesthetics:** Make sure checklist completion includes not only raw categories but also the mood families expected from FF-style world, battle, and emotional storytelling.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`
- **Line where code is to be edited or create:** Edit `L21-L145` (the checklist sections for music, SFX, ambience, transitions, and voice); add annotations or completion marks inline where coverage becomes real.

## Task 17

- **Task Name:** Document the remaining runtime and completion blockers clearly
- **Coding logic of task and narrative design required:** Record the still-open gaps so future agents do not mistake the repo for finished when key runtime and coverage problems remain.
- **Logic of how it functions in the program and design it must follow:** Keep this file aligned with implemented reality and use it to surface the highest-value unresolved issues during future handoffs.
- **Check to adhere to Final Fantasy aesthetics:** Call out the blockers that specifically prevent cinematic JRPG presentation: looping, crossfades, adaptive intensity, and missing world-audio coverage.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/KNOWN_ISSUES.md`
- **Line where code is to be edited or create:** Edit `L1-L39` (current high-impact gaps section); add new issue entries there.
