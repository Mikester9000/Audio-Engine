# Compact Execution Checklist

Purpose: Compact checklist for future use to complete the standalone audio editor/synth/mastering program roadmap.  
This checklist is single-file-edit-per-task and optimized for small coding models.

## Global instruction preface

- Edit exactly ONE file per task.
- No unrelated refactors.
- Preserve existing behavior unless task says otherwise.
- Prefer modular “lego style” additions.
- Use explicit validation and clear error messages.
- Return only patch content for the target file.

## Phased compact checklist (T-001 to T-014)

- **Task Number:** T-001  
  **Task Name:** Create canonical master task list doc  
  **File to edit (single file):** `docs/AI_FACTORY/TASKS/MASTER_TASK_LIST.md`  
  **Lines/section target:** New file (all lines)  
  **Purpose:** Create one canonical start-to-finish task source.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Create `docs/AI_FACTORY/TASKS/MASTER_TASK_LIST.md` with phase-ordered checkboxes, current status, and done criteria. Keep concise and deterministic. Return only patch content.”  
  **Additional user info:** Keep sections copy-paste friendly for weak local LLMs.

- **Task Number:** T-002  
  **Task Name:** Link master task list in AI index  
  **File to edit (single file):** `docs/AI_FACTORY/README.md`  
  **Lines/section target:** `Tracking and templates` list  
  **Purpose:** Make canonical task list discoverable.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `docs/AI_FACTORY/README.md`. Under `Tracking and templates`, add bullet for `TASKS/MASTER_TASK_LIST.md`. No other changes. Return only patch content.”  
  **Additional user info:** Single-line doc link only.

- **Task Number:** T-003  
  **Task Name:** Add Studio Project model helpers  
  **File to edit (single file):** `audio_engine/ui/studio.py`  
  **Lines/section target:** Helper-function area near existing state/preset helpers  
  **Purpose:** Add reusable project payload build/read/write helpers.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/ui/studio.py`. Add helper functions to build, save, and load studio project JSON with required-key validation and clear `ValueError` messages. Keep isolated and modular. Return only patch content.”  
  **Additional user info:** Use lego-style helper block; no broad refactor.

- **Task Number:** T-004  
  **Task Name:** Add Studio project save/load wiring  
  **File to edit (single file):** `audio_engine/ui/studio.py`  
  **Lines/section target:** Control-bar button setup and handlers  
  **Purpose:** Wire UI buttons to persist/restore project state.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/ui/studio.py`. Add `Save Project`/`Load Project` buttons and handlers using project helpers. Gracefully handle missing keys during restore and show status messages. Return only patch content.”  
  **Additional user info:** Depends on T-003 helpers.

- **Task Number:** T-005  
  **Task Name:** Add timeline data primitives  
  **File to edit (single file):** `audio_engine/ui/studio.py`  
  **Lines/section target:** Helper area near timeline/piano-roll data utilities  
  **Purpose:** Add pure clip constructors/validators/sorters for arranger data.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/ui/studio.py`. Add pure timeline helper functions for new clip creation, sorting, and validation with explicit numeric range checks. Return only patch content.”  
  **Additional user info:** Keep functions UI-independent and testable.

- **Task Number:** T-006  
  **Task Name:** Add Arranger tab skeleton UI  
  **File to edit (single file):** `audio_engine/ui/studio.py`  
  **Lines/section target:** Notebook tab construction area  
  **Purpose:** Add initial arranger UX shell and controls.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/ui/studio.py`. Add an `Arranger` tab with basic clip list controls and placeholder handlers (`Add Clip`, `Remove Clip`, `Render Arrangement`, `Play latest`) that update status text. Return only patch content.”  
  **Additional user info:** Depends on T-005 data primitives.

- **Task Number:** T-007  
  **Task Name:** Add SFX alias normalization  
  **File to edit (single file):** `audio_engine/ai/sfx_gen.py`  
  **Lines/section target:** `generate()` preprocessing area and helper block  
  **Purpose:** Normalize common aliases before SFX parsing for better hit rate.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/ai/sfx_gen.py`. Add deterministic alias-normalization helper and call it at the start of `generate()` before parser dispatch. No output format changes. Return only patch content.”  
  **Additional user info:** Keep alias map small and explicit.

- **Task Number:** T-008  
  **Task Name:** Add music style fallback tiers  
  **File to edit (single file):** `audio_engine/ai/prompt.py`  
  **Lines/section target:** `parse_music()` style-resolution block  
  **Purpose:** Improve style resolution with deterministic fallback tiers.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/ai/prompt.py` in `parse_music()`. Add 3-tier fallback: exact style keywords, mood-word mapping, default style fallback. Keep concise and deterministic. Return only patch content.”  
  **Additional user info:** Prioritize unambiguous mapping for small models.

