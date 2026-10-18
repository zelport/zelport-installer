# Zelport Installer

`install.sh` is the standalone installer for Zelport App. Installer releases use
date-based versions independently from the App: this source is `20261018.2` and
installs Zelport App `0.10.0`.

Download the exact release asset, inspect it, and run it as your regular user:

```sh
curl -fsSLO https://github.com/zelport/zelport-installer/releases/download/v20261018.2/install.sh
curl -fsSLO https://github.com/zelport/zelport-installer/releases/download/v20261018.2/SHA256SUMS
sha256sum --check SHA256SUMS
less install.sh
bash install.sh
```

The website copy at `https://zelport.com/install.sh` is generated only from a
released asset after its checksum is verified. This repository is the only
editable source of the installer.

## Platform behavior

| Platform | Behavior |
| --- | --- |
| macOS | Prints Homebrew install and service commands; makes no changes. |
| Arch Linux and Omarchy | Fetches a commit-pinned and SHA-256-verified `PKGBUILD`, then runs `makepkg --syncdeps --install`. |
| Other Linux on x86-64 or ARM64 | Installs the verified release binary into `~/.local/bin/zelport`. |
| Linux without a reachable systemd user manager | Installs normally and prints manual startup instructions. |
| Windows shells | Reports that the Bash installer is not supported and makes no changes. |

Unsupported operating systems and CPU architectures fail before a download.
Linux installation requires Bash, curl, tar, ordinary POSIX tools, and either
`sha256sum` or `shasum`. Arch installation additionally requires pacman,
makepkg, and the package build dependencies declared by the reviewed recipe.
Before installing, the script reports the detected operating system,
architecture, installation method, and systemd user-manager availability.

Use `--no-start` to install without creating, enabling, starting, stopping, or
restarting a user service:

```sh
bash install.sh --no-start
```

When the selected Zelport version is already installed, the installer exits
without changing the installation or service. Use `--reinstall` to download,
verify, and install that version again. It can be combined with `--no-start`.

## Integrity and ownership boundaries

The installer pins one App release and never resolves a moving latest version.
Binary installs verify the selected archive against that App release's
`SHA256SUMS`. Arch installs verify the fetched recipe against the
`ZELPORT_ARCH_SHA256` embedded beside its immutable App commit. The recipe then
verifies the App source archive and Go verifies module dependencies.

Only the selected executable and license notices are streamed from a binary
archive. Existing Zelport configuration, endpoint hints, services, and runtime
identities are preserved. The installer does not install or manage desktop
integrations. It refuses conflicting managed or user-local installations instead
of replacing them silently.

When systemd user services are available, binary installs use
`~/.config/systemd/user/zelport.service`; Arch uses the package-owned user unit.
Existing custom units and symlinks are not overwritten. An already active
managed service is restarted only when its binary, package, or managed unit
changes. No unrelated process is stopped.

## Versioning

`ZELPORT_INSTALLER_VERSION` uses `YYYYMMDD.N`, where `N` starts at 1 and
increments for another installer release on the same date. Tags and releases
prefix this value with `v`. Every published script change, including an App or
Arch recipe pin update, requires a new installer version.

`ZELPORT_RELEASE` is numeric SemVer without a `v`; App tags and release URLs add
the `v` prefix. Update the App version, reviewed Arch commit, and recipe checksum
together only after the corresponding App artifacts and packaging commit exist.
Never move a published tag or replace released assets.

## Development and release checks

```sh
bash -n install.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
make check
make release-assets
```

The Python suite uses temporary homes, synthetic archives, and mocked platform,
network, package-manager, and service commands. It does not install packages or
modify a running Zelport App. Native distribution and systemd verification are
separate release checks.

`make release-assets` writes deterministic `dist/install.sh` and
`dist/SHA256SUMS`. The release workflow accepts only a tag matching
`vYYYYMMDD.N`, requires it to equal the script version, reruns all checks, and
publishes those exact two files. Website synchronization is a separate verified
release step and is never sourced from an untagged branch.

Licensed under the [MIT License](LICENSE).
