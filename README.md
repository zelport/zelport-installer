# Zelport Installer

`install.sh` and `uninstall.sh` are Bash scripts for installing and removing
Zelport App. They run preflight checks, perform supported operations, and
otherwise provide platform-specific guidance and tips.

## Install

Do not run the installer as root or with `sudo`. On Arch Linux and Omarchy,
`makepkg` may request your password when pacman installs packages or
dependencies. Run the installer as your regular user:

```sh
curl -fsSL https://zelport.com/install.sh | bash
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

Downloaded application archives and Arch package recipes are checked before
installation.

## Uninstall

Run the uninstaller as your regular user:

```sh
curl -fsSL https://zelport.com/uninstall.sh | bash
```

The default configuration and state files are preserved. Use `--help` to list
the available options or remove the preserved files explicitly with `--purge`:

```sh
curl -fsSL https://zelport.com/uninstall.sh | bash -s -- --help
curl -fsSL https://zelport.com/uninstall.sh | bash -s -- --purge
```

On Arch Linux and Omarchy, the uninstaller removes the package through `pacman`.
On macOS, it shows the corresponding Homebrew commands without making changes.

## Example output

A binary installation in a Linux container without systemd looks like this:

```text
  :::::::
  ::::::::::
  :::::::::::::                                           ::::
  ::::::::::::::::                                        ::::                                ::::
  ::::::::::::::::::                 :::::::::: ::::::::  :::::::::::::::   :::::::: :::::::::::::::
  ::::::::::::::::::::::             :::::::::::::::::::: ::::::::::::::::::::::::::::::::::::::::::
  ::::::::::::::::::::::                ::::: :::::::::::::::::::::   ::::::::   :::::::::    ::::
  ::::::::::::::::::                   :::::  ::::::::::::::::::::    ::::::::   :::::::::    ::::
  ::::::::::::::::                   :::::::::::::::::::::::::::::::::::::::::::::::::::::    ::::::
  :::::::::::::                      :::::::::: ::::::::: :::::::::::::::  ::::::::: :::::    ::::::
  ::::::::::                                                  ::::
  :::::::                                                     ::::

Zelport Installer <installer-version>

Preflight checks:
  Host: Linux (ubuntu)
  Architecture: arm64
  Init system: none detected (container)
  Installation method: binary
  Privileges: regular user
  Service manager: systemd user manager unavailable (systemctl not found)

Progress:
  Installing Zelport <app-version> from the arm64 release archive.

Result:
  Zelport <app-version> was installed successfully at /home/user/.local/bin/zelport
  No reachable systemd user manager. Automatic startup was not configured.

Tips:
  Configuration file: /home/user/.config/zelport/config.json
  Default URL: http://localhost:8080
  Start Zelport manually: /home/user/.local/bin/zelport
```

## Versioning

`ZELPORT_INSTALLER_VERSION` and `ZELPORT_UNINSTALLER_VERSION` use `YYYYMMDD.N`,
where `N` starts at 1 and increments for another release on the same date. Both
values match, and tags and releases prefix them with `v`. Every published script
change, including an App or Arch recipe pin update, requires a new version.

`ZELPORT_RELEASE` is numeric SemVer without a `v`. App tags and release URLs add
the `v` prefix. Update the App version, reviewed Arch commit, and recipe checksum
together only after the corresponding App artifacts and packaging commit exist.
Never move a published tag or replace released assets.

Maintainer instructions are in [RELEASING.md](RELEASING.md).

Licensed under the [MIT License](LICENSE).
