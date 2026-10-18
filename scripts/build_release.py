#!/usr/bin/env python3
"""Build deterministic Zelport Installer release assets."""

import argparse
import hashlib
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_VERSION_RE = re.compile(
    r"^ZELPORT_INSTALLER_VERSION=([0-9]{8}\.[1-9][0-9]*)$", re.MULTILINE
)
UNINSTALLER_VERSION_RE = re.compile(
    r"^ZELPORT_UNINSTALLER_VERSION=([0-9]{8}\.[1-9][0-9]*)$", re.MULTILINE
)


def build(output: Path) -> dict[str, str]:
    installer = (ROOT / "install.sh").read_bytes()
    uninstaller = (ROOT / "uninstall.sh").read_bytes()
    installer_match = INSTALLER_VERSION_RE.search(installer.decode("utf-8"))
    uninstaller_match = UNINSTALLER_VERSION_RE.search(uninstaller.decode("utf-8"))
    if not installer_match:
        raise SystemExit("install.sh has an invalid ZELPORT_INSTALLER_VERSION")
    if not uninstaller_match:
        raise SystemExit("uninstall.sh has an invalid ZELPORT_UNINSTALLER_VERSION")
    if installer_match.group(1) != uninstaller_match.group(1):
        raise SystemExit("install.sh and uninstall.sh versions must match")

    output.mkdir(parents=True, exist_ok=True)
    destinations = {
        output / "install.sh": installer,
        output / "uninstall.sh": uninstaller,
    }
    manifest = output / "SHA256SUMS"
    for path in (*destinations, manifest):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise SystemExit(f"refusing unsafe release output: {path}")
    digests = {}
    for destination, script in destinations.items():
        destination.write_bytes(script)
        destination.chmod(0o755)
        digests[destination.name] = hashlib.sha256(script).hexdigest()
    manifest.write_text(
        "".join(f"{digests[name]}  {name}\n" for name in ("install.sh", "uninstall.sh")),
        encoding="utf-8",
        newline="\n",
    )
    manifest.chmod(0o644)

    # Stable metadata helps downstream archive or artifact tooling remain
    # reproducible even though only the file bytes are release-significant.
    for destination in destinations:
        os.utime(destination, (0, 0))
    os.utime(manifest, (0, 0))
    return digests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    digests = build(args.output)
    for name in ("install.sh", "uninstall.sh"):
        print(f"{digests[name]}  {name}")


if __name__ == "__main__":
    main()
