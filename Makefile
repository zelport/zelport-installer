PYTHON ?= python3
DIST_DIR ?= dist

.DEFAULT_GOAL := check
.PHONY: help check verify test version verify-version verify-app-release release-ready release-assets verify-release-assets verify-published-release

help:
	@printf '%s\n' 'make check' 'make verify' 'make release-ready' 'make verify-published-release'

check:
	bash -n install.sh uninstall.sh
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

verify: check verify-version
	$(MAKE) release-assets
	$(MAKE) verify-release-assets

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

version:
	@$(PYTHON) scripts/release_version.py

verify-version:
	@$(PYTHON) scripts/release_version.py --check

verify-app-release:
	$(PYTHON) scripts/verify_app_release.py

release-ready: check verify-version verify-app-release
	$(MAKE) release-assets
	$(MAKE) verify-release-assets

release-assets:
	$(PYTHON) scripts/build_release.py --output "$(DIST_DIR)"

verify-release-assets:
	$(PYTHON) scripts/verify_release_assets.py --release-dir "$(DIST_DIR)"

verify-published-release:
	$(PYTHON) scripts/verify_published_release.py --repository zelport/zelport-installer
