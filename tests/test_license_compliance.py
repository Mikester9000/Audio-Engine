"""Tests for the license compliance checker (SESSION-032)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from audio_engine.compliance.license_checker import (
    LicenseReport,
    PackageEntry,
    _declared_package_names,
    _first_spdx_token,
    _get_package_license,
    _load_policy,
    _normalise_license,
    check_licenses,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_POLICY_PATH = Path(__file__).parent.parent / "tools" / "license_policy.toml"


# ---------------------------------------------------------------------------
# Unit tests — normalisation and parsing helpers
# ---------------------------------------------------------------------------

class TestNormaliseLicense:
    def test_returns_alias(self):
        assert _normalise_license("MIT License") == "MIT"

    def test_returns_identity_for_unknown(self):
        assert _normalise_license("SomeCustomLicense") == "SomeCustomLicense"

    def test_strips_whitespace(self):
        assert _normalise_license("  MIT License  ") == "MIT"

    def test_bsd_3_clause(self):
        assert _normalise_license("BSD License") == "BSD-3-Clause"

    def test_apache_software_license(self):
        assert _normalise_license("Apache Software License") == "Apache-2.0"


class TestFirstSpdxToken:
    def test_single_token(self):
        assert _first_spdx_token("MIT") == "MIT"

    def test_compound_and(self):
        result = _first_spdx_token("BSD-3-Clause AND 0BSD AND MIT")
        assert result == "BSD-3-Clause"

    def test_compound_or(self):
        result = _first_spdx_token("Apache-2.0 OR MIT")
        assert result == "Apache-2.0"

    def test_strips_whitespace(self):
        assert _first_spdx_token("  MIT  ") == "MIT"


# ---------------------------------------------------------------------------
# Unit tests — policy loading
# ---------------------------------------------------------------------------

class TestLoadPolicy:
    def test_loads_allow_section(self):
        policy = _load_policy(_POLICY_PATH)
        assert "MIT" in policy
        assert policy["MIT"]["policy"] == "allow"

    def test_loads_block_section(self):
        policy = _load_policy(_POLICY_PATH)
        assert "CC-BY-NC-4.0" in policy
        assert policy["CC-BY-NC-4.0"]["policy"] == "block"

    def test_loads_conditional_section(self):
        policy = _load_policy(_POLICY_PATH)
        # At least one conditional should exist
        conditionals = [k for k, v in policy.items() if v["policy"] == "conditional"]
        assert len(conditionals) > 0

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises((FileNotFoundError, OSError)):
            _load_policy(tmp_path / "nonexistent.toml")


# ---------------------------------------------------------------------------
# Unit tests — package name discovery
# ---------------------------------------------------------------------------

class TestDeclaredPackageNames:
    def test_returns_non_empty_set(self):
        names = _declared_package_names(include_dev=False)
        assert len(names) > 0

    def test_includes_core_deps(self):
        names = _declared_package_names(include_dev=False)
        assert "numpy" in names or "numpy" in names
        assert "scipy" in names

    def test_include_dev_adds_pytest(self):
        without_dev = _declared_package_names(include_dev=False)
        with_dev = _declared_package_names(include_dev=True)
        assert len(with_dev) >= len(without_dev)


# ---------------------------------------------------------------------------
# Unit tests — check_licenses (scoped to declared deps)
# ---------------------------------------------------------------------------

class TestCheckLicenses:
    def test_returns_license_report(self):
        report = check_licenses()
        assert isinstance(report, LicenseReport)

    def test_includes_numpy(self):
        report = check_licenses()
        names = [p.package.lower() for p in report.packages]
        assert "numpy" in names

    def test_includes_scipy(self):
        report = check_licenses()
        names = [p.package.lower() for p in report.packages]
        assert "scipy" in names

    def test_summary_keys(self):
        report = check_licenses()
        assert set(report.summary.keys()) == {"allow", "conditional", "block", "unknown"}

    def test_core_deps_are_compliant(self):
        report = check_licenses()
        # numpy and scipy must not be blocked
        for pkg in report.packages:
            if pkg.package.lower() in ("numpy", "scipy"):
                assert pkg.policy in ("allow", "conditional"), (
                    f"{pkg.package} has policy '{pkg.policy}' — expected allow or conditional"
                )

    def test_compliant_flag_true_for_declared_deps(self):
        report = check_licenses()
        # All declared deps are BSD/MIT/Apache — report should be compliant
        assert report.compliant, (
            f"Declared deps are not all compliant: {report.summary}"
        )

    def test_to_json_is_valid_json(self):
        report = check_licenses()
        data = json.loads(report.to_json())
        assert "packages" in data
        assert "summary" in data
        assert "compliant" in data

    def test_to_dict_roundtrip(self):
        report = check_licenses()
        d = report.to_dict()
        assert isinstance(d["packages"], list)
        assert isinstance(d["summary"], dict)

    def test_custom_policy_path(self, tmp_path):
        policy = tmp_path / "custom_policy.toml"
        policy.write_text(
            '[allow]\nBSD-3-Clause = "BSD"\n\n[block]\n[conditional]\n',
            encoding="utf-8",
        )
        report = check_licenses(policy_path=policy)
        # Should not raise; numpy (BSD-3-Clause) should be allow
        numpy_entries = [p for p in report.packages if p.package.lower() == "numpy"]
        assert len(numpy_entries) > 0
        assert numpy_entries[0].policy == "allow"

    def test_blocked_package_makes_report_non_compliant(self, tmp_path):
        """Inject a fake package with a blocked license and verify compliant=False."""
        policy = tmp_path / "policy.toml"
        policy.write_text(
            '[allow]\nBSD-3-Clause = "ok"\n\n[conditional]\n[block]\nFake-NC = "blocked"\n',
            encoding="utf-8",
        )

        fake_meta = MagicMock()
        fake_meta.get.side_effect = lambda key, default=None: {
            "Name": "fake-nc-pkg",
            "Version": "1.0.0",
            "License": "Fake-NC",
            "License-Expression": None,
        }.get(key, default)
        fake_meta.get_all.return_value = []

        fake_dist = MagicMock()
        fake_dist.metadata = fake_meta

        import importlib.metadata as _meta
        real_dists = list(_meta.distributions())

        with patch("importlib.metadata.distributions", return_value=[*real_dists, fake_dist]):
            report = check_licenses(policy_path=policy, all_installed=True)

        blocked = [p for p in report.packages if p.package == "fake-nc-pkg"]
        assert len(blocked) == 1
        assert blocked[0].policy == "block"
        assert not report.compliant


# ---------------------------------------------------------------------------
# Integration test — CLI command
# ---------------------------------------------------------------------------

class TestCheckLicensesCLI:
    def test_cli_exits_zero_on_compliant(self, tmp_path):
        """Running against default policy should exit 0 for declared deps."""
        from audio_engine.cli import main as cli_main
        import sys

        argv_backup = sys.argv[:]
        out_report = tmp_path / "report.json"
        sys.argv = ["audio-engine", "check-licenses", "--output-report", str(out_report), "--quiet"]
        try:
            rc = cli_main()
        except SystemExit as exc:
            rc = exc.code
        finally:
            sys.argv = argv_backup

        assert rc == 0, "CLI should exit 0 when all declared deps comply"
        assert out_report.exists(), "Report file should have been written"
        data = json.loads(out_report.read_text())
        assert data["compliant"] is True
