# Task Plan Order

Absolute repository paths are used intentionally in this file because the task explicitly required repository file references to use absolute paths.

Tasks 01-17 remain sourced from `Task_List.md` and are mirrored here so this file can serve as one complete execution order document.

For execution sequencing, `taskplanorder.md` is the authoritative plan; if it ever diverges from `Task_List.md`, sync the Task 01-17 blocks to keep both documents aligned.

---

## Phase A: Core Infrastructure and Release Gate (Tasks 01-17)

## Task 01

- **Task Name:** Fix runtime music playback, looping, and cross-fade ownership
- **Coding logic of task and narrative design required:** Replace fire-and-forget music playback with managed music objects so exploration, battle, boss, and cinematic cues behave like persistent JRPG score layers instead of disposable one-shots.
- **Logic of how it functions in the program and design it must follow:** The runtime must own current/next music handles, support loop-safe playback, preserve stop/start control, and keep compatibility with the existing Lua/C++ integration surface.
- **Check to adhere to Final Fantasy aesthetics:** Ensure seamless loop continuity, graceful battle transitions, and a more cinematic PS2-era presentation instead of abrupt cuts.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **Line where code is to be edited or create:** Edit `L303-L345` (`Update`, `OnStateChange`, `PlayMusic`), `L462-L485` (`VerifyManifest` music file list), and `L562-L626` (`_TrackForState`, `_UpdateCrossfade`, member state); create new helper/state code after `L579`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **READ_LINES:** Edit `L303-L345` (`Update`, `OnStateChange`, `PlayMusic`), `L462-L485` (`VerifyManifest` music file list), and `L562-L626` (`_TrackForState`, `_UpdateCrossfade`, member state); create new helper/state code after `L579`.

## Task 02

- **Task Name:** Expand the canonical game-audio manifest to full JRPG coverage
- **Coding logic of task and narrative design required:** Add the missing music, ambience, fanfare, transition, movement, combat, and spell families so the factory knows what the game actually needs.
- **Logic of how it functions in the program and design it must follow:** This file is the source-of-truth mapping for factory generation and downstream runtime lookup, so every new audio family must have stable identifiers, filenames, prompts, durations, and loop flags.
- **Check to adhere to Final Fantasy aesthetics:** Add exploration-region identity, mystery/dungeon moods, cinematic battle framing, readable combat verbs, and layered ambience expected from PS2-era FF presentation with modern action gameplay.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/game_state_map.py`
- **Line where code is to be edited or create:** Edit `L116-L197` (`MUSIC_MANIFEST`) and `L204-L249` (`SFX_MANIFEST`); create new manifest blocks after `L249`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/game_state_map.py`
- **READ_LINES:** Edit `L116-L197` (`MUSIC_MANIFEST`) and `L204-L249` (`SFX_MANIFEST`); create new manifest blocks after `L249`.

## Task 03

- **Task Name:** Add missing procedural SFX recipes and surface variation hooks
- **Coding logic of task and narrative design required:** Implement the missing low-level sound recipes for traversal, defense, damage, spell identity, interactions, and transition moments.
- **Logic of how it functions in the program and design it must follow:** Each new family needs a dedicated synthesizer function plus alias registration so prompt-driven and manifest-driven generation resolve deterministically to the right sound class.
- **Check to adhere to Final Fantasy aesthetics:** Favor crisp action readability, magical identity by element, and stylized but not overly realistic texture so the sounds sit between PS2 JRPG readability and modern action polish.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **Line where code is to be edited or create:** Extend recipe functions after `L148-L260` (starting from `_sfx_footstep` and nearby combat/spell helpers); update alias registry at `L746-L861` (`_SFX_FUNCTIONS`, `synthesise_sfx`, `available_sfx_types`).
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **READ_LINES:** Extend recipe functions after `L148-L260` (starting from `_sfx_footstep` and nearby combat/spell helpers); update alias registry at `L746-L861` (`_SFX_FUNCTIONS`, `synthesise_sfx`, `available_sfx_types`).

## Task 04

- **Task Name:** Add missing music style presets for narrative and world-state gaps
- **Coding logic of task and narrative design required:** Introduce presets for stealth, memorial, mystery, underscore, ending, regional overworld variants, and short transition stings so prompts can land on stable musical behavior.
- **Logic of how it functions in the program and design it must follow:** Keep style additions additive by extending `TrackStyle` and `_STYLE_DEFS` without breaking current preset names or generator behavior.
- **Check to adhere to Final Fantasy aesthetics:** The new presets should cover melancholic, sacred, mysterious, heroic, and cinematic action states without copying franchise melodies.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/generator.py`
- **Line where code is to be edited or create:** Edit `L58-L92` (`TrackStyle`) and extend `_STYLE_DEFS` beginning at `L116`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/generator.py`
- **READ_LINES:** Edit `L58-L92` (`TrackStyle`) and extend `_STYLE_DEFS` beginning at `L116`.

