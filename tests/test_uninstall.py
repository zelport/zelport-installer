"""Uninstaller integration tests with isolated homes and mocked system operations."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANAGED_UNIT = """# Managed by Zelport Installer.
[Unit]
Description=Zelport App
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/zelport
Restart=on-failure
RestartSec=5
UMask=0077

[Install]
WantedBy=default.target
"""


class UninstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.binary = self.home / ".local/bin/zelport"
        self.data = self.home / ".local/share/zelport"
        self.unit = self.home / ".config/systemd/user/zelport.service"
        self.config = self.home / ".config/zelport/config.json"
        self.state = self.home / ".local/state/zelport/endpoint.json"
        self.config.parent.mkdir(parents=True)
        self.state.parent.mkdir(parents=True)
        self.config.write_text("preserve configuration")
        self.state.write_text("preserve state")

    def create_binary_install(self, service=False):
        self.binary.parent.mkdir(parents=True, exist_ok=True)
        self.binary.write_text('#!/bin/sh\necho "zelport 0.10.0 (built fixture)"\n')
        self.binary.chmod(0o755)
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "LICENSE").write_text("license")
        (self.data / "THIRD_PARTY_NOTICES.txt").write_text("notices")
        if service:
            self.unit.parent.mkdir(parents=True, exist_ok=True)
            self.unit.write_text(MANAGED_UNIT)

    def run_uninstaller(
        self,
        args=(),
        os_name="Linux",
        arch="x86_64",
        distro="debian",
        init_system="systemd",
        uid=1000,
        session=True,
        fragment="",
        package_version="",
        other_install=False,
        sudo_user=None,
    ):
        self.log = self.home / "operations"
        program = r'''
source "$UNINSTALLER"
uname() { if [[ ${1:-} == -m ]]; then printf '%s\n' "$TEST_ARCH"; else printf '%s\n' "$TEST_OS"; fi; }
id() { printf '%s\n' "$TEST_UID"; }
detect_distro() { printf '%s\n' "$TEST_DISTRO"; }
detect_init_system() { printf '%s\n' "$TEST_INIT_SYSTEM"; }
systemctl() {
    printf 'systemctl %s\n' "$*" >> "$TEST_LOG"
    case "$*" in
        *show-environment*) [[ $TEST_SESSION == yes ]] ;;
        *FragmentPath*) printf '%s\n' "$TEST_FRAGMENT" ;;
        *) return 0 ;;
    esac
}
pacman() {
    if [[ ${1:-} == -Q && ${2:-} == zelport && -n $TEST_PACKAGE_VERSION ]]; then
        printf 'zelport %s\n' "$TEST_PACKAGE_VERSION"
        return 0
    fi
    return 1
}
sudo() { printf 'sudo %s\n' "$*" >> "$TEST_LOG"; }
main "$@"
'''
        path = str(self.home / ".local/bin") + ":/usr/bin:/bin:/usr/sbin:/sbin"
        if other_install:
            other = self.home / "other/bin"
            other.mkdir(parents=True)
            binary = other / "zelport"
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o755)
            path = str(other) + ":" + path
        env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_DATA_HOME": str(self.home / ".local/share"),
            "XDG_STATE_HOME": str(self.home / ".local/state"),
            "PATH": path,
            "UNINSTALLER": str(ROOT / "uninstall.sh"),
            "TEST_LOG": str(self.log),
            "TEST_ARCH": arch,
            "TEST_OS": os_name,
            "TEST_DISTRO": distro,
            "TEST_INIT_SYSTEM": init_system,
            "TEST_UID": str(uid),
            "TEST_SESSION": "yes" if session else "no",
            "TEST_FRAGMENT": fragment,
            "TEST_PACKAGE_VERSION": package_version,
        }
        env.pop("SUDO_USER", None)
        if sudo_user is not None:
            env["SUDO_USER"] = sudo_user
        return subprocess.run(
            ["bash", "-c", program, "uninstaller", *args],
            env=env,
            text=True,
            capture_output=True,
        )

    def ops(self):
        return self.log.read_text() if self.log.exists() else ""

    def test_binary_install_is_removed_and_user_data_is_preserved(self):
        self.create_binary_install(service=True)
        result = self.run_uninstaller(fragment=str(self.unit))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.binary.exists())
        self.assertFalse(self.unit.exists())
        self.assertFalse((self.data / "LICENSE").exists())
        self.assertEqual(self.config.read_text(), "preserve configuration")
        self.assertEqual(self.state.read_text(), "preserve state")
        self.assertIn("systemctl --user disable --now zelport.service", self.ops())
        self.assertIn("systemctl --user daemon-reload", self.ops())
        self.assertIn("Zelport was uninstalled successfully.", result.stdout)
        self.assertIn(f"Configuration preserved at {self.config}", result.stdout)
        self.assertTrue(result.stdout.endswith("\n\n"))

    def test_purge_removes_default_configuration_and_state(self):
        self.create_binary_install()
        saved = Path(str(self.config) + ".saved")
        saved.write_text("backup")
        result = self.run_uninstaller(args=["--purge"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.config.exists())
        self.assertFalse(saved.exists())
        self.assertFalse(self.state.exists())
        self.assertIn("Default configuration and state files were removed", result.stdout)

    def test_purge_can_remove_remnants_without_an_installation(self):
        result = self.run_uninstaller(args=["--purge"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.config.exists())
        self.assertFalse(self.state.exists())
        self.assertIn("configuration and state remnants were removed", result.stdout)

    def test_no_installation_is_an_idempotent_no_op(self):
        result = self.run_uninstaller()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No supported Zelport installation was found", result.stdout)
        self.assertEqual(self.config.read_text(), "preserve configuration")
        self.assertNotIn("Progress:", result.stdout)

    def test_custom_service_blocks_removal_and_is_preserved(self):
        self.create_binary_install(service=True)
        self.unit.write_text("custom service")
        result = self.run_uninstaller(fragment=str(self.unit))
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.binary.exists())
        self.assertEqual(self.unit.read_text(), "custom service")
        self.assertIn("custom Zelport user service was preserved", result.stderr)
        self.assertNotIn("disable --now", self.ops())

    def test_managed_service_requires_reachable_user_manager(self):
        self.create_binary_install(service=True)
        result = self.run_uninstaller(session=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.binary.exists())
        self.assertTrue(self.unit.exists())
        self.assertIn("cannot be stopped", result.stderr)

    def test_binary_without_service_can_be_removed_without_systemd(self):
        self.create_binary_install()
        result = self.run_uninstaller(session=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.binary.exists())
        self.assertNotIn("disable --now", self.ops())
        self.assertNotIn("loaded service", result.stdout)

    def test_symlink_and_unrecognized_binary_are_preserved(self):
        target = self.home / "target"
        target.write_text("preserve")
        self.binary.parent.mkdir(parents=True)
        self.binary.symlink_to(target)
        result = self.run_uninstaller()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.binary.is_symlink())
        self.assertEqual(target.read_text(), "preserve")

        self.binary.unlink()
        self.binary.write_text("#!/bin/sh\necho another-program\n")
        self.binary.chmod(0o755)
        result = self.run_uninstaller()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.binary.exists())

    def test_data_directory_symlink_target_is_preserved(self):
        self.create_binary_install()
        for child in self.data.iterdir():
            child.unlink()
        self.data.rmdir()
        target = self.home / "external-data"
        target.mkdir()
        notice = target / "LICENSE"
        notice.write_text("preserve")
        self.data.symlink_to(target, target_is_directory=True)
        result = self.run_uninstaller()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(notice.read_text(), "preserve")
        self.assertTrue(self.data.is_symlink())
        self.assertIn("Preserved unexpected data directory symlink", result.stdout)

    def test_other_installation_method_is_not_changed(self):
        result = self.run_uninstaller(other_install=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not owned by this uninstaller", result.stdout)
        self.assertIn("original installation method", result.stdout)

    def test_multiple_installation_methods_are_preserved(self):
        self.create_binary_install()
        result = self.run_uninstaller(other_install=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.binary.exists())
        self.assertIn("Another Zelport installation exists", result.stderr)

        result = self.run_uninstaller(package_version="0.10.0-1")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.binary.exists())
        self.assertNotIn("sudo pacman -R", self.ops())

    def test_arch_package_is_removed_through_pacman(self):
        result = self.run_uninstaller(
            distro="arch",
            package_version="0.10.0-1",
            fragment="/usr/lib/systemd/user/zelport.service",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Removal method: pacman", result.stdout)
        self.assertIn("systemctl --user disable --now zelport.service", self.ops())
        self.assertIn("sudo pacman -R zelport", self.ops())

    def test_root_is_reported_and_no_files_are_removed(self):
        self.create_binary_install()
        result = self.run_uninstaller(uid=0, sudo_user="user")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Privileges: root (sudo)", result.stdout)
        self.assertIn("root privileges were detected", result.stdout)
        self.assertTrue(self.binary.exists())

    def test_macos_prints_homebrew_guidance_without_changes(self):
        result = self.run_uninstaller(os_name="Darwin", arch="arm64")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Removal method: Homebrew", result.stdout)
        self.assertIn("brew services stop zelport", result.stdout)
        self.assertIn("brew uninstall zelport", result.stdout)
        self.assertEqual(self.config.read_text(), "preserve configuration")

    def test_direct_and_pipe_help_match_without_banner(self):
        direct = subprocess.run(
            ["bash", str(ROOT / "uninstall.sh"), "--help"], text=True, capture_output=True
        )
        piped = subprocess.run(
            ["bash", "-s", "--", "--help"],
            input=(ROOT / "uninstall.sh").read_text(),
            text=True,
            capture_output=True,
        )
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(direct.stdout, piped.stdout)
        self.assertTrue(direct.stdout.startswith("Zelport Uninstaller 20261018.6\n"))
        self.assertNotIn(":::::::", direct.stdout)
        self.assertIn("--purge", direct.stdout)


if __name__ == "__main__":
    unittest.main()
