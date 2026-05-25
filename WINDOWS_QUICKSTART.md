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

`setup.bat` will automatically:

1. Check Python version
2. Create `.venv/`
3. Install `pip install -e ".[neural]"` (with automatic fallback to `pip install -e ".[musicgen]"` if that install step fails)
4. Download AI model files into `models/`

The model download is about **~1.5GB total** and may take a few minutes the first time.

## Step 3: Double-click `run.bat`

`run.bat` activates the virtual environment and shows Audio Engine CLI commands.

After setup has finished once, generation runs fully offline from local files.

## What the AI model does

- **MusicGen Medium (`models/musicgen-medium/`)**: prompt-driven background music and sound effects

MusicGen Medium handles both music and sound effect generation. Voice synthesis uses the built-in procedural synthesiser.

## Generating audio

Examples (run from a terminal in the repo after `run.bat`):

```bat
audio-engine generate-music --prompt "epic orchestral battle theme" --duration 30 --output battle.wav --backend musicgen
audio-engine generate-sfx --prompt "large explosion with deep rumble" --duration 1.5 --output explosion.wav --backend musicgen
audio-engine generate-voice --text "Welcome, hero." --voice narrator --output voice.wav
```

## Generating general music for YouTube/streaming

```bat
audio-engine generate-music --prompt "cinematic orchestral music, emotional arc, suitable for YouTube" --duration 90 --output youtube_cinematic.wav --backend musicgen
audio-engine generate-music --prompt "solo piano composition, expressive, professional" --duration 120 --output youtube_piano.wav --backend musicgen
audio-engine generate-music --prompt "ambient atmospheric music, relaxing layered pads" --duration 120 --output youtube_ambient.wav --backend musicgen
```

## If you already have the model

Place the pre-downloaded model folder in `models/` using this exact name:

- `models/musicgen-medium/`

Then run `setup.bat` anyway to install Python dependencies.

## Hardware notes

- CPU-only works (slower generation)
- GPU is optional and can accelerate generation significantly
- Once models are local, normal generation does not require internet

## Troubleshooting

### Python not found / wrong version
Install Python 3.11+ and ensure it is on PATH:
https://www.python.org/downloads/windows/

### `.venv` activation or dependency install failed
Run `setup.bat` again. If needed, delete `.venv/` and rerun setup.

If stage 4 fails while installing full `.[neural]` dependencies, setup now automatically retries with the MusicGen-only dependency set (`.[musicgen]`) and continues when that succeeds.

### Model download interrupted
Run `setup.bat` again. `tools/download_models.py` resumes incomplete downloads and skips only model folders that already contain the required local files.

### Backend not available
Run:

```bat
audio-engine list-backends
```

If `musicgen` shows unavailable, verify `models/musicgen-medium/` exists and that `setup.bat` finished successfully.
