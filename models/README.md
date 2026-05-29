# Models Folder

This folder stores local AI model weights used by the Audio Engine.

## Model layout

- `models/musicgen-small/` → `facebook/musicgen-small`
- `models/musicgen-medium/` → `facebook/musicgen-medium`

## Why these models

MusicGen Medium remains the higher-quality baseline for local/offline workflows, while MusicGen Small provides a lighter-weight option with faster load times and lower memory requirements. Both are supported so users can trade quality for hardware practicality without changing the overall workflow.

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

- `models/musicgen-small/`
- `models/musicgen-medium/`
