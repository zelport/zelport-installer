# Working on Zelport Installer

Write documentation, comments, errors, user-visible output, and commit messages
in English.
`install.sh` and `uninstall.sh` are the canonical editable sources. The copies
in `zelport-web` are generated from exact verified release assets. Never edit
the website copies directly or synchronize them from an untagged branch.

The canonical Installer release identifier is `vYYYY.MM.MICRO`. Use it in
documentation, operator inputs, workflow dispatches, tags, GitHub Releases and
reports. The embedded `ZELPORT_INSTALLER_VERSION` and
`ZELPORT_UNINSTALLER_VERSION` fields are derived payloads without `v` because
their script format requires it; they must match. `MICRO` starts at `0` each
month and increments for each additional release in that month. Change both
script fields for every published script change. Resolve the latest stable App
release at runtime from its published `SHA256SUMS`, validate its canonical
`vMAJOR.MINOR.PATCH` tag, and download remaining assets from that exact release.
Never fabricate a checksum or use draft or prerelease assets.

Preserve existing Zelport configuration and custom services. Manage only the
Zelport service owned by the selected installation method. Never stop unrelated
processes. Keep tests isolated with temporary homes and mocked system
operations.

Before a release commit, run `make release-ready`; it checks shell syntax, the
complete Python suite, the latest public App release contract, deterministic
release assets, and their exact contents. Use `make check` for changes that do
not affect release preparation.

Use Conventional Commits. Preserve the existing repository-local Git author and
committer configuration unless the user explicitly requests a change. Do not
add or change a remote, push, tag, publish a release, or write to another
repository without the user's explicit approval.
