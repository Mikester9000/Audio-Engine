"""
asset_pipeline.py – pre-generate the complete audio asset library for the
Game Engine for Teaching, plus a request-batch execution pipeline for
factory-driven generation workflows. Execute factory generation-request batches.

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

Execute a generation-request batch using the AssetPipeline (path-safe mode):

>>> from audio_engine.integration import load_generation_request_batch
>>> from audio_engine.integration.asset_pipeline import AssetPipeline
>>> batch = load_generation_request_batch("generation_requests.music.v1.json")
>>> pipeline = AssetPipeline()
>>> result = pipeline.execute_request_batch(batch, "/tmp/output")
>>> print(result.summary())

Usage (from the CLI)
--------------------
    audio-engine generate-game-assets --output-dir ./game/assets/audio
    audio-engine generate-request-batch --batch-file generation_requests.music.v1.json \
        --output-dir /tmp/factory_output
    audio-engine generate-request-batch --request-file generation_requests.sfx.v1.json \
        --output-dir /tmp/output

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
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path, PureWindowsPath
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
    from audio_engine.integration.factory_inputs import AudioPlan, GenerationRequest, GenerationRequestBatch

__all__ = ["ApprovalWorkflow", "AssetPipeline", "GenerationManifest", "RequestBatchPipeline", "PlanBatchOrchestrator", "DraftExportPipeline", "RequestBatchRecord", "RequestBatchResult"]


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
# RequestBatchResult
# ---------------------------------------------------------------------------

@dataclass
class RequestBatchRecord:
    """Record for a single generation request executed by :meth:`AssetPipeline.execute_request_batch`.

    Fields
    ------
    request_id:
        Unique identifier from the request fixture.
    asset_id:
        Asset identifier from the request.
    type:
        Request type: ``"music"``, ``"sfx"``, or ``"voice"``.
    seed:
        Seed used for this request (taken verbatim from the request).
    output_path:
        Absolute path to the output file (or intended path if skipped/failed).
    status:
        ``"ok"`` | ``"skipped"`` | ``"error"``.
    error:
        Error message when *status* is ``"error"``; ``None`` otherwise.
    """

    request_id: str
    asset_id: str
    type: str
    seed: int
    output_path: str
    status: str
    error: str | None = None


@dataclass
class RequestBatchResult:
    """Aggregated result of :meth:`AssetPipeline.execute_request_batch`.

    This is the machine-readable counterpart to :class:`GenerationManifest`
    for factory-input-driven (request-batch) execution paths.
    """

    output_dir: str
    """Base output directory used for this batch run."""

    project: str
    """Project name from the request batch."""

    scope: str
    """Scope label from the request batch."""

    records: list[RequestBatchRecord] = field(default_factory=list)
    """Per-request execution records."""

    total_duration_seconds: float = 0.0
    """Wall-clock time taken to execute all requests."""

    def summary(self) -> str:
        """Return a human-readable summary string."""
        ok = sum(1 for r in self.records if r.status == "ok")
        skipped = sum(1 for r in self.records if r.status == "skipped")
        errors = [r for r in self.records if r.status == "error"]
        lines = [
            f"Request-batch execution complete — {self.output_dir}",
            f"  Project : {self.project} / {self.scope}",
            f"  OK      : {ok}",
            f"  Skipped : {skipped}",
            f"  Errors  : {len(errors)}",
            f"  Total   : {len(self.records)} requests in {self.total_duration_seconds:.1f}s",
        ]
        for r in errors:
            lines.append(f"    • [{r.request_id}] {r.error}")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(
            {
                "output_dir": self.output_dir,
                "project": self.project,
                "scope": self.scope,
                "records": [asdict(r) for r in self.records],
                "total_duration_seconds": self.total_duration_seconds,
            },
            indent=2,
        )


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
    # Request-batch execution (factory-input driven)
    # ------------------------------------------------------------------

    def execute_request_batch(
        self,
        batch: "GenerationRequestBatch",
        output_dir: str | Path,
        *,
        force: bool = False,
        default_music_duration: float = 30.0,
        default_sfx_duration: float = 2.0,
    ) -> RequestBatchResult:
        """Execute all requests in a :class:`~audio_engine.integration.factory_inputs.GenerationRequestBatch`.

        Each request carries its own ``seed`` which is passed explicitly to the
        generator, ensuring deterministic reproduction from the same fixture.

        Parameters
        ----------
        batch:
            Typed request batch loaded by
            :func:`~audio_engine.integration.factory_inputs.load_generation_request_batch`.
        output_dir:
            Base directory under which output files are written.  Each
            request's ``output.targetPath`` is appended to this root, so the
            directory layout mirrors the project's content tree.
        force:
            If ``True``, regenerate files that already exist.  If ``False``
            (default), skip existing files.
        default_music_duration:
            Duration in seconds used for music requests that do not embed a
            duration in their prompt (default: 30 s).
        default_sfx_duration:
            Duration in seconds used for SFX requests that do not embed a
            duration in their prompt (default: 2 s).

        Returns
        -------
        RequestBatchResult
            Per-request execution records with status, seed, and output path.
        """
        output_dir = Path(output_dir)
        result = RequestBatchResult(
            output_dir=str(output_dir),
            project=batch.project,
            scope=batch.scope,
        )
        t_start = time.monotonic()

        for request in batch.requests:
            exported_path = request.output.target_path

            try:
                output_path = self._resolve_request_output_path(
                    output_dir=output_dir,
                    target_path=request.output.target_path,
                )
                exported_path = output_path.with_suffix(f".{request.output.format}")

                if not force and exported_path.exists():
                    self.progress_callback(f"  [skip] {request.request_id} → {exported_path}")
                    result.records.append(
                        RequestBatchRecord(
                            request_id=request.request_id,
                            asset_id=request.asset_id,
                            type=request.type,
                            seed=request.seed,
                            output_path=str(exported_path),
                            status="skipped",
                        )
                    )
                    continue

                if request.type == "music":
                    exported_path = self._execute_music_request(request, output_path, default_music_duration)
                elif request.type == "sfx":
                    exported_path = self._execute_sfx_request(request, output_path, default_sfx_duration)
                elif request.type == "voice":
                    exported_path = self._execute_voice_request(request, output_path)
                else:
                    raise ValueError(f"unsupported request type: {request.type!r}")

                result.records.append(
                    RequestBatchRecord(
                        request_id=request.request_id,
                        asset_id=request.asset_id,
                        type=request.type,
                        seed=request.seed,
                        output_path=str(exported_path),
                        status="ok",
                    )
                )
                self.progress_callback(f"  [ok]   {request.request_id} → {exported_path}")

            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                result.records.append(
                    RequestBatchRecord(
                        request_id=request.request_id,
                        asset_id=request.asset_id,
                        type=request.type,
                        seed=request.seed,
                        output_path=str(exported_path),
                        status="error",
                        error=msg,
                    )
                )
                self.progress_callback(f"  [err]  {request.request_id}: {msg}")

        result.total_duration_seconds = time.monotonic() - t_start
        return result

    def _execute_music_request(
        self,
        request: "GenerationRequest",
        output_path: Path,
        default_duration: float,
    ) -> Path:
        """Generate and export one music request using per-request seed."""
        from audio_engine.ai.music_gen import MusicGen

        output_path.parent.mkdir(parents=True, exist_ok=True)
        gen = MusicGen(
            sample_rate=request.output.sample_rate,
            backend=request.backend,
            seed=request.seed,
        )
        return gen.generate_to_file(
            prompt=request.prompt,
            output_path=output_path,
            duration=default_duration,
            loopable=request.qa.loop_required,
            fmt=request.output.format,
        )

    def _execute_sfx_request(
        self,
        request: "GenerationRequest",
        output_path: Path,
        default_duration: float,
    ) -> Path:
        """Generate and export one SFX request using per-request seed."""
        from audio_engine.ai.sfx_gen import SFXGen
        from audio_engine.export.audio_exporter import AudioExporter

        output_path.parent.mkdir(parents=True, exist_ok=True)
        gen = SFXGen(
            sample_rate=request.output.sample_rate,
            backend=request.backend,
            seed=request.seed,
        )
        audio = gen.generate(
            prompt=request.prompt,
            duration=default_duration,
        )
        audio = self._normalize_request_channels(audio, request.output.channels)
        exporter = AudioExporter(sample_rate=request.output.sample_rate, bit_depth=16)
        return exporter.export(audio, output_path, fmt=request.output.format)

    def _execute_voice_request(
        self,
        request: "GenerationRequest",
        output_path: Path,
    ) -> Path:
        """Generate and export one voice request using per-request seed."""
        from audio_engine.ai.voice_gen import VoiceGen
        from audio_engine.export.audio_exporter import AudioExporter

        output_path.parent.mkdir(parents=True, exist_ok=True)
        voice_sr = request.output.sample_rate
        gen = VoiceGen(sample_rate=voice_sr, backend=request.backend, seed=request.seed)
        audio = gen.generate(request.prompt)
        audio = self._normalize_request_channels(audio, request.output.channels)
        exporter = AudioExporter(sample_rate=voice_sr, bit_depth=16)
        return exporter.export(audio, output_path, fmt=request.output.format)

    @staticmethod
    def _resolve_request_output_path(*, output_dir: Path, target_path: str) -> Path:
        """Resolve and validate a request target path under ``output_dir``."""
        requested = Path(target_path)
        if requested.is_absolute() or PureWindowsPath(target_path).is_absolute():
            raise ValueError(f"unsafe targetPath (absolute paths are not allowed): {target_path}")
        if ".." in requested.parts:
            raise ValueError(f"unsafe targetPath (path traversal is not allowed): {target_path}")

        candidate = output_dir / requested
        root = output_dir.resolve()
        resolved_candidate = candidate.resolve(strict=False)
        try:
            is_within_root = os.path.commonpath([str(root), str(resolved_candidate)]) == str(root)
        except ValueError as exc:
            raise ValueError(
                f"unsafe targetPath (cross-drive paths are not allowed): {target_path}"
            ) from exc
        if not is_within_root:
            raise ValueError(f"unsafe targetPath escapes output directory: {target_path}")
        return candidate

    @staticmethod
    def _normalize_request_channels(audio: np.ndarray, channels: int) -> np.ndarray:
        """Normalize mono generator output to the requested channel count."""
        if channels == 1:
            return audio
        if channels == 2:
            if audio.ndim == 1:
                return np.column_stack((audio, audio))
            return audio
        raise ValueError(f"unsupported channel count {channels}; supported values are 1 or 2")

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
        A shape of ``(N, 1)`` is treated as mono.
    target_channels:
        Desired number of output channels.  Only 1 (mono) and 2 (stereo)
        are supported.

    Returns
    -------
    np.ndarray
        Audio in the requested channel layout.

    Raises
    ------
    ValueError
        If *target_channels* is not 1 or 2.
    """
    if target_channels not in (1, 2):
        raise ValueError(
            f"unsupported channel count {target_channels}; supported values are 1 or 2"
        )

    # Normalise (N, 1) to 1-D mono before conversion.
    if audio.ndim == 2 and audio.shape[1] == 1:
        audio = audio[:, 0]

    is_stereo = audio.ndim == 2 and audio.shape[1] == 2
    is_mono = audio.ndim == 1

    if target_channels == 1:
        if is_stereo:
            return audio.mean(axis=1).astype(audio.dtype)
        return audio
    else:  # target_channels == 2
        if is_mono:
            return np.column_stack([audio, audio])
        return audio


