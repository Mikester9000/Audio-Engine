# Troubleshooting Playbook

> Update this file whenever a recurring failure mode becomes known.

## Installation failures

### `pip install -e ".[dev]"` fails

Check:

- Python version is at least 3.9
- virtual environment is active
- network access is available for `numpy`, `scipy`, and test dependencies

Recovery:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Test failures

### `pytest` fails after a docs-only change

That usually means the failure is unrelated or the environment changed. Confirm the diff really is docs-only, then rerun from a clean environment.

### `pytest` fails after generation changes

Prioritize reading:

- the failing test module
- the relevant subsystem page in `docs/AI_FACTORY/SUBSYSTEMS/`
- `audio_engine/cli.py` or the changed module

## Manifest validation failures

### `tools/validate-assets.py` fails

Check:

- schema path exists
- manifest fields still match the documented schema
- new example files are valid JSON
- CI workflow path filters still include the files you changed if appropriate

## Audio output triage

### Clipping or distortion

1. run `audio-engine qa --input <file>`
2. inspect true peak and clipping output
3. reduce gain, adjust mastering, or revisit the source synthesis chain
4. update `QA/QUALITY_BARS.md` if thresholds changed

### Loop seam clicks

1. run `audio-engine qa --input <file> --check-loop`
2. verify the asset should actually be loopable
3. check fade/zero-crossing behavior at the boundary
4. record whether the issue is generator-side or export-metadata-side

### Style mismatch

Symptoms:

- track is usable technically but wrong emotionally
- output feels too close to a known copyrighted work
- battle/town/dungeon categories blur together

Response:

1. revisit `STYLES/STYLE_FAMILIES.md`
2. adjust prompt descriptors toward emotion/instrumentation/gameplay role
3. avoid naming copyrighted works in output-facing metadata
4. capture the correction in review notes or future request schemas

### Weak voice quality

Treat current voice as lower-priority prototype output unless the PR specifically improves voice. Do not block music/SFX progress on voice polish.

## Repository recovery checklist

- confirm branch and diff are expected
- confirm no generated binaries were accidentally committed
- rerun tests
- rerun manifest validation
- review `HANDOFF.md` and `ACTIVE_WORK.md` to reestablish context

## When to create a new troubleshooting entry

Add a new section when:

- the same failure appears in more than one session
- a failure has a reliable diagnosis path
- future agents would likely hit it again
