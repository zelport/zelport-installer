#!/usr/bin/env python3
"""Verify that the latest Zelport App release satisfies the installer contract."""

import hashlib
import json
from pathlib import Path
import re
import tempfile
import urllib.request


SEMVER_TAG = re.compile(
    r"v((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"
)
SHA256 = re.compile(r"[0-9a-f]{64}")
PLATFORMS = ("darwin_arm64", "darwin_amd64", "linux_arm64", "linux_amd64")


def request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "zelport-installer-release-verifier",
        },
    )


def expected_assets(version: str) -> set[str]:
    return {
        *(f"zelport_{version}_{platform}.tar.gz" for platform in PLATFORMS),
        f"zelport_{version}_source.tar.gz",
        "PKGBUILD",
        f"zelport-{version}.SRCINFO",
        "SHA256SUMS",
    }


def verify_downloaded_assets(directory: Path, version: str) -> None:
    expected = expected_assets(version)
    if {path.name for path in directory.iterdir()} != expected:
        raise ValueError("App release must contain exactly the eight supported assets")
    for name in expected:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"App release asset must be a regular file: {name}")
    payloads = expected - {"SHA256SUMS"}
    entries = {}
    for line in (directory / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or not SHA256.fullmatch(parts[0]) or parts[1] in entries:
            raise ValueError("App SHA256SUMS has an invalid or duplicate entry")
        entries[parts[1]] = parts[0]
    if set(entries) != payloads:
        raise ValueError("App SHA256SUMS must cover every payload exactly once")
    for name, expected_digest in entries.items():
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if digest != expected_digest:
            raise ValueError(f"App checksum mismatch for {name}")
    recipe = (directory / "PKGBUILD").read_text(encoding="utf-8")
    srcinfo = (directory / f"zelport-{version}.SRCINFO").read_text(encoding="utf-8")
    if re.findall(r"(?m)^pkgver=(.+)$", recipe) != [version]:
        raise ValueError("App PKGBUILD version does not match its release")
    if re.findall(r"(?m)^\s*pkgver = (.+)$", srcinfo) != [version]:
        raise ValueError("App .SRCINFO version does not match its release")


def verify_latest_release() -> str:
    api = "https://api.github.com/repos/zelport/zelport/releases/latest"
    with urllib.request.urlopen(request(api)) as response:
        release = json.load(response)
    match = SEMVER_TAG.fullmatch(release.get("tag_name", ""))
    if not match or release.get("draft") or release.get("prerelease"):
        raise ValueError("latest App release must be public stable numeric SemVer")
    version = match.group(1)
    assets = {
        asset["name"]: asset["browser_download_url"]
        for asset in release.get("assets", [])
    }
    if set(assets) != expected_assets(version):
        raise ValueError("latest App release does not expose the exact required asset set")
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        for name, url in assets.items():
            with urllib.request.urlopen(request(url)) as response:
                (directory / name).write_bytes(response.read())
        verify_downloaded_assets(directory, version)
    return version


def main() -> None:
    try:
        version = verify_latest_release()
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(f"App release verification failed: {error}") from error
    print(f"Verified latest Zelport App release v{version}")


if __name__ == "__main__":
    main()
