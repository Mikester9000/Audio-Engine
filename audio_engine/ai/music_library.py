"""
Music Library — catalog of all Final Fantasy and generic styles.

This module provides:

* :data:`FF_RADIO_CATALOG` — the complete FF1–FF16 catalog, organized by
  game and track type, for the ``ff15_radio`` experience.

* :class:`MusicLibrary` — query, filter, and retrieve style metadata.
  Answers questions like "what battle themes are available?", "list all
  FF7 tracks", "give me something slow and emotional".

* :func:`style_for_request` — natural-language → style-name resolution
  beyond what the prompt parser handles (e.g. "to zanarkand", "aria de
  mezzo", "eyes on me", "blinded by light").

Usage
-----
>>> from audio_engine.ai.music_library import MusicLibrary
>>> catalog = MusicLibrary()
>>> ff7_tracks = catalog.by_game("ff7")
>>> battle_tracks = catalog.by_type("battle")
>>> style = catalog.style_for_request("something sad and slow with piano")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

__all__ = [
    "MusicLibrary",
    "TrackEntry",
    "FF_RADIO_CATALOG",
    "style_for_request",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TrackEntry:
    """Metadata entry for one track in the music library.

    Attributes
    ----------
    style_key:
        The engine style key (matches a key in ``_STYLE_DEFS``).
    display_name:
        Human-readable track title for display / export filenames.
    game:
        Game abbreviation: ``"ff1"`` … ``"ff16"``, or ``"generic"``.
    game_full:
        Full game title string.
    track_type:
        Category: ``"battle"``, ``"overworld"``, ``"theme"``, ``"ballad"``,
        ``"ambient"``, ``"boss"``, ``"fanfare"``, ``"opera"``, ``"radio"``.
    bpm_approx:
        Approximate BPM for reference.
    key_mood:
        Short mood descriptor: ``"epic"``, ``"sad"``, ``"tense"``, etc.
    with_vocals:
        Whether this track is typically performed with vocals.
    composer:
        Primary composer name (Uematsu, Hamauzu, Soken, etc.).
    export_filename:
        Suggested base filename (no extension) for export.
    tags:
        Free-form searchable tags.
    """
    style_key: str
    display_name: str
    game: str
    game_full: str
    track_type: str
    bpm_approx: int
    key_mood: str
    with_vocals: bool = False
    composer: str = "Nobuo Uematsu"
    export_filename: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.export_filename:
            self.export_filename = self.style_key.replace("_", "-")


# ---------------------------------------------------------------------------
# Full catalog — FF Radio playlist (FF1–FF16) + generic
# ---------------------------------------------------------------------------

FF_RADIO_CATALOG: list[TrackEntry] = [

    # ---- FF1 (NES, 1987) -------------------------------------------------
    TrackEntry("ff1_battle",   "Battle Theme I",          "ff1", "Final Fantasy",           "battle",   150, "intense",   False, "Nobuo Uematsu", "ff1-battle",       ["nes", "retro", "battle", "square-wave"]),
    TrackEntry("ff1_overworld","Main Theme",               "ff1", "Final Fantasy",           "overworld", 110, "adventurous",False,"Nobuo Uematsu","ff1-overworld",    ["nes", "retro", "overworld", "hopeful"]),

    # ---- FF4 (SNES, 1991) ------------------------------------------------
    TrackEntry("ff4_battle",   "Fight 1",                  "ff4", "Final Fantasy IV",        "battle",   136, "urgent",    False, "Nobuo Uematsu", "ff4-battle",       ["snes", "retro", "battle", "minor"]),
    TrackEntry("ff4_theme",    "Main Theme of FFIV",       "ff4", "Final Fantasy IV",        "theme",     96, "heroic",    False, "Nobuo Uematsu", "ff4-theme",        ["snes", "orchestral", "heroic", "major"]),

    # ---- FF6 (SNES, 1994) ------------------------------------------------
    TrackEntry("ff6_battle",   "The Decisive Battle",      "ff6", "Final Fantasy VI",        "battle",   148, "dramatic",  False, "Nobuo Uematsu", "ff6-decisive-battle", ["snes", "battle", "boss", "dissonant"]),
    TrackEntry("ff6_opera",    "Aria di Mezzo Carattere",  "ff6", "Final Fantasy VI",        "opera",     80, "romantic",  True,  "Nobuo Uematsu", "ff6-aria",         ["opera", "ballad", "vocals", "classical", "sad"]),
    TrackEntry("ff6_sad",      "Terra's Theme",            "ff6", "Final Fantasy VI",        "theme",     70, "melancholy",False, "Nobuo Uematsu", "ff6-terra-theme",  ["sad", "emotional", "minor", "piano", "strings"]),

    # ---- FF7 (PS1, 1997) -------------------------------------------------
    TrackEntry("ff7_battle",   "Let the Battles Begin!",   "ff7", "Final Fantasy VII",       "battle",   132, "intense",   False, "Nobuo Uematsu", "ff7-battle",       ["ps1", "battle", "minor", "iconic"]),
    TrackEntry("ff7_overworld","Main Theme of FF7",        "ff7", "Final Fantasy VII",       "overworld",  84, "nostalgic", False, "Nobuo Uematsu", "ff7-main-theme",   ["ps1", "overworld", "emotional", "iconic"]),
    TrackEntry("ff7_boss",     "J-E-N-O-V-A",             "ff7", "Final Fantasy VII",        "boss",      132, "tense",    False, "Nobuo Uematsu", "ff7-jenova",       ["ps1", "boss", "intense", "sci-fi"]),
    TrackEntry("ff7_sad",      "Aerith's Theme",           "ff7", "Final Fantasy VII",       "theme",      65, "sad",      False, "Nobuo Uematsu", "ff7-aerith-theme", ["ps1", "sad", "emotional", "piano", "strings", "iconic"]),
    TrackEntry("ff7_town",     "Tifa's Theme",             "ff7", "Final Fantasy VII",       "theme",      80, "warm",     False, "Nobuo Uematsu", "ff7-tifa-theme",   ["ps1", "town", "warm", "piano", "gentle"]),

    # ---- FF8 (PS1, 1999) -------------------------------------------------
    TrackEntry("ff8_battle",   "Don't Be Afraid",          "ff8", "Final Fantasy VIII",      "battle",    140, "driving",   False, "Nobuo Uematsu", "ff8-dont-be-afraid",  ["ps1", "battle", "rock", "electric-guitar"]),
    TrackEntry("ff8_ballad",   "Eyes on Me",               "ff8", "Final Fantasy VIII",      "ballad",     74, "romantic",  True,  "Nobuo Uematsu", "ff8-eyes-on-me",   ["ps1", "ballad", "vocals", "romantic", "iconic", "piano"]),

    # ---- FF9 (PS1, 2000) -------------------------------------------------
    TrackEntry("ff9_battle",   "Battle 1",                 "ff9", "Final Fantasy IX",        "battle",    140, "energetic", False, "Nobuo Uematsu", "ff9-battle",       ["ps1", "battle", "classic"]),
    TrackEntry("ff9_overworld","Crossing Those Hills",     "ff9", "Final Fantasy IX",        "overworld",  88, "nostalgic", False, "Nobuo Uematsu", "ff9-crossing-hills",["ps1","overworld","warm","nostalgic"]),

    # ---- FF10 (PS2, 2001) ------------------------------------------------
    TrackEntry("ff10_zanarkand","To Zanarkand",            "ff10","Final Fantasy X",          "theme",     70, "melancholy",False, "Nobuo Uematsu", "ff10-to-zanarkand",["ps2", "piano", "sad", "iconic", "solo", "emotional"]),
    TrackEntry("ff10_calm",    "Wandering Flame",          "ff10","Final Fantasy X",          "theme",     76, "bittersweet",False,"Nobuo Uematsu","ff10-wandering-flame",["ps2","emotional","strings","choir"]),
    TrackEntry("ff10_battle",  "Fight with Seymour",       "ff10","Final Fantasy X",          "boss",     144, "intense",   False, "Nobuo Uematsu", "ff10-seymour-battle", ["ps2","boss","electric-guitar","aggressive"]),

    # ---- FF12 (PS2, 2006) ------------------------------------------------
    TrackEntry("ff12_battle",  "Boss Battle",              "ff12","Final Fantasy XII",        "boss",     120, "tense",     False, "Hitoshi Sakimoto", "ff12-boss-battle",["ps2","boss","orchestral","dissonant"]),

    # ---- FF13 (PS3, 2009) ------------------------------------------------
    TrackEntry("ff13_battle",  "Blinded by Light",         "ff13","Final Fantasy XIII",       "battle",   140, "energetic", False, "Masashi Hamauzu", "ff13-blinded-by-light", ["ps3","battle","electronic","hybrid","major"]),
    TrackEntry("ff13_theme",   "Promised Eternity",        "ff13","Final Fantasy XIII",       "theme",     80, "serene",    False, "Masashi Hamauzu", "ff13-promised-eternity",["ps3","theme","emotional","strings","piano"]),

    # ---- FF14 (PC/PS3+, 2013) --------------------------------------------
    TrackEntry("ff14_battle",  "Torn from the Heavens",    "ff14","Final Fantasy XIV",        "battle",   150, "epic",      False, "Masayoshi Soken", "ff14-torn-from-heavens",["mmo","battle","aggressive","electric-guitar","choir"]),
    TrackEntry("ff14_overworld","The Answers",             "ff14","Final Fantasy XIV",        "overworld", 90, "vast",      True,  "Masayoshi Soken", "ff14-the-answers",   ["mmo","overworld","choir","orchestral","epic"]),

    # ---- FF15 (PS4, 2016) ------------------------------------------------
    TrackEntry("ff15_road",    "Somnus (Road Trip)",       "ff15","Final Fantasy XV",         "theme",    120, "free",      False, "Yoko Shimomura",  "ff15-road-trip",    ["ps4","road","rock","electric-guitar","modern"]),
    TrackEntry("ff15_radio",   "FF Radio (Classic Mix)",   "ff15","Final Fantasy XV",         "radio",    100, "nostalgic", False, "Various",         "ff15-radio",        ["ps4","radio","covers","classic","piano"]),

    # ---- FF16 (PS5, 2023) ------------------------------------------------
    TrackEntry("ff16_battle",  "Away",                     "ff16","Final Fantasy XVI",        "battle",   156, "brutal",    False, "Masayoshi Soken", "ff16-away",         ["ps5","battle","metal","choir","aggressive"]),
    TrackEntry("ff16_theme",   "My Star",                  "ff16","Final Fantasy XVI",        "theme",     88, "dark",      True,  "Masayoshi Soken", "ff16-my-star",      ["ps5","theme","choral","dark","orchestral"]),

    # ---- Legacy / shared -------------------------------------------------
    TrackEntry("prelude",      "Prelude",                  "ff",  "Final Fantasy (series)",   "theme",    120, "mystical",  False, "Nobuo Uematsu",   "ff-prelude",        ["crystal","arpeggio","iconic","ambient"]),
    TrackEntry("victory",      "Victory Fanfare",          "ff",  "Final Fantasy (series)",   "fanfare",  120, "triumphant",False, "Nobuo Uematsu",   "ff-victory",        ["fanfare","victory","brass","short"]),
    TrackEntry("healing",      "Inn Theme",                "ff",  "Final Fantasy (series)",   "ambient",   95, "peaceful",  False, "Nobuo Uematsu",   "ff-inn",            ["inn","rest","healing","peaceful"]),
    TrackEntry("world_map",    "World Map",                "ff",  "Final Fantasy (series)",   "overworld",100, "epic",      False, "Nobuo Uematsu",   "ff-world-map",      ["world","overworld","sweep","strings","choir"]),
    TrackEntry("dungeon",      "Dungeon Theme",            "ff",  "Final Fantasy (series)",   "ambient",   70, "eerie",     False, "Nobuo Uematsu",   "ff-dungeon",        ["dungeon","dark","minor","tense"]),
    TrackEntry("tension",      "Tension",                  "ff",  "Final Fantasy (series)",   "battle",   100, "tense",     False, "Nobuo Uematsu",   "ff-tension",        ["tension","suspense","minor","pre-battle"]),

    # ---- Generic styles (non-FF) ----------------------------------------
    TrackEntry("orchestral_epic",  "Orchestral Epic",      "generic","Generic",              "theme",     104, "epic",      False, "Unknown",         "orchestral-epic",   ["orchestral","epic","cinematic","dramatic"]),
    TrackEntry("choral_fantasy",   "Choral Fantasy",       "generic","Generic",              "theme",      76, "mystical",  True,  "Unknown",         "choral-fantasy",    ["choir","fantasy","orchestral","sacred"]),
    TrackEntry("celtic_adventure", "Celtic Adventure",     "generic","Generic",              "overworld", 120, "lively",    False, "Unknown",         "celtic-adventure",  ["celtic","folk","flute","lively"]),
    TrackEntry("jazz_lounge",      "Jazz Lounge",          "generic","Generic",              "ambient",    88, "smooth",    False, "Unknown",         "jazz-lounge",       ["jazz","lounge","piano","smooth"]),
    TrackEntry("electronic_ambient","Electronic Ambient",  "generic","Generic",              "ambient",    70, "atmospheric",False,"Unknown",         "electronic-ambient",["electronic","ambient","synth","chill"]),
    TrackEntry("rock_battle",      "Rock Battle",          "generic","Generic",              "battle",    144, "aggressive",False, "Unknown",         "rock-battle",       ["rock","battle","electric-guitar","drums"]),
    TrackEntry("piano_ballad",     "Piano Ballad",         "generic","Generic",              "ballad",     66, "emotional", False, "Unknown",         "piano-ballad",      ["piano","ballad","solo","emotional"]),
    TrackEntry("folk_tavern",      "Folk Tavern",          "generic","Generic",              "theme",     130, "lively",    False, "Unknown",         "folk-tavern",       ["folk","tavern","lively","drinking"]),
    TrackEntry("horror_ambient",   "Horror Ambient",       "generic","Generic",              "ambient",    55, "unsettling",False, "Unknown",         "horror-ambient",    ["horror","dark","ambient","dissonant"]),
    TrackEntry("triumph_fanfare",  "Triumph Fanfare",      "generic","Generic",              "fanfare",   120, "triumphant",False, "Unknown",         "triumph-fanfare",   ["fanfare","victory","brass","short"]),
    TrackEntry("ff6_opera",        "Opera Aria",           "ff6",  "Final Fantasy VI",       "opera",      80, "romantic",  True,  "Nobuo Uematsu",   "opera-aria",        ["opera","ballad","vocals","romantic"]),
    TrackEntry("ff10_calm",        "Calm Ballad",          "ff10", "Final Fantasy X",        "theme",      76, "bittersweet",False,"Nobuo Uematsu",   "calm-ballad",       ["piano","strings","emotional","bittersweet"]),
]

# Index for fast lookup
_CATALOG_BY_STYLE: dict[str, TrackEntry] = {e.style_key: e for e in FF_RADIO_CATALOG}
_CATALOG_BY_GAME:  dict[str, list[TrackEntry]] = {}
_CATALOG_BY_TYPE:  dict[str, list[TrackEntry]] = {}
for _entry in FF_RADIO_CATALOG:
    _CATALOG_BY_GAME.setdefault(_entry.game, []).append(_entry)
    _CATALOG_BY_TYPE.setdefault(_entry.track_type, []).append(_entry)

# Alias map for natural-language titles → style keys
_ALIAS_MAP: dict[str, str] = {
    # FF7
    "let the battles begin":   "ff7_battle",
    "main theme of ff7":       "ff7_overworld",
    "main theme":              "ff7_overworld",
    "aerith":                  "ff7_sad",
    "aerith's theme":          "ff7_sad",
    "aeris theme":             "ff7_sad",
    "tifa":                    "ff7_town",
    "tifa's theme":            "ff7_town",
    "jenova":                  "ff7_boss",
    "j-e-n-o-v-a":            "ff7_boss",
    # FF8
    "eyes on me":              "ff8_ballad",
    "eyes on you":             "ff8_ballad",
    "don't be afraid":         "ff8_battle",
    "dont be afraid":          "ff8_battle",
    # FF6
    "terra":                   "ff6_sad",
    "terra's theme":           "ff6_sad",
    "aria":                    "ff6_opera",
    "aria di mezzo":           "ff6_opera",
    "aria de mezzo":           "ff6_opera",
    "decisive battle":         "ff6_battle",
    # FF10
    "to zanarkand":            "ff10_zanarkand",
    "zanarkand":               "ff10_zanarkand",
    "wandering flame":         "ff10_calm",
    # FF13
    "blinded by light":        "ff13_battle",
    "promised eternity":       "ff13_theme",
    # FF14
    "torn from the heavens":   "ff14_battle",
    "the answers":             "ff14_overworld",
    "answers":                 "ff14_overworld",
    # FF15
    "somnus":                  "ff15_road",
    "stand by me":             "ff15_radio",
    # FF16
    "away":                    "ff16_battle",
    "my star":                 "ff16_theme",
    # Shared
    "prelude":                 "prelude",
    "victory fanfare":         "victory",
    "chocobo":                 "ff1_overworld",
    # Generic
    "epic":                    "orchestral_epic",
    "choral":                  "choral_fantasy",
    "celtic":                  "celtic_adventure",
    "jazz":                    "jazz_lounge",
    "electronic":              "electronic_ambient",
    "rock":                    "rock_battle",
    "ballad":                  "piano_ballad",
    "tavern":                  "folk_tavern",
    "horror":                  "horror_ambient",
    "fanfare":                 "triumph_fanfare",
}

# Mood/keyword → style fallback map
_MOOD_STYLE_MAP: list[tuple[list[str], str]] = [
    (["sad", "emotional", "tearjerker", "cry", "mourn", "aerith"],         "ff7_sad"),
    (["romantic", "love", "ballad", "vocal", "singer", "eyes on"],         "ff8_ballad"),
    (["battle", "fight", "combat", "boss", "intense", "aggressive"],       "ff7_battle"),
    (["overworld", "travel", "adventure", "explore", "journey", "road"],   "ff7_overworld"),
    (["peaceful", "calm", "rest", "heal", "inn", "quiet"],                 "healing"),
    (["epic", "cinematic", "orchestral", "dramatic", "grand"],             "orchestral_epic"),
    (["choir", "choral", "sacred", "church"],                              "choral_fantasy"),
    (["piano", "solo", "intimate", "minimal"],                             "piano_ballad"),
    (["dungeon", "cave", "dark", "eerie", "mysterious"],                   "dungeon"),
    (["tension", "suspense", "suspenseful", "tense", "pre-battle"],        "tension"),
    (["celtic", "folk", "flute", "irish"],                                 "celtic_adventure"),
    (["rock", "electric", "guitar", "metal"],                              "rock_battle"),
    (["jazz", "lounge", "swing", "smooth"],                                "jazz_lounge"),
    (["horror", "scary", "creepy", "unsettling", "ambient"],               "horror_ambient"),
    (["triumph", "victory", "win", "fanfare", "celebration"],              "triumph_fanfare"),
    (["modern", "ff15", "road trip", "car"],                               "ff15_road"),
    (["ff16", "brutal", "raw"],                                            "ff16_battle"),
    (["ff14", "mmo", "online"],                                            "ff14_battle"),
    (["ff13", "lighting", "lightning", "hope"],                            "ff13_battle"),
    (["ff12", "ivalice"],                                                  "ff12_battle"),
    (["ff10", "zanarkand", "tidus", "yuna"],                               "ff10_zanarkand"),
    (["ff9", "zidane", "garnet"],                                          "ff9_overworld"),
    (["ff6", "terra", "kefka"],                                            "ff6_sad"),
    (["ff4", "cecil", "rydia"],                                            "ff4_battle"),
    (["ff1", "nes", "8-bit", "retro"],                                     "ff1_battle"),
    (["ff7", "cloud", "sephiroth", "midgar"],                              "ff7_battle"),
    (["ff8", "squall", "rinoa", "balamb"],                                 "ff8_battle"),
]


class MusicLibrary:
    """Query and browse the full FF + generic music style catalog.

    Parameters
    ----------
    catalog:
        List of :class:`TrackEntry` objects.  Defaults to
        :data:`FF_RADIO_CATALOG`.
    """

    def __init__(self, catalog: list[TrackEntry] | None = None) -> None:
        self._catalog: list[TrackEntry] = catalog if catalog is not None else FF_RADIO_CATALOG

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def all_entries(self) -> list[TrackEntry]:
        """Return all catalog entries."""
        return list(self._catalog)

    def all_style_keys(self) -> list[str]:
        """Return sorted list of all style keys."""
        return sorted(e.style_key for e in self._catalog)

    def by_game(self, game: str) -> list[TrackEntry]:
        """Return all entries for a game abbreviation (e.g. ``"ff7"``)."""
        game = game.lower().strip()
        return [e for e in self._catalog if e.game == game]

    def by_type(self, track_type: str) -> list[TrackEntry]:
        """Return all entries matching a track type (e.g. ``"battle"``)."""
        return [e for e in self._catalog if e.track_type == track_type]

    def by_mood(self, mood: str) -> list[TrackEntry]:
        """Return entries whose key_mood contains the given keyword."""
        kw = mood.lower().strip()
        return [e for e in self._catalog if kw in e.key_mood or kw in e.tags]

    def with_vocals(self) -> list[TrackEntry]:
        """Return entries that have vocal performance."""
        return [e for e in self._catalog if e.with_vocals]

    def search(self, query: str) -> list[TrackEntry]:
        """Free-text search across all text fields."""
        q = query.lower()
        results = []
        for e in self._catalog:
            text = " ".join([
                e.style_key, e.display_name, e.game, e.game_full,
                e.track_type, e.key_mood, e.composer,
            ] + e.tags).lower()
            if any(word in text for word in q.split()):
                results.append(e)
        return results

    def get(self, style_key: str) -> TrackEntry | None:
        """Look up a single entry by style key."""
        return _CATALOG_BY_STYLE.get(style_key)

    def style_for_request(self, request: str) -> str:
        """Best-match style key for a natural-language request.

        Parameters
        ----------
        request:
            Free-form description, e.g. ``"something sad from FF7"``,
            ``"eyes on me"`, ``"an epic battle theme"``.

        Returns
        -------
        str
            A style key that can be passed to the music generator.
        """
        return style_for_request(request)

    def games(self) -> list[str]:
        """Return sorted unique game abbreviations in the catalog."""
        return sorted({e.game for e in self._catalog})

    def track_types(self) -> list[str]:
        """Return sorted unique track types in the catalog."""
        return sorted({e.track_type for e in self._catalog})


def style_for_request(request: str) -> str:
    """Resolve a natural-language music request to a style key.

    Parameters
    ----------
    request:
        Free-form string describing what the user wants.

    Returns
    -------
    str
        Best-matching style key.
    """
    r = request.lower().strip()

    # 1. Direct alias match (exact song title)
    for alias, style_key in _ALIAS_MAP.items():
        if alias in r:
            return style_key

    # 2. Mood / keyword match
    for keywords, style_key in _MOOD_STYLE_MAP:
        if any(kw in r for kw in keywords):
            return style_key

    # 3. Fallback: use the prompt parser
    try:
        from audio_engine.ai.prompt import PromptParser
        parsed = PromptParser().parse(request)
        if parsed.style:
            return parsed.style
    except Exception:
        pass

    # 4. Last resort: ff7_overworld (universally appropriate)
    return "ff7_overworld"