- **Task Number:** T-009  
  **Task Name:** Add quick-create-pack CLI command  
  **File to edit (single file):** `audio_engine/cli.py`  
  **Lines/section target:** CLI parser/dispatch sections for commands  
  **Purpose:** One command to generate starter music+SFX pack quickly.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/cli.py`. Add `quick-create-pack` command, arguments (`theme`, `output-dir`, `music-count`, `sfx-count`, `format`, `seed`), handler wiring to existing generators, and manifest output. Return only patch content.”  
  **Additional user info:** Reuse existing generation paths; no new deps.

- **Task Number:** T-010  
  **Task Name:** Add mastering profile descriptions  
  **File to edit (single file):** `audio_engine/render/offline_bounce.py`  
  **Lines/section target:** Profile constants area  
  **Purpose:** Expose short plain-English profile guidance.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/render/offline_bounce.py`. Add profile-description map and getter function for existing profiles without changing DSP behavior. Return only patch content.”  
  **Additional user info:** Keep strings short and user-facing.

- **Task Number:** T-011  
  **Task Name:** Add optional OGG fallback mode  
  **File to edit (single file):** `audio_engine/export/audio_exporter.py`  
  **Lines/section target:** Exporter init and `_write_ogg()`  
  **Purpose:** Allow optional WAV fallback when OGG encoder dependency is missing.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/export/audio_exporter.py`. Add `allow_ogg_fallback_to_wav` flag. If OGG dependency missing and flag true, write WAV with same stem and return WAV path; otherwise keep current error behavior. Return only patch content.”  
  **Additional user info:** Preserve current default behavior.

- **Task Number:** T-012  
  **Task Name:** Add Studio contextual help panel  
  **File to edit (single file):** `audio_engine/ui/studio.py`  
  **Lines/section target:** Main layout/control-bar/tab context area  
  **Purpose:** Improve UX with in-app per-tab guidance panel.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `audio_engine/ui/studio.py`. Add collapsible contextual help panel with short instructions per tab and a `Show Help` toggle in control bar. Keep text concise. Return only patch content.”  
  **Additional user info:** User-friendly and intuitive navigation is a priority.

- **Task Number:** T-013  
  **Task Name:** Add tests for project save/load helpers  
  **File to edit (single file):** `tests/test_studio_ui.py`  
  **Lines/section target:** Append new unit tests near studio helper tests  
  **Purpose:** Verify project helper validation and JSON roundtrip behavior.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `tests/test_studio_ui.py`. Add tests for required-key validation, write/read roundtrip using `tmp_path`, and invalid JSON/project shape raising `ValueError`. Return only patch content.”  
  **Additional user info:** Run after T-003/T-004.

- **Task Number:** T-014  
  **Task Name:** Add tests for OGG fallback behavior  
  **File to edit (single file):** `tests/test_exporter.py`  
  **Lines/section target:** Append exporter fallback tests  
  **Purpose:** Verify optional fallback-on and fallback-off behavior.  
  **Compact prompt for qwen2.5 coder 0.5 instruct:** “Edit `tests/test_exporter.py`. Add tests for OGG dependency failure: fallback flag on returns WAV output, fallback flag off keeps ImportError. Use monkeypatch for failure simulation. Return only patch content.”  
  **Additional user info:** Run after T-011.

## Dependency and order

- **Order:** T-001, T-002, T-003, T-004, T-005, T-006, T-007, T-008, T-009, T-010, T-011, T-012, T-013, T-014
- **Notes:**
  - T-004 depends on T-003
  - T-006 depends on T-005
  - T-013 should run after T-003/T-004
  - T-014 should run after T-011

## Minimal verification checklist

- run targeted tests for touched files
- run full test suite: `python -m pytest`
- validate asset manifests: `python tools/validate-assets.py assets/examples/ --verbose` (and/or `python tools/validate-assets.py assets/ --verbose` when relevant)
