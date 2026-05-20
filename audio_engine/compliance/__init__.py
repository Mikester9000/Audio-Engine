"""License compliance module for Audio-Engine."""

from audio_engine.compliance.license_checker import (
    check_licenses,
    LicenseReport,
    PackageEntry,
)

__all__ = ["check_licenses", "LicenseReport", "PackageEntry"]
