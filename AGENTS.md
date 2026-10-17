# Working on Zelport Installer

Write documentation, comments, errors, and user-visible output in English.
`install.sh` is the only editable installer source. The copy published by the
website is generated from an exact verified release asset and must not be edited
here or synchronized from an untagged branch.

Use `YYYYMMDD.N` for `ZELPORT_INSTALLER_VERSION` and `vYYYYMMDD.N` for installer
tags and releases. Use numeric SemVer for `ZELPORT_RELEASE`; App tags and URLs add
the `v` prefix. Change the installer version for every published script change.
Keep the App version, immutable Arch recipe commit, and measured recipe SHA-256
together. Never fabricate a checksum or resolve a moving latest release.

Preserve existing Zelport configuration, services, and unrelated processes.
Keep tests isolated with temporary homes and mocked system operations. Before a
commit, run `bash -n install.sh`, the complete Python suite, `make check`, and a
deterministic two-build comparison of `make release-assets` output.

Use Conventional Commits in English. Configure Git author and committer as
`zdeneksvarc <79550344+zdeneksvarc@users.noreply.github.com>`. Do not create a
remote, push, tag, publish a release, or change another repository without the
user's explicit approval.
