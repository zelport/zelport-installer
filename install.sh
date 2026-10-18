#!/usr/bin/env bash
# Canonical source: https://github.com/zelport/zelport-installer/blob/main/install.sh
# The website copy is generated only from a verified installer release asset.
# Install Zelport without changing its configuration or installing desktop plugins.
# Keep the release and reviewed Arch recipe pins together when publishing updates.

ZELPORT_INSTALLER_VERSION=20261018.7
ZELPORT_RELEASE=0.10.0
ZELPORT_ARCH_REF=4f57dc7487503ce5b1b3eb407b6bc2032f810aac
ZELPORT_ARCH_SHA256=b1bb51677515a2db9c1612a0990ef80bd92af03e33bec1b18228029afe3febde

say() { printf '%s\n' "$*"; }

color_message() {
    local fd=$1 color=$2 message=$3
    if [[ -t $fd && ${TERM:-dumb} != dumb && -z ${NO_COLOR+x} ]]; then
        if [[ $fd == 2 ]]; then
            printf '\033[%sm%s\033[0m\n' "$color" "$message" >&2
        else
            printf '\033[%sm%s\033[0m\n' "$color" "$message"
        fi
    elif [[ $fd == 2 ]]; then
        printf '%s\n' "$message" >&2
    else
        say "$message"
    fi
}

success_message() { color_message 1 32 "$*"; }
warning_message() { color_message 1 33 "$*"; }
warning_stderr() { color_message 2 33 "Warning: $*"; }
die() { color_message 2 31 "Error: $*"; exit 1; }
require() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

# Source: zelport-identity-kit/assets/ascii/zelport-logo.txt
banner() {
    cat <<'EOF'

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

EOF
}

usage() {
    cat <<EOF
Zelport Installer $ZELPORT_INSTALLER_VERSION

Usage:
  bash install.sh [options]

Options:
  --no-start     Install without managing the Zelport user service.
  --reinstall    Reinstall Zelport $ZELPORT_RELEASE when it is already current.
  -h, --help     Show this help.

Supported systems:
  Arch Linux / Omarchy  Install the verified pacman package.
  Other Linux           Install the verified binary in ~/.local/bin/zelport.
  macOS                 Print Homebrew commands without making changes.
  Windows               Unsupported; make no changes.

By default, the installer starts and enables Zelport through the systemd user
manager when available. Run the installer as a regular user, without sudo.
EOF
}

already_installed_notice() {
    local message="  Zelport $1 is already installed."
    say 'Result:'
    warning_message "$message"
    say ''
    say 'Tips:'
    say '  If you want to reinstall Zelport, run this installer with --reinstall.'
    say ''
}

installation_success_notice() {
    success_message "  Zelport $1 was installed successfully at $2"
}

progress() {
    if [[ $progress_started == no ]]; then
        say 'Progress:'
        progress_started=yes
    fi
    say "  $*"
}

progress_warning() {
    if [[ $progress_started == no ]]; then
        say 'Progress:'
        progress_started=yes
    fi
    warning_message "  $*"
}

root_privileges_result() {
    say 'Result:'
    color_message 1 31 '  Zelport installation was not started because root privileges were detected.'
    say ''
    say 'Tips:'
    warning_message '  Run this installer as your regular user, without sudo.'
    say ''
}

cleanup() {
    local result=$?
    trap - EXIT
    # Go module-cache directories are read-only. Change only directories inside
    # our private build workspace; find does not follow symlinks by default.
    if ! find "$work_dir" -type d -exec chmod u+w {} + || ! rm -rf -- "$work_dir"; then
        warning_stderr "could not fully remove temporary build directory: $work_dir"
    fi
    if [[ -n ${install_tmp:-} ]] && ! rm -f -- "$install_tmp"; then
        warning_stderr "could not remove temporary binary: $install_tmp"
    fi
    exit "$result"
}

fetch() {
    curl --fail --location --silent --show-error --proto '=https' --proto-redir '=https' \
        --connect-timeout 20 --max-time 600 --retry 2 "$1" --output "$2"
}

