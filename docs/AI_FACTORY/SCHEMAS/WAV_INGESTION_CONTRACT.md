# WAV Sample-Folder Ingestion Contract

> **SESSION-030** — docs_only.
> Defines the deterministic folder layout, file naming, metadata, and rejection rules for
> user-provided WAV sample folders consumed by remaster workflows.
>
> Keep all requirements explicit so a low-reasoning agent can apply them without
> interpretation.

---

## 1. Root folder layout

```text
<samples-root>/          ← path passed to --samples-dir or SampleBackend
├── strings/             ← violin, viola, cello, double-bass WAV files
├── brass/               ← french horn, trumpet, trombone, tuba WAV files
├── choir/               ← vowel-pad WAV files
├── piano/               ← piano multi-samples
├── flute/               ← flute / woodwind samples
├── electric_guitar/     ← electric guitar samples
├── percussion/          ← kick, snare, hi-hat, tom WAV files
├── sfx/                 ← sound effect one-shots
├── orchestral_hit/      ← orchestral hit samples
├── crystal_synth/       ← crystal/bell synth samples
├── bass/                ← bass guitar or bass synth samples
├── ff7_lead/            ← FF7-style lead synth samples
├── ff7_strings/         ← FF7-style string samples
├── ff7_bass/            ← FF7-style bass samples
├── ff7_electric_guitar/ ← FF7-style electric guitar samples
├── harpsichord/         ← harpsichord samples
├── synth_pad/           ← synth pad samples
└── voice/               ← sung or spoken voice samples
```

- Every sample file **must be** placed inside one of the above named category
  sub-directories.
- Files placed at the root level (not in a sub-directory) are loaded into an
  internal `"root"` category and are **not** selected by name in generation
  requests.
- Sub-directories whose names do not match the list above are still scanned and
  loaded but will not be requested by name in generation commands.

---

## 2. Accepted file format

| Property        | Requirement                                              |
|-----------------|----------------------------------------------------------|
| Container       | WAV (`.wav` or `.WAV`)                                   |
| Encoding        | PCM linear (int16 or int32 preferred; float32 accepted)  |
| Channels        | Mono or stereo (multi-channel files are averaged to mono)|
| Sample rate     | Any — files are resampled to engine sample rate on load  |
| Bit depth       | 16, 24, or 32 bit                                        |
| Duration        | Any — engine will trim or loop to target duration        |
| File size limit | No hard limit; large files increase load time            |

---

## 3. Naming rules

- File names may be anything.  The scanner does **not** interpret names for
  pitch, note, or instrument metadata.
- Using descriptive names is recommended for human maintainability but is **not**
  enforced by the engine.
- Example good names: `violin_c4_pp.wav`, `brass_hit_01.wav`, `choir_ah.wav`
- The engine selects samples within a category by sequential index or randomly;
  naming does **not** affect which file is selected for a given request.

---

## 4. Pitch-shift behaviour

- The engine pitch-shifts samples at runtime using ratio-based resampling
  (`scipy.signal.resample_poly` when available, otherwise NumPy interpolation).
- This is the tracker/hardware-sampler approach: appropriate for PS1/PS2-era
  aesthetic targets.
- Pitch ratio is computed from the note interval requested by the generation
  pipeline.
- For best results, provide samples at their natural pitch; extreme pitch shifts
  (more than ±12 semitones) will introduce audible artefacts.

---

## 5. Rejection rules

The scanner **silently skips** (does not reject the whole folder) files that:

- Cannot be opened as a valid WAV file (corrupted, wrong container, etc.)
- Have zero frames after reading

Files with unsupported bit depths are loaded with best-effort type coercion.

No hard rejections of individual files will halt the entire ingestion; problematic
files are simply omitted from the category cache.

---

## 6. Ingestion verification

Run the following command to verify that samples are found:

```bash
# List available categories that have loaded samples
python - <<'EOF'
from audio_engine.samples.sample_library import SampleLibrary
lib = SampleLibrary("samples/", sample_rate=44100)
print("Loaded categories:", lib.available_categories())
EOF
```

Expected output includes all category names that contain at least one valid `.wav`
file.

---

## 7. CLI integration

The `--samples-dir` flag is supported by the following commands:

| Command                 | Effect                                              |
|-------------------------|-----------------------------------------------------|
| `generate-music`        | Enables sample-augmented music generation           |
| `generate-sfx`          | Enables sample-augmented SFX generation             |
| `generate-voice`        | Selects SampleBackend base (no voice blending)      |
| `remaster`              | Blends samples into an existing WAV file            |
| `generate-request-batch`| Forwarded via `--samples-dir` for sample backend    |
| `compose-piece`         | Enables sample-augmented piece composition          |
| `generate-track`        | Enables sample-augmented track generation           |
| `generate-radio-playlist`| Enables sample-augmented playlist generation       |
| `generate-album`        | Enables sample-augmented album generation           |

---

## 8. Related files

- `audio_engine/samples/sample_library.py` — scanner implementation
- `audio_engine/ai/sample_backend.py` — SampleBackend that uses this library
- `samples/README.md` — operator quick-start guide
- `docs/AI_FACTORY/SUBSYSTEMS/MUSIC.md` — music generation subsystem docs