# ---------------------------------------------------------------------------
# RequestBatchPipeline
# ---------------------------------------------------------------------------

class RequestBatchPipeline:
    """Execute a :class:`~audio_engine.integration.factory_inputs.GenerationRequestBatch` deterministically.

    Each request in the batch is generated using the request's own ``seed``,
    ``prompt``, ``format``, ``sampleRate``, and ``channels``.  Outputs are
    written to ``<output_dir>/drafts/<type>/<request_id>.<format>``, using the
    request ID as the stem so that two requests with different directory prefixes
    but the same basename never collide.  The original ``targetImportPath`` is
    preserved in the ``.provenance.json`` sidecar for use by
    :class:`DraftExportPipeline`.

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

            # Use request_id as the stem to guarantee uniqueness across requests
            # that share a targetPath basename but differ in directory prefix.
            target_ext = f".{request.output.format.lower().lstrip('.')}"
            target_name = request.request_id + target_ext
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
            Actual path of the written file.
        """
        from audio_engine.export.audio_exporter import AudioExporter

        audio = self._generate_audio(request)
        audio = _convert_channels(audio, request.output.channels)

        exporter = AudioExporter(sample_rate=request.output.sample_rate, bit_depth=16)
        fmt = request.output.format.lower()
        written = exporter.export(audio, output_path, fmt=fmt)

        if request.qa.loop_required and written.suffix.lower() == ".wav":
            n_samples = audio.shape[0] if audio.ndim == 2 else len(audio)
            exporter.write_loop_points(written, loop_start=0, loop_end=n_samples - 1)

        return written

    def _generate_audio(self, request: GenerationRequest) -> np.ndarray:
        """Generate raw audio for *request* using the appropriate generator."""
        sr = request.output.sample_rate

        if request.type == "music":
            from audio_engine.ai.music_gen import MusicGen

            gen = MusicGen(sample_rate=sr, backend=request.backend, seed=request.seed)
            return gen.generate(
                prompt=request.prompt,
                loopable=request.qa.loop_required,
            )
        elif request.type == "sfx":
            from audio_engine.ai.sfx_gen import SFXGen

            gen = SFXGen(sample_rate=sr, backend=request.backend, seed=request.seed)
            return gen.generate(prompt=request.prompt)
        elif request.type == "voice":
            from audio_engine.ai.voice_gen import VoiceGen

            gen = VoiceGen(sample_rate=sr, backend=request.backend, seed=request.seed)
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


