# Models Folder

This folder stores local AI model weights used by the Audio Engine.

## Model layout

- `models/musicgen-medium/` → `facebook/musicgen-medium`

## Why one model

MusicGen Medium is the chosen single-model baseline because it delivers much higher musical quality than small variants while still being practical for local/offline CPU workflows. It also provides acceptable sound-effect generation with strong prompting, which avoids maintaining separate AudioGen/Kokoro model downloads by default.

## How models get here

`setup.bat` automatically downloads this model into this folder by running:

- `python tools/download_models.py`

During setup, dependency installation is handled separately:

- setup first tries `pip install -e ".[neural]"`.
- if that install step fails locally, setup automatically falls back to `pip install -e ".[musicgen]"`.

This is a one-time download. After that, the engine loads from local files only.

## Git behavior

Model weights are intentionally gitignored and are **not** committed to this repository.
The folder itself is tracked so the expected path exists.

## Manual model placement

If you already downloaded the model separately, place it in the folder above using the exact name:

- `models/musicgen-medium/`
