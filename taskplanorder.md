# Task Plan Order

Absolute repository paths are used intentionally in this file because the task explicitly required repository file references to use absolute paths.

This file now extends the canonical task plan instead of duplicating it. Tasks 01–17 remain canonical in the repo-root `Task_List.md` (local clone: `/tmp/workspace/Mikester9000/Audio-Engine/Task_List.md`). This document only appends the Studio GUI follow-up tasks 18–26.

---

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
