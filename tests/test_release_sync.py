"""Release-to-website synchronization contract tests."""

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'scripts/verify-release-sync.py'
VERSION = '20261018.2'


class ReleaseSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.release = self.root / 'release'
        self.release.mkdir()
        self.script = b'#!/usr/bin/env bash\nZELPORT_INSTALLER_VERSION=20261018.2\nprintf ok\\n\n'
        self.uninstaller = b'#!/usr/bin/env bash\nZELPORT_UNINSTALLER_VERSION=20261018.2\nprintf ok\\n\n'
        (self.release / 'install.sh').write_bytes(self.script)
        (self.release / 'uninstall.sh').write_bytes(self.uninstaller)
        self.write_manifest()
        self.website = self.root / 'website-install.sh'
        self.website.write_bytes(b'old installer\n')
        self.output = self.root / 'github-output'

    def write_manifest(self):
        installer_digest = hashlib.sha256(self.script).hexdigest()
        uninstaller_digest = hashlib.sha256(self.uninstaller).hexdigest()
        (self.release / 'SHA256SUMS').write_text(
            f'{installer_digest}  install.sh\n{uninstaller_digest}  uninstall.sh\n'
        )

    def run_helper(self, version=VERSION):
        return subprocess.run([
            'python3', str(HELPER),
            '--release-dir', str(self.release),
            '--website-script', str(self.website),
            '--version', version,
            '--github-output', str(self.output),
        ], text=True, capture_output=True)

    def outputs(self):
        return dict(line.split('=', 1) for line in self.output.read_text().splitlines())

    def test_verified_release_replaces_only_the_website_script(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.website.read_bytes(), self.script)
        expected = hashlib.sha256(self.script).hexdigest()
        output = self.outputs()
        self.assertEqual(output['changed'], 'true')
        self.assertEqual(output['release_sha256'], expected)
        self.assertEqual(output['website_sha256'], hashlib.sha256(b'old installer\n').hexdigest())
        self.assertEqual(output['result_sha256'], expected)
        self.assertEqual(output['commit_message'], 'chore(installer): sync v20261018.2')

    def test_identical_website_bytes_are_idempotent(self):
        self.website.write_bytes(self.script)
        before = self.website.stat().st_mtime_ns
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        digest = hashlib.sha256(self.script).hexdigest()
        output = self.outputs()
        self.assertEqual(output['changed'], 'false')
        self.assertEqual(output['release_sha256'], digest)
        self.assertEqual(output['website_sha256'], digest)
        self.assertEqual(output['result_sha256'], digest)
        self.assertEqual(self.website.stat().st_mtime_ns, before)

    def test_checksum_mismatch_never_changes_website(self):
        (self.release / 'SHA256SUMS').write_text(f'{"0" * 64}  install.sh\n')
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.website.read_bytes(), b'old installer\n')
        self.assertFalse(self.output.exists())

    def test_extra_or_missing_release_assets_are_rejected(self):
        for mutation in ('extra', 'missing'):
            with self.subTest(mutation=mutation):
                if mutation == 'extra':
                    path = self.release / 'unexpected.txt'
                    path.write_text('unexpected')
                else:
                    path = self.release / 'SHA256SUMS'
                    path.unlink()
                result = self.run_helper()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.website.read_bytes(), b'old installer\n')
                if mutation == 'extra':
                    path.unlink()
                else:
                    self.write_manifest()

    def test_multiple_manifest_entries_are_rejected(self):
        installer_digest = hashlib.sha256(self.script).hexdigest()
        uninstaller_digest = hashlib.sha256(self.uninstaller).hexdigest()
        (self.release / 'SHA256SUMS').write_text(
            f'{installer_digest}  install.sh\n{uninstaller_digest}  uninstall.sh\n'
            f'{installer_digest}  install.sh\n'
        )
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.website.read_bytes(), b'old installer\n')

    def test_release_version_must_match_argument_and_script_once(self):
        self.assertNotEqual(self.run_helper('20261018.3').returncode, 0)
        (self.release / 'install.sh').write_bytes(self.script + b'ZELPORT_INSTALLER_VERSION=20261018.2\n')
        self.script = (self.release / 'install.sh').read_bytes()
        self.write_manifest()
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(self.website.read_bytes(), b'old installer\n')

    def test_symlink_assets_and_destination_are_rejected(self):
        real = self.root / 'real-script'
        real.write_bytes(self.script)
        (self.release / 'install.sh').unlink()
        (self.release / 'install.sh').symlink_to(real)
        self.assertNotEqual(self.run_helper().returncode, 0)

        (self.release / 'install.sh').unlink()
        (self.release / 'install.sh').write_bytes(self.script)
        target = self.root / 'protected'
        target.write_bytes(b'protected\n')
        self.website.unlink()
        self.website.symlink_to(target)
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(target.read_bytes(), b'protected\n')

    def test_release_workflow_downloads_and_verifies_published_assets(self):
        workflow = (ROOT / '.github/workflows/release.yml').read_text()
        download = workflow.index('gh release download "$GITHUB_REF_NAME"')
        verify = workflow.index('(cd released && sha256sum --check SHA256SUMS)')
        self.assertLess(download, verify)
        self.assertNotIn('INSTALLER_SYNC_PRIVATE_KEY', workflow)
        self.assertNotIn('repository: zelport/zelport-web', workflow)
        self.assertNotIn('--pattern', workflow)
        self.assertNotIn('push --force', workflow)
        self.assertNotIn('push -f', workflow)


if __name__ == '__main__':
    unittest.main()
