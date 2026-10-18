PYTHON ?= python3
DIST_DIR ?= dist

.PHONY: check test release-assets

check:
	bash -n install.sh uninstall.sh
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

release-assets:
	$(PYTHON) scripts/build_release.py --output "$(DIST_DIR)"
