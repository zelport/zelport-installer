# Working on Zelport Installer

Write documentation, comments, errors, user-visible output, and commit messages
in English.
`install.sh` and `uninstall.sh` are the canonical editable sources. The copies
in `zelport-web` are generated from exact verified release assets. Never edit
the website copies directly or synchronize them from an untagged branch.

Use `YYYYMMDD.N` for `ZELPORT_INSTALLER_VERSION` and
`ZELPORT_UNINSTALLER_VERSION`, which must match, and `vYYYYMMDD.N` for installer
tags and releases. Use numeric SemVer for `ZELPORT_RELEASE`. App tags and URLs
add the `v` prefix. Change both script versions for every published script
change. Keep the App version, immutable Arch recipe commit, and measured recipe
SHA-256 together. Never fabricate a checksum or resolve a moving App or package
release from the installer.

Preserve existing Zelport configuration and custom services. Manage only the
Zelport service owned by the selected installation method. Never stop unrelated
processes. Keep tests isolated with temporary homes and mocked system
operations.

Before a commit, run `make check` and `make release-assets`. `make check` covers
shell syntax, the complete Python suite, and the deterministic two-build
comparison of release assets.

Use Conventional Commits. Preserve the existing repository-local Git author and
committer configuration unless the user explicitly requests a change. Do not
add or change a remote, push, tag, publish a release, or write to another
repository without the user's explicit approval.
