#!/usr/bin/env python3
"""Read and validate the shared Zelport Installer release version."""

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"[0-9]{8}\.[1-9][0-9]*")


def script_version(path: Path, variable: str) -> str:
    source = path.read_text(encoding="utf-8")
    values = re.findall(rf"(?m)^{re.escape(variable)}=([^\r\n]+)$", source)
    if len(values) != 1 or not VERSION_RE.fullmatch(values[0]):
        raise ValueError(f"{path.name} must define exactly one valid {variable}")
    return values[0]


def release_version() -> str:
    installer = script_version(ROOT / "install.sh", "ZELPORT_INSTALLER_VERSION")
    uninstaller = script_version(ROOT / "uninstall.sh", "ZELPORT_UNINSTALLER_VERSION")
    if installer != uninstaller:
        raise ValueError("installer and uninstaller versions must match")
    return installer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    try:
        version = release_version()
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(f"version verification failed: {error}") from error
    print(version)


if __name__ == "__main__":
    main()