digest() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

verify() {
    [[ $2 =~ ^[0-9a-fA-F]{64}$ ]] || die 'Missing or invalid SHA-256 checksum.'
    [[ $(digest "$1") == "$2" ]] || die "Checksum mismatch: ${1##*/}. Nothing from this download was installed."
}

detect_distro() {
    # Read only identifiers; do not execute /etc/os-release as shell code.
    if [[ -r /etc/os-release ]]; then
        sed -n -e 's/^ID=//p' -e 's/^ID_LIKE=//p' /etc/os-release | tr -d "\"'" | tr '\n' ' '
    fi
}

detect_init_system() {
    local pid_one=''
    if [[ -r /proc/1/comm ]]; then
        IFS= read -r pid_one < /proc/1/comm || true
    fi
    case "$pid_one" in
        systemd) say systemd; return ;;
        openrc-init) say OpenRC; return ;;
        runit|runsvdir) say runit; return ;;
        s6-svscan) say s6; return ;;
        dinit) say dinit; return ;;
        init)
            if [[ -d /run/systemd/system ]]; then
                say systemd
            elif [[ -d /run/openrc ]]; then
                say OpenRC
            else
                say 'SysV-style init'
            fi
            return ;;
    esac
    if [[ -e /.dockerenv || -e /run/.containerenv ]] ||
       { [[ -r /proc/1/cgroup ]] && grep -Eq '/(docker|lxc|kubepods)(/|$)' /proc/1/cgroup; }; then
        say 'none detected (container)'
    elif [[ -n $pid_one ]]; then
        printf 'unknown (%s as PID 1)\n' "$pid_one"
    else
        say unknown
    fi
}

user_unit() {
    cat <<'EOF'
# Managed by Zelport Installer.
[Unit]
Description=Zelport App
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/zelport
Restart=on-failure
RestartSec=5
UMask=0077

[Install]
WantedBy=default.target
EOF
}

install_binary() {
    local asset="zelport_${ZELPORT_RELEASE}_linux_${cpu}.tar.gz"
    local base="https://github.com/zelport/zelport/releases/download/v${ZELPORT_RELEASE}"
    local expected members notice
    fetch "$base/SHA256SUMS" "$work_dir/SHA256SUMS"
    expected=$(awk -v name="$asset" '$2 == name {print $1}' "$work_dir/SHA256SUMS")
    fetch "$base/$asset" "$work_dir/$asset"
    verify "$work_dir/$asset" "$expected"
    members=$(tar -tzf "$work_dir/$asset")
    [[ $(printf '%s\n' "$members" | awk '$0 == "zelport" {n++} END {print n+0}') == 1 ]] || die 'Archive must contain exactly one zelport binary.'
    # Stream only the binary to a chosen path, never extract archive paths to disk.
    tar -xOzf "$work_dir/$asset" zelport > "$work_dir/zelport"
    [[ -s $work_dir/zelport ]] || die 'The downloaded binary is empty.'
    for notice in LICENSE THIRD_PARTY_NOTICES.txt; do
        tar -xOzf "$work_dir/$asset" "$notice" > "$work_dir/$notice"
        [[ -s $work_dir/$notice ]] || die "Missing release notice: $notice"
    done
    mkdir -p "$data_dir"
    for notice in LICENSE THIRD_PARTY_NOTICES.txt; do
        [[ ! -L $data_dir/$notice ]] || die "Refusing to replace a symlink: $data_dir/$notice"
        install -m 644 "$work_dir/$notice" "$data_dir/$notice"
    done
    mkdir -p "$HOME/.local/bin"
    install_tmp=$(mktemp "$HOME/.local/bin/.zelport-install.XXXXXX")
    install -m 755 "$work_dir/zelport" "$install_tmp"
    mv -f -- "$install_tmp" "$binary"
    install_tmp=''
}

