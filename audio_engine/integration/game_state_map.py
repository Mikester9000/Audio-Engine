"""
game_state_map.py – mapping of Game Engine for Teaching states to audio assets.

This module defines the canonical mapping between:
  - ``GameState`` enum values (from ``src/engine/core/Types.hpp``)
  - Music tracks to generate and their Audio Engine style / prompt
  - SFX events and their generation prompts
  - Voice lines for narrative moments

The mapping was derived by inspecting:
  - ``src/engine/core/Types.hpp``  (GameState enum)
  - ``src/game/Game.hpp``          (per-state Update/Render methods)
  - ``src/game/systems/``          (CombatSystem, CampSystem, QuestSystem …)
  - ``scripts/main.lua``           (existing Lua hooks)

Keeping the map here (rather than hard-coding in the pipeline) makes it
easy to extend when new states or SFX events are added to the game engine.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MusicAsset:
    """A music track that should be generated for one game state.

    Parameters
    ----------
    game_state:
        The ``GameState`` enum name from the C++ engine (e.g. ``"EXPLORING"``).
    filename:
        Output WAV filename (no directory prefix).
    style:
        AudioEngine style shorthand used by ``MusicGen`` when no richer prompt
        is available.
    prompt:
        Full natural-language generation prompt.
    duration:
        Target duration in seconds.
    loopable:
        Whether to embed WAV loop-point metadata for seamless game-engine looping.
    """

    game_state: str
    filename: str
    style: str
    prompt: str
    duration: float
    loopable: bool = True


@dataclass(frozen=True)
class SFXAsset:
    """A sound effect tied to a specific in-game event.

    Parameters
    ----------
    event:
        Logical event name used as the key in the C++ ``AudioSystem``.
    filename:
        Output WAV filename.
    prompt:
        Free-form description passed to ``SFXGen``.
    duration:
        Target duration in seconds.
    pitch_hz:
        Optional base pitch.  ``None`` = use SFX default.
    """

    event: str
    filename: str
    prompt: str
    duration: float
    pitch_hz: float | None = None


@dataclass(frozen=True)
class VoiceAsset:
    """A voiced narrator / character line.

    Parameters
    ----------
    key:
        Logical key (used as the Lua-callable name).
    filename:
        Output WAV filename.
    text:
        Text to synthesise.
    voice:
        Voice preset: ``"narrator"``, ``"hero"``, ``"villain"``,
        ``"announcer"``, or ``"npc"``.
    """

    key: str
    filename: str
    text: str
    voice: str = "narrator"


# ---------------------------------------------------------------------------
# Music manifest – one entry per distinct GameState or named scene
# ---------------------------------------------------------------------------
# GameState values from Types.hpp:
#   MAIN_MENU, EXPLORING, COMBAT, DIALOGUE, VEHICLE
# Implied states from Game.hpp Update* methods:
#   INVENTORY, SHOPPING, CAMPING
# Extra "named scene" tracks (not a direct state, but used in-game):
#   BOSS_COMBAT, VICTORY

MUSIC_MANIFEST: tuple[MusicAsset, ...] = (
    MusicAsset(
        game_state="MAIN_MENU",
        filename="music_main_menu.wav",
        style="menu",
        prompt="calm introspective piano main menu RPG 80 BPM loopable",
        duration=60.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="EXPLORING",
        filename="music_exploring.wav",
        style="exploration",
        prompt="open world adventure exploration orchestral 90 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="COMBAT",
        filename="music_combat.wav",
        style="battle",
        prompt="intense action combat orchestra brass strings 140 BPM loopable",
        duration=60.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="BOSS_COMBAT",
        filename="music_boss_combat.wav",
        style="boss",
        prompt="epic climactic boss battle full orchestra electric guitar 160 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="DIALOGUE",
        filename="music_dialogue.wav",
        style="ambient",
        prompt="gentle atmospheric dialogue scene ambient strings piano 70 BPM loopable",
        duration=60.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="VEHICLE",
        filename="music_vehicle.wav",
        style="exploration",
        prompt="driving journey open road synth brass adventure 100 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="CAMPING",
        filename="music_camping.wav",
        style="ambient",
        prompt="cosy camp night sky fire ambient peaceful acoustic 60 BPM loopable",
        duration=60.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="INVENTORY",
        filename="music_inventory.wav",
        style="menu",
        prompt="soft menu inventory browsing crystal piano 75 BPM loopable",
        duration=45.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="SHOPPING",
        filename="music_shopping.wav",
        style="menu",
        prompt="lively town market shopping piano strings 85 BPM loopable",
        duration=45.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="VICTORY",
        filename="music_victory.wav",
        style="victory",
        prompt="triumphant victory fanfare brass orchestra major key 120 BPM",
        duration=15.0,
        loopable=False,
    ),
    MusicAsset(
        game_state="DUNGEON",
        filename="music_dungeon.wav",
        style="dungeon",
        prompt="mysterious dungeon traversal with eerie pads and sparse percussion 72 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="TENSION_STEALTH",
        filename="music_tension_stealth.wav",
        style="tension",
        prompt="low-intensity stealth underscore with pulsing bass and subtle strings 80 BPM loopable",
        duration=60.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="SADNESS_MEMORIAL",
        filename="music_sadness_memorial.wav",
        style="ff7_sad",
        prompt="somber memorial cue with piano and strings, restrained emotional arc",
        duration=90.0,
        loopable=False,
    ),
    MusicAsset(
        game_state="MYSTERY_PUZZLE",
        filename="music_mystery_puzzle.wav",
        style="ambient",
        prompt="mystery puzzle ambience with celesta motifs and uncertain harmony 68 BPM loopable",
        duration=75.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="CUTSCENE_UNDERSCORE",
        filename="music_cutscene_underscore.wav",
        style="ambient",
        prompt="cinematic story cutscene underscore with soft orchestra and emotional contour",
        duration=90.0,
        loopable=False,
    ),
    MusicAsset(
        game_state="CUTSCENE_STINGER_REVEAL",
        filename="music_cutscene_stinger_reveal.wav",
        style="victory",
        prompt="short dramatic reveal stinger with brass impact and choir accent",
        duration=4.0,
        loopable=False,
    ),
    MusicAsset(
        game_state="ENDING_CREDITS",
        filename="music_ending_credits.wav",
        style="prelude",
        prompt="final credits orchestral suite with hopeful closure and expansive melody",
        duration=210.0,
        loopable=False,
    ),
    MusicAsset(
        game_state="TITLE_SCREEN_LONG",
        filename="music_title_screen_long.wav",
        style="prelude",
        prompt="long-form title theme with piano arpeggios and orchestral swell",
        duration=180.0,
        loopable=False,
    ),
    MusicAsset(
        game_state="EXPLORING_PLAINS",
        filename="music_exploring_plains.wav",
        style="exploration",
        prompt="open plains exploration with bright strings and heroic motion 92 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="EXPLORING_FOREST",
        filename="music_exploring_forest.wav",
        style="exploration",
        prompt="forest exploration with woodwinds and shimmering strings 88 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="EXPLORING_COAST",
        filename="music_exploring_coast.wav",
        style="exploration",
        prompt="coastal exploration with airy pads and rolling rhythm 86 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="EXPLORING_ARID",
        filename="music_exploring_arid.wav",
        style="world_map",
        prompt="arid frontier exploration with sparse percussion and distant strings 84 BPM loopable",
        duration=90.0,
        loopable=True,
    ),
    MusicAsset(
        game_state="BATTLE_INTRO",
        filename="music_battle_intro.wav",
        style="battle",
        prompt="short transition intro sting with immediate orchestral hit and rising stakes",
        duration=3.0,
        loopable=False,
    ),
    MusicAsset(
        game_state="BATTLE_END",
        filename="music_battle_end.wav",
        style="victory",
        prompt="short battle end resolution cue with concise triumphant cadence",
        duration=3.0,
        loopable=False,
    ),
)


# ---------------------------------------------------------------------------
# SFX manifest – one entry per named in-game event
# ---------------------------------------------------------------------------

SFX_MANIFEST: tuple[SFXAsset, ...] = (
    # --- Combat ---
    SFXAsset("combat_hit",      "sfx_combat_hit.wav",      "sword metallic impact clang",      0.3),
    SFXAsset("combat_miss",     "sfx_combat_miss.wav",     "whoosh blade swipe air",           0.3),
    SFXAsset("combat_critical", "sfx_combat_critical.wav", "impact explosion heavy",           0.4),
    SFXAsset("melee_swing",     "sfx_melee_swing.wav",     "fast melee swing whoosh",          0.25),
    SFXAsset("melee_hit_light", "sfx_melee_hit_light.wav", "light melee hit impact",           0.25),
    SFXAsset("melee_hit_medium","sfx_melee_hit_medium.wav","medium melee hit impact",          0.3),
    SFXAsset("melee_hit_heavy", "sfx_melee_hit_heavy.wav", "heavy melee hit impact",           0.4),
    SFXAsset("block_parry",     "sfx_block_parry.wav",     "metallic block parry ring",        0.25),
    SFXAsset("dodge_evade",     "sfx_dodge_evade.wav",     "quick dodge evade whoosh",         0.22),
    SFXAsset("damage_taken",    "sfx_damage_taken.wav",    "character damage taken thud",      0.25),
    SFXAsset("critical_hit",    "sfx_critical_hit.wav",    "critical hit impact flare",        0.35),
    SFXAsset("enemy_defeat",    "sfx_enemy_defeat.wav",    "enemy defeat collapse burst",      0.6),
    SFXAsset("player_defeat",   "sfx_player_defeat.wav",   "player defeat collapse and low end", 0.8),
    SFXAsset("warp_strike",     "sfx_warp_strike.wav",     "warp whoosh teleport blade slash", 0.8),
    SFXAsset("link_strike",     "sfx_link_strike.wav",     "impact sword heavy slam",          0.5),
    SFXAsset("combat_victory",  "sfx_combat_victory.wav",  "short jingle fanfare win",         1.5),
    SFXAsset("combat_defeat",   "sfx_combat_defeat.wav",   "low ominous tone fail",            2.0),

    # --- Magic ---
    SFXAsset("spell_cast",      "sfx_spell_cast.wav",      "magic spell arcane energy",        0.6),
    SFXAsset("spell_fire",      "sfx_spell_fire.wav",      "fire explosion burst",             0.7),
    SFXAsset("spell_fire_hit",  "sfx_spell_fire_hit.wav",  "fire spell impact burst",          0.6),
    SFXAsset("spell_fire_loop", "sfx_spell_fire_loop.wav", "sustained fire spell burn loop",   1.2),
    SFXAsset("spell_ice",       "sfx_spell_ice.wav",       "ice crystal shatter freeze",       0.6),
    SFXAsset("spell_ice_shatter","sfx_spell_ice_shatter.wav","ice shatter crack and scatter", 0.7),
    SFXAsset("spell_thunder",   "sfx_spell_thunder.wav",   "thunder lightning crack",          0.8),
    SFXAsset("spell_wind_cast", "sfx_spell_wind_cast.wav", "wind spell cast swirl",            0.6),
    SFXAsset("spell_earth_quake","sfx_spell_earth_quake.wav","earth quake spell rumble",       0.8),
    SFXAsset("spell_water_heal","sfx_spell_water_heal.wav","water healing spell chime",        0.7),
    SFXAsset("spell_holy_light","sfx_spell_holy_light.wav","holy light spell chime",           0.8),
    SFXAsset("spell_dark_curse","sfx_spell_dark_curse.wav","dark curse spell drone",           0.9),
    SFXAsset("spell_buff_shield","sfx_spell_buff_shield.wav","buff shield aura rise",          0.65),
    SFXAsset("spell_debuff_poison","sfx_spell_debuff_poison.wav","poison debuff hiss",         0.7),
    SFXAsset("spell_summon_charge","sfx_spell_summon_charge.wav","summon charge energy build", 2.4),

    # --- Player / inventory ---
    SFXAsset("level_up",        "sfx_level_up.wav",        "magic ascending sparkle power up", 1.5),
    SFXAsset("item_pickup",     "sfx_item_pickup.wav",     "coin collect item",                0.3),
    SFXAsset("item_use",        "sfx_item_use.wav",        "magic potion glug heal",           0.5),
    SFXAsset("equip_weapon",    "sfx_equip_weapon.wav",    "metallic sword equip click",       0.3),

    # --- Economy ---
    SFXAsset("shop_buy",        "sfx_shop_buy.wav",        "coin purchase transaction",        0.4),
    SFXAsset("shop_sell",       "sfx_shop_sell.wav",       "coin drop transaction",            0.3),
    SFXAsset("crafting_success","sfx_crafting_success.wav","crafting success sparkle chime",   0.6),

    # --- World / exploration ---
    SFXAsset("footstep",        "sfx_footstep.wav",        "footstep stone",                   0.2),
    SFXAsset("footstep_grass_var01","sfx_footstep_grass_var01.wav","footstep grass variant",   0.2),
    SFXAsset("footstep_dirt_var01", "sfx_footstep_dirt_var01.wav", "footstep dirt variant",    0.2),
    SFXAsset("footstep_stone_var01","sfx_footstep_stone_var01.wav","footstep stone variant",   0.2),
    SFXAsset("footstep_wood_var01", "sfx_footstep_wood_var01.wav", "footstep wood variant",    0.2),
    SFXAsset("footstep_metal_var01","sfx_footstep_metal_var01.wav","footstep metal variant",   0.2),
    SFXAsset("footstep_water_var01","sfx_footstep_water_var01.wav","footstep shallow water variant", 0.22),
    SFXAsset("jump",            "sfx_jump.wav",            "character jump rise",              0.22),
    SFXAsset("land",            "sfx_land.wav",            "character landing impact",         0.24),
    SFXAsset("mount_vehicle",   "sfx_mount_vehicle.wav",   "mount or vehicle engage",          0.4),
    SFXAsset("camp_fire",       "sfx_camp_fire.wav",       "fire crackle ambient",             3.0),
    SFXAsset("weather_wind",    "sfx_weather_wind.wav",    "wind gust ambient",                2.0),
    SFXAsset("weather_rain",    "sfx_weather_rain.wav",    "rain ambient drops",               3.0),
    SFXAsset("door_open",       "sfx_door_open.wav",       "door creak open wood",             0.5),
    SFXAsset("door_close",      "sfx_door_close.wav",      "door close thud wood",             0.4),
    SFXAsset("chest_open",      "sfx_chest_open.wav",      "treasure chest open creak and click", 0.6),
    SFXAsset("chest_close",     "sfx_chest_close.wav",     "treasure chest close thud",        0.45),
    SFXAsset("lever_pull",      "sfx_lever_pull.wav",      "mechanical lever pull clunk",      0.55),
    SFXAsset("breakable_object","sfx_breakable_object.wav","breakable object shatter",         0.65),
    SFXAsset("dialogue_blip",   "sfx_dialogue_blip.wav",   "dialogue text blip",               0.08),

    # --- Quests ---
    SFXAsset("quest_accept",    "sfx_quest_accept.wav",    "short fanfare quest begin",        0.8),
    SFXAsset("quest_complete",  "sfx_quest_complete.wav",  "fanfare quest complete reward",    1.5),
    SFXAsset("quest_fail",      "sfx_quest_fail.wav",      "low tone failure",                 0.8),

    # --- UI ---
    SFXAsset("ui_confirm",      "sfx_ui_confirm.wav",      "click select confirm",             0.15),
    SFXAsset("ui_cancel",       "sfx_ui_cancel.wav",       "click cancel back",                0.15),
    SFXAsset("ui_open",         "sfx_ui_open.wav",         "menu whoosh open",                 0.25),
    SFXAsset("ui_close",        "sfx_ui_close.wav",        "menu whoosh close",                0.25),
    SFXAsset("ui_scroll",       "sfx_ui_scroll.wav",       "click tick scroll",                0.1),
    SFXAsset("transition_whoosh_scene","sfx_transition_whoosh_scene.wav","scene transition whoosh", 0.6),
    SFXAsset("transition_battle_start","sfx_transition_battle_start.wav","battle start sting transition", 0.8),
    SFXAsset("transition_battle_end","sfx_transition_battle_end.wav","battle end sting transition", 0.6),
    SFXAsset("transition_teleport_warp","sfx_transition_teleport_warp.wav","teleport warp transition", 0.9),
    SFXAsset("transition_respawn_revive","sfx_transition_respawn_revive.wav","respawn revive stinger", 0.9),
)


# ---------------------------------------------------------------------------
# Ambience / fanfare / transition extension manifests
# ---------------------------------------------------------------------------

AMBIENCE_MANIFEST: tuple[SFXAsset, ...] = (
    SFXAsset("ambience_town", "sfx_ambience_town.wav", "town ambience with distant crowd", 20.0),
    SFXAsset("ambience_forest", "sfx_ambience_forest.wav", "forest ambience with wind and leaves", 22.0),
    SFXAsset("ambience_cave", "sfx_ambience_cave.wav", "cave ambience with low rumble and drips", 20.0),
    SFXAsset("ambience_dungeon", "sfx_ambience_dungeon.wav", "dungeon ambience with eerie drones", 20.0),
    SFXAsset("ambience_interior_room_tone", "sfx_ambience_interior_room_tone.wav", "interior room tone subtle hum", 18.0),
    SFXAsset("ambience_wind_weather", "sfx_ambience_wind_weather.wav", "wind weather loop", 18.0),
    SFXAsset("ambience_rain_weather", "sfx_ambience_rain_weather.wav", "rain weather loop", 18.0),
    SFXAsset("ambience_storm_thunder", "sfx_ambience_storm_thunder.wav", "storm and thunder ambience", 18.0),
    SFXAsset("ambience_river_water", "sfx_ambience_river_water.wav", "river water ambience", 20.0),
    SFXAsset("ambience_fire_torch", "sfx_ambience_fire_torch.wav", "torch fire ambience", 18.0),
    SFXAsset("ambience_magical_shrine", "sfx_ambience_magical_shrine.wav", "magical shrine ambience", 18.0),
)

FANFARE_MANIFEST: tuple[SFXAsset, ...] = (
    SFXAsset("fanfare_item_obtain", "sfx_fanfare_item_obtain.wav", "item obtain fanfare", 4.0),
    SFXAsset("fanfare_quest_complete", "sfx_fanfare_quest_complete.wav", "quest complete fanfare", 5.0),
    SFXAsset("fanfare_secret_discovered", "sfx_fanfare_secret_discovered.wav", "secret discovered fanfare", 4.0),
    SFXAsset("fanfare_chapter_start", "sfx_fanfare_chapter_start.wav", "chapter start fanfare", 5.0),
    SFXAsset("fanfare_chapter_end", "sfx_fanfare_chapter_end.wav", "chapter end fanfare", 5.0),
    SFXAsset("fanfare_fail_game_over", "sfx_fanfare_fail_game_over.wav", "fail game over fanfare", 4.0),
    SFXAsset("fanfare_crafting_upgrade", "sfx_fanfare_crafting_upgrade.wav", "crafting upgrade fanfare", 4.0),
)

TRANSITION_MANIFEST: tuple[SFXAsset, ...] = (
    SFXAsset("transition_scene_whoosh", "sfx_transition_scene_whoosh.wav", "scene transition whoosh", 0.7),
    SFXAsset("transition_battle_start_alt", "sfx_transition_battle_start_alt.wav", "battle start transition sting", 0.8),
    SFXAsset("transition_battle_end_alt", "sfx_transition_battle_end_alt.wav", "battle end transition sting", 0.7),
    SFXAsset("transition_fade_helper", "sfx_transition_fade_helper.wav", "fade helper transition", 0.5),
    SFXAsset("transition_teleport_warp_alt", "sfx_transition_teleport_warp_alt.wav", "teleport warp transition", 0.9),
    SFXAsset("transition_respawn_revive_alt", "sfx_transition_respawn_revive_alt.wav", "respawn revive transition", 0.9),
)


# ---------------------------------------------------------------------------
# Voice manifest – narrator / character lines
# ---------------------------------------------------------------------------

VOICE_MANIFEST: tuple[VoiceAsset, ...] = (
    VoiceAsset("welcome",       "voice_welcome.wav",
               "Welcome, adventurer. Your destiny awaits.", "narrator"),
    VoiceAsset("level_up",      "voice_level_up.wav",
               "You have grown stronger.", "narrator"),
    VoiceAsset("game_over",     "voice_game_over.wav",
               "Your journey has ended here. Rise again.", "narrator"),
    VoiceAsset("boss_intro",    "voice_boss_intro.wav",
               "A powerful enemy approaches!", "narrator"),
    VoiceAsset("camp_rest",     "voice_camp_rest.wav",
               "Rest, and face tomorrow with renewed strength.", "narrator"),
    VoiceAsset("quest_complete","voice_quest_complete.wav",
               "Quest complete! Your deeds will be remembered.", "announcer"),
    VoiceAsset("combat_low_hp", "voice_combat_low_hp.wav",
               "Danger! We are near the brink!", "hero"),
    VoiceAsset("combat_start",  "voice_combat_start.wav",
               "Engage! Fight with everything you have!", "hero"),
    VoiceAsset("villain_intro", "voice_villain_intro.wav",
               "You think you can defeat me? Pathetic.", "villain"),
)
