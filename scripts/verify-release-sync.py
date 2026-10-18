#!/usr/bin/env python3
"""Verify released installer assets and synchronize the website copy."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import tempfile


VERSION_RE = re.compile(r"^[0-9]{8}\.[1-9][0-9]*$")
INSTALLER_VERSION_RE = re.compile(r"^ZELPORT_INSTALLER_VERSION=([^\r\n]+)$", re.MULTILINE)
UNINSTALLER_VERSION_RE = re.compile(r"^ZELPORT_UNINSTALLER_VERSION=([^\r\n]+)$", re.MULTILINE)
MANIFEST_RE = re.compile(
    r"^([0-9a-f]{64})  install\.sh\n([0-9a-f]{64})  uninstall\.sh\n$"
)
ASSET_NAMES = {"install.sh", "uninstall.sh", "SHA256SUMS"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")


def verify_assets(release_dir: Path, version: str) -> tuple[bytes, str]:
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version must use YYYYMMDD.N without a v prefix")
    if release_dir.is_symlink() or not release_dir.is_dir():
        raise ValueError("release directory must be a real directory")

    names = {entry.name for entry in release_dir.iterdir()}
    if names != ASSET_NAMES:
        raise ValueError("release must contain exactly install.sh, uninstall.sh, and SHA256SUMS")

    installer_path = release_dir / "install.sh"
    uninstaller_path = release_dir / "uninstall.sh"
    manifest_path = release_dir / "SHA256SUMS"
    regular_file(installer_path, "installer asset")
    regular_file(uninstaller_path, "uninstaller asset")
    regular_file(manifest_path, "checksum asset")
    installer = installer_path.read_bytes()
    uninstaller = uninstaller_path.read_bytes()
    try:
        installer_source = installer.decode("utf-8")
        uninstaller_source = uninstaller.decode("utf-8")
        manifest = manifest_path.read_text(encoding="ascii")
    except UnicodeError as error:
        raise ValueError("release assets must use UTF-8 script and ASCII manifest") from error

    if INSTALLER_VERSION_RE.findall(installer_source) != [version]:
        raise ValueError("released installer version does not exactly match the release tag")
    if UNINSTALLER_VERSION_RE.findall(uninstaller_source) != [version]:
        raise ValueError("released uninstaller version does not exactly match the release tag")
    match = MANIFEST_RE.fullmatch(manifest)
    if not match:
        raise ValueError("SHA256SUMS must contain exactly one entry for each script")

    installer_digest = digest(installer)
    uninstaller_digest = digest(uninstaller)
    if match.group(1) != installer_digest:
        raise ValueError("released install.sh does not match SHA256SUMS")
    if match.group(2) != uninstaller_digest:
        raise ValueError("released uninstall.sh does not match SHA256SUMS")
    return installer, installer_digest


def replace_website_script(path: Path, script: bytes) -> tuple[str, bool]:
    regular_file(path, "website installer")
    previous = path.read_bytes()
    previous_digest = digest(previous)
    if previous == script:
        return previous_digest, False

    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".install.sh.", suffix=".tmp", delete=False
        ) as temporary:
            temporary.write(script)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.chmod(temporary_name, 0o755)
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    return previous_digest, True


def append_outputs(path: Path, values: dict[str, str]) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("GitHub output path must be a regular file")
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--website-script", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--github-output", required=True, type=Path)
    args = parser.parse_args()

    try:
        script, release_digest = verify_assets(args.release_dir, args.version)
        website_digest, changed = replace_website_script(args.website_script, script)
        result_digest = digest(args.website_script.read_bytes())
        values = {
            "changed": "true" if changed else "false",
            "release_sha256": release_digest,
            "website_sha256": website_digest,
            "result_sha256": result_digest,
            "commit_message": f"chore(installer): sync v{args.version}",
        }
        append_outputs(args.github_output, values)
    except (OSError, ValueError) as error:
        raise SystemExit(f"release synchronization refused: {error}") from error

    print(f"release_sha256={release_digest}")
    print(f"website_sha256={website_digest}")
    print(f"result_sha256={result_digest}")
    print(f"changed={'true' if changed else 'false'}")


if __name__ == "__main__":
    main()