## Task 05

- **Task Name:** Teach the high-level music generator about region context and adaptive output
- **Coding logic of task and narrative design required:** Add region-aware prompt shaping and an optional stem/layer path so one generated cue can support open-world region identity and modern combat-intensity behavior.
- **Logic of how it functions in the program and design it must follow:** Keep the current mixed-output API intact, but add optional context fields and optional layer export behavior that downstream runtime systems can consume.
- **Check to adhere to Final Fantasy aesthetics:** Region tags should bias music toward plains, forest, coast, ruins, and arid identities while preserving the repo’s orchestral-plus-synth style families.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/music_gen.py`
- **Line where code is to be edited or create:** Edit `L55-L79` (`__init__`, `generate`) and `L97-L180` (`generate_from_plan`, `generate_to_file`, `_generate_from_plan`, `_master`).
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/music_gen.py`
- **READ_LINES:** Edit `L55-L79` (`__init__`, `generate`) and `L97-L180` (`generate_from_plan`, `generate_to_file`, `_generate_from_plan`, `_master`).

## Task 06

- **Task Name:** Build the one-command vertical-slice release gate
- **Coding logic of task and narrative design required:** Create a deterministic pipeline that runs plan selection, request execution, QA, compliance, approval, and export in one machine-verifiable flow.
- **Logic of how it functions in the program and design it must follow:** Reuse existing batch/orchestration/provenance/export surfaces instead of inventing a parallel system, and emit one stable gate report artifact for later automation.
- **Check to adhere to Final Fantasy aesthetics:** The goal is not a style change here; it is ensuring that the repo can reliably deliver a complete JRPG-ready asset set without manual orchestration gaps.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/asset_pipeline.py`
- **Line where code is to be edited or create:** Edit `L722-L910` (`generate_all`, `generate_music_only`, `generate_sfx_only`, `generate_voice_only`) and add new orchestration code near `L1433-L1843` (`RequestBatchPipeline`, `PlanBatchOrchestrator`) before the later export/approval pipeline classes.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/asset_pipeline.py`
- **READ_LINES:** Edit `L722-L910` (`generate_all`, `generate_music_only`, `generate_sfx_only`, `generate_voice_only`) and add new orchestration code near `L1433-L1843` (`RequestBatchPipeline`, `PlanBatchOrchestrator`) before the later export/approval pipeline classes.

## Task 07

- **Task Name:** Expose the new completion flow and runtime options on the CLI
- **Coding logic of task and narrative design required:** Add command and flag surfaces for vertical-slice execution, PS2-mode routing, region-aware music generation, and any new generation entrypoints needed by the expanded factory.
- **Logic of how it functions in the program and design it must follow:** Preserve existing command compatibility and extend parser/dispatch blocks additively.
- **Check to adhere to Final Fantasy aesthetics:** The CLI should make it easy to request PS1/PS2-era color, region-specific world themes, and complete slice builds without ad hoc operator reasoning.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/cli.py`
- **Line where code is to be edited or create:** Edit `_resolve_backend` at `L88-L106`, command helpers near `L136-L223`, parser blocks at `L988-L1941`, and command dispatch at `L2210-L2214`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/cli.py`
- **READ_LINES:** Edit `_resolve_backend` at `L88-L106`, command helpers near `L136-L223`, parser blocks at `L988-L1941`, and command dispatch at `L2210-L2214`.

## Task 08

- **Task Name:** Upgrade Lua hooks for ambience, transitions, and intensity behavior
- **Coding logic of task and narrative design required:** Add Lua-level controls for ambience playback, combat-intensity transitions, battle-intro stings, and vehicle playlist usage so the game script layer can drive the richer runtime audio system.
- **Logic of how it functions in the program and design it must follow:** Keep the nil-safe wrapper pattern, preserve current hooks, and add new ones as wrappers rather than destructive rewrites.
- **Check to adhere to Final Fantasy aesthetics:** Scripted hooks should reinforce battle start drama, ambient world presence, and vehicle/travel identity typical of modern FF presentation.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/lua/audio.lua`
- **Line where code is to be edited or create:** Edit `L54-L84` (Lua wrapper helpers) and `L94-L220` (explore/combat/camp/shop/inventory/spell hooks); create new hook wrappers after the current hook blocks.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/lua/audio.lua`
- **READ_LINES:** Edit `L54-L84` (Lua wrapper helpers) and `L94-L220` (explore/combat/camp/shop/inventory/spell hooks); create new hook wrappers after the current hook blocks.

