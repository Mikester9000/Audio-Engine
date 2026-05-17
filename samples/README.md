# Sample Drop-In Folder

This folder is for optional user-provided WAV orchestral samples that future remaster workflows can use.

The engine works without these samples. If this folder is empty, generation continues with the built-in synth.

## Current runtime-compatible folder structure

Current `SampleLibrary`/`SampleBackend` loading scans category folders directly under the selected `--samples-dir` root:

```text
samples/
  strings/
  brass/
  piano/
  choir/
  flute/
  bass/
  percussion/
  electric_guitar/
  synth_pad/
  sfx/
  voice/
```

The committed `samples/orchestral/*` scaffold is for the planned scanner/remaster workflow; until that lands, place active WAV content in top-level category folders above (or point `--samples-dir` directly at a category root that matches this layout).

## Naming convention

Use note names in this format:

- `{note}{octave}.wav`
- Examples: `C4.wav`, `G3.wav`, `A#4.wav`

## Recommended note coverage per instrument

At minimum include:

- `C3.wav`, `E3.wav`, `G3.wav`, `C4.wav`, `E4.wav`, `G4.wav`, `C5.wav`

The engine pitch-shifts between provided notes, so more notes improve quality.

## Instrument folder mapping

- `strings/` → synth `strings`
- `brass/` → synth `brass`
- `piano/` → synth `piano`
- `choir/` → synth `choir`
- `flute/` → synth `flute`
- `bass/` → synth `bass`
- `percussion/` → synth `percussion`
- `electric_guitar/` → guitar-family synth instruments
- `synth_pad/` → synth `synth_pad`

## Free sample sources

- Spitfire LABS (free tier)
- BBC Symphony Orchestra Discover (free tier)
- freesound.org CC0 samples

Always verify license terms before commercial use.

## Triggering remastering

Current CLI surface:

- `audio-engine remaster --input <wav> --samples-dir samples --output <wav>`

Notes:

- `--samples-dir` must point at the runtime-compatible root layout shown above.
- A future planned remaster/scanner pass will add direct orchestral-nested layout support.
