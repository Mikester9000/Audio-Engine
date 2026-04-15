--[[
  @file audio.lua
  @brief Audio integration for the Game Engine for Teaching.
  ============================================================================
  OVERVIEW
  ============================================================================

  This script extends the existing Lua hook system (main.lua, quests.lua,
  enemies.lua) with audio calls for every in-game event.

  Drop this file into the game engine's scripts/ directory and it will
  automatically wire itself into the hooks that C++ already calls.

  Requirements
  ------------
  1. The Audio Engine must have pre-generated all assets:
       audio-engine generate-game-assets --output-dir assets/audio

  2. The C++ AudioSystem must be wired up (see AudioSystem.hpp).

  3. The following Lua bindings must be registered in LuaEngine (see
     AudioSystem.hpp § "Register Lua bindings"):
       audio_play_sfx(event_key)      -- play a sound effect
       audio_play_music(filename)     -- switch music track directly
       audio_set_volume(0.0 – 1.0)   -- master volume
       audio_play_voice(key)          -- play a voiced line

  Usage
  -----
  The bindings are nil-safe: if the C++ audio system hasn't registered them
  (e.g. on a CI server with no audio device) every call is a no-op.

  ============================================================================
  TEACHING NOTE — Lua as a Scripting Glue Layer
  ============================================================================

  This script demonstrates how Lua can *extend* existing C++ callbacks
  without modifying the C++ source.  The C++ engine calls on_combat_start()
  at exactly one place; multiple Lua scripts can each augment that hook.

  In production engines (e.g. Unreal's Blueprint, Godot's GDScript) the same
  principle applies: the engine provides event hooks, and scripts react to them.
]]

-- ---------------------------------------------------------------------------
-- Audio module table (namespaced to avoid polluting the global scope)
-- ---------------------------------------------------------------------------
Audio = {}

-- ---------------------------------------------------------------------------
-- Nil-safe wrapper helpers
-- ---------------------------------------------------------------------------

---Play a sound effect.  No-op if the C++ binding is unavailable.
---@param eventKey string  Logical SFX key (e.g. "combat_hit", "level_up")
function Audio.PlaySFX(eventKey)
    if audio_play_sfx then
        audio_play_sfx(eventKey)
    end
end

---Play a music track by filename.
---@param filename string  e.g. "music_combat.wav"
function Audio.PlayMusic(filename)
    if audio_play_music then
        audio_play_music(filename)
    end
end

---Play a voiced narrator/character line.
---@param key string  e.g. "welcome", "level_up", "boss_intro"
function Audio.PlayVoice(key)
    if audio_play_voice then
        audio_play_voice(key)
    end
end

---Set the master volume (0.0 = silent, 1.0 = full).
---@param vol number
function Audio.SetVolume(vol)
    if audio_set_volume then
        audio_set_volume(vol)
    end
end

-- ---------------------------------------------------------------------------
-- Hook into on_explore_update (already defined in main.lua)
-- ---------------------------------------------------------------------------
-- We wrap the existing function rather than replacing it, so main.lua's
-- behaviour is preserved.

local _orig_on_explore_update = on_explore_update or function() end

function on_explore_update()
    _orig_on_explore_update()
    -- Footstep sound every N steps (cosmetic — feel free to adjust).
    -- The C++ side increments a step counter; Lua mirrors it here.
    if GameState and GameState.totalSteps and GameState.totalSteps % 8 == 0 then
        Audio.PlaySFX("footstep")
    end
end

-- ---------------------------------------------------------------------------
-- Hook into on_combat_start
-- ---------------------------------------------------------------------------
--[[
  TEACHING NOTE — Augmenting hooks
  When C++ calls on_combat_start(enemyName), both the original main.lua
  implementation AND this audio extension run.  This is possible because
  we wrap the original function.
]]

local _orig_on_combat_start = on_combat_start or function() end

function on_combat_start(enemyName)
    _orig_on_combat_start(enemyName)

    -- Play combat voice line then switch to combat music.
    Audio.PlayVoice("combat_start")
    Audio.PlayMusic("music_combat.wav")

    -- Boss fight detection: if the enemy name contains "Boss" or "Dragon"
    -- or other boss keywords, switch to the boss music track.
    local name = tostring(enemyName or ""):lower()
    if name:find("boss") or name:find("dragon") or
       name:find("emperor") or name:find("demon") or
       name:find("final") then
        Audio.PlayMusic("music_boss_combat.wav")
        Audio.PlayVoice("boss_intro")
    end
end

-- ---------------------------------------------------------------------------
-- Hook into on_camp_rest
-- ---------------------------------------------------------------------------

local _orig_on_camp_rest = on_camp_rest or function() end

function on_camp_rest()
    _orig_on_camp_rest()
    Audio.PlaySFX("camp_fire")
    Audio.PlayVoice("camp_rest")
    Audio.PlayMusic("music_camping.wav")
end

-- ---------------------------------------------------------------------------
-- Hook into on_level_up
-- ---------------------------------------------------------------------------

local _orig_on_level_up = on_level_up or function() end

function on_level_up(newLevel)
    _orig_on_level_up(newLevel)
    Audio.PlaySFX("level_up")
    Audio.PlayVoice("level_up")
end

-- ---------------------------------------------------------------------------
-- New hooks (add calls from C++ when the corresponding events fire)
-- ---------------------------------------------------------------------------

---Called by C++ when a quest is completed.
---Wire up in QuestSystem::CompleteQuest() with:
---  m_lua.CallVoid("on_quest_complete", questID)
function on_quest_complete(questID)
    Audio.PlaySFX("quest_complete")
    Audio.PlayVoice("quest_complete")
end

---Called by C++ when the player opens a shop.
function on_shop_open()
    Audio.PlayMusic("music_shopping.wav")
    Audio.PlaySFX("ui_open")
end

---Called by C++ when the player buys an item.
function on_shop_buy()
    Audio.PlaySFX("shop_buy")
end

---Called by C++ when the player opens the inventory.
function on_inventory_open()
    Audio.PlayMusic("music_inventory.wav")
    Audio.PlaySFX("ui_open")
end

---Called by C++ when the player casts a spell.
---@param spellID  integer  The spell's ID from GameData.
function on_spell_cast(spellID)
    -- Generic spell SFX; extend with per-spell logic as needed.
    Audio.PlaySFX("spell_cast")
end

---Called by C++ when the player uses a warp strike.
function on_warp_strike()
    Audio.PlaySFX("warp_strike")
end

---Called by C++ when a link strike fires.
function on_link_strike()
    Audio.PlaySFX("link_strike")
end

---Called by C++ when weather changes.
function on_weather_change(weatherType)
    Audio.PlaySFX("weather_wind")
end

-- ---------------------------------------------------------------------------
-- Game-start welcome voice
-- ---------------------------------------------------------------------------
-- Play the welcome narrator line once when the game transitions from
-- MAIN_MENU to EXPLORING for the first time.

Audio._welcomePlayed = false

local _orig_on_explore_update_audio = on_explore_update

function on_explore_update()
    _orig_on_explore_update_audio()
    if not Audio._welcomePlayed then
        Audio.PlayVoice("welcome")
        Audio._welcomePlayed = true
    end
end

-- ---------------------------------------------------------------------------
-- Startup confirmation
-- ---------------------------------------------------------------------------
if engine_log then
    engine_log("[Lua/audio.lua] Audio integration loaded.")
end