# ---------------------------------------------------------------------------
# PlanBatchOrchestrator
# ---------------------------------------------------------------------------

class PlanBatchOrchestrator:
    """Execute request batches using an audio plan as the selection contract.

    The plan determines which assets should be generated and in what order.
    Requests provide executable generation details (prompt, seed, backend, and
    output settings). Missing required plan targets are treated as errors.
    """

    def __init__(
        self,
        progress_callback: Callable[[str], None] | None = None,
        skip_existing: bool = True,
    ) -> None:
        self.progress_callback = progress_callback or (lambda msg: None)
        self.skip_existing = skip_existing

    def execute(
        self,
        plan: "AudioPlan",
        request_batches: list["GenerationRequestBatch"],
        output_dir: str | Path,
    ) -> GenerationManifest:
        """Select plan-targeted requests and execute via :class:`RequestBatchPipeline`."""
        selected_requests = self._select_requests(plan, request_batches)
        merged_batch = self._merge_selected_requests(plan, selected_requests)
        pipeline = RequestBatchPipeline(
            progress_callback=self.progress_callback,
            skip_existing=self.skip_existing,
        )
        return pipeline.execute(merged_batch, output_dir)

    def _select_requests(
        self,
        plan: "AudioPlan",
        request_batches: list["GenerationRequestBatch"],
    ) -> list["GenerationRequest"]:
        request_by_asset_id: dict[str, GenerationRequest] = {}
        seen_request_ids: set[str] = set()
        for batch in request_batches:
            for request in batch.requests:
                if request.request_id in seen_request_ids:
                    raise ValueError(f"duplicate requestId across request batches: {request.request_id}")
                seen_request_ids.add(request.request_id)
                if request.asset_id in request_by_asset_id:
                    raise ValueError(
                        f"duplicate assetId across request batches: {request.asset_id}"
                    )
                request_by_asset_id[request.asset_id] = request

        selected: list[GenerationRequest] = []
        missing_required: list[str] = []

        for group in plan.asset_groups:
            for target in group.targets:
                request = request_by_asset_id.get(target.asset_id)
                if request is None:
                    if group.required:
                        missing_required.append(target.asset_id)
                    continue

                if request.type != group.type:
                    raise ValueError(
                        f"plan/request type mismatch for assetId {target.asset_id}: "
                        f"plan={group.type}, request={request.type}"
                    )
                if request.output.target_path != target.target_path:
                    raise ValueError(
                        f"plan/request targetPath mismatch for assetId {target.asset_id}: "
                        f"plan={target.target_path}, request={request.output.target_path}"
                    )

                plan_format = Path(target.target_path).suffix.lower().lstrip(".")
                if plan_format not in {"wav", "ogg"}:
                    raise ValueError(
                        f"unsupported plan target format for assetId {target.asset_id}: .{plan_format}"
                    )

                request_target_format = Path(request.output.target_path).suffix.lower().lstrip(".")
                if request_target_format not in {"wav", "ogg"}:
                    raise ValueError(
                        f"unsupported request target format for assetId {target.asset_id}: .{request_target_format}"
                    )

                request_format = request.output.format.lower()
                if request_format != request_target_format:
                    raise ValueError(
                        f"request output format/targetPath mismatch for assetId {target.asset_id}: "
                        f"format={request.output.format}, targetPath={request.output.target_path}"
                    )
                if request_format != plan_format:
                    raise ValueError(
                        f"plan/request format mismatch for assetId {target.asset_id}: "
                        f"plan={plan_format}, request={request.output.format}"
                    )

                selected.append(request)

        if missing_required:
            raise ValueError(
                "missing generation requests for required plan assetIds: "
                + ", ".join(sorted(missing_required))
            )
        if not selected:
            raise ValueError("no matching requests found for audio plan targets")

        return selected

    @staticmethod
    def _merge_selected_requests(
        plan: "AudioPlan",
        selected_requests: list["GenerationRequest"],
    ) -> "GenerationRequestBatch":
        from audio_engine.integration.factory_inputs import GenerationRequestBatch

        return GenerationRequestBatch(
            request_batch_version="1.0.0",
            project=plan.project,
            scope=plan.scope,
            requests=selected_requests,
        )