## Task 09

- **Task Name:** Expand music request fixtures to cover the missing soundtrack families
- **Coding logic of task and narrative design required:** Add request records for regional exploration, stealth, mystery, memorial, underscore, credits, battle transitions, and additional OST variants.
- **Logic of how it functions in the program and design it must follow:** Every request needs stable `requestId`, `assetId`, prompt, seed, target path, duration, and QA shape so the batch pipeline can execute without ambiguity.
- **Check to adhere to Final Fantasy aesthetics:** Prompts should describe heroic sci-fantasy, melancholic techno-fantasy, sacred, mysterious, and cinematic action moods without asking for direct franchise copying.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json`
- **Line where code is to be edited or create:** Edit the existing request list at `L1-L520` (current music request array); append new entries after the current last request block.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json`
- **READ_LINES:** Edit the existing request list at `L1-L520` (current music request array); append new entries after the current last request block.

## Task 10

- **Task Name:** Expand SFX request fixtures to full combat, traversal, ambience, and transition coverage
- **Coding logic of task and narrative design required:** Add deterministic requests for the missing surface footsteps, combat readability cues, spell identities, world interactions, ambience loops, and transition stings.
- **Logic of how it functions in the program and design it must follow:** Use distinct request IDs and seeds, preserve acceptance profiles, and follow the repo’s `_varNN` variant-family rules for repeated assets like footsteps.
- **Check to adhere to Final Fantasy aesthetics:** The resulting request set should support crisp action readability, stylized magic, and immersive open-world ambience instead of generic placeholder effects.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json`
- **Line where code is to be edited or create:** Edit `L1-L227` (current SFX request array); append new request families and variant entries after the current last block.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json`
- **READ_LINES:** Edit `L1-L227` (current SFX request array); append new request families and variant entries after the current last block.

## Task 11

- **Task Name:** Expand the vertical-slice plan from a slice into a near-complete audio contract
- **Coding logic of task and narrative design required:** Add new target groups for expanded exploration music, ambience, transitions, combat states, fanfares, and any required optional voice placeholders.
- **Logic of how it functions in the program and design it must follow:** Keep the audio-plan schema stable while increasing target coverage so plan-driven orchestration can represent what the game actually needs.
- **Check to adhere to Final Fantasy aesthetics:** Target groups should reflect world travel, dungeon mystery, battle escalation, reward stingers, and environmental ambience consistent with FF-style worldbuilding.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json`
- **Line where code is to be edited or create:** Edit `L23-L305`, especially `assetGroups` and `notes`; append new groups after the current final group.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/audio_plan.vertical_slice.v1.json`
- **READ_LINES:** Edit `L23-L305`, especially `assetGroups` and `notes`; append new groups after the current final group.

## Task 12

- **Task Name:** Wire vehicle playlist generation into the factory
- **Coding logic of task and narrative design required:** Turn the existing radio/playlist generator into a factory output that can support travel-mode playback and road-trip flavor.
- **Logic of how it functions in the program and design it must follow:** Reuse the existing preset system and emit a stable `playlist.json` contract that runtime code can parse without guessing.
- **Check to adhere to Final Fantasy aesthetics:** Playlist content should support modern-FF travel energy while staying inside the repo’s safe inspiration rules.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/radio_playlist.py`
- **Line where code is to be edited or create:** Edit preset/generator areas at `L105-L106` (`PLAYLIST_PRESETS`), `L291-L433` (`RadioPlaylistGenerator`, `generate_playlist`), and related helper code through `L542`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/radio_playlist.py`
- **READ_LINES:** Edit preset/generator areas at `L105-L106` (`PLAYLIST_PRESETS`), `L291-L433` (`RadioPlaylistGenerator`, `generate_playlist`), and related helper code through `L542`.

## Task 13

