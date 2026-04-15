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
)


# ---------------------------------------------------------------------------
# SFX manifest – one entry per named in-game event
# ---------------------------------------------------------------------------

SFX_MANIFEST: tuple[SFXAsset, ...] = (
    # --- Combat ---
    SFXAsset("combat_hit",      "sfx_combat_hit.wav",      "sword metallic impact clang",      0.3),
    SFXAsset("combat_miss",     "sfx_combat_miss.wav",     "whoosh blade swipe air",           0.3),
    SFXAsset("combat_critical", "sfx_combat_critical.wav", "impact explosion heavy",           0.4),
    SFXAsset("warp_strike",     "sfx_warp_strike.wav",     "warp whoosh teleport blade slash", 0.8),
    SFXAsset("link_strike",     "sfx_link_strike.wav",     "impact sword heavy slam",          0.5),
    SFXAsset("combat_victory",  "sfx_combat_victory.wav",  "short jingle fanfare win",         1.5),
    SFXAsset("combat_defeat",   "sfx_combat_defeat.wav",   "low ominous tone fail",            2.0),

    # --- Magic ---
    SFXAsset("spell_cast",      "sfx_spell_cast.wav",      "magic spell arcane energy",        0.6),
    SFXAsset("spell_fire",      "sfx_spell_fire.wav",      "fire explosion burst",             0.7),
    SFXAsset("spell_ice",       "sfx_spell_ice.wav",       "ice crystal shatter freeze",       0.6),
    SFXAsset("spell_thunder",   "sfx_spell_thunder.wav",   "thunder lightning crack",          0.8),

    # --- Player / inventory ---
    SFXAsset("level_up",        "sfx_level_up.wav",        "magic ascending sparkle power up", 1.5),
    SFXAsset("item_pickup",     "sfx_item_pickup.wav",     "coin collect item",                0.3),
    SFXAsset("item_use",        "sfx_item_use.wav",        "magic potion glug heal",           0.5),
    SFXAsset("equip_weapon",    "sfx_equip_weapon.wav",    "metallic sword equip click",       0.3),

    # --- Economy ---
    SFXAsset("shop_buy",        "sfx_shop_buy.wav",        "coin purchase transaction",        0.4),
    SFXAsset("shop_sell",       "sfx_shop_sell.wav",       "coin drop transaction",            0.3),

    # --- World / exploration ---
    SFXAsset("footstep",        "sfx_footstep.wav",        "footstep stone",                   0.2),
    SFXAsset("camp_fire",       "sfx_camp_fire.wav",       "fire crackle ambient",             3.0),
    SFXAsset("weather_wind",    "sfx_weather_wind.wav",    "wind gust ambient",                2.0),
    SFXAsset("weather_rain",    "sfx_weather_rain.wav",    "rain ambient drops",               3.0),
    SFXAsset("door_open",       "sfx_door_open.wav",       "door creak open wood",             0.5),
    SFXAsset("door_close",      "sfx_door_close.wav",      "door close thud wood",             0.4),

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
