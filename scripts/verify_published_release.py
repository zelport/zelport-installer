#!/usr/bin/env python3
"""Download and verify the public release for the current installer version."""

import argparse
import json
from pathlib import Path
import tempfile
import urllib.request

from release_version import release_version
from verify_release_assets import ASSET_NAMES, verify_assets


def request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "zelport-installer-release-verifier",
        },
    )


def verify_published(repository: str) -> str:
    version = release_version()
    tag = f"v{version}"
    api = f"https://api.github.com/repos/{repository}/releases/tags/{tag}"
    with urllib.request.urlopen(request(api)) as response:
        release = json.load(response)
    if release.get("tag_name") != tag or release.get("draft") or release.get("prerelease"):
        raise ValueError("installer release must be public, stable, and match the source version")
    assets = {
        asset["name"]: asset["browser_download_url"]
        for asset in release.get("assets", [])
    }
    if set(assets) != ASSET_NAMES:
        raise ValueError("published installer release has an unexpected asset set")
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        for name, url in assets.items():
            with urllib.request.urlopen(request(url)) as response:
                (directory / name).write_bytes(response.read())
        verify_assets(directory, version)
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    try:
        version = verify_published(args.repository)
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(f"published release verification failed: {error}") from error
    print(f"Verified public {args.repository} release v{version}")


if __name__ == "__main__":
    main()