- **Task Name:** Add PS2-era SPU2 coloration to the DSP effects chain
- **Coding logic of task and narrative design required:** Introduce a PS2-flavored reverb/profile option so FF10/FF12-style ambience and score color can be distinguished from the rougher PS1 character.
- **Logic of how it functions in the program and design it must follow:** Extend the existing mode table and effect chain additively, keeping PS1 behavior unchanged unless the new mode is requested.
- **Check to adhere to Final Fantasy aesthetics:** The target is wider, cleaner, more spacious PS2-style reverb rather than raw PS1 crunch.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/dsp/ps1_effects.py`
- **Line where code is to be edited or create:** Edit `L38-L86` (`SPUReverbMode`, `_SPU_REVERB_MODES`), constructor region `L130-L140`, and reverb processing path starting at `L207` (`spu_reverb` / `apply` behavior).
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/dsp/ps1_effects.py`
- **READ_LINES:** Edit `L38-L86` (`SPUReverbMode`, `_SPU_REVERB_MODES`), constructor region `L130-L140`, and reverb processing path starting at `L207` (`spu_reverb` / `apply` behavior).

## Task 14

- **Task Name:** Expose PS2-mode behavior through the retro backend
- **Coding logic of task and narrative design required:** Teach the PS1 backend to operate in a PS2-flavored mode so higher-era presets can request cleaner bit depth and PS2-style reverb defaults.
- **Logic of how it functions in the program and design it must follow:** Preserve the current `ps1` backend behavior, but add a mode flag and routing path that CLI/runtime code can request explicitly.
- **Check to adhere to Final Fantasy aesthetics:** Use PS2 mode for FF10/FF12-style calm, sacred, and cinematic cues while keeping harsher PS1 color for FF7/FF8 presets.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/ps1_backend.py`
- **Line where code is to be edited or create:** Edit constructor and generation flow at `L54-L139` (`__init__`, `generate_music_audio`, `generate_voice_audio`).
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/ps1_backend.py`
- **READ_LINES:** Edit constructor and generation flow at `L54-L139` (`__init__`, `generate_music_audio`, `generate_voice_audio`).

## Task 15

- **Task Name:** Add mastering profiles for PS1 and PS2 presentation polish
- **Coding logic of task and narrative design required:** Add two new mastering targets that can shape already-generated audio toward retro-console coloration without changing higher-level composition logic.
- **Logic of how it functions in the program and design it must follow:** Extend the profile set additively, provide defaults, and keep existing profile behavior unchanged.
- **Check to adhere to Final Fantasy aesthetics:** `ps1` should sound narrower and gritier; `ps2` should sound cleaner, broader, and more cinematic.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/render/offline_bounce.py`
- **Line where code is to be edited or create:** Edit `L31-L34` (`_VALID_PROFILES`, `VALID_PROFILES`), constructor profile defaults at `L98-L131`, EQ build logic at `L150-L171`, and profile-dependent processing at `L208-L218`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/render/offline_bounce.py`
- **READ_LINES:** Edit `L31-L34` (`_VALID_PROFILES`, `VALID_PROFILES`), constructor profile defaults at `L98-L131`, EQ build logic at `L150-L171`, and profile-dependent processing at `L208-L218`.

## Task 16

- **Task Name:** Turn the full-game checklist into a real completion tracker
- **Coding logic of task and narrative design required:** Keep the checklist synchronized with actual generated-and-approved coverage so “program complete” can be measured honestly.
- **Logic of how it functions in the program and design it must follow:** This file must remain a truthful completion ledger; only mark items complete when fixtures, generation, QA, approval, and export support really exist.
- **Check to adhere to Final Fantasy aesthetics:** Make sure checklist completion includes not only raw categories but also the mood families expected from FF-style world, battle, and emotional storytelling.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`
- **Line where code is to be edited or create:** Edit `L21-L145` (the checklist sections for music, SFX, ambience, transitions, and voice); add annotations or completion marks inline where coverage becomes real.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`
- **READ_LINES:** Edit `L21-L145` (the checklist sections for music, SFX, ambience, transitions, and voice); add annotations or completion marks inline where coverage becomes real.

## Task 17

- **Task Name:** Document the remaining runtime and completion blockers clearly
- **Coding logic of task and narrative design required:** Record the still-open gaps so future agents do not mistake the repo for finished when key runtime and coverage problems remain.
- **Logic of how it functions in the program and design it must follow:** Keep this file aligned with implemented reality and use it to surface the highest-value unresolved issues during future handoffs.
- **Check to adhere to Final Fantasy aesthetics:** Call out the blockers that specifically prevent cinematic JRPG presentation: looping, crossfades, adaptive intensity, and missing world-audio coverage.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/KNOWN_ISSUES.md`
- **Line where code is to be edited or create:** Edit `L1-L39` (current high-impact gaps section); add new issue entries there.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/KNOWN_ISSUES.md`
- **READ_LINES:** Edit `L1-L39` (current high-impact gaps section); add new issue entries there.

