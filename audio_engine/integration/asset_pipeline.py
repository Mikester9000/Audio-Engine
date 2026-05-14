"""
asset_pipeline.py – pre-generate the complete audio asset library for the
Game Engine for Teaching, and execute factory generation-request batches.

Usage (from Python)
-------------------
>>> from audio_engine.integration import AssetPipeline
>>> pipeline = AssetPipeline(sample_rate=44100, seed=42)
>>> manifest = pipeline.generate_all("./game/assets/audio")
>>> print(manifest.summary())

Execute a generation-request batch from a factory JSON fixture:

>>> from audio_engine.integration import load_generation_request_batch
>>> batch = load_generation_request_batch("generation_requests.music.v1.json")
>>> result = pipeline.execute_request_batch(batch, "/tmp/output")
>>> print(result.summary())

Usage (from the CLI)
--------------------
    audio-engine generate-game-assets --output-dir ./game/assets/audio
    audio-engine generate-request-batch --request-file generation_requests.sfx.v1.json \\
        --output-dir /tmp/output

The pipeline creates three sub-directories:

    <output_dir>/
    ├── music/      # One WAV per GameState + named scenes
    ├── sfx/        # One WAV per in-game event
    └── voice/      # Voice/TTS lines

It also writes ``manifest.json`` at the root of *output_dir* so the C++
AudioSystem can verify all assets are present at startup.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

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

__all__ = ["AssetPipeline", "GenerationManifest", "RequestBatchRecord", "RequestBatchResult"]


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
            output_path = output_dir / request.output.target_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if not force and output_path.exists():
                self.progress_callback(f"  [skip] {request.request_id} → {output_path}")
                result.records.append(
                    RequestBatchRecord(
                        request_id=request.request_id,
                        asset_id=request.asset_id,
                        type=request.type,
                        seed=request.seed,
                        output_path=str(output_path),
                        status="skipped",
                    )
                )
                continue

            try:
                if request.type == "music":
                    self._execute_music_request(request, output_path, default_music_duration)
                elif request.type == "sfx":
                    self._execute_sfx_request(request, output_path, default_sfx_duration)
                elif request.type == "voice":
                    self._execute_voice_request(request, output_path)
                else:
                    raise ValueError(f"unsupported request type: {request.type!r}")

                result.records.append(
                    RequestBatchRecord(
                        request_id=request.request_id,
                        asset_id=request.asset_id,
                        type=request.type,
                        seed=request.seed,
                        output_path=str(output_path),
                        status="ok",
                    )
                )
                self.progress_callback(f"  [ok]   {request.request_id} → {output_path}")

            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                result.records.append(
                    RequestBatchRecord(
                        request_id=request.request_id,
                        asset_id=request.asset_id,
                        type=request.type,
                        seed=request.seed,
                        output_path=str(output_path),
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
    ) -> None:
        """Generate and export one music request using per-request seed."""
        from audio_engine.ai.music_gen import MusicGen

        gen = MusicGen(
            sample_rate=request.output.sample_rate,
            seed=request.seed,
        )
        gen.generate_to_file(
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
    ) -> None:
        """Generate and export one SFX request using per-request seed."""
        from audio_engine.ai.sfx_gen import SFXGen

        gen = SFXGen(
            sample_rate=request.output.sample_rate,
            seed=request.seed,
        )
        gen.generate_to_file(
            prompt=request.prompt,
            output_path=output_path,
            duration=default_duration,
        )

    def _execute_voice_request(
        self,
        request: "GenerationRequest",
        output_path: Path,
    ) -> None:
        """Generate and export one voice request using per-request seed."""
        from audio_engine.ai.voice_gen import VoiceGen
        from audio_engine.export.audio_exporter import AudioExporter

        voice_sr = request.output.sample_rate
        gen = VoiceGen(sample_rate=voice_sr, seed=request.seed)
        audio = gen.generate(request.prompt)
        exporter = AudioExporter(sample_rate=voice_sr, bit_depth=16)
        exporter.export(audio, output_path, fmt="wav")

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
