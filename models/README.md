# Models Folder

This folder stores local AI model weights used by the Audio Engine.

## Model layout

- `models/musicgen-small/` → `facebook/musicgen-small`
- `models/audiogen-medium/` → `facebook/audiogen-medium`
- `models/kokoro/` → `hexgrad/Kokoro-82M`

## How models get here

`setup.bat` automatically downloads these models into this folder by running:

- `python tools/download_models.py`

This is a one-time download. After that, the engine loads from local files only.

## Git behavior

Model weights are intentionally gitignored and are **not** committed to this repository.
The folder itself is tracked so the expected path exists.

## Manual model placement

If you already downloaded the models separately, place each model in the folder above using the exact names:

- `models/musicgen-small/`
- `models/audiogen-medium/`
- `models/kokoro/`