---

## Phase B: Content Expansion and Full-Game Coverage (Tasks 27-39)

## Task 27

- **Task Name:** Expand region-specific exploration music in game_state_map.py
- **Coding logic of task and narrative design required:** Expand exploration-region mappings so plains, forest, coast, ruins, arid, mountain, and settlement states route to distinct full-game exploration families.
- **Logic of how it functions in the program and design it must follow:** Keep mappings deterministic and additive in the existing manifest/state-map structure so runtime and generation fixtures resolve stable IDs without breaking existing lookups.
- **Check to adhere to Final Fantasy aesthetics:** Preserve FF-inspired regional identity and melancholic/heroic world-travel mood balance while avoiding direct IP copying.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/game_state_map.py`
- **Line where code is to be edited or create:** Edit `L116-L197` (`MUSIC_MANIFEST`) to append region-specific exploration families and state keys.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/game_state_map.py`
- **READ_LINES:** `L100-L210`

## Task 28

- **Task Name:** Add tension/stealth/mystery/memorial/ending music families to music_gen.py
- **Coding logic of task and narrative design required:** Extend MusicGen style-family handling with the missing narrative-state families needed by assessment27 coverage.
- **Logic of how it functions in the program and design it must follow:** Add family parsing/selection additively so existing generation behavior remains stable while new family prompts map to deterministic outputs.
- **Check to adhere to Final Fantasy aesthetics:** Support sacred, mysterious, memorial, stealth, and ending moods in FF-inspired orchestral-plus-synth language.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/music_gen.py`
- **Line where code is to be edited or create:** Edit family/style routing around `L55-L79` and generation flow in `L97-L180`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/music_gen.py`
- **READ_LINES:** `L50-L220`

## Task 29

- **Task Name:** Create ambience synthesis and layering system
- **Coding logic of task and narrative design required:** Add a dedicated ambience synthesis module with deterministic multi-layer ambience construction for biome/region playback.
- **Logic of how it functions in the program and design it must follow:** Provide reusable ambience layer presets and render entry points compatible with existing ai module conventions.
- **Check to adhere to Final Fantasy aesthetics:** Ambience beds should support immersive FF-style world atmosphere without imitating franchise assets.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/ambience_synth.py`
- **Line where code is to be edited or create:** Create new module and implement core ambience layer synthesis from `L1` onward.
- **READ_FILE:** Template 1: `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/music_gen.py`; Template 2: `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **READ_LINES:** `music_gen.py L1-L220`; `sfx_synth.py L140-L880` (new target file `ambience_synth.py` is N/A pre-create)

## Task 30

- **Task Name:** Add transition stings generator to sfx_synth.py
- **Coding logic of task and narrative design required:** Add transition-sting synthesis families for battle intro/outro, dramatic scene cuts, and state-change punctuation.
- **Logic of how it functions in the program and design it must follow:** Implement new transition generators and register them in existing alias dispatch so manifest/prompt requests resolve deterministically.
- **Check to adhere to Final Fantasy aesthetics:** Transition stings should feel cinematic and readable in an FF-inspired style-safe way.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **Line where code is to be edited or create:** Extend recipe helpers after `L148-L260`; update registry at `L746-L861`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **READ_LINES:** `L140-L880`

## Task 31

- **Task Name:** Expand surface-specific footsteps in sfx_synth.py
- **Coding logic of task and narrative design required:** Add broader traversal surface families (stone, wood, metal, sand, grass, snow, wet, debris) with deterministic variation hooks.
- **Logic of how it functions in the program and design it must follow:** Keep the existing footstep family contract intact while extending family aliases and synthesis parameters for new surfaces.
- **Check to adhere to Final Fantasy aesthetics:** Footstep texture should preserve stylized JRPG readability while reflecting environment identity.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **Line where code is to be edited or create:** Extend `_sfx_footstep` and related traversal families in `L148-L260`; update alias coverage in `L746-L861`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **READ_LINES:** `L148-L880`

## Task 32

- **Task Name:** Add fuller combat readability SFX to sfx_synth.py
- **Coding logic of task and narrative design required:** Expand combat cues (light/heavy impacts, guards, breaks, status confirms, threat tells) to improve full-game readability.
- **Logic of how it functions in the program and design it must follow:** Add new deterministic combat family functions and aliases while maintaining compatibility with existing generation calls.
- **Check to adhere to Final Fantasy aesthetics:** Combat cues should be clear, dramatic, and stylized for FF-inspired action readability.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **Line where code is to be edited or create:** Extend combat recipe functions after `L148-L260`; expand `_SFX_FUNCTIONS` entries in `L746-L861`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **READ_LINES:** `L148-L880`

