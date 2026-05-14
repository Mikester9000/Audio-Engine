# Audio Engine

> **AI-first repository note:** this repository now operates as a **GitHub-native audio asset factory** for generating reusable game audio assets, especially for downstream projects like `GameRewritten`. Start with [`docs/AI_FACTORY/README.md`](docs/AI_FACTORY/README.md) and [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for the current mission, state, roadmap, and handoff rules. Music and SFX are higher priority than voice, and inspiration targets must be treated as style families rather than copyrighted copying targets.

## AI-First Documentation Quick Start

- Mission and non-goals: [`docs/AI_FACTORY/PROJECT_MISSION.md`](docs/AI_FACTORY/PROJECT_MISSION.md)
- Current implementation status: [`docs/AI_FACTORY/CURRENT_STATE.md`](docs/AI_FACTORY/CURRENT_STATE.md)
- Implementation truth table: [`docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`](docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md)
- Next priorities: [`docs/AI_FACTORY/ACTIVE_WORK.md`](docs/AI_FACTORY/ACTIVE_WORK.md)
- Mechanical next PR order: [`docs/AI_FACTORY/NEXT_PR_SEQUENCE.md`](docs/AI_FACTORY/NEXT_PR_SEQUENCE.md)
- Code locator map: [`docs/AI_FACTORY/CODEBASE_MAP.md`](docs/AI_FACTORY/CODEBASE_MAP.md)
- Handoff / what changed last: [`docs/AI_FACTORY/HANDOFF.md`](docs/AI_FACTORY/HANDOFF.md)
- Build/run/test workflow: [`docs/AI_FACTORY/PLAYBOOKS/BUILD_AND_RUN.md`](docs/AI_FACTORY/PLAYBOOKS/BUILD_AND_RUN.md)
- Style safety and inspiration guidance: [`docs/AI_FACTORY/STYLES/STYLE_FAMILIES.md`](docs/AI_FACTORY/STYLES/STYLE_FAMILIES.md)

**Audio Engine** – a Python library that rapidly generates production-quality
music, sound effects, and voice for games, using a local AI pipeline.
Inspired by cinematic RPG soundtracks (*Final Fantasy XV*-calibre output),
it ships with a multi-layer synthesiser, an AI-assisted composer, a mastering
pipeline, and a QA validation suite.  No cloud services required.

Fully compatible with the
[Game Engine for Teaching](https://github.com/Mikester9000/Game-Engine-for-Teaching-)
— see the [Game Engine Integration](#game-engine-for-teaching-integration) section below.

---

## Features

| Component | Description |
|-----------|-------------|
| **Synthesizer** | Oscillators (sine, square, sawtooth, triangle, FM, additive), ADSR envelopes, filters (low/high/band-pass, notch), and effects (reverb, delay, chorus, distortion, compressor). |
| **Instrument Library** | 9 pre-built timbres: `strings`, `brass`, `piano`, `choir`, `synth_pad`, `electric_guitar`, `bass`, `flute`, `crystal_synth`. |
| **AI Music Generator** | Markov-chain melody + rule-based harmony. Six style presets: `battle`, `exploration`, `ambient`, `boss`, `victory`, `menu`. Prompt-driven generation with BPM/loop/style detection. |
| **AI SFX Generator** | 20+ procedural SFX types from a text prompt: explosions, footsteps, lasers, magic, UI sounds, and more. |
| **AI Voice / TTS** | Local formant-based text-to-speech with 5 voice presets (`narrator`, `hero`, `villain`, `announcer`, `npc`). Upgradeable to Piper or ONNX TTS. |
| **DSP Pipeline** | Parametric EQ (multi-band biquad), dynamic compressor, true-peak limiter, convolution reverb, polyphase resampler, and noise dithering. |
| **Mastering (OfflineBounce)** | Full render/master path: EQ → compression → loudness normalisation (LUFS) → true-peak limiter → dither → export. |
| **Stem Renderer** | Export individual sequencer tracks as separate stems for adaptive/interactive audio. |
| **QA Suite** | EBU R128 loudness meter, clipping detector, loop boundary click analyser. |
| **Exporter** | Writes 16-bit or 32-bit WAV files (built-in) and OGG Vorbis (optional). Game-engine loop-point metadata (`smpl` chunk). |
| **CLI** | `generate`, `generate-music`, `generate-sfx`, `generate-voice`, `qa`, `sfx`, `list-styles`, `list-instruments`, `generate-game-assets`, `verify-game-assets`. |
| **Game Engine Integration** | Pre-generates all audio assets for the [Game Engine for Teaching](https://github.com/Mikester9000/Game-Engine-for-Teaching-) with a single command.  Includes a drop-in C++ `AudioSystem.hpp` (miniaudio-based) and Lua hook integration. |

---

## Requirements

- Python ≥ 3.9
- [NumPy](https://numpy.org/) ≥ 1.24
- [SciPy](https://scipy.org/) ≥ 1.10
- *(optional)* [soundfile](https://python-soundfile.readthedocs.io/) ≥ 0.12 for OGG export

---

## Installation

```bash
# Standard install (WAV export only)
pip install .

# With OGG export support
pip install ".[ogg]"

# Development (includes pytest)
pip install -e ".[dev]"
```

---

## Quick Start

### Python API

```python
from audio_engine import AudioEngine

engine = AudioEngine(sample_rate=44100, seed=42)

# Generate an 8-bar battle track (style-based)
audio = engine.generate_track("battle", bars=8, output_path="battle.wav")

# Generate music from a natural-language prompt (with mastering)
engine.generate_music(
    "dark orchestral battle theme 140 BPM loopable",
    duration=60.0,
    loopable=True,
    output_path="battle_loop.wav",
)

# Generate a sound effect from a prompt
engine.generate_sfx_from_prompt("laser zap", duration=0.5, output_path="laser.wav")
engine.generate_sfx_from_prompt("coin collect", output_path="coin.wav")

# Synthesise voice with local TTS
engine.generate_voice("The hero must find the crystal sword.", voice="narrator", output_path="narration.wav")
engine.generate_voice("Level complete!", voice="announcer", output_path="win.wav")

# Quick sound effect – piano C-major chord
sfx = engine.render_sfx("piano", [261.63, 329.63, 392.0], duration=0.5, overlap=True)
engine.export(sfx, "chord.wav")
```

### AI Pipeline (direct module access)

```python
from audio_engine.ai import MusicGen, SFXGen, VoiceGen

# Music
gen = MusicGen(sample_rate=44100, seed=42)
gen.generate_to_file("epic ambient exploration 90 BPM", "explore.wav", duration=60, loopable=True)
gen.generate_to_file("intense boss battle 160 BPM", "boss.wav", duration=120)

# SFX
sfx = SFXGen()
sfx.generate_to_file("explosion impact", "boom.wav", duration=1.5)
sfx.generate_to_file("magic spell sparkle", "magic.wav", duration=0.8)

# Voice
voice = VoiceGen()
voice.generate_to_file("Welcome, adventurer.", "welcome.wav", voice="narrator")
voice.generate_to_file("You shall not pass!", "villain.wav", voice="villain")
```

### Mastering Pipeline

```python
from audio_engine.render import OfflineBounce

# Master raw audio to -16 LUFS with true-peak limiting
bounce = OfflineBounce(sample_rate=44100, target_lufs=-16.0, ceiling_db=-0.3)
mastered = bounce.process(raw_audio)
bounce.process_and_export(raw_audio, "mastered.wav", loopable=True, loop_start=0, loop_end=len(raw_audio)-1)
```

### DSP Processing

```python
from audio_engine.dsp import EQ, Compressor, Limiter, ConvolutionReverb
from audio_engine.dsp.eq import EQBand

# EQ
eq = EQ(44100)
eq.add_band(EQBand(120.0, gain_db=-3.0, band_type="low_shelf"))   # tighten low end
eq.add_band(EQBand(10000.0, gain_db=+2.0, band_type="high_shelf")) # add air
processed = eq.process(audio)

# Convolution reverb
reverb = ConvolutionReverb(44100, rt60=2.0, room_size=0.8, wet=0.3)
reverbed = reverb.process(audio)

# Compressor + limiter chain
comp = Compressor(44100, threshold_db=-18.0, ratio=4.0, attack_ms=10.0, release_ms=100.0)
limiter = Limiter(44100, ceiling_db=-0.3)
output = limiter.process(comp.process(audio))
```

### Quality Assurance

```python
from audio_engine.qa import LoudnessMeter, ClippingDetector, LoopAnalyzer

meter = LoudnessMeter(44100)
result = meter.measure(audio)
print(f"Integrated: {result.integrated_lufs:.1f} LUFS")
print(f"True peak:  {result.true_peak_dbfs:.1f} dBFS")
print(f"LRA:        {result.loudness_range_lu:.1f} LU")

clip = ClippingDetector().detect(audio)
print(clip.summary())

loop = LoopAnalyzer(44100).analyze(audio)
print(loop.summary())
```

### Command-Line Interface

```bash
# List available styles and instruments
audio-engine list-styles
audio-engine list-instruments

# Generate music from a prompt (with mastering)
audio-engine generate-music --prompt "dark ambient dungeon loop 90 BPM" \
    --duration 60 --loop --output dungeon.wav

# Generate music from a style preset (legacy)
audio-engine generate --style battle --bars 8 --output battle.wav

# Generate a sound effect from a prompt
audio-engine generate-sfx --prompt "explosion impact" --duration 1.5 --output boom.wav
audio-engine generate-sfx --prompt "laser zap" --duration 0.4 --pitch 800 --output laser.wav

# Generate voice / TTS
audio-engine generate-voice --text "Welcome, hero." --voice narrator --output greeting.wav
audio-engine generate-voice --text "Level complete!" --voice announcer --speed 0.9 --output win.wav

# Quality-assurance check on a WAV file
audio-engine qa --input track.wav
audio-engine qa --input loop.wav --check-loop

# Render a quick SFX chord (instrument-based)
audio-engine sfx --instrument piano --notes 261.63 329.63 392.0 --overlap --output chord.wav

# Reproducible generation with a fixed seed
audio-engine generate-music --prompt "battle" --seed 42 --output battle.wav
```

---

## Music Styles

| Style | BPM | Key / Scale | Instrumentation |
|-------|-----|-------------|-----------------|
| `battle` | 140 | A harmonic minor | Brass, strings, bass, percussion |
| `exploration` | 90 | G major | Flute, strings, choir, bass |
| `ambient` | 60 | E natural minor | Synth pad, choir |
| `boss` | 160 | D Phrygian | Brass, electric guitar, bass, percussion |
| `victory` | 120 | C major | Brass, piano, strings, bass, percussion |
| `menu` | 80 | F major | Piano, crystal synth, strings, synth pad, bass |

---

## Voice Presets

| Preset | Pitch | Character |
|--------|-------|-----------|
| `narrator` | 120 Hz | Neutral, clear, storytelling |
| `hero` | 110 Hz | Confident, warm |
| `villain` | 85 Hz | Deep, dark, foreboding |
| `announcer` | 130 Hz | Bright, authoritative |
| `npc` | 150 Hz | Character voice, varied |

---

## Extending with Real AI Models

The pipeline uses a pluggable **backend** system.  The default `"procedural"`
backend works entirely offline with zero extra dependencies.

To upgrade to a real AI model:

```python
from audio_engine.ai.backend import InferenceBackend, BackendRegistry
import numpy as np

class MyTTSBackend(InferenceBackend):
    """Wrap Piper TTS for high-quality local speech synthesis."""
    def generate_voice_audio(self, text, voice_preset="narrator", speed=1.0, **kw):
        # Call your local Piper model here
        ...
        return audio_array  # np.ndarray, mono float32

    def generate_music_audio(self, style, duration, bpm=None, **kw):
        ...  # delegate to procedural for music

    def generate_sfx_audio(self, sfx_type, duration, pitch_hz=None, **kw):
        ...

BackendRegistry.register("piper_tts", MyTTSBackend)

from audio_engine.ai import VoiceGen
voice = VoiceGen(backend="piper_tts", sample_rate=22050)
voice.generate_to_file("Hello, world!", "hello.wav")
```

Recommended local models:
- **Voice/TTS**: [Piper](https://github.com/rhasspy/piper) (ONNX, MIT licence, runs on CPU)
- **Music/SFX**: [MusicGen](https://github.com/facebookresearch/audiocraft) via ONNX Runtime

---

## Game Engine for Teaching Integration

The Audio Engine is designed to work seamlessly as the audio layer for the
[Game Engine for Teaching](https://github.com/Mikester9000/Game-Engine-for-Teaching-) —
a C++17 FFXV-style action RPG engine.

### One-command asset generation

```bash
# Generate the complete audio asset library (music + SFX + voice):
audio-engine generate-game-assets --output-dir assets/audio

# Check that all assets are present:
audio-engine verify-game-assets --assets-dir assets/audio

# Generate only SFX (faster iteration):
audio-engine generate-game-assets --output-dir assets/audio --only sfx

# Regenerate everything from scratch:
audio-engine generate-game-assets --output-dir assets/audio --force
```

Output layout:

```
assets/audio/
├── music/
│   ├── music_main_menu.wav      ← GameState::MAIN_MENU
│   ├── music_exploring.wav      ← GameState::EXPLORING
│   ├── music_combat.wav         ← GameState::COMBAT
│   ├── music_boss_combat.wav    ← boss encounters
│   ├── music_dialogue.wav       ← GameState::DIALOGUE
│   ├── music_vehicle.wav        ← GameState::VEHICLE
│   ├── music_camping.wav        ← CAMPING state
│   ├── music_inventory.wav      ← INVENTORY state
│   ├── music_shopping.wav       ← SHOPPING state
│   └── music_victory.wav        ← post-combat victory sting
├── sfx/
│   ├── sfx_combat_hit.wav       ← sword hit
│   ├── sfx_spell_cast.wav       ← magic spell
│   ├── sfx_level_up.wav         ← level-up fanfare
│   ├── sfx_quest_complete.wav   ← quest reward
│   └── … (30+ events — see game_state_map.py)
├── voice/
│   ├── voice_welcome.wav        ← narrator intro line
│   ├── voice_level_up.wav       ← "You have grown stronger."
│   ├── voice_boss_intro.wav     ← "A powerful enemy approaches!"
│   └── … (9 narrator/character lines)
└── manifest.json                ← asset inventory read by AudioSystem.hpp
```

### C++ integration (drop-in header)

Copy the pre-built header into the game engine:

```bash
# 1. Download miniaudio (single-file, public domain)
curl -o src/engine/audio/miniaudio.h \
     https://raw.githubusercontent.com/mackron/miniaudio/master/miniaudio.h

# 2. Copy the AudioSystem header
cp $(python -c "import audio_engine; print(audio_engine.__file__)"/../integration/cpp/AudioSystem.hpp \
   src/engine/audio/AudioSystem.hpp
```

Create `src/engine/audio/AudioSystem.cpp` (one line):
```cpp
#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio.h"
```

Wire into `Game.hpp`:
```cpp
#include "engine/audio/AudioSystem.hpp"

class Game {
    …
    std::unique_ptr<AudioSystem> m_audio;
    …
};
```

Wire into `Game.cpp`:
```cpp
// Game::Init()
m_audio = std::make_unique<AudioSystem>("assets/audio");
m_audio->Init();

// Game::SetState()  — add one line:
m_audio->OnStateChange(newState);

// Game::Shutdown()
m_audio->Shutdown();
```

Register Lua bindings (in `LuaEngine::RegisterEngineBindings()`):
```cpp
AudioSystem* audio = &Game::Instance().GetAudio();
lua_pushlightuserdata(L, audio);
lua_setglobal(L, "__audio_ptr");
lua_register(L, "audio_play_sfx",   AudioSystem::Lua_PlaySFX);
lua_register(L, "audio_play_music", AudioSystem::Lua_PlayMusic);
lua_register(L, "audio_set_volume", AudioSystem::Lua_SetVolume);
lua_register(L, "audio_play_voice", AudioSystem::Lua_PlayVoice);
```

### Lua integration

Copy the Lua hook script into the game engine's `scripts/` directory:

```bash
cp $(python -c "import audio_engine; print(audio_engine.__file__)"/../integration/lua/audio.lua \
   scripts/audio.lua
```

The script auto-wires into every existing Lua hook (`on_combat_start`,
`on_camp_rest`, `on_level_up`, …) and adds new hooks (`on_quest_complete`,
`on_spell_cast`, `on_warp_strike`, …).  No changes to existing `.lua` files
are required.

### Python API

```python
from audio_engine.integration import AssetPipeline

# Generate all assets with progress reporting
pipeline = AssetPipeline(sample_rate=44100, seed=42)
manifest = pipeline.generate_all("assets/audio")
print(manifest.summary())

# Check what's present / missing
report = pipeline.verify("assets/audio")
print("Missing:", report["missing"])
```

---


## Architecture

```
audio_engine/
├── engine.py               # AudioEngine façade (main entry-point)
├── cli.py                  # Command-line interface
├── synthesizer/
│   ├── oscillator.py       # Waveform generators (sine, saw, FM, additive…)
│   ├── envelope.py         # ADSR envelope shaping
│   ├── filter.py           # Butterworth IIR filters
│   ├── effects.py          # Reverb, delay, chorus, distortion, compressor
│   └── instrument.py       # Named instruments + InstrumentLibrary registry
├── composer/
│   ├── scale.py            # Western & modal scales
│   ├── chord.py            # Chord qualities & named progressions
│   ├── pattern.py          # Rhythmic trigger patterns
│   └── sequencer.py        # Multi-track timeline → stereo render
├── ai/
│   ├── generator.py        # Markov-chain melody + rule-based orchestration
│   ├── music_gen.py        # MusicGen – prompt-driven music generation
│   ├── sfx_gen.py          # SFXGen – prompt-driven SFX generation
│   ├── voice_gen.py        # VoiceGen – local text-to-speech
│   ├── sfx_synth.py        # Procedural SFX synthesiser (20+ types)
│   ├── voice_synth.py      # Formant speech synthesiser (5 presets)
│   ├── prompt.py           # Prompt-to-plan parser
│   └── backend.py          # Pluggable inference backend interface
├── dsp/
│   ├── eq.py               # Parametric biquad EQ
│   ├── compressor.py       # Feed-forward dynamic compressor
│   ├── limiter.py          # True-peak brick-wall limiter
│   ├── reverb.py           # Convolution reverb (synthetic + IR loading)
│   ├── resample.py         # Polyphase sample-rate converter
│   └── dither.py           # TPDF/RPDF noise dithering
├── render/
│   ├── offline_bounce.py   # OfflineBounce – full mastering pipeline
│   └── stem_renderer.py    # StemRenderer – per-track stem export
├── qa/
│   ├── loudness_meter.py   # EBU R128 integrated loudness (LUFS / LRA)
│   ├── clipping_detector.py # Digital over-threshold clipping detection
│   └── loop_analyzer.py    # Loop boundary click / discontinuity detection
├── export/
│   └── audio_exporter.py   # WAV (16/32-bit) & OGG export + loop metadata
└── integration/            # Game Engine for Teaching compatibility layer
    ├── game_state_map.py   # GameState → audio asset mapping
    ├── asset_pipeline.py   # AssetPipeline – generate all game assets
    ├── cpp/
    │   └── AudioSystem.hpp # Drop-in C++ header (miniaudio-based)
    └── lua/
        └── audio.lua       # Lua hook integration for game engine scripts
```

---

## Running the Tests

```bash
pip install -e ".[dev]"
pytest
```

264 tests cover the synthesizer, composer, AI generators, DSP chain, render
pipeline, QA suite, exporter, engine façade, CLI, and integration layer.

---

## Asset Manifest & Validator

A shared asset manifest system (identical to the one in
[Game Engine for Teaching](https://github.com/Mikester9000/Game-Engine-for-Teaching-))
is included to validate all game assets before they ship.

```
assets/
├── schema/
│   └── asset-manifest.schema.json   ← canonical JSON Schema (draft-07)
├── examples/
│   ├── audio-manifest.json
│   ├── texture-manifest.json
│   ├── tilemap-manifest.json
│   └── model-manifest.json
tools/
│   └── validate-assets.py           ← validator CLI
docs/
│   └── asset-manifest.md            ← full schema reference
.github/workflows/
    └── validate-assets.yml          ← CI gate (runs on asset changes)
```

### Quick Start

```bash
# Validate all example manifests (run from repo root)
python3 tools/validate-assets.py

# Optional: install jsonschema for full JSON Schema draft-07 validation
pip install jsonschema

# Verbose output — show field-level errors
python3 tools/validate-assets.py assets/examples/ --verbose
```

See [`docs/asset-manifest.md`](docs/asset-manifest.md) for the full schema
reference and integration guide.

---

## License

MIT
