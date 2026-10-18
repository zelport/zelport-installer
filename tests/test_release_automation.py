"""Release automation unit and workflow contract tests."""

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import release_version
import verify_app_release
import verify_release_assets


class ReleaseAutomationTests(unittest.TestCase):
    def test_source_versions_are_read_once_and_match(self):
        self.assertEqual(release_version.release_version(), "2026.10.0")

    def test_installer_version_uses_year_month_micro(self):
        for version in ("2026.01.0", "2026.10.0", "2026.12.19"):
            with self.subTest(version=version):
                self.assertIsNotNone(release_version.VERSION_RE.fullmatch(version))
        for version in ("20261018.8", "2026.00.0", "2026.13.0", "2026.10.01", "2026.10.-1"):
            with self.subTest(version=version):
                self.assertIsNone(release_version.VERSION_RE.fullmatch(version))

    def test_local_release_asset_verifier_rejects_extras(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            installer = b"ZELPORT_INSTALLER_VERSION=2026.10.0\n"
            uninstaller = b"ZELPORT_UNINSTALLER_VERSION=2026.10.0\n"
            (directory / "install.sh").write_bytes(installer)
            (directory / "uninstall.sh").write_bytes(uninstaller)
            (directory / "SHA256SUMS").write_text(
                f"{hashlib.sha256(installer).hexdigest()}  install.sh\n"
                f"{hashlib.sha256(uninstaller).hexdigest()}  uninstall.sh\n"
            )
            verify_release_assets.verify_assets(directory, "2026.10.0")
            (directory / "unexpected").write_text("no")
            with self.assertRaisesRegex(ValueError, "exactly"):
                verify_release_assets.verify_assets(directory, "2026.10.0")

    def test_app_contract_requires_all_assets_and_checksums(self):
        version = "0.10.1"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            lines = []
            for name in verify_app_release.expected_assets(version) - {"SHA256SUMS"}:
                if name == "PKGBUILD":
                    content = f"pkgver={version}\n".encode()
                elif name.endswith(".SRCINFO"):
                    content = f"pkgver = {version}\n".encode()
                else:
                    content = name.encode()
                (directory / name).write_bytes(content)
                lines.append(f"{hashlib.sha256(content).hexdigest()}  {name}")
            (directory / "SHA256SUMS").write_text("\n".join(lines) + "\n")
            verify_app_release.verify_downloaded_assets(directory, version)
            (directory / "PKGBUILD").write_text(f"pkgver={version}\nchanged\n")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_app_release.verify_downloaded_assets(directory, version)

    def test_workflow_passes_one_verified_artifact_to_publication(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn("make release-ready", workflow)
        self.assertIn("actions/upload-artifact@", workflow)
        self.assertIn("actions/download-artifact@", workflow)
        release_job = workflow.split("\n  release:", 1)[1]
        self.assertNotIn("make release-assets", release_job)
        self.assertIn("make verify-release-assets", release_job)
        self.assertIn("cmp dist/install.sh released/install.sh", release_job)
        self.assertIn("retention-days: 1", workflow)


if __name__ == "__main__":
    unittest.main()
