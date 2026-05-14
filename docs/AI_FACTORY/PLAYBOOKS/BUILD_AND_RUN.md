# Build and Run Playbook

> Update this file whenever installation, commands, or dependency strategy changes.

## Primary supported path

Primary development path today:

- Python on Linux/macOS
- local editable install
- CLI and pytest-based verification

Windows support is desired but lower priority. See [`../WINDOWS/SETUP.md`](../WINDOWS/SETUP.md).

## Environment setup

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Optional OGG export support

```bash
pip install -e ".[dev,ogg]"
```

## Core commands

### Run tests

```bash
pytest
```

### Validate asset manifests

```bash
python tools/validate-assets.py assets/examples/ --verbose
python tools/validate-assets.py assets/ --verbose
```

### Explore the CLI

```bash
audio-engine list-styles
audio-engine list-instruments
```

### Generate single assets

```bash
audio-engine generate --style battle --bars 8 --output battle.wav
audio-engine generate-music --prompt "dark ambient dungeon loop 90 BPM" --duration 60 --loop --output dungeon.wav
audio-engine generate-sfx --prompt "explosion impact" --duration 1.5 --output boom.wav
audio-engine generate-voice --text "Welcome, hero." --voice narrator --output greeting.wav
```

### Generate batch assets

```bash
audio-engine generate-game-assets --output-dir ./assets/audio
audio-engine generate-game-assets --output-dir ./assets/audio --only sfx
audio-engine generate-game-assets --output-dir ./assets/audio --force
```

### Verify generated batch assets

```bash
audio-engine verify-game-assets --assets-dir ./assets/audio
```

## Dependency strategy

### Required today

- `numpy>=1.24`
- `scipy>=1.10`
- Python `>=3.9`

### Optional today

- `soundfile>=0.12` for OGG export

### Future dependency policy

1. Prefer local/open tooling.
2. Keep the procedural backend working without extra model downloads.
3. Document any new backend dependency in this file and in relevant subsystem docs.
4. If a new dependency is required for production-quality generation, capture install, version, fallback, and failure mode.

## How to verify outputs manually

### Music

- confirm file exists and is non-empty
- run `audio-engine qa --input <file>`
- if intended to loop, also run `audio-engine qa --input <file> --check-loop`
- listen for obvious clipping, seam clicks, abrupt endings, or missing dynamics

### SFX

- confirm transient is audible
- confirm tail is not unintentionally cut off
- confirm loudness is appropriate for category
- check that repeated assets have useful variation if variation is expected

### Voice

- confirm intelligibility
- confirm line length roughly matches gameplay need
- treat current voice quality as prototype-grade unless explicitly improved

## Broken state recovery

If the repository seems broken:

1. recreate the virtual environment
2. reinstall with `pip install -e ".[dev]"`
3. rerun `pytest`
4. rerun manifest validation
5. check whether the change affected docs only, code only, or both
6. consult [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)

## Important note for future asset-factory work

As the repo matures, generation should move from ad hoc commands toward plan-driven and request-driven batch flows. When that happens, preserve these direct commands as debugging primitives even if a higher-level orchestration layer is added.
