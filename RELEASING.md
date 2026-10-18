# Releasing Zelport Installer

`install.sh` and `uninstall.sh` are the editable sources. The website copies are
generated from verified release assets and must not be edited or synchronized
from an untagged branch. Versioning rules are documented in
[README.md](README.md#versioning).

## Checks

Run the complete check and build deterministic release assets:

```sh
make check
make release-assets
```

The test suite uses temporary homes and mocked system operations. It does not
install packages or modify a running Zelport App. Native distribution and
systemd verification remain separate release checks.

Before publishing an installer that resolves App releases dynamically, verify
that the latest stable Zelport App release publishes `PKGBUILD`, its source
archive, and checksums for both the package recipe and platform archives. Publish
the compatible App release before the installer release.

The release workflow accepts only a matching `vYYYYMMDD.N` tag, reruns the
checks, builds `dist/install.sh`, `dist/uninstall.sh`, and `dist/SHA256SUMS`, and
publishes those exact files. Website synchronization is a separate verified
release step.
