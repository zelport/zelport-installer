# Zelport Installer

`install.sh` is a Bash script that runs preflight checks, installs Zelport App
where direct installation is supported, and otherwise provides platform-specific
installation guidance and tips.

## Install

Download the latest release, verify it, inspect it, and run it as your regular
user:

```sh
curl -fsSLO https://github.com/zelport/zelport-installer/releases/latest/download/install.sh
curl -fsSLO https://github.com/zelport/zelport-installer/releases/latest/download/SHA256SUMS

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum --check SHA256SUMS
else
  shasum -a 256 --check SHA256SUMS
fi

less install.sh
bash install.sh
```

Do not run the installer with `sudo`. On Arch Linux and Omarchy, `makepkg` may
request your password when pacman installs packages or dependencies.

## Supported systems

| System | Behavior |
| --- | --- |
| macOS | Shows Homebrew installation and service commands without making changes. |
| Arch Linux / Omarchy | Builds and installs the checked pacman package through `makepkg`. |
| Other Linux on x86-64 or ARM64 | Installs the checked binary in `~/.local/bin/zelport`. |
| Linux without systemd | Installs the binary and shows how to start it manually. |
| Windows | Reports that the Bash installer is unsupported and makes no changes. |

Before installation, the script reports the detected host, architecture, init
system, installation method, privileges, and service manager.

Use `--no-start` to install without managing the user service. Use `--reinstall`
to reinstall an already current installation:

```sh
bash install.sh --no-start
bash install.sh --reinstall
```

Downloaded application archives and Arch package recipes are checked before
installation. `SHA256SUMS` confirms that `install.sh` matches the manifest from
the same GitHub release; because both files come from the same source, this is
an integrity check rather than an independent signature.

## Versioning

`ZELPORT_INSTALLER_VERSION` uses `YYYYMMDD.N`, where `N` starts at 1 and
increments for another installer release on the same date. Tags and releases
prefix this value with `v`. Every published script change, including an App or
Arch recipe pin update, requires a new installer version.

`ZELPORT_RELEASE` is numeric SemVer without a `v`; App tags and release URLs add
the `v` prefix. Update the App version, reviewed Arch commit, and recipe checksum
together only after the corresponding App artifacts and packaging commit exist.
Never move a published tag or replace released assets.

Maintainer instructions are in [RELEASING.md](RELEASING.md).

Licensed under the [MIT License](LICENSE).
