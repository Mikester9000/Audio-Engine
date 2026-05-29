# Windows Quickstart (Offline Audio Engine)

## Prerequisites

- **Python 3.11+** (required): https://www.python.org/downloads/windows/
- **Git** (optional): https://git-scm.com/download/win
  - You can also use **Download ZIP** on GitHub instead of Git.

## Step 1: Download this repository

Choose one:

- `git clone https://github.com/Mikester9000/Audio-Engine.git`
- Download ZIP from GitHub and extract it

## Step 2: Double-click `setup.bat`

`setup.bat` now asks you to choose a setup mode:

```
Choose a setup mode:
  1  Manual / procedural only  (no AI models, fastest setup)
  2  AI workflow               (installs MusicGen + downloads ~1.5 GB model)
```

### Mode 1 — Manual / Procedural Only (recommended for first-time users)

- Installs the core package only (`pip install -e "."`)
- No AI model download required
- All audio uses the built-in procedural synthesiser
- You can use the Studio GUI and all CLI commands immediately

### Mode 2 — AI Workflow

- Attempts `pip install -e ".[neural]"` (includes Kokoro voice)
- If that fails (common on Windows), automatically retries with `pip install -e ".[musicgen]"`
- Downloads MusicGen Medium (~1.5 GB) into `models/musicgen-medium/`
- Model download may be slow on first run; see troubleshooting below if it stalls

## Step 3: Launch the Studio GUI

After setup, start the GUI:

```bat
audio-engine studio
```

The **Studio** has four tabs:

| Tab | What it does |
|---|---|
| **Music** | Generate background music from style presets, with custom instrument arrangement |
| **SFX** | Generate sound effects by category |
| **Voice** | Generate voice lines from text |
| **Synth Workbench** | Manually create any sound from scratch: choose waveform, set ADSR envelope, apply filter, export WAV — no AI required |

### Synth Workbench

The **Synth Workbench** tab gives you direct control over:

- **Waveform**: sine, square, sawtooth, triangle, noise, band-limited sawtooth/square
- **Frequency**: in Hz (any pitch)
- **Duration**: how long the sound plays
- **Amplitude**: overall volume (0–1)
- **ADSR Envelope**: Attack / Decay / Sustain / Release sliders
- **Filter**: lowpass, highpass, bandpass, or none — with adjustable cutoff frequency
- **Output path**: where to save the WAV

Click **Generate WAV** to create the sound immediately. No AI model needed.

## Step 4: Double-click `run.bat` (optional)

`run.bat` activates the virtual environment and shows Audio Engine CLI commands.

After setup has finished once, generation runs fully offline from local files.

## What the AI model does (Mode 2 only)

- **MusicGen Medium (`models/musicgen-medium/`)**: prompt-driven background music and sound effects

MusicGen Medium handles AI music and sound effect generation. Voice synthesis and procedural audio use the built-in synthesiser and do not require the model.

## Generating audio without AI (procedural mode)

All commands below work with no AI model:

```bat
audio-engine generate-music --prompt "battle" --duration 30 --output battle.wav
audio-engine generate-sfx --prompt "explosion" --duration 1.5 --output boom.wav
audio-engine generate-voice --text "Welcome, hero." --voice narrator --output voice.wav
```

Or launch the Studio and use the Synth Workbench for full manual control.

## Generating audio with MusicGen (AI mode)

```bat
audio-engine generate-music --prompt "epic orchestral battle theme" --duration 30 --output battle.wav --backend musicgen
audio-engine generate-sfx --prompt "large explosion with deep rumble" --duration 1.5 --output explosion.wav --backend musicgen
```

## If you already have the model

Place the pre-downloaded model folder in `models/` using this exact name:

- `models/musicgen-medium/`

Then run `setup.bat` (choose mode 2) to install Python dependencies.

## Hardware notes

- CPU-only works (slower AI generation)
- GPU is optional and can accelerate MusicGen significantly
- Procedural generation (mode 1) is fast on any hardware
- Once models are local, AI generation does not require internet

## Troubleshooting

### Python not found / wrong version
Install Python 3.11+ and ensure it is on PATH:
https://www.python.org/downloads/windows/

### `.venv` activation or dependency install failed
Run `setup.bat` again. If needed, delete `.venv/` and rerun setup.

In AI mode, if the neural install fails (common for Kokoro on Windows), setup automatically retries with the MusicGen-only dependency set (`.[musicgen]`).

If the install still fails, choose **mode 1** (Manual/Procedural) instead — all non-AI features work with no extra dependencies.

### Model download stalls or freezes

The MusicGen download is ~1.5 GB. If it stalls:

1. Press **Ctrl+C** to cancel
2. Set a Hugging Face token for faster authenticated downloads:
   ```bat
   set HF_TOKEN=your_token_here
   ```
   Get a free token at: https://huggingface.co/settings/tokens
3. Retry the download only:
   ```bat
   .venv\Scripts\activate.bat
   python tools\download_models.py
   ```

To skip the download and get manual placement instructions:
```bat
.venv\Scripts\activate.bat
python tools\download_models.py --skip
```

### Backend not available
Run:

```bat
audio-engine list-backends
```

If `musicgen` shows unavailable, verify `models/musicgen-medium/` exists and that `setup.bat` finished successfully in AI mode.

Procedural generation is always available even without the model.
