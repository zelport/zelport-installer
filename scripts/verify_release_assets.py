#!/usr/bin/env python3
"""Verify exact Zelport Installer release assets and their version."""

import argparse
import hashlib
from pathlib import Path
import re

from release_version import release_version


ASSET_NAMES = {"install.sh", "uninstall.sh", "SHA256SUMS"}
MANIFEST_RE = re.compile(
    r"^([0-9a-f]{64})  install\.sh\n([0-9a-f]{64})  uninstall\.sh\n$"
)


def verify_assets(release_dir: Path, version: str) -> None:
    if release_dir.is_symlink() or not release_dir.is_dir():
        raise ValueError("release directory must be a real directory")
    if {path.name for path in release_dir.iterdir()} != ASSET_NAMES:
        raise ValueError("release must contain exactly install.sh, uninstall.sh, and SHA256SUMS")
    paths = [release_dir / name for name in ASSET_NAMES]
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError("every release asset must be a regular file")
    installer = (release_dir / "install.sh").read_bytes()
    uninstaller = (release_dir / "uninstall.sh").read_bytes()
    installer_source = installer.decode("utf-8")
    uninstaller_source = uninstaller.decode("utf-8")
    if re.findall(r"(?m)^ZELPORT_INSTALLER_VERSION=([^\r\n]+)$", installer_source) != [version]:
        raise ValueError("install.sh version does not match the release")
    if re.findall(r"(?m)^ZELPORT_UNINSTALLER_VERSION=([^\r\n]+)$", uninstaller_source) != [version]:
        raise ValueError("uninstall.sh version does not match the release")
    manifest = (release_dir / "SHA256SUMS").read_text(encoding="ascii")
    match = MANIFEST_RE.fullmatch(manifest)
    if not match:
        raise ValueError("SHA256SUMS must contain exactly one entry for each script")
    if match.group(1) != hashlib.sha256(installer).hexdigest():
        raise ValueError("install.sh checksum mismatch")
    if match.group(2) != hashlib.sha256(uninstaller).hexdigest():
        raise ValueError("uninstall.sh checksum mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        version = release_version()
        verify_assets(args.release_dir, version)
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(f"release verification failed: {error}") from error
    print(f"Verified Zelport Installer {version} assets in {args.release_dir}")


if __name__ == "__main__":
    main()
