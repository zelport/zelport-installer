#!/usr/bin/env python3
"""Build deterministic Zelport Installer release assets."""

import argparse
import hashlib
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^ZELPORT_INSTALLER_VERSION=([0-9]{8}\.[1-9][0-9]*)$", re.MULTILINE)


def build(output: Path) -> str:
    source = ROOT / "install.sh"
    script = source.read_bytes()
    text = script.decode("utf-8")
    if not VERSION_RE.search(text):
        raise SystemExit("install.sh has an invalid ZELPORT_INSTALLER_VERSION")

    output.mkdir(parents=True, exist_ok=True)
    destination = output / "install.sh"
    manifest = output / "SHA256SUMS"
    for path in (destination, manifest):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise SystemExit(f"refusing unsafe release output: {path}")
    destination.write_bytes(script)
    destination.chmod(0o755)

    digest = hashlib.sha256(script).hexdigest()
    manifest.write_text(f"{digest}  install.sh\n", encoding="utf-8", newline="\n")
    manifest.chmod(0o644)

    # Stable metadata helps downstream archive or artifact tooling remain
    # reproducible even though only the file bytes are release-significant.
    os.utime(destination, (0, 0))
    os.utime(manifest, (0, 0))
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    digest = build(args.output)
    print(f"{digest}  install.sh")


if __name__ == "__main__":
    main()
