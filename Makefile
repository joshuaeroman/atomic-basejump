# Atomic Basejump — common build targets
#
# Usage:
#   make build-flatpak     Prune intermediates, build, export to local repo/
#   make install-flatpak   Fresh build, then bundle + user install
#   make prune             Remove all build outputs except the bundle
#   make run               Run the installed Flatpak
#   make info              Show installed Flatpak metadata
#   make clean             Prune, and remove the bundle too

APP_ID      := io.github.joshuaroman.AtomicBasejump
MANIFEST    := io.github.joshuaroman.AtomicBasejump.yml
BUILD_DIR   := build-flatpak
REPO        := repo
BUNDLE      := atomic-basejump.flatpak
TOOLBOX     := fedora-toolbox-44

FLATPAK_BUILDER_FLAGS := --disable-rofiles-fuse --force-clean --repo=$(REPO)

# Prefer host flatpak-builder; fall back to toolbox (common on Atomic hosts).
ifeq ($(shell command -v flatpak-builder 2>/dev/null),)
  FLATPAK_BUILDER := toolbox run --container $(TOOLBOX) flatpak-builder
else
  FLATPAK_BUILDER := flatpak-builder
endif

.PHONY: build-flatpak install-flatpak run info prune clean

# Remove everything except the final bundle (atomic-basejump.flatpak).
# Runs automatically at the start of build-flatpak.
prune:
	rm -rf $(BUILD_DIR) .flatpak-builder $(REPO) build-dir build __pycache__ *.whl
	find . -type d -name __pycache__ -not -path './.git/*' -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -not -path './.git/*' -prune -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.py[cod]' -not -path './.git/*' -delete 2>/dev/null || true

build-flatpak: prune
	$(FLATPAK_BUILDER) $(FLATPAK_BUILDER_FLAGS) $(BUILD_DIR) $(MANIFEST)

install-flatpak: build-flatpak
	flatpak build-bundle $(REPO) $(BUNDLE) $(APP_ID)
	flatpak --user install -y --reinstall $(BUNDLE)

run:
	flatpak run $(APP_ID)

info:
	flatpak info $(APP_ID)

clean: prune
	rm -f $(BUNDLE)