# ---------------------------------------------------------------------------
# DraftExportPipeline
# ---------------------------------------------------------------------------

class DraftExportPipeline:
    """Copy draft assets from ``<factory_root>/drafts/`` to the GameRewritten export surface.

    Reads the ``<stem>.provenance.json`` sidecar alongside each audio file to
    determine the stable downstream filename (``targetImportPath``).  If no
    sidecar exists, the audio file's own name is used and placed under
    ``Content/Audio/``.

    Destination layout::

        <factory_root>/
        └── exports/
            └── gamerewritten/
                └── Content/
                    └── Audio/
                        ├── sfx_ui_confirm.wav
                        ├── bgm_field_day.wav
                        └── ...

    An ``export_manifest.json`` is written to
    ``<factory_root>/exports/gamerewritten/`` listing every source and
    destination path.

    Parameters
    ----------
    progress_callback:
        Optional callable ``(message: str) -> None`` invoked after each file
        is copied.
    """

    EXPORT_SUBDIR = Path("exports") / "gamerewritten"
    AUDIO_SUBDIR = Path("Content") / "Audio"

    def __init__(
        self,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.progress_callback = progress_callback or (lambda msg: None)

    def export(self, factory_root: str | Path) -> dict:
        """Copy all draft audio files to the GameRewritten export surface.

        Parameters
        ----------
        factory_root:
            Root of the factory output directory.  Must contain a ``drafts/``
            sub-directory with audio files (and optional ``.provenance.json``
            sidecars) generated by :class:`RequestBatchPipeline`.

        Returns
        -------
        dict
            The export manifest as a Python dict.  Also written to disk at
            ``<factory_root>/exports/gamerewritten/export_manifest.json``.

        Raises
        ------
        ValueError
            If no audio files are found in the ``drafts/`` sub-directory.
        """
        import datetime
        import shutil

        factory_root = Path(factory_root)
        drafts_dir = factory_root / "drafts"

        audio_files = sorted(
            f for f in drafts_dir.rglob("*")
            if f.suffix.lower() in {".wav", ".ogg"}
        )

        if not audio_files:
            raise ValueError(f"No audio files found under {drafts_dir}")

        export_root = factory_root / self.EXPORT_SUBDIR
        audio_root = export_root / self.AUDIO_SUBDIR
        audio_root.mkdir(parents=True, exist_ok=True)

        entries = []

        for audio_path in audio_files:
            target_path = self._resolve_target(audio_path, audio_root)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(audio_path), str(target_path))
            entries.append({
                "source": str(audio_path),
                "destination": str(target_path),
            })
            self.progress_callback(f"  [export]  {audio_path.name} → {target_path}")

        manifest = {
            "exportManifestVersion": "1.0.0",
            "factoryRoot": str(factory_root),
            "exportedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "summary": {"total": len(entries)},
            "entries": entries,
        }

        manifest_path = export_root / "export_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.progress_callback(f"export manifest written → {manifest_path}")

        return manifest

    @staticmethod
    def _resolve_target(audio_path: Path, audio_root: Path) -> Path:
        """Resolve the export destination path for *audio_path*.

        Reads the ``.provenance.json`` sidecar to get ``targetImportPath`` if
        available.  Falls back to the audio file's own name.

        The destination is rooted at *audio_root*.  The ``targetImportPath``
        value is expected to carry a ``Content/Audio/`` prefix (the canonical
        GameRewritten convention); that prefix is stripped and the remainder
        is used as a safe relative path under *audio_root*, preserving any
        intended subdirectories.  A containment check ensures that no path
        with ``..`` components can escape *audio_root*.

        Parameters
        ----------
        audio_path:
            Path of the draft audio file.
        audio_root:
            ``Content/Audio/`` directory under the export root.

        Returns
        -------
        Path
            Absolute destination path for the exported file.
        """
        from pathlib import PurePosixPath

        provenance_path = audio_path.with_name(audio_path.stem + ".provenance.json")
        if provenance_path.exists():
            try:
                provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
                raw_target = provenance.get("targetImportPath", "")
                if raw_target:
                    p = PurePosixPath(raw_target)
                    # Strip the canonical Content/Audio prefix if present so the
                    # remainder is the path relative to audio_root.
                    try:
                        rel = Path(*p.relative_to("Content/Audio").parts)
                    except ValueError:
                        # targetImportPath lacks the Content/Audio prefix; fall
                        # back to just the filename to avoid unintended nesting.
                        rel = Path(p.name)

                    if not rel.is_absolute() and ".." not in rel.parts:
                        candidate = audio_root / rel
                        root_r = os.path.normcase(str(audio_root.resolve(strict=False)))
                        cand_r = os.path.normcase(str(candidate.resolve(strict=False)))
                        try:
                            is_safe = os.path.commonpath([root_r, cand_r]) == root_r
                        except ValueError:
                            is_safe = False
                        if is_safe:
                            return candidate
            except Exception:
                pass  # Fall through to default
        return audio_root / audio_path.name


