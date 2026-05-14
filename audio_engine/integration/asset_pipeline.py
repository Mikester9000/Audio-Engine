"""
asset_pipeline.py – pre-generate the complete audio asset library for the
Game Engine for Teaching, plus a request-batch execution pipeline for
factory-driven generation workflows.

Usage (from Python)
-------------------
>>> from audio_engine.integration import AssetPipeline
>>> pipeline = AssetPipeline(sample_rate=44100, seed=42)
>>> manifest = pipeline.generate_all("./game/assets/audio")
>>> print(manifest.summary())

>>> from audio_engine.integration import RequestBatchPipeline, load_generation_request_batch
>>> batch = load_generation_request_batch("generation_requests.music.v1.json")
>>> pipeline = RequestBatchPipeline()
>>> manifest = pipeline.execute(batch, "/tmp/factory_output")

Usage (from the CLI)
--------------------
    audio-engine generate-game-assets --output-dir ./game/assets/audio
    audio-engine generate-request-batch --batch-file generation_requests.music.v1.json \\
        --output-dir /tmp/factory_output

The AssetPipeline creates three sub-directories:

    <output_dir>/
    ├── music/      # One WAV per GameState + named scenes
    ├── sfx/        # One WAV per in-game event
    └── voice/      # Voice/TTS lines

The RequestBatchPipeline creates:

    <output_dir>/
    └── drafts/
        ├── music/    # Generated music from batch requests
        ├── sfx/      # Generated SFX from batch requests
        └── voice/    # Generated voice from batch requests

It also writes ``manifest.json`` at the root of *output_dir* so the C++
AudioSystem can verify all assets are present at startup.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import numpy as np

from audio_engine.integration.game_state_map import (
    MUSIC_MANIFEST,
    SFX_MANIFEST,
    VOICE_MANIFEST,
    MusicAsset,
    SFXAsset,
    VoiceAsset,
)

if TYPE_CHECKING:
    from audio_engine.integration.factory_inputs import GenerationRequest, GenerationRequestBatch

__all__ = ["AssetPipeline", "GenerationManifest", "RequestBatchPipeline"]


# ---------------------------------------------------------------------------
# GenerationManifest
# ---------------------------------------------------------------------------

@dataclass
class GenerationManifest:
    """Records every generated asset along with its path and timing.

    This is serialised as ``manifest.json`` so the C++ ``AudioSystem`` can
    verify all files are present at startup and report meaningful errors when
    an asset is missing.
    """

    output_dir: str
    """Root output directory."""

    music: list[dict] = field(default_factory=list)
    """List of generated music asset records."""

    sfx: list[dict] = field(default_factory=list)
    """List of generated SFX asset records."""

    voice: list[dict] = field(default_factory=list)
    """List of generated voice asset records."""

    errors: list[str] = field(default_factory=list)
    """Non-fatal error messages (assets that failed to generate)."""

    total_duration_seconds: float = 0.0
    """Wall-clock time taken to generate all assets."""

    def summary(self) -> str:
        """Return a human-readable summary string."""
        n_ok = len(self.music) + len(self.sfx) + len(self.voice)
        n_err = len(self.errors)
        lines = [
            f"Asset pipeline complete — {self.output_dir}",
            f"  Music  : {len(self.music)} tracks",
            f"  SFX    : {len(self.sfx)} effects",
            f"  Voice  : {len(self.voice)} lines",
            f"  Total  : {n_ok} assets generated in {self.total_duration_seconds:.1f}s",
        ]
        if n_err:
            lines.append(f"  Errors : {n_err}")
            for err in self.errors:
                lines.append(f"    • {err}")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialise to a JSON string (written to ``manifest.json``)."""
        return json.dumps(
            {
                "output_dir": self.output_dir,
                "music": self.music,
                "sfx": self.sfx,
                "voice": self.voice,
                "errors": self.errors,
                "total_duration_seconds": self.total_duration_seconds,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> "GenerationManifest":
        """Deserialise from a JSON string."""
        d = json.loads(text)
        return cls(**d)


# ---------------------------------------------------------------------------
# AssetPipeline
# ---------------------------------------------------------------------------

class AssetPipeline:
    """Pre-generate all audio assets required by the Game Engine for Teaching.

    Parameters
    ----------
    sample_rate:
        Audio sample rate in Hz for all exported files (default 44 100 Hz).
    seed:
        Random seed for reproducible generation.  ``None`` = random.
    progress_callback:
        Optional callable ``(message: str) -> None`` called after each asset
        is generated.  Useful for CLI progress reporting.
    skip_existing:
        If ``True`` (default), skip assets whose output file already exists.
        Set to ``False`` to regenerate everything.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        seed: int | None = None,
        progress_callback: Callable[[str], None] | None = None,
        skip_existing: bool = True,
    ) -> None:
        self.sample_rate = sample_rate
        self.seed = seed
        self.progress_callback = progress_callback or (lambda msg: None)
        self.skip_existing = skip_existing

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all(self, output_dir: str | Path) -> GenerationManifest:
        """Generate the complete audio asset library.

        Parameters
        ----------
        output_dir:
            Root directory where assets will be written.  Created if it
            doesn't exist.  Three sub-directories are created: ``music/``,
            ``sfx/``, and ``voice/``.

        Returns
        -------
        GenerationManifest
            Record of every generated asset.  Also written to
            ``<output_dir>/manifest.json``.
        """
        output_dir = Path(output_dir)
        music_dir = output_dir / "music"
        sfx_dir = output_dir / "sfx"
        voice_dir = output_dir / "voice"
        for d in (music_dir, sfx_dir, voice_dir):
            d.mkdir(parents=True, exist_ok=True)

        manifest = GenerationManifest(output_dir=str(output_dir))
        t_start = time.monotonic()

        # --- Music ---
        self.progress_callback("Generating music tracks…")
        for asset in MUSIC_MANIFEST:
            path = music_dir / asset.filename
            if self.skip_existing and path.exists():
                self.progress_callback(f"  [skip] {asset.filename}")
                manifest.music.append(
                    {"game_state": asset.game_state, "file": str(path), "status": "skipped"}
                )
                continue
            try:
                self._generate_music(asset, path)
                manifest.music.append(
                    {"game_state": asset.game_state, "file": str(path), "status": "ok"}
                )
                self.progress_callback(f"  [ok]   {asset.filename}")
            except Exception as exc:  # noqa: BLE001
                msg = f"music/{asset.filename}: {exc}"
                manifest.errors.append(msg)
                self.progress_callback(f"  [err]  {msg}")

        # --- SFX ---
        self.progress_callback("Generating SFX…")
        for asset in SFX_MANIFEST:
            path = sfx_dir / asset.filename
            if self.skip_existing and path.exists():
                self.progress_callback(f"  [skip] {asset.filename}")
                manifest.sfx.append(
                    {"event": asset.event, "file": str(path), "status": "skipped"}
                )
                continue
            try:
                self._generate_sfx(asset, path)
                manifest.sfx.append(
                    {"event": asset.event, "file": str(path), "status": "ok"}
                )
                self.progress_callback(f"  [ok]   {asset.filename}")
            except Exception as exc:  # noqa: BLE001
                msg = f"sfx/{asset.filename}: {exc}"
                manifest.errors.append(msg)
                self.progress_callback(f"  [err]  {msg}")

        # --- Voice ---
        self.progress_callback("Generating voice lines…")
        for asset in VOICE_MANIFEST:
            path = voice_dir / asset.filename
            if self.skip_existing and path.exists():
                self.progress_callback(f"  [skip] {asset.filename}")
                manifest.voice.append(
                    {"key": asset.key, "file": str(path), "status": "skipped"}
                )
                continue
            try:
                self._generate_voice(asset, path)
                manifest.voice.append(
                    {"key": asset.key, "file": str(path), "status": "ok"}
                )
                self.progress_callback(f"  [ok]   {asset.filename}")
            except Exception as exc:  # noqa: BLE001
                msg = f"voice/{asset.filename}: {exc}"
                manifest.errors.append(msg)
                self.progress_callback(f"  [err]  {msg}")

        manifest.total_duration_seconds = time.monotonic() - t_start

        # Write manifest
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")
        self.progress_callback(f"manifest written → {manifest_path}")

        return manifest

    def generate_music_only(self, output_dir: str | Path) -> GenerationManifest:
        """Generate only the music tracks (skip SFX and voice)."""
        output_dir = Path(output_dir)
        music_dir = output_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)
        manifest = GenerationManifest(output_dir=str(output_dir))
        t_start = time.monotonic()
        for asset in MUSIC_MANIFEST:
            path = music_dir / asset.filename
            try:
                self._generate_music(asset, path)
                manifest.music.append(
                    {"game_state": asset.game_state, "file": str(path), "status": "ok"}
                )
            except Exception as exc:  # noqa: BLE001
                manifest.errors.append(f"music/{asset.filename}: {exc}")
        manifest.total_duration_seconds = time.monotonic() - t_start
        return manifest

    def generate_sfx_only(self, output_dir: str | Path) -> GenerationManifest:
        """Generate only the SFX library (skip music and voice)."""
        output_dir = Path(output_dir)
        sfx_dir = output_dir / "sfx"
        sfx_dir.mkdir(parents=True, exist_ok=True)
        manifest = GenerationManifest(output_dir=str(output_dir))
        t_start = time.monotonic()
        for asset in SFX_MANIFEST:
            path = sfx_dir / asset.filename
            if self.skip_existing and path.exists():
                self.progress_callback(f"  [skip] {asset.filename}")
                manifest.sfx.append(
                    {"event": asset.event, "file": str(path), "status": "skipped"}
                )
                continue
            try:
                self._generate_sfx(asset, path)
                manifest.sfx.append(
                    {"event": asset.event, "file": str(path), "status": "ok"}
                )
                self.progress_callback(f"  [ok]   {asset.filename}")
            except Exception as exc:  # noqa: BLE001
                manifest.errors.append(f"sfx/{asset.filename}: {exc}")
        manifest.total_duration_seconds = time.monotonic() - t_start
        return manifest

    def generate_voice_only(self, output_dir: str | Path) -> GenerationManifest:
        """Generate only the voice lines (skip music and SFX)."""
        output_dir = Path(output_dir)
        voice_dir = output_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)
        manifest = GenerationManifest(output_dir=str(output_dir))
        t_start = time.monotonic()
        for asset in VOICE_MANIFEST:
            path = voice_dir / asset.filename
            if self.skip_existing and path.exists():
                self.progress_callback(f"  [skip] {asset.filename}")
                manifest.voice.append(
                    {"key": asset.key, "file": str(path), "status": "skipped"}
                )
                continue
            try:
                self._generate_voice(asset, path)
                manifest.voice.append(
                    {"key": asset.key, "file": str(path), "status": "ok"}
                )
                self.progress_callback(f"  [ok]   {asset.filename}")
            except Exception as exc:  # noqa: BLE001
                manifest.errors.append(f"voice/{asset.filename}: {exc}")
        manifest.total_duration_seconds = time.monotonic() - t_start
        return manifest

    def verify(self, output_dir: str | Path) -> dict[str, list[str]]:
        """Check that all expected asset files exist in *output_dir*.

        Returns
        -------
        dict
            ``{"missing": [...], "present": [...]}`` keyed by relative path.
        """
        output_dir = Path(output_dir)
        missing: list[str] = []
        present: list[str] = []

        for asset in MUSIC_MANIFEST:
            rel = f"music/{asset.filename}"
            (present if (output_dir / rel).exists() else missing).append(rel)
        for asset in SFX_MANIFEST:
            rel = f"sfx/{asset.filename}"
            (present if (output_dir / rel).exists() else missing).append(rel)
        for asset in VOICE_MANIFEST:
            rel = f"voice/{asset.filename}"
            (present if (output_dir / rel).exists() else missing).append(rel)

        return {"present": present, "missing": missing}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_music(self, asset: MusicAsset, output_path: Path) -> None:
        """Generate and export one music track using the AI pipeline + mastering."""
        from audio_engine.ai.music_gen import MusicGen
        from audio_engine.render.offline_bounce import OfflineBounce
        from audio_engine.export.audio_exporter import AudioExporter

        gen = MusicGen(sample_rate=self.sample_rate, seed=self.seed)
        audio = gen.generate(
            prompt=asset.prompt,
            duration=asset.duration,
            loopable=asset.loopable,
        )

        # Master the audio through the offline bounce chain
        bounce = OfflineBounce(
            sample_rate=self.sample_rate,
            target_lufs=-16.0,
            ceiling_db=-1.0,
        )
        mastered = bounce.process(audio)

        exporter = AudioExporter(sample_rate=self.sample_rate, bit_depth=16)
        exporter.export(mastered, output_path, fmt="wav")

        if asset.loopable:
            n_samples = mastered.shape[0] if mastered.ndim == 2 else len(mastered)
            exporter.write_loop_points(output_path, loop_start=0, loop_end=n_samples - 1)

    def _generate_sfx(self, asset: SFXAsset, output_path: Path) -> None:
        """Generate and export one SFX clip."""
        from audio_engine.ai.sfx_gen import SFXGen
        from audio_engine.export.audio_exporter import AudioExporter

        gen = SFXGen(sample_rate=self.sample_rate, seed=self.seed)
        audio = gen.generate(
            prompt=asset.prompt,
            duration=asset.duration,
            pitch_hz=asset.pitch_hz,
        )

        exporter = AudioExporter(sample_rate=self.sample_rate, bit_depth=16)
        exporter.export(audio, output_path, fmt="wav")

    def _generate_voice(self, asset: VoiceAsset, output_path: Path) -> None:
        """Generate and export one voice/TTS line."""
        from audio_engine.ai.voice_gen import VoiceGen
        from audio_engine.export.audio_exporter import AudioExporter

        voice_sr = 22050  # TTS typically uses 22050 Hz
        gen = VoiceGen(sample_rate=voice_sr, seed=self.seed)
        audio = gen.generate(asset.text, voice=asset.voice)

        exporter = AudioExporter(sample_rate=voice_sr, bit_depth=16)
        exporter.export(audio, output_path, fmt="wav")


# ---------------------------------------------------------------------------
# Channel conversion helper
# ---------------------------------------------------------------------------

def _convert_channels(audio: np.ndarray, target_channels: int) -> np.ndarray:
    """Convert a NumPy audio array to the requested channel count.

    Parameters
    ----------
    audio:
        Input array: 1-D (mono) or shape ``(N, 2)`` (stereo).
        A shape of ``(N, 1)`` is treated as mono.  Arrays with more than 2
        channels are passed through unchanged.
    target_channels:
        Desired number of output channels (1 or 2).  Values other than 1 or 2
        result in a pass-through without conversion.

    Returns
    -------
    np.ndarray
        Audio in the requested channel layout.
    """
    # Normalise (N, 1) to 1-D mono before conversion.
    if audio.ndim == 2 and audio.shape[1] == 1:
        audio = audio[:, 0]

    is_stereo = audio.ndim == 2 and audio.shape[1] == 2
    is_mono = audio.ndim == 1

    if target_channels == 1:
        if is_stereo:
            return audio.mean(axis=1).astype(audio.dtype)
        return audio
    elif target_channels == 2:
        if is_mono:
            return np.column_stack([audio, audio])
        return audio
    # Unsupported channel count: return audio unchanged (caller's responsibility).
    return audio


# ---------------------------------------------------------------------------
# RequestBatchPipeline
# ---------------------------------------------------------------------------

class RequestBatchPipeline:
    """Execute a :class:`~audio_engine.integration.factory_inputs.GenerationRequestBatch` deterministically.

    Each request in the batch is generated using the request's own ``seed``,
    ``prompt``, ``format``, ``sampleRate``, and ``channels``.  Outputs are
    written to ``<output_dir>/drafts/<type>/<basename_of_targetPath>``.

    Parameters
    ----------
    progress_callback:
        Optional callable ``(message: str) -> None`` invoked after each asset
        is processed.
    skip_existing:
        If ``True`` (default), skip requests whose output file already exists.
    """

    def __init__(
        self,
        progress_callback: Callable[[str], None] | None = None,
        skip_existing: bool = True,
    ) -> None:
        self.progress_callback = progress_callback or (lambda msg: None)
        self.skip_existing = skip_existing

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        batch: GenerationRequestBatch,
        output_dir: str | Path,
    ) -> GenerationManifest:
        """Execute all requests in *batch* and return a :class:`GenerationManifest`.

        Parameters
        ----------
        batch:
            Loaded :class:`~audio_engine.integration.factory_inputs.GenerationRequestBatch`.
        output_dir:
            Root output directory.  Each request is written to
            ``<output_dir>/drafts/<type>/<filename>``.

        Returns
        -------
        GenerationManifest
            Record of every generated (or skipped) asset, plus any errors.
            Also written to ``<output_dir>/drafts/batch_manifest.json``.
        """
        output_dir = Path(output_dir)
        manifest = GenerationManifest(output_dir=str(output_dir))
        t_start = time.monotonic()

        self.progress_callback(
            f"Executing request batch: {batch.project} / {batch.scope} "
            f"({len(batch.requests)} requests) → {output_dir}"
        )

        for request in batch.requests:
            type_dir = output_dir / "drafts" / request.type
            type_dir.mkdir(parents=True, exist_ok=True)

            # Derive output filename from targetPath basename.
            target_name = Path(request.output.target_path).name
            output_path = type_dir / target_name

            if self.skip_existing and output_path.exists():
                self.progress_callback(f"  [skip] {request.request_id} → {output_path}")
                self._append_record(manifest, request, output_path, "skipped")
                continue

            try:
                actual_path = self._generate_one(request, output_path)
                self._write_provenance(request, actual_path)
                self.progress_callback(f"  [ok]   {request.request_id} → {actual_path}")
                self._append_record(manifest, request, actual_path, "ok")
            except Exception as exc:  # noqa: BLE001
                msg = f"{request.request_id}: {exc}"
                manifest.errors.append(msg)
                self.progress_callback(f"  [err]  {msg}")

        manifest.total_duration_seconds = time.monotonic() - t_start

        # Write batch manifest under drafts/
        drafts_dir = output_dir / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = drafts_dir / "batch_manifest.json"
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")
        self.progress_callback(f"manifest written → {manifest_path}")

        return manifest

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_one(self, request: GenerationRequest, output_path: Path) -> Path:
        """Generate audio for one request and write it to *output_path*.

        Parameters
        ----------
        request:
            A single :class:`~audio_engine.integration.factory_inputs.GenerationRequest`.
        output_path:
            Desired output file path.

        Returns
        -------
        Path
            Actual path of the written file (may differ in extension if OGG
            fallback to WAV is needed).
        """
        from audio_engine.export.audio_exporter import AudioExporter

        audio = self._generate_audio(request)
        audio = _convert_channels(audio, request.output.channels)

        exporter = AudioExporter(sample_rate=request.output.sample_rate, bit_depth=16)
        fmt = request.output.format.lower()

        try:
            written = exporter.export(audio, output_path, fmt=fmt)
        except ImportError:
            # OGG requires optional soundfile dependency; fall back to WAV.
            self.progress_callback(
                f"  [warn] OGG not available for {request.request_id}; writing WAV instead"
            )
            written = exporter.export(audio, output_path.with_suffix(".wav"), fmt="wav")

        if request.qa.loop_required and written.suffix.lower() == ".wav":
            n_samples = audio.shape[0] if audio.ndim == 2 else len(audio)
            exporter.write_loop_points(written, loop_start=0, loop_end=n_samples - 1)

        return written

    def _generate_audio(self, request: GenerationRequest) -> np.ndarray:
        """Generate raw audio for *request* using the appropriate generator."""
        sr = request.output.sample_rate

        if request.type == "music":
            from audio_engine.ai.music_gen import MusicGen

            gen = MusicGen(sample_rate=sr, seed=request.seed)
            return gen.generate(
                prompt=request.prompt,
                loopable=request.qa.loop_required,
            )
        elif request.type == "sfx":
            from audio_engine.ai.sfx_gen import SFXGen

            gen = SFXGen(sample_rate=sr, seed=request.seed)
            return gen.generate(prompt=request.prompt)
        elif request.type == "voice":
            from audio_engine.ai.voice_gen import VoiceGen

            gen = VoiceGen(sample_rate=sr, seed=request.seed)
            return gen.generate(request.prompt)
        else:
            raise ValueError(f"Unknown request type: {request.type!r}")

    def _append_record(
        self,
        manifest: GenerationManifest,
        request: GenerationRequest,
        path: Path,
        status: str,
    ) -> None:
        """Append a result record to the appropriate manifest list."""
        record: dict = {
            "request_id": request.request_id,
            "asset_id": request.asset_id,
            "type": request.type,
            "seed": request.seed,
            "file": str(path),
            "status": status,
        }
        if request.type == "music":
            manifest.music.append(record)
        elif request.type == "sfx":
            manifest.sfx.append(record)
        else:
            manifest.voice.append(record)

    def _write_provenance(
        self,
        request: GenerationRequest,
        output_path: Path,
    ) -> None:
        """Write a machine-readable provenance sidecar file next to *output_path*.

        The provenance file is named ``<stem>.provenance.json`` and contains
        the request ID, seed, backend, review status, and generation timestamp
        so that each generated file is independently traceable.

        Parameters
        ----------
        request:
            The :class:`~audio_engine.integration.factory_inputs.GenerationRequest`
            that produced *output_path*.
        output_path:
            Path of the generated audio file.
        """
        import datetime

        provenance = {
            "provenanceVersion": "1.0.0",
            "requestId": request.request_id,
            "assetId": request.asset_id,
            "type": request.type,
            "backend": request.backend,
            "seed": request.seed,
            "prompt": request.prompt,
            "styleFamily": request.style_family,
            "generatedOutputPath": str(output_path),
            "targetImportPath": request.output.target_path,
            "reviewStatus": request.qa.review_status,
            "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        provenance_path = output_path.with_name(output_path.stem + ".provenance.json")
        provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
