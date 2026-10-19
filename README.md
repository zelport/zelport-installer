# Zelport Installer

`install.sh` and `uninstall.sh` are Bash scripts for installing and removing
Zelport App. They run preflight checks, perform supported operations, and
otherwise provide platform-specific guidance and tips.

## Install

Do not run the installer as root or with `sudo`. On Arch Linux and Omarchy,
`makepkg` may request your password when pacman installs packages or
dependencies. Run the installer as your regular user:

```sh
bash install.sh
```

## Supported systems

| System | Behavior |
| --- | --- |
| macOS | Shows Homebrew installation and service commands without making changes. |
| Linux with systemd | Installs the Zelport binary and manages the user service |
| Linux without systemd | Installs the Zelport binary and shows how to start it manually |
| Arch Linux / Omarchy | Builds and installs the Zelport package with `makepkg` |
| Windows | Reports that the Bash installer is unsupported and makes no changes. |

Binary installation supports `amd64` and `arm64`.

Use `--help` to list the available options, `--no-start` to install without
managing the user service, and `--reinstall` to reinstall an already current
installation:

```sh
bash install.sh --help
bash install.sh --no-start
bash install.sh --reinstall
```

The installer resolves the latest stable Zelport App release at runtime.
Downloaded application archives and Arch package recipes are checked against
that release's `SHA256SUMS` before installation.

## Uninstall

Run the uninstaller as your regular user:

```sh
bash uninstall.sh
```

The default configuration and state files are preserved. Use `--help` to list
the available options or remove the preserved files explicitly with `--purge`:

```sh
bash uninstall.sh --help
bash uninstall.sh --purge
```

On Arch Linux and Omarchy, the uninstaller removes the package through `pacman`.
On macOS, it shows the corresponding Homebrew commands without making changes.

## Versioning

The canonical Installer release identifier is `vYYYY.MM.MICRO`. Use that form
in documentation, commands, tags, GitHub Releases and reports. The embedded
`ZELPORT_INSTALLER_VERSION` and `ZELPORT_UNINSTALLER_VERSION` fields contain the
derived `YYYY.MM.MICRO` payload and must match. App releases use independent
canonical `vMAJOR.MINOR.PATCH` identifiers and are resolved at runtime. See
[RELEASING.md](RELEASING.md) for the complete maintainer policy.

Licensed under the [MIT License](LICENSE).
