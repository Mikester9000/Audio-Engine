# Audio Engine

**Audio Engine for Game Engine for Teaching** – a Python library that generates
music and sound effects inspired by cinematic RPG soundtracks (such as those
found in *Final Fantasy XV*). It ships with a multi-layer synthesiser, an
AI-assisted composer, and a game-engine–compatible audio exporter.

---

## Features

| Component | Description |
|-----------|-------------|
| **Synthesizer** | Oscillators (sine, square, sawtooth, triangle, FM, additive), ADSR envelopes, filters (low/high/band-pass, notch), and effects (reverb, delay, chorus, distortion, compressor). |
| **Instrument Library** | 9 pre-built timbres: `strings`, `brass`, `piano`, `choir`, `synth_pad`, `electric_guitar`, `bass`, `flute`, `crystal_synth`. |
| **AI Composer** | Markov-chain melody generation + rule-based harmony. Six style presets: `battle`, `exploration`, `ambient`, `boss`, `victory`, `menu`. |
| **Sequencer** | Multi-track timeline with per-track pan, volume, and velocity. Renders to stereo float32 NumPy arrays. |
| **Exporter** | Writes 16-bit or 32-bit WAV files (built-in) and OGG Vorbis (optional). Supports game-engine loop-point metadata (`smpl` chunk). |
| **CLI** | `audio-engine generate`, `sfx`, `list-styles`, `list-instruments`. |

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

# Generate an 8-bar battle track and save it
audio = engine.generate_track("battle", bars=8, output_path="battle.wav")

# Generate an ambient background loop
engine.generate_track("ambient", bars=4, output_path="ambient.wav")

# Export with game-engine loop points
engine.generate_track(
    "exploration",
    bars=8,
    output_path="exploration.wav",
    loop_start=0,
    loop_end=len(audio) - 1,
)

# Quick sound effect – piano C-major chord
sfx = engine.render_sfx("piano", [261.63, 329.63, 392.0], duration=0.5, overlap=True)
engine.export(sfx, "chord.wav")

# Custom sequencer
from audio_engine.composer import Sequencer
from audio_engine.synthesizer import InstrumentLibrary

seq = engine.create_sequencer(bpm=120)
seq.add_track("piano", InstrumentLibrary.get("piano"))
seq.add_note("piano", frequency=440.0, onset=0.0, duration=0.4)
seq.add_note("piano", frequency=554.0, onset=0.5, duration=0.4)
seq.add_note("piano", frequency=659.0, onset=1.0, duration=0.4)
audio = seq.render()
engine.export(audio, "custom.wav")
```

### Command-Line Interface

```bash
# List available styles and instruments
audio-engine list-styles
audio-engine list-instruments

# Generate a 16-bar exploration track
audio-engine generate --style exploration --bars 16 --output exploration.wav

# Generate a boss battle track (OGG)
audio-engine generate --style boss --bars 8 --output boss.ogg --format ogg

# Render a quick A-minor chord SFX
audio-engine sfx --instrument piano --notes 220 261.63 329.63 --overlap --output chord.wav

# Reproducible generation with a fixed seed
audio-engine generate --style battle --seed 42 --output battle.wav
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

## Game Engine Integration

The exported WAV files are compatible with:

- **Godot** – import as AudioStream; use `loop_begin`/`loop_end` from the `smpl` chunk.
- **Unity** – import as AudioClip; enable "Loop" in the import settings.
- **Unreal Engine** – import as Sound Wave; set loop region in the audio editor.
- **GameMaker Studio** – import as audio asset; loop points are read automatically.

### Setting Loop Points

```python
engine.generate_track(
    "ambient",
    bars=8,
    output_path="ambient.wav",
    loop_start=0,          # sample index where the loop begins
    loop_end=44100 * 16,   # sample index where the loop ends
)
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
│   └── generator.py        # Markov-chain melody + rule-based orchestration
└── export/
    └── audio_exporter.py   # WAV (16/32-bit) & OGG export + loop metadata
```

---

## Running the Tests

```bash
pip install -e ".[dev]"
pytest
```

All 142 tests cover the synthesizer, composer, AI generator, exporter, engine façade, and CLI.

---

## License

MIT
