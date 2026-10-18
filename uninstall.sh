#!/usr/bin/env bash
# Canonical source: https://github.com/zelport/zelport-installer/blob/main/uninstall.sh
# Remove only Zelport files owned by the detected installation method.
# Preserve user configuration and state unless --purge is explicitly requested.

ZELPORT_UNINSTALLER_VERSION=2026.10.0

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
Zelport Uninstaller $ZELPORT_UNINSTALLER_VERSION

Usage:
  bash uninstall.sh [options]

Options:
  --purge        Also remove the default Zelport configuration and state files.
  -h, --help     Show this help.

The uninstaller removes only files owned by a recognized Zelport installation.
Run it as a regular user, without sudo. User configuration and state are
preserved unless --purge is specified.
EOF
}

detect_distro() {
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

managed_unit() {
    [[ -f $1 && ! -L $1 ]] || return 1
    [[ $(cat -- "$1") == "$(user_unit)" ]]
}

remove_regular_file() {
    local path=$1
    if [[ -L $path ]]; then
        warning_message "  Preserved unexpected symlink: $path"
    elif [[ -e $path && ! -f $path ]]; then
        warning_message "  Preserved unexpected non-file: $path"
    elif [[ -f $path ]]; then
        rm -f -- "$path"
    fi
}

purge_user_data() {
    local path
    for path in "$config_file" "$config_file.saved" "$state_file"; do
        if [[ -L $path || -f $path ]]; then
            rm -f -- "$path"
        elif [[ -e $path ]]; then
            die "Refusing to purge a non-file: $path"
        fi
    done
    rmdir -- "${config_file%/*}" 2>/dev/null || true
    rmdir -- "${state_file%/*}" 2>/dev/null || true
}

root_privileges_result() {
    say 'Result:'
    color_message 1 31 '  Zelport removal was not started because root privileges were detected.'
    say ''
    say 'Tips:'
    warning_message '  Run this uninstaller as your regular user, without sudo.'
    say ''
}

main() {
    set -euo pipefail
    local purge=no platform cpu distro distro_name init_system method=none privileges uid root=no
    local binary existing unit_dir unit fragment='' systemd_status use_systemd=no package_version=''
    local data_dir config_base state_base config_file state_file service_known=no service_removed=no
    local service_unchecked=no omarchy=no

    for arg in "$@"; do
        case "$arg" in
            --help|-h) usage; return 0 ;;
            --purge) purge=yes ;;
            *) die "Unknown argument: $arg. Use --help." ;;
        esac
    done

    banner
    say "Zelport Uninstaller $ZELPORT_UNINSTALLER_VERSION"
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
            say '  Removal method: Homebrew'
            if [[ $root == yes ]]; then warning_message "  Privileges: $privileges"; else say "  Privileges: $privileges"; fi
            say '  Service manager: launchd'
            say ''
            if [[ $root == yes ]]; then root_privileges_result; return 1; fi
            say 'Result:'
            warning_message '  Zelport removal on macOS is managed through Homebrew. No changes were made.'
            say ''
            say 'Tips:'
            say '  Stop Zelport: brew services stop zelport'
            say '  Uninstall Zelport: brew uninstall zelport'
            say ''
            return 0 ;;
        MINGW*|MSYS*|CYGWIN*|Windows_NT)
            warning_message 'This Bash uninstaller is not supported on Windows. No changes were made.'
            say ''
            return 0 ;;
        Linux) ;;
        *) die "Unsupported operating system: $platform" ;;
    esac

    [[ ${HOME:-} == /* && $HOME != / ]] || die 'HOME must be an absolute user home directory.'
    case "$(uname -m)" in
        x86_64|amd64) cpu=amd64 ;;
        aarch64|arm64) cpu=arm64 ;;
        *) cpu=$(uname -m) ;;
    esac
    distro=$(detect_distro)
    distro_name=${distro%% *}
    [[ -n $distro_name ]] || distro_name=unknown
    init_system=$(detect_init_system)
    binary="$HOME/.local/bin/zelport"
    data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/zelport"
    config_base="${XDG_CONFIG_HOME:-$HOME/.config}"
    state_base="${XDG_STATE_HOME:-$HOME/.local/state}"
    [[ $data_dir == /* ]] || die 'XDG_DATA_HOME must be absolute when set.'
    [[ $config_base == /* ]] || die 'XDG_CONFIG_HOME must be absolute when set.'
    [[ $state_base == /* ]] || die 'XDG_STATE_HOME must be absolute when set.'
    config_file="$config_base/zelport/config.json"
    state_file="$state_base/zelport/endpoint.json"
    unit_dir="$config_base/systemd/user"
    unit="$unit_dir/zelport.service"

    if command -v pacman >/dev/null 2>&1; then
        package_version=$(pacman -Q zelport 2>/dev/null || true)
    fi
    if [[ -n $package_version ]]; then
        method=pacman
    elif [[ -e $binary || -L $binary ]]; then
        method=binary
    else
        existing=$(command -v zelport 2>/dev/null || true)
        if [[ -n $existing ]]; then method=other; fi
    fi

    if ! command -v systemctl >/dev/null 2>&1; then
        systemd_status='unavailable (systemctl not found)'
    elif systemctl --user show-environment >/dev/null 2>&1; then
        systemd_status=available
        use_systemd=yes
    else
        systemd_status='unavailable (user manager not reachable)'
    fi

    say ''
    say 'Preflight checks:'
    say "  Host: $platform ($distro_name)"
    say "  Architecture: $cpu"
    say "  Init system: $init_system"
    say "  Removal method: $method"
    if [[ $root == yes ]]; then warning_message "  Privileges: $privileges"; else say "  Privileges: $privileges"; fi
    if [[ $systemd_status == unavailable* ]]; then
        warning_message "  Service manager: systemd user manager $systemd_status"
    else
        say "  Service manager: systemd user manager $systemd_status"
    fi
    say ''
    if [[ $root == yes ]]; then root_privileges_result; return 1; fi

    if [[ $method == other ]]; then
        say 'Result:'
        color_message 1 31 "  Zelport at $existing is not owned by this uninstaller. No changes were made."
        say ''
        say 'Tips:'
        warning_message '  Remove Zelport with its original installation method.'
        say ''
        return 1
    fi

    if [[ $method == none && $purge == no ]]; then
        say 'Result:'
        warning_message '  No supported Zelport installation was found. No changes were made.'
        say ''
        return 0
    fi

    if [[ $method == binary ]]; then
        existing=$(command -v zelport 2>/dev/null || true)
        [[ -z $existing || $existing == "$binary" ]] || die "Another Zelport installation exists at $existing. Remove it with its original installation method."
        [[ ! -L $binary ]] || die 'The installation target is a symlink. Remove it with its original installation method.'
        [[ -f $binary ]] || die 'The installation target is not a regular file.'
        [[ -x $binary ]] || die 'The installation target is not executable.'
        [[ $("$binary" --version 2>/dev/null || true) == 'zelport '* ]] || die 'The installation target does not identify itself as Zelport.'
        if [[ -e $unit || -L $unit ]]; then
            [[ $use_systemd == yes ]] || die 'The managed Zelport user service cannot be stopped because the systemd user manager is unavailable.'
            managed_unit "$unit" || die 'The existing custom Zelport user service was preserved. Remove it with its original installation method.'
            service_known=yes
        fi
        if [[ $use_systemd == yes ]]; then
            fragment=$(systemctl --user show -p FragmentPath --value zelport.service 2>/dev/null || true)
            [[ -z $fragment || $fragment == "$unit" ]] || die 'A service from another installation exists. Remove it with its original installation method.'
            if [[ -n $fragment ]]; then service_known=yes; fi
        fi
    elif [[ $method == pacman ]]; then
        [[ ! -e $binary && ! -L $binary ]] || die 'A user-local Zelport installation was preserved. Remove it with its original installation method.'
        if [[ -e $unit || -L $unit ]]; then
            die 'A user-local Zelport service was preserved. Remove it with its original installation method.'
        fi
        if [[ $use_systemd == yes ]]; then
            fragment=$(systemctl --user show -p FragmentPath --value zelport.service 2>/dev/null || true)
            [[ -z $fragment || $fragment == /usr/lib/systemd/user/zelport.service ]] || die 'A service from another installation exists. Remove it with its original installation method.'
            if [[ -n $fragment ]]; then service_known=yes; fi
        else
            service_unchecked=yes
        fi
    fi

    say 'Progress:'
    if [[ $service_known == yes ]]; then
        say '  Stopping and disabling the Zelport user service.'
        systemctl --user disable --now zelport.service
        service_removed=yes
    fi

    if [[ $method == binary ]]; then
        say '  Removing the Zelport binary and installer-managed files.'
        rm -f -- "$binary"
        if [[ -e $unit ]]; then rm -f -- "$unit"; service_removed=yes; fi
        if [[ -L $data_dir ]]; then
            warning_message "  Preserved unexpected data directory symlink: $data_dir"
        elif [[ -e $data_dir && ! -d $data_dir ]]; then
            warning_message "  Preserved unexpected non-directory: $data_dir"
        else
            remove_regular_file "$data_dir/LICENSE"
            remove_regular_file "$data_dir/THIRD_PARTY_NOTICES.txt"
            rmdir -- "$data_dir" 2>/dev/null || true
        fi
        rmdir -- "${binary%/*}" 2>/dev/null || true
    elif [[ $method == pacman ]]; then
        require sudo
        warning_message '  Removing the Zelport package. pacman may request your sudo password.'
        if [[ ! -t 0 ]] && ( : < /dev/tty ) 2>/dev/null; then
            sudo pacman -R zelport < /dev/tty
        else
            sudo pacman -R zelport
        fi
    fi

    if [[ $service_removed == yes ]]; then systemctl --user daemon-reload; fi
    if [[ $purge == yes ]]; then
        say '  Removing the default Zelport configuration and state files.'
        purge_user_data
    fi

    say ''
    say 'Result:'
    if [[ $method == none ]]; then
        success_message '  Zelport configuration and state remnants were removed successfully.'
    else
        success_message '  Zelport was uninstalled successfully.'
    fi
    if [[ $service_unchecked == yes ]]; then
        warning_message '  No reachable systemd user manager was available to stop the packaged user service.'
    fi
    say ''
    say 'Tips:'
    if [[ $purge == yes ]]; then
        say '  Default configuration and state files were removed where present.'
    else
        say "  Configuration was preserved in ${config_file%/*}/"
        say "  Runtime state directory may remain at ${state_file%/*}/"
    fi
    if command -v omarchy-version >/dev/null 2>&1 && omarchy-version >/dev/null 2>&1; then omarchy=yes; fi
    if [[ $omarchy == yes ]]; then
        say '  Remove the separate Omarchy plugin, if installed: omarchy plugin remove zelport.integration'
    fi
    say ''
}

if [[ ${BASH_SOURCE[0]:-} == "$0" || -z ${BASH_SOURCE[0]:-} ]]; then main "$@"; fi
