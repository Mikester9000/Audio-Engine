"""
Deterministic WAV delivery pipeline for commercial audio asset distribution.

Reads from the ``approved/`` factory output tree, writes renamed copies to a
delivery directory using a deterministic stable naming contract, and emits a
machine-readable ``delivery_manifest.json`` that maps every source file to its
delivery destination.

Naming contract
---------------
Delivery filenames follow the pattern::

    <category>__<asset_id>__seed<seed>.wav

where:

- ``category``  – asset type sub-directory (``music``, ``sfx``, ``voice``, …)
- ``asset_id``  – stable asset identifier from the provenance sidecar
  (``assetId`` field) or the file stem when no sidecar is present.
- ``seed``      – generation seed from provenance (``seed`` field) or ``0000``
  when unavailable.

This naming is intentionally collision-resistant and sortable without a
manifest: category prefix allows directory-less sorting, asset_id carries
semantic meaning, and seed makes exact variant identity unambiguous.

Usage
-----
>>> from audio_engine.integration.export_contract import WavDeliveryPipeline
>>> pipeline = WavDeliveryPipeline()
>>> report = pipeline.deliver(
...     factory_root="/tmp/factory",
...     delivery_dir="/tmp/delivery/v1",
... )
>>> print(report["summary"])
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

__all__ = ["WavDeliveryPipeline"]

_AUDIO_EXTS = {".wav", ".ogg"}


def _deterministic_delivery_name(
    category: str,
    asset_id: str,
    seed: int | str,
    ext: str = ".wav",
) -> str:
    """Return the deterministic delivery filename for one asset.

    Parameters
    ----------
    category:
        Asset category (e.g. ``"music"``, ``"sfx"``).
    asset_id:
        Stable asset identifier string.
    seed:
        Generation seed.  Formatted as zero-padded 4-digit integer when
        a plain integer is provided; used as-is when already a string.
    ext:
        File extension including the leading dot (default ``.wav``).

    Returns
    -------
    str
        Deterministic filename such as ``music__bgm_field__seed0042.wav``.
    """
    if isinstance(seed, int):
        seed_str = f"{seed:04d}"
    else:
        seed_str = str(seed)
    # Sanitise components: replace path separators and spaces with underscores
    safe_category = str(category).replace("/", "_").replace("\\", "_").replace(" ", "_")
    safe_asset_id = str(asset_id).replace("/", "_").replace("\\", "_").replace(" ", "_")
    return f"{safe_category}__{safe_asset_id}__seed{seed_str}{ext}"


class WavDeliveryPipeline:
    """Package approved audio assets for commercial WAV delivery.

    Reads from ``<factory_root>/approved/`` and writes deterministically-named
    copies plus a ``delivery_manifest.json`` to *delivery_dir*.

    Parameters
    ----------
    progress_callback:
        Optional callable ``(message: str) -> None`` called after each file
        is copied.

    Example
    -------
    >>> pipeline = WavDeliveryPipeline()
    >>> report = pipeline.deliver(
    ...     factory_root="/tmp/factory",
    ...     delivery_dir="/tmp/delivery/v1",
    ... )
    """

    def __init__(
        self,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.progress_callback = progress_callback or (lambda msg: None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deliver(
        self,
        factory_root: str | Path,
        delivery_dir: str | Path,
        categories: list[str] | None = None,
    ) -> dict:
        """Copy approved assets to *delivery_dir* with deterministic naming.

        Parameters
        ----------
        factory_root:
            Root of the factory output directory (must contain an ``approved/``
            sub-directory).
        delivery_dir:
            Destination directory for the delivery package.  Created if it
            does not exist.
        categories:
            Optional list of category sub-directories to include (e.g.
            ``["music", "sfx"]``).  When ``None`` all sub-directories of
            ``approved/`` are included.

        Returns
        -------
        dict
            Delivery report with keys:

            - ``"deliveryManifestVersion"``: schema version string
            - ``"factoryRoot"``: resolved factory root path
            - ``"deliveryDir"``: resolved delivery directory path
            - ``"generatedAt"``: ISO-8601 UTC timestamp
            - ``"summary"``: dict with ``total``, ``copied``, ``skipped``
            - ``"entries"``: list of per-file delivery records

        Raises
        ------
        FileNotFoundError
            If ``<factory_root>/approved/`` does not exist or is empty.
        """
        import datetime

        factory_root = Path(factory_root).resolve()
        delivery_dir = Path(delivery_dir).resolve()

        approved_root = factory_root / "approved"
        if not approved_root.exists():
            raise FileNotFoundError(
                f"approved/ directory not found under factory_root: {factory_root}"
            )

        delivery_dir.mkdir(parents=True, exist_ok=True)

        # Collect source files
        source_files = self._collect_source_files(approved_root, categories)
        if not source_files:
            raise FileNotFoundError(
                f"No audio files found in {approved_root}"
            )

        entries: list[dict] = []
        n_copied = 0
        n_skipped = 0

        for src_path, category in source_files:
            record = self._deliver_file(src_path, category, delivery_dir)
            entries.append(record)
            if record["status"] == "copied":
                n_copied += 1
                self.progress_callback(f"copied {record['deliveryName']}")
            else:
                n_skipped += 1

        report = {
            "deliveryManifestVersion": "1.0.0",
            "factoryRoot": str(factory_root),
            "deliveryDir": str(delivery_dir),
            "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "summary": {
                "total": len(entries),
                "copied": n_copied,
                "skipped": n_skipped,
            },
            "entries": entries,
        }

        manifest_path = delivery_dir / "delivery_manifest.json"
        manifest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.progress_callback(f"delivery_manifest.json written → {manifest_path}")

        return report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_source_files(
        self,
        approved_root: Path,
        categories: list[str] | None,
    ) -> list[tuple[Path, str]]:
        """Return ``[(path, category)]`` for all approved audio files."""
        results: list[tuple[Path, str]] = []

        if categories is not None:
            category_dirs = [approved_root / cat for cat in categories]
        else:
            category_dirs = [
                p for p in sorted(approved_root.iterdir()) if p.is_dir()
            ]

        for cat_dir in category_dirs:
            if not cat_dir.is_dir():
                continue
            category = cat_dir.name
            for audio_file in sorted(cat_dir.rglob("*")):
                if audio_file.suffix.lower() in _AUDIO_EXTS:
                    results.append((audio_file, category))

        return results

    def _deliver_file(
        self,
        src_path: Path,
        category: str,
        delivery_dir: Path,
    ) -> dict:
        """Copy one source file and return its delivery record."""
        # Load provenance sidecar if present
        prov_path = src_path.with_name(src_path.stem + ".provenance.json")
        if prov_path.exists():
            try:
                prov = json.loads(prov_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                prov = {}
        else:
            prov = {}

        asset_id: str = prov.get("assetId") or src_path.stem
        seed = prov.get("seed", 0)
        ext = src_path.suffix.lower() if src_path.suffix.lower() in _AUDIO_EXTS else ".wav"

        delivery_name = _deterministic_delivery_name(category, asset_id, seed, ext)
        dest_path = delivery_dir / delivery_name

        shutil.copy2(src_path, dest_path)
        status = "copied"

        return {
            "sourcePath": str(src_path),
            "deliveryName": delivery_name,
            "deliveryPath": str(dest_path),
            "category": category,
            "assetId": asset_id,
            "seed": seed,
            "status": status,
        }