## Task 33

- **Task Name:** Expand spell identity families in sfx_synth.py
- **Coding logic of task and narrative design required:** Add missing spell families (elemental tiers, holy, dark, support, heal, debuff, summon accents) for full-game identity separation.
- **Logic of how it functions in the program and design it must follow:** Implement additive spell-family synthesis functions and alias mappings so requests remain deterministic and backward compatible.
- **Check to adhere to Final Fantasy aesthetics:** Spell identities should clearly communicate magical archetypes in an FF-inspired but original style.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **Line where code is to be edited or create:** Extend spell helpers after `L148-L260`; update spell alias routing in `L746-L861`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ai/sfx_synth.py`
- **READ_LINES:** `L148-L880`

## Task 34

- **Task Name:** Add region-aware music selection logic to AudioSystem.hpp
- **Coding logic of task and narrative design required:** Extend runtime state->track resolution to include region-aware exploration choices and broader world-state coverage.
- **Logic of how it functions in the program and design it must follow:** Keep managed playback/crossfade model intact while adding deterministic selection branches keyed by expanded state map families.
- **Check to adhere to Final Fantasy aesthetics:** Runtime selection should support seamless regional world-travel scoring with cinematic continuity.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **Line where code is to be edited or create:** Edit `_TrackForState` and related runtime selection in `L599-L616` and nearby helper/state blocks.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **READ_LINES:** `L562-L700`

## Task 35

- **Task Name:** Add ambience layering to AudioSystem.hpp runtime
- **Coding logic of task and narrative design required:** Add ambience layer ownership/update paths so runtime can blend base ambience and region/event overlays.
- **Logic of how it functions in the program and design it must follow:** Reuse managed runtime update flow and add deterministic ambience channels synchronized with gameplay states.
- **Check to adhere to Final Fantasy aesthetics:** Layered ambience should deepen world presence without masking dialogue/combat readability.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **Line where code is to be edited or create:** Edit runtime update/state helpers around `L342-L364` and `L562-L728` to include ambience layer updates.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **READ_LINES:** `L330-L760`

## Task 36

- **Task Name:** Add battle transition intensity logic to AudioSystem.hpp
- **Coding logic of task and narrative design required:** Add transition intensity logic to shape battle entry/escalation using new transition/sting families.
- **Logic of how it functions in the program and design it must follow:** Extend state-change and crossfade pathways with deterministic intensity tiers while preserving current playback safety.
- **Check to adhere to Final Fantasy aesthetics:** Battle transitions should feel cinematic and escalating in a PS2-era FF-inspired style.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **Line where code is to be edited or create:** Edit `OnStateChange`, `_TrackForState`, and `_UpdateCrossfade` around `L303-L345`, `L599-L616`, `L708-L728`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/cpp/AudioSystem.hpp`
- **READ_LINES:** `L300-L740`

## Task 37

- **Task Name:** Expand audio.lua game state mapping for new families
- **Coding logic of task and narrative design required:** Extend Lua-side hook/state mapping to expose new music, ambience, and transition families added for full-game coverage.
- **Logic of how it functions in the program and design it must follow:** Keep existing wrapper compatibility while adding deterministic hook routes for new family keys and states.
- **Check to adhere to Final Fantasy aesthetics:** Lua mappings should preserve cinematic pacing and FF-inspired world/battle transitions.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/lua/audio.lua`
- **Line where code is to be edited or create:** Edit wrapper/helper and state-hook sections in `L54-L84` and `L94-L220`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/integration/lua/audio.lua`
- **READ_LINES:** `L54-L240`

## Task 38

