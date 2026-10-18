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

The release workflow accepts only a matching `vYYYYMMDD.N` tag, reruns the
checks, builds `dist/install.sh`, `dist/uninstall.sh`, and `dist/SHA256SUMS`, and
publishes those exact files. Website synchronization is a separate verified
release step.
