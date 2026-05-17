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
3. Install `pip install -e ".[neural]"`
4. Download AI models into `models/`

The model download is about **~2GB total** and may take a few minutes the first time.

## Step 3: Double-click `run.bat`

`run.bat` activates the virtual environment and shows Audio Engine CLI commands.

After setup has finished once, generation runs fully offline from local files.

## What the AI models do

- **MusicGen (`models/musicgen-small/`)**: prompt-driven background music
- **AudioGen (`models/audiogen-medium/`)**: prompt-driven sound effects
- **Kokoro (`models/kokoro/`)**: local voice synthesis (TTS)

## Generating audio

Examples (run from a terminal in the repo after `run.bat`):

```bat
audio-engine generate-music --prompt "epic orchestral battle theme" --duration 30 --output battle.wav --backend musicgen
audio-engine generate-sfx --prompt "large explosion with rumble" --duration 1.5 --output explosion.wav --backend audiogen
audio-engine generate-voice --text "Welcome, hero." --voice narrator --output voice.wav --backend kokoro
```

## If you already have the models

Place pre-downloaded model folders in `models/` using these exact names:

- `models/musicgen-small/`
- `models/audiogen-medium/`
- `models/kokoro/`

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

### Model download interrupted
Run `setup.bat` again. `tools/download_models.py` is idempotent and resumes/skips existing folders.

### Backend not available
Run:

```bat
audio-engine list-backends
```

If neural backends show unavailable, verify model folders exist under `models/` and that `setup.bat` finished successfully.