install_arch() {
    fetch "https://raw.githubusercontent.com/zelport/zelport/${ZELPORT_ARCH_REF}/contrib/archlinux/PKGBUILD" "$work_dir/PKGBUILD"
    verify "$work_dir/PKGBUILD" "$ZELPORT_ARCH_SHA256"
    local pkgver pkgrel installed
    pkgver=$(sed -n 's/^pkgver=//p' "$work_dir/PKGBUILD")
    pkgrel=$(sed -n 's/^pkgrel=//p' "$work_dir/PKGBUILD")
    [[ $pkgver =~ ^[a-zA-Z0-9.+_]+$ && $pkgrel =~ ^[0-9]+$ ]] || die 'Invalid pinned Arch package version.'
    installed=$(pacman -Q zelport 2>/dev/null || true)
    if [[ $installed == "zelport $pkgver-$pkgrel" ]] && pacman -Qk zelport >/dev/null 2>&1; then
        if [[ $reinstall == no ]]; then
            already_installed_notice "$pkgver-$pkgrel"
            already_installed=yes
            return
        fi
        progress "Reinstalling Zelport $pkgver-$pkgrel from the verified Arch package recipe."
    fi
    command -v makepkg >/dev/null 2>&1 || die 'Install Arch build tools first: sudo pacman -S --needed base-devel git'
    changed=yes
    progress_warning 'Building the Arch package. Package installation may request your sudo password.'
    # A pipe-fed installer must leave package-manager prompts on the terminal.
    if [[ ! -t 0 ]] && ( : < /dev/tty ) 2>/dev/null; then
        (cd "$work_dir" && makepkg --syncdeps --install < /dev/tty)
    else
        (cd "$work_dir" && makepkg --syncdeps --install)
    fi
}

start_service() {
    if [[ $changed == yes || $unit_changed == yes ]]; then systemctl --user daemon-reload; fi
    if [[ $was_active == yes && ( $changed == yes || $unit_changed == yes ) ]]; then
        systemctl --user restart zelport.service || die 'Installed, but the existing service could not restart. Inspect journalctl --user -u zelport.service.'
    elif [[ $was_active == no ]]; then
        if ! systemctl --user start zelport.service; then
            systemctl --user stop zelport.service || true
            die 'Installed, but startup failed. Inspect journalctl --user -u zelport.service. No other process was stopped.'
        fi
    fi
    sleep 1
    if ! systemctl --user is-active --quiet zelport.service; then
        if [[ $was_active == no ]]; then systemctl --user stop zelport.service || true; fi
        die 'Installed, but the service is not running. Check for a port conflict with journalctl --user -u zelport.service.'
    fi
    if ! systemctl --user is-enabled --quiet zelport.service; then
        systemctl --user enable zelport.service
    fi
}