- **Task Name:** Create generation_requests.ambience.v1.json fixture
- **Coding logic of task and narrative design required:** Add a dedicated ambience request fixture representing full-game ambience families for deterministic request-batch generation.
- **Logic of how it functions in the program and design it must follow:** Follow existing request fixture schema conventions (stable IDs, prompts, seeds, target paths, QA profile fields).
- **Check to adhere to Final Fantasy aesthetics:** Ambience prompts should cover FF-inspired biomes/moods while staying style-safe and original.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.ambience.v1.json`
- **Line where code is to be edited or create:** Create new fixture file and define ambience request array from `L1` onward.
- **READ_FILE:** Template 1: `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.music.v1.json`; Template 2: `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/generation_requests.sfx.v1.json`
- **READ_LINES:** `music L1-L520`; `sfx L1-L227` (new target fixture `generation_requests.ambience.v1.json` is N/A pre-create)

## Task 39

- **Task Name:** Update FULL_GAME_AUDIO_CHECKLIST.md completion status
- **Coding logic of task and narrative design required:** Update checklist completion tracking to reflect newly implemented full-game content/runtime/fixture coverage.
- **Logic of how it functions in the program and design it must follow:** Keep checklist as an auditable truth source and only mark statuses supported by implemented generation/QA/runtime pathways.
- **Check to adhere to Final Fantasy aesthetics:** Ensure completion checks include mood-family and runtime-presentation expectations for FF-inspired delivery quality.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`
- **Line where code is to be edited or create:** Edit coverage status sections in `L21-L145` and annotate completion deltas.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/docs/AI_FACTORY/FULL_GAME_AUDIO_CHECKLIST.md`
- **READ_LINES:** `L21-L180`


---

## Phase C: Manual GUI Authoring Completion (Tasks 18-26)

## Task 18

- **Task Name:** Restructure studio state model for full manual GUI authoring
- **Coding logic of task and narrative design required:** Split studio runtime state into explicit models for project metadata, manual composition controls, manual SFX controls, manual voice controls, preview state, and render queue state.
- **Logic of how it functions in the program and design it must follow:** Keep all GUI state deterministic and serializable so manual authoring sessions can be saved and restored without hidden values.
- **Check to adhere to Final Fantasy aesthetics:** Preserve existing style-safe defaults while allowing manual authoring to intentionally shape orchestral-plus-synth textures.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **Line where code is to be edited or create:** Edit `L24-L230` (state helpers and preset/new-file schema helpers) and create additional state/validation helpers before `launch_studio`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **READ_LINES:** `L24-L230`

## Task 19

- **Task Name:** Build a project/session panel for manual audio authoring
- **Coding logic of task and narrative design required:** Add a dedicated project panel for session name, output workspace, template loading, autosave toggles, and recent project history.
- **Logic of how it functions in the program and design it must follow:** The panel must drive all output targets and preset persistence so the user can manually create assets without command-line steps.
- **Check to adhere to Final Fantasy aesthetics:** Project templates should include FF-style mood starter presets without direct franchise copying.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **Line where code is to be edited or create:** Edit `L242-L288` (control bar + notebook setup) and add new project/session frame wiring before music tab construction.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **READ_LINES:** `L242-L288`

## Task 20

- **Task Name:** Expand manual music-authoring controls into full composition workflow
- **Coding logic of task and narrative design required:** Add manual controls for key/scale/root, progression selection, melody pattern, chord pattern, arrangement layers, loop markers, and per-layer instrument routing.
- **Logic of how it functions in the program and design it must follow:** Manual controls must map directly to generator/runtime parameters so every UI decision deterministically changes rendered output.
- **Check to adhere to Final Fantasy aesthetics:** Include controls for melancholic, sacred, heroic, mystery, and techno-fantasy orchestration balance.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **Line where code is to be edited or create:** Edit `L289-L488` (music tab UI + generation path) and create additional manual composition parameter mapping in `_run_music_generation`.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **READ_LINES:** `L289-L488`

## Task 21

- **Task Name:** Expand manual SFX design controls for procedural and sample workflows
- **Coding logic of task and narrative design required:** Add manual SFX controls for attack/decay/sustain/release, filter curve shape, transient amount, noise blend, layer stacking, and audition variants.
- **Logic of how it functions in the program and design it must follow:** Each control must map to deterministic synthesis parameters and remain compatible with existing `SFXGen` generation contracts.
- **Check to adhere to Final Fantasy aesthetics:** Provide readable combat/transitions while keeping stylized JRPG impact and magic identity.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **Line where code is to be edited or create:** Edit `L490-L561` (SFX tab + `_run_sfx_generation`) and add parameter translation helpers in nearby UI logic.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **READ_LINES:** `L490-L561`

## Task 22

- **Task Name:** Expand manual voice-authoring controls for dialogue production
- **Coding logic of task and narrative design required:** Add controls for pacing sections, pause insertion, emphasis tags, pronunciation notes, voice blending, and line-variant batch generation.
- **Logic of how it functions in the program and design it must follow:** The voice panel must remain backend-safe while exposing deterministic controls for reproducible voice renders.
- **Check to adhere to Final Fantasy aesthetics:** Support cinematic JRPG dialogue timing and emotional delivery without copying existing IP performances.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **Line where code is to be edited or create:** Edit `L563-L635` (voice tab + `_run_voice_generation`) and add manual voice-parameter normalization around these functions.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **READ_LINES:** `L563-L635`

## Task 23

- **Task Name:** Add timeline-style batch authoring and render-queue management in studio
- **Coding logic of task and narrative design required:** Introduce a timeline/queue section where users can schedule multiple music/SFX/voice clips, define render order, and execute batch renders from the GUI.
- **Logic of how it functions in the program and design it must follow:** Queue items must persist in presets/new-file JSON and execute with explicit status tracking plus retry support.
- **Check to adhere to Final Fantasy aesthetics:** Enable layering and sequencing workflows needed for cinematic scenes and transitions.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **Line where code is to be edited or create:** Edit `L637-L852` (preset/load/save/new-file + batch actions) and create queue/timeline state handlers in this region.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **READ_LINES:** `L637-L852`

## Task 24

- **Task Name:** Upgrade preview panel into manual review workstation
- **Coding logic of task and narrative design required:** Add preview waveform/segment controls, loop in/out points, A/B compare slots, and per-asset approval tags directly in the GUI.
- **Logic of how it functions in the program and design it must follow:** Preview actions must operate on generated files and update project state without requiring terminal commands.
- **Check to adhere to Final Fantasy aesthetics:** Manual review should make it easy to tune loop transitions and cinematic timing.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **Line where code is to be edited or create:** Edit `L853-L942` (preview frame, playback controls, close handling) and add review/approval metadata hooks in this section.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/ui/studio.py`
- **READ_LINES:** `L853-L942`

