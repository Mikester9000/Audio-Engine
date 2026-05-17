# Sample Drop-In Folder

This folder is for optional user-provided WAV orchestral samples that future remaster workflows can use.

The engine works without these samples. If this folder is empty, generation continues with the built-in synth.

## Required folder structure

```text
samples/
  orchestral/
    strings/
    brass/
    piano/
    choir/
    flute/
    bass/
    percussion/
    guitar/
    synth_pad/
  sfx/
  voice/
```

## Naming convention

Use note names in this format:

- `{note}{octave}.wav`
- Examples: `C4.wav`, `G3.wav`, `A#4.wav`

## Recommended note coverage per instrument

At minimum include:

- `C3.wav`, `E3.wav`, `G3.wav`, `C4.wav`, `E4.wav`, `G4.wav`, `C5.wav`

The engine pitch-shifts between provided notes, so more notes improve quality.

## Instrument folder mapping

- `orchestral/strings/` → synth `strings`
- `orchestral/brass/` → synth `brass`
- `orchestral/piano/` → synth `piano`
- `orchestral/choir/` → synth `choir`
- `orchestral/flute/` → synth `flute`
- `orchestral/bass/` → synth `bass`
- `orchestral/percussion/` → synth `percussion`
- `orchestral/guitar/` → guitar-family synth instruments
- `orchestral/synth_pad/` → synth `synth_pad`

## Free sample sources

- Spitfire LABS (free tier)
- BBC Symphony Orchestra Discover (free tier)
- freesound.org CC0 samples

Always verify license terms before commercial use.

## Triggering remastering

A remaster command is planned for an upcoming session:

- `audio-engine remaster --input <wav> --samples samples/orchestral/ --output <wav>`

Once implemented, this command will replay generated note events and substitute matching sample voices when available.