# ---------------------------------------------------------------------------
# ApprovalWorkflow
# ---------------------------------------------------------------------------

class ApprovalWorkflow:
    """Promote a draft audio asset to ``approved`` status.

    This workflow:

    1. Reads the ``.provenance.json`` sidecar for the given draft audio file.
    2. Updates ``reviewStatus`` to ``"approved"`` and records ``approvedAt``.
    3. Copies the audio file to ``<factory_root>/approved/<type>/``.
    4. Writes an updated provenance sidecar next to the approved copy and
       also updates the original draft provenance file in place.

    Parameters
    ----------
    progress_callback:
        Optional callable ``(message: str) -> None`` invoked after each step.
    """

    def __init__(
        self,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.progress_callback = progress_callback or (lambda msg: None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def approve(self, factory_root: str | Path, draft_path: str | Path) -> dict:
        """Approve a draft asset and copy it to ``<factory_root>/approved/<type>/``.

        Parameters
        ----------
        factory_root:
            Root of the factory output directory (contains ``drafts/`` and
            will receive an ``approved/`` sub-directory).
        draft_path:
            Path to the draft audio file.  It must exist and must be a WAV
            or OGG file.

        Returns
        -------
        dict
            Approval record with keys ``requestId``, ``assetId``, ``type``,
            ``draftPath``, ``approvedPath``, and ``approvedAt``.

        Raises
        ------
        FileNotFoundError
            If *draft_path* does not exist.
        ValueError
            If *draft_path* does not have a recognised audio extension.
        """
        import datetime
        import shutil

        factory_root = Path(factory_root).resolve()
        draft_path = Path(draft_path).resolve()

        # Ensure draft_path is under factory_root/drafts/ to prevent operating
        # on unrelated files outside the factory tree.
        drafts_root = factory_root / "drafts"
        try:
            draft_path.relative_to(drafts_root)
        except ValueError:
            raise ValueError(
                f"draft_path must be under <factory_root>/drafts/; "
                f"got {draft_path!s} (factory_root={factory_root!s})"
            )

        if not draft_path.exists():
            raise FileNotFoundError(f"draft file not found: {draft_path}")
        if draft_path.suffix.lower() not in {".wav", ".ogg"}:
            raise ValueError(
                f"unsupported file type {draft_path.suffix!r}; expected .wav or .ogg"
            )

        # Read or synthesise provenance sidecar.
        prov_path = draft_path.with_name(draft_path.stem + ".provenance.json")
        if prov_path.exists():
            provenance: dict = json.loads(prov_path.read_text(encoding="utf-8"))
        else:
            # No sidecar: infer minimal provenance from path conventions.
            provenance = {
                "provenanceVersion": "1.0.0",
                "requestId": draft_path.stem,
                "assetId": draft_path.stem,
                "type": draft_path.parent.name,
                "reviewStatus": "draft",
            }

        raw_type: str = provenance.get("type", draft_path.parent.name)
        # Validate asset_type: must be a single path component with no separators
        # or relative-path indicators to prevent writing outside approved/.
        asset_type = Path(raw_type).name
        if not asset_type or asset_type != raw_type or asset_type in {".", ".."}:
            raise ValueError(
                f"unsafe asset type {raw_type!r} in provenance; "
                "must be a plain directory name with no path separators"
            )
        approved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Build approved destination directory.
        approved_dir = factory_root / "approved" / asset_type
        approved_dir.mkdir(parents=True, exist_ok=True)
        approved_path = approved_dir / draft_path.name

        # Copy audio file.
        shutil.copy2(str(draft_path), str(approved_path))
        self.progress_callback(f"  [copy]  {draft_path.name} → {approved_path}")

        # Update provenance fields.
        provenance["reviewStatus"] = "approved"
        provenance["approvedAt"] = approved_at
        provenance["approvedPath"] = str(approved_path)
        updated_prov_text = json.dumps(provenance, indent=2)

        # Write updated provenance alongside the approved copy.
        approved_prov_path = approved_dir / (draft_path.stem + ".provenance.json")
        approved_prov_path.write_text(updated_prov_text, encoding="utf-8")
        self.progress_callback(f"  [prov]  provenance written → {approved_prov_path}")

        # Also update the original draft provenance so reviewStatus is consistent.
        prov_path.write_text(updated_prov_text, encoding="utf-8")

        record = {
            "requestId": provenance.get("requestId", draft_path.stem),
            "assetId": provenance.get("assetId", draft_path.stem),
            "type": asset_type,
            "draftPath": str(draft_path),
            "approvedPath": str(approved_path),
            "approvedAt": approved_at,
        }
        return record

    def approve_batch(
        self,
        factory_root: str | Path,
        draft_paths: list[str | Path],
    ) -> list[dict]:
        """Approve multiple draft assets in a single call.

        Parameters
        ----------
        factory_root:
            Root of the factory output directory.
        draft_paths:
            List of paths to draft audio files.

        Returns
        -------
        list[dict]
            One approval record per successfully approved file.  Errors for
            individual files are reported via *progress_callback* and recorded
            with ``"status": "error"`` in the returned list rather than raising.
        """
        records: list[dict] = []
        for draft_path in draft_paths:
            try:
                record = self.approve(factory_root, draft_path)
                record["status"] = "ok"
                records.append(record)
            except Exception as exc:  # noqa: BLE001
                self.progress_callback(f"  [err]  {Path(draft_path).name}: {exc}")
                records.append({
                    "draftPath": str(draft_path),
                    "status": "error",
                    "error": str(exc),
                })
        return records