## Task 25

- **Task Name:** Extend CLI studio command for full manual-GUI configuration
- **Coding logic of task and narrative design required:** Add studio CLI flags for startup preset, project template, output workspace, backend defaults, and GUI-mode feature toggles.
- **Logic of how it functions in the program and design it must follow:** Keep existing `studio` command backward compatible while exposing deterministic startup configuration for manual workflows.
- **Check to adhere to Final Fantasy aesthetics:** Startup presets should quickly route users to FF-style safe mood families and render profiles.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/cli.py`
- **Line where code is to be edited or create:** Edit `L191-L196` (`_cmd_studio`) and parser wiring around `build_parser` in `L978-L1941` to pass studio startup arguments.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/audio_engine/cli.py`
- **READ_LINES:** `L191-L196`, `L978-L1941`

## Task 26

- **Task Name:** Expand studio UI tests for complete manual-authoring workflows
- **Coding logic of task and narrative design required:** Add tests covering project/session persistence, manual control serialization, queue/timeline payloads, preview metadata, and CLI studio launch argument mapping.
- **Logic of how it functions in the program and design it must follow:** Tests must validate deterministic JSON payloads and guard against regressions in manual GUI-to-render parameter mapping.
- **Check to adhere to Final Fantasy aesthetics:** Validate that saved presets keep the intended mood/style-safe configuration values.
- **Name of the file to be edited or create:** `/tmp/workspace/Mikester9000/Audio-Engine/tests/test_studio_ui.py`
- **Line where code is to be edited or create:** Edit `L20-L150` existing serialization tests and append new coverage blocks after current final test.
- **READ_FILE:** `/tmp/workspace/Mikester9000/Audio-Engine/tests/test_studio_ui.py`
- **READ_LINES:** `L20-L150`

---

## Completion Criteria

A “fully developed program” for GameRewritten delivery means all of the following are true:

- Tasks 01-17 (core infrastructure/release-gate) are complete and validated.
- Tasks 27-39 (content expansion/full-game coverage) close assessment gaps documented in repo-root `/tmp/workspace/Mikester9000/Audio-Engine/assessment27.md` for (read this assessment before Phase B execution):
  - content expansion (music families, SFX breadth, ambience system),
  - runtime integration (region/state-aware music, ambience layering, transition intensity),
  - fixture expansion (including `generation_requests.ambience.v1.json`),
  - validation tracking (`FULL_GAME_AUDIO_CHECKLIST.md` updated against implemented reality).
  - measurable validation checkpoints: new fixture file exists and is schema-valid, runtime mapping files include the new family keys, and checklist sections for content/runtime/fixtures are marked complete only after implementation proof exists.
- Tasks 18-26 (manual GUI authoring) are complete for end-to-end manual production workflows.
- Task coverage totals 39 tasks with deterministic IDs 01-39 and phase ordering A -> B -> C.
