# Orchestral Sample Library

Drop `.wav` files into the category subdirectories below. The engine will
automatically load them for orchestral remastering and the `sample` backend.

## Directory Layout

```
samples/
├── strings/          ← string ensemble multi-samples (violin, viola, cello)
├── brass/            ← brass section samples (french horn, trumpet, trombone, tuba)
├── choir/            ← vowel-pad samples: "aah", "ooh", ensemble voices
├── piano/            ← piano multi-samples (grand or upright)
├── flute/            ← flute / woodwind solo or ensemble
├── electric_guitar/  ← rhythm and lead electric guitar samples
├── percussion/       ← orchestral or studio drum kit samples
├── orchestral_hit/   ← orchestral stab / hit one-shots
├── sfx/              ← one-shot sound effect samples (WAV)
├── ff7_lead/         ← FF7-specific crystal lead samples (optional)
├── ff7_strings/      ← FF7-specific synthetic string samples (optional)
├── ff7_bass/         ← FF7-specific bass samples (optional)
├── ff7_electric_guitar/ ← FF7-specific electric guitar samples (optional)
└── voice/            ← vocal performance samples or choir patches
```

## File Requirements

- **Format**: `.wav` (16-bit or 24-bit PCM, any sample rate — the engine resamples automatically)
- **Naming**: Any filename works; the engine loads all `.wav` files recursively within each sub-directory
- **Root note**: For pitched instruments, tuning to **A4 = 440 Hz** gives the best pitch-shift accuracy, but any root works — the engine adjusts

## Usage

### Sample-augmented generation (CLI)

```bash
# Generate an FF7 overworld with real strings and choir blended in
audio-engine generate-music \
  --prompt "ff7 overworld" \
  --samples-dir samples/ \
  --output ff7_overworld_remastered.wav \
  --duration 60

# Generate an Eyes on Me style ballad with vocals
audio-engine compose-piece \
  --style ff8_ballad \
  --with-vocals \
  --samples-dir samples/ \
  --output eyes_on_me.wav \
  --duration 120
```

### Remaster an existing file

```bash
# Take an existing PS1-era WAV and blend in real orchestral samples
audio-engine remaster \
  --input my_ff7_track.wav \
  --samples-dir samples/ \
  --style ff7_overworld \
  --output my_ff7_track_remastered.wav
```

### Python API

```python
from audio_engine.ai.sample_backend import SampleBackend

backend = SampleBackend(samples_dir="samples/", sample_rate=44100)
audio = backend.generate_music_audio("ff8_ballad", duration=90.0)
```

## Three-Mode Audio Pipeline

The engine has three quality tiers — easy to switch between:

| Mode | CLI Flag | Character |
|------|----------|-----------|
| **PS1** | `--ps1` | Bit-crushed, SPU reverb, authentic PlayStation hardware sound |
| **Synth Orchestral** | `--orchestral` | Clean synthesised orchestra — "what the composer intended" |
| **Sample Remaster** | `--samples-dir DIR` | Real WAV samples blended over synth base — full fidelity |

## Recommended Free Sample Sources

- **VSCO Community Orchestra** (CC0): strings, brass, winds, perc
- **Spitfire LABS** (free): various orchestral and synth patches
- **FreePats** (CC): general MIDI-compatible patches
- **OpenGameArt.org**: game-ready SFX one-shots

## Category → Style Mapping

| Category | Used for styles |
|----------|----------------|
| `strings` | ff7_overworld, ff7_sad, ff7_town, world_map, healing |
| `brass` | ff7_battle, ff8_battle, ff7_boss, world_map |
| `choir` | ff7_boss, ff7_overworld, ff7_sad, dungeon, chorus sections |
| `piano` | ff7_sad, ff7_town, ff8_ballad (Eyes on Me), prelude, healing |
| `flute` | ff7_overworld, ff7_town, healing |
| `electric_guitar` | ff7_boss, ff8_battle |
| `percussion` | ff7_battle, ff8_battle, ff7_boss |
| `sfx` | All SFX generation (sword_swing, spell_fire, cure, etc.) |
| `voice` | Vocal overlay for compose-piece |