main() {
    set -euo pipefail
    local start=yes reinstall=no platform distro distro_name init_system method existing unit_dir unit fragment
    local config_file config_tip manual_start privileges uid root=no
    local cpu binary data_dir was_active=no use_systemd=no changed=no unit_changed=no installed_version
    local systemd_status omarchy=no already_installed=no progress_started=no
    for arg in "$@"; do
        case "$arg" in
            --help|-h) usage; return 0 ;;
            --no-start) start=no ;;
            --reinstall) reinstall=yes ;;
            *) die "Unknown argument: $arg. Use --help." ;;
        esac
    done
    banner
    say "Zelport Installer $ZELPORT_INSTALLER_VERSION"
    uid=$(id -u)
    if [[ $uid == 0 ]]; then
        root=yes
        if [[ -n ${SUDO_USER:-} ]]; then privileges='root (sudo)'; else privileges=root; fi
    else
        privileges='regular user'
    fi
    platform=$(uname -s)
    case "$platform" in
        Darwin)
            case "$(uname -m)" in
                x86_64|amd64) cpu=amd64 ;;
                aarch64|arm64) cpu=arm64 ;;
                *) cpu=$(uname -m) ;;
            esac
            say ''
            say 'Preflight checks:'
            say '  Host: Darwin (macOS)'
            say "  Architecture: $cpu"
            say '  Init system: launchd'
            say '  Installation method: Homebrew'
            if [[ $root == yes ]]; then
                warning_message "  Privileges: $privileges"
            else
                say "  Privileges: $privileges"
            fi
            say '  Service manager: launchd'
            say ''
            if [[ $root == yes ]]; then
                root_privileges_result
                return 1
            fi
            say 'Result:'
            warning_message '  Zelport installation on macOS is managed through Homebrew. No changes were made.'
            say ''
            say 'Tips:'
            say '  Install Zelport: brew install zelport/tap/zelport'
            say '  Start Zelport: brew services start zelport'
            say ''
            return 0 ;;
        MINGW*|MSYS*|CYGWIN*|Windows_NT)
            warning_message 'This Bash installer is not supported on Windows. No changes were made.'
            return 0 ;;
        Linux) ;;
        *) die "Unsupported operating system: $platform" ;;
    esac
    [[ ${HOME:-} == /* && $HOME != / ]] || die 'HOME must be an absolute user home directory.'
    case "$(uname -m)" in
        x86_64|amd64) cpu=amd64 ;;
        aarch64|arm64) cpu=arm64 ;;
        *) die 'This installer supports Linux x86_64 and aarch64 only.' ;;
    esac
    distro=$(detect_distro)
    distro_name=${distro%% *}
    [[ -n $distro_name ]] || distro_name=unknown
    init_system=$(detect_init_system)
    case " $distro " in
        *' arch '*|*' archlinux '*) method=arch; binary=/usr/bin/zelport ;;
        *) method=binary; binary="$HOME/.local/bin/zelport" ;;
    esac
    if [[ $root == yes ]]; then
        say ''
        say 'Preflight checks:'
        say "  Host: $platform ($distro_name)"
        say "  Architecture: $cpu"
        say "  Init system: $init_system"
        say "  Installation method: $method"
        warning_message "  Privileges: $privileges"
        say '  Service manager: systemd user manager not checked (root privileges)'
        say ''
        root_privileges_result
        return 1
    fi
    require curl
    require tar
    if ! command -v sha256sum >/dev/null 2>&1; then require shasum; fi
    existing=$(command -v zelport || true)
    [[ -z $existing || $existing == "$binary" ]] || die "Zelport already exists at $existing. Update it with its original installer; refusing a second installation."
    if [[ $method == arch ]]; then
        require pacman
        [[ ! -e $HOME/.local/bin/zelport && ! -L $HOME/.local/bin/zelport ]] || die 'A user-local Zelport exists. Remove that installation before switching to pacman.'
        if [[ -e $binary ]]; then
            pacman -Q zelport >/dev/null 2>&1 || die 'An unmanaged /usr/bin/zelport exists; refusing to replace it.'
        fi
    else
        [[ ! -L $binary ]] || die 'The installation target is a symlink. Update Zelport using its original installer.'
        [[ ! -e $binary || -f $binary ]] || die 'The installation target is not a regular file.'
        data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/zelport"
        [[ $data_dir == /* ]] || die 'XDG_DATA_HOME must be absolute when set.'
    fi
    if command -v omarchy-version >/dev/null 2>&1 && omarchy-version >/dev/null 2>&1; then omarchy=yes; fi
    if [[ $start == no ]]; then
        systemd_status='not checked (--no-start)'
    elif ! command -v systemctl >/dev/null 2>&1; then
        systemd_status='unavailable (systemctl not found)'
    elif systemctl --user show-environment >/dev/null 2>&1; then
        systemd_status=available
        use_systemd=yes
        if systemctl --user is-active --quiet zelport.service; then was_active=yes; fi
    else
        systemd_status='unavailable (user manager not reachable)'
    fi
    say ''
    say 'Preflight checks:'
    say "  Host: $platform ($distro_name)"
    say "  Architecture: $cpu"
    say "  Init system: $init_system"
    say "  Installation method: $method"
    say "  Privileges: $privileges"
    if [[ $systemd_status == unavailable* ]]; then
        warning_message "  Service manager: systemd user manager $systemd_status"
    else
        say "  Service manager: systemd user manager $systemd_status"
    fi
    say ''
    if [[ $method == binary ]]; then
        installed_version=''
        if [[ -x $binary ]]; then installed_version=$("$binary" --version 2>/dev/null || true); fi
        if [[ $installed_version == "zelport $ZELPORT_RELEASE (built "*")" && $reinstall == no ]]; then
            already_installed_notice "$ZELPORT_RELEASE"
            return 0
        fi
    fi
    # The temporary directory is removed even when verification or installation fails.
    work_dir=$(mktemp -d "${TMPDIR:-/tmp}/zelport-install.XXXXXX")
    install_tmp=''
    trap cleanup EXIT
    if [[ $use_systemd == yes ]]; then
        if [[ $method == binary ]]; then
            unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
            [[ $unit_dir == /* ]] || die 'XDG_CONFIG_HOME must be absolute when set.'
            unit="$unit_dir/zelport.service"
            user_unit > "$work_dir/zelport.service"
            [[ ! -L $unit ]] || die 'Existing service is a symlink. Use --no-start and manage the service yourself.'
            if [[ -e $unit ]] && ! cmp -s "$unit" "$work_dir/zelport.service"; then
                die 'Existing custom user service was preserved. Use --no-start and manage the service yourself.'
            fi
            fragment=$(systemctl --user show -p FragmentPath --value zelport.service 2>/dev/null || true)
            [[ -z $fragment || $fragment == "$unit" ]] || die 'A service from another installation exists. Use its original installation method.'
        fi
        if [[ $was_active == no ]] && command -v ss >/dev/null 2>&1; then
            if [[ -n $(ss -H -ltn 'sport = :8080') ]]; then
                die 'Port 8080 is already in use. Stop the conflicting instance yourself or use --no-start. No process was stopped.'
            fi
        fi
    fi
    if [[ $method == arch ]]; then
        install_arch
        if [[ $already_installed == yes ]]; then return 0; fi
    else
        if [[ $installed_version == "zelport $ZELPORT_RELEASE (built "*")" ]]; then
            progress "Reinstalling Zelport $ZELPORT_RELEASE from the $cpu release archive."
        else
            progress "Installing Zelport $ZELPORT_RELEASE from the $cpu release archive."
        fi
        install_binary
        changed=yes
    fi
    if [[ $use_systemd == yes ]]; then
        if [[ $method == binary ]]; then
            mkdir -p "$unit_dir"
            if [[ ! -f $unit ]]; then
                install -m 644 "$work_dir/zelport.service" "$unit"
                unit_changed=yes
            fi
        fi
        start_service
    fi
    say ''
    say 'Result:'
    installation_success_notice "$ZELPORT_RELEASE" "$binary"
    if [[ $use_systemd == yes ]]; then
        success_message '  Zelport is running and enabled for your user session.'
    elif [[ $start == yes ]]; then
        warning_message '  No reachable systemd user manager. Automatic startup was not configured.'
    fi
    say ''
    say 'Tips:'
    if [[ ${XDG_CONFIG_HOME:-} == /* ]]; then
        config_file="$XDG_CONFIG_HOME/zelport/config.json"
    else
        config_file="$HOME/.config/zelport/config.json"
    fi
    printf -v config_tip '  Configuration file: %q' "$config_file"
    say "$config_tip"
    say '  Default URL: http://localhost:8080'
    if [[ $use_systemd != yes ]]; then
        printf -v manual_start '  Start Zelport manually: %q' "$binary"
        warning_message "$manual_start"
    fi
    if [[ $method == binary ]]; then
        case ":$PATH:" in
            *":$HOME/.local/bin:"*) ;;
            *) warning_message '  Add ~/.local/bin to PATH to use the zelport command.' ;;
        esac
    fi
    if [[ $omarchy == yes ]]; then
        say '  The Omarchy plugin is separate: omarchy plugin add https://github.com/zelport/zelport-omarchy.git --enable'
    fi
    say ''
}

# Sourcing exposes functions for isolated tests; execution and curl | bash run main.
if [[ ${BASH_SOURCE[0]:-} == "$0" || -z ${BASH_SOURCE[0]:-} ]]; then main "$@"; fi
