"""
audio_engine.compliance.license_checker
========================================

Machine-readable license compliance checker for the Audio-Engine package.

Reads installed package metadata via ``importlib.metadata``, looks up each
license against the policy defined in ``tools/license_policy.toml``, and
emits a structured report.

By default only the packages declared in ``pyproject.toml`` (core and optional
neural/ogg deps) are scanned so that system-wide environment packages do not
pollute the report.

Public API
----------
``check_licenses(policy_path, include_dev, all_installed) -> LicenseReport``
    Scan installed packages and return a :class:`LicenseReport`.

Exit-code contract (when used as the ``audio-engine check-licenses`` CLI):
    0 — all scanned packages are ``allow`` or ``conditional``
    1 — at least one package is ``block`` or ``unknown``
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

try:
    import tomllib  # Python 3.11+
except ImportError:  # Python 3.9 / 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError as _tomli_err:
        raise ImportError(
            "tomllib is not available (Python < 3.11) and the 'tomli' back-port "
            "is not installed.  Install it with:  pip install tomli"
        ) from _tomli_err

__all__ = ["check_licenses", "LicenseReport", "PackageEntry"]

Policy = Literal["allow", "conditional", "block", "unknown"]

# Default policy file relative to the repository root.
_DEFAULT_POLICY = Path(__file__).parent.parent.parent / "tools" / "license_policy.toml"

# pyproject.toml location relative to repository root.
_PYPROJECT = Path(__file__).parent.parent.parent / "pyproject.toml"

# Known SPDX aliases that appear in package metadata but map to a standard id.
_SPDX_ALIASES: dict[str, str] = {
    "BSD": "BSD-3-Clause",
    "BSD License": "BSD-3-Clause",
    "BSD-3-Clause License": "BSD-3-Clause",
    "BSD 3-Clause License": "BSD-3-Clause",
    "BSD 2-Clause License": "BSD-2-Clause",
    "MIT License": "MIT",
    "MIT license": "MIT",
    "Apache 2.0": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "Apache Software License": "Apache-2.0",
    "Apache Software License 2.0": "Apache-2.0",
    "GNU Lesser General Public License v2 or later (LGPLv2+)": "LGPL-2.1-or-later",
    "GNU Lesser General Public License v3 or later (LGPLv3+)": "LGPL-3.0-or-later",
    "PSF": "PSF-2.0",
    "Python Software Foundation License": "PSF-2.0",
    "ISC License (ISCL)": "ISC",
    "Creative Commons Attribution-NonCommercial 4.0": "CC-BY-NC-4.0",
    "CC BY-NC 4.0": "CC-BY-NC-4.0",
    "GNU Affero General Public License v3 or later (AGPLv3+)": "AGPL-3.0",
    "LGPL-2.1+": "LGPL-2.1-or-later",
    "LGPL-3.0+": "LGPL-3.0-or-later",
}

# Packages to always skip (build-time-only / meta packages).
_SKIP_PACKAGES = frozenset({"pip", "setuptools", "wheel", "pkg_resources", "distribute"})


@dataclass
class PackageEntry:
    """Single-package compliance record."""

    package: str
    version: str
    spdx_license: str
    policy: Policy
    policy_notes: str = ""
    raw_classifiers: list[str] = field(default_factory=list)


@dataclass
class LicenseReport:
    """Full compliance report for all scanned packages."""

    packages: list[PackageEntry] = field(default_factory=list)
    policy_path: str = ""
    summary: dict[str, int] = field(default_factory=dict)
    compliant: bool = True
    scanned_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _load_policy(policy_path: Path) -> dict[str, dict[str, str]]:
    """Load and parse the TOML policy file into a flat spdx->policy+notes map."""
    with policy_path.open("rb") as fh:
        raw = tomllib.load(fh)

    result: dict[str, dict[str, str]] = {}
    for category in ("allow", "conditional", "block"):
        for spdx, notes in raw.get(category, {}).items():
            result[spdx] = {"policy": category, "notes": notes}
    return result


def _normalise_license(raw: str) -> str:
    """Map a raw classifier/metadata license string to a canonical SPDX id."""
    raw = raw.strip()
    return _SPDX_ALIASES.get(raw, raw)


def _first_spdx_token(expression: str) -> str:
    """Return the first SPDX identifier from a compound License-Expression.

    For example ``"BSD-3-Clause AND 0BSD AND MIT"`` returns ``"BSD-3-Clause"``,
    and ``"(MIT OR Apache-2.0)"`` returns ``"MIT"``.
    The first token is typically the primary license.
    """
    # Strip SPDX operators and parentheses; find the first non-empty token
    tokens = re.split(r"\s+(?:AND|OR|WITH)\s+|[()\s]", expression.strip())
    for token in tokens:
        stripped = token.strip()
        if stripped:
            return stripped
    return ""


def _get_package_license(dist) -> tuple[str, list[str]]:
    """Extract a single SPDX license string and raw classifiers from a dist."""
    classifiers: list[str] = []
    try:
        meta = dist.metadata
        classifiers = [
            c
            for c in (meta.get_all("Classifier") or [])
            if c.startswith("License")
        ]
    except Exception:
        pass

    # Prefer PEP 639 License-Expression (e.g. numpy 2.x)
    try:
        lic_expr = dist.metadata.get("License-Expression") or ""
        if lic_expr and lic_expr.strip() not in ("", "UNKNOWN", "None"):
            return _first_spdx_token(lic_expr.strip()), classifiers
    except Exception:
        pass

    # Next: top-level License metadata field
    try:
        license_meta = dist.metadata.get("License") or ""
        if license_meta and license_meta.strip() not in ("", "UNKNOWN", "None"):
            # Only use the field if it looks like a short SPDX id or alias (not a full-text)
            stripped = license_meta.strip()
            if len(stripped) < 80 and "\n" not in stripped:
                return _normalise_license(stripped), classifiers
    except Exception:
        pass

    # Fall back to classifiers
    for clf in classifiers:
        parts = [p.strip() for p in clf.split("::")]
        if len(parts) >= 3:
            candidate = _normalise_license(parts[-1])
            if candidate:
                return candidate, classifiers

    return "unknown", classifiers


def _declared_package_names(include_dev: bool) -> set[str]:
    """Read pyproject.toml and return the set of declared dependency package names."""
    if not _PYPROJECT.exists():
        raise FileNotFoundError(
            f"pyproject.toml not found at {_PYPROJECT}. "
            "Cannot determine which packages to scan. "
            "Either run from the repository root or pass all_installed=True "
            "(CLI flag: --all-installed) to scan all installed packages."
        )

    with _PYPROJECT.open("rb") as fh:
        proj = tomllib.load(fh)

    names: set[str] = set()
    project = proj.get("project", {})

    def _add_reqs(reqs: list[str]) -> None:
        for req in reqs:
            m = re.match(r"^([A-Za-z0-9_\-\.]+)", req)
            if m:
                n = m.group(1).lower()
                names.add(n)
                names.add(n.replace("-", "_"))

    _add_reqs(project.get("dependencies", []))
    for group_name, reqs in project.get("optional-dependencies", {}).items():
        if include_dev or group_name not in ("dev",):
            _add_reqs(reqs)

    # Always include the package itself
    pkg_name = project.get("name", "audio-engine")
    names.add(pkg_name.lower())
    names.add(pkg_name.lower().replace("-", "_"))

    return names


def check_licenses(
    policy_path: Path | None = None,
    include_dev: bool = False,
    all_installed: bool = False,
) -> LicenseReport:
    """Scan installed packages and produce a :class:`LicenseReport`.

    By default scans only the packages declared in ``pyproject.toml`` (core
    and optional neural/ogg deps).  Set ``all_installed=True`` to scan every
    package in the current environment.

    Parameters
    ----------
    policy_path:
        Path to the TOML policy file.  Defaults to ``tools/license_policy.toml``.
    include_dev:
        If ``True``, include dev/test packages declared in the dev extra.
    all_installed:
        If ``True``, scan every installed package instead of only declared deps.

    Returns
    -------
    :class:`LicenseReport`
    """
    if policy_path is None:
        policy_path = _DEFAULT_POLICY
        if not policy_path.exists():
            raise FileNotFoundError(
                f"Default policy file not found at {policy_path}. "
                "In a wheel install the policy file is not bundled. "
                "Provide the path explicitly with --policy <file>."
            )

    policy_map = _load_policy(policy_path)

    target_names: set[str] | None = None
    if not all_installed:
        target_names = _declared_package_names(include_dev=include_dev)

    import importlib.metadata as _meta

    entries: list[PackageEntry] = []
    try:
        all_dists = list(_meta.distributions())
    except Exception:
        all_dists = []

    seen: set[str] = set()
    for dist in all_dists:
        try:
            name = dist.metadata.get("Name") or ""
            version = dist.metadata.get("Version") or ""
        except Exception:
            continue

        if not name:
            continue
        key = name.lower()
        normalised_key = key.replace("-", "_")

        if key in seen or key in _SKIP_PACKAGES:
            continue

        if target_names is not None:
            if key not in target_names and normalised_key not in target_names:
                continue

        seen.add(key)

        spdx, raw_clf = _get_package_license(dist)
        normalised_spdx = _normalise_license(spdx)

        pol_entry = policy_map.get(normalised_spdx)
        if pol_entry:
            policy: Policy = pol_entry["policy"]  # type: ignore[assignment]
            notes = pol_entry["notes"]
        elif normalised_spdx in ("unknown", "UNKNOWN", ""):
            policy = "unknown"
            notes = "License not detected in package metadata"
            normalised_spdx = "unknown"
        else:
            policy = "unknown"
            notes = (
                f"SPDX id '{normalised_spdx}' not found in policy file; "
                "add it to tools/license_policy.toml"
            )

        entries.append(
            PackageEntry(
                package=name,
                version=version,
                spdx_license=normalised_spdx,
                policy=policy,
                policy_notes=notes,
                raw_classifiers=raw_clf,
            )
        )

    entries.sort(key=lambda e: e.package.lower())

    summary: dict[str, int] = {"allow": 0, "conditional": 0, "block": 0, "unknown": 0}
    for e in entries:
        summary[e.policy] = summary.get(e.policy, 0) + 1

    compliant = summary["block"] == 0 and summary["unknown"] == 0
    scanned_names = sorted(target_names) if target_names is not None else []

    return LicenseReport(
        packages=entries,
        policy_path=str(policy_path),
        summary=summary,
        compliant=compliant,
        scanned_names=scanned_names,
    )
