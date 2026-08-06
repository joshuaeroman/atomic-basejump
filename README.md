# Atomic Basejump

**Atomic Basejump** is a desktop application for managing system deployments, base images, and package layers on Fedora Atomic desktops (Silverblue, Kinoite, Aurora, Bazzite, Bluefin, and custom bootc images).

**Status:** pre-release **0.9** of the multi-frontend rewrite — expect rough edges; report issues on the tracker below.

It ships dual native frontends (KDE/Kirigami and GNOME/Libadwaita) selected by desktop environment or a settings preference, sharing one Python core.

**License:** [GPL-3.0-or-later](LICENSE)

---

## Features

- **System Overview**: View active deployment details, OS version, container image reference, and currently layered packages at a glance.
- **Deployment Management**: Manage active, staged, and rollback deployments. Pin key deployments to prevent automatic deletion, or roll back to a previous state with one click.
- **Base Image Rebase**: Switch OCI base images using built-in presets (Bazzite, Aurora, Bluefin, Fedora) or registry tags, with optional overlay apply/reset alongside rebase.
- **Overlay Sets**: Create, save, apply, duplicate, import, and export layered package profiles.
- **Host Auto-Update Policy**: Inspect and toggle the host `rpm-ostreed-automatic.timer`, plus manual “check for updates” with last-checked tracking.
- **Desktop Notifications**: Optional notifications for update-related events (when enabled in Settings).
- **Live Activity Logs**: Stream operation logs in a status bar (KDE) or log dialog (both frontends) so you know what the system is doing.
- **Desktop Transition Safety**: Detect GNOME-family → Plasma rebases and staged Plasma while booted elsewhere; prepare Plasma login accounts when needed.

---

## Why not Flathub?

Atomic Basejump is distributed via GitHub Releases and self-built Flatpak bundles rather than Flathub.

Because Atomic Basejump is a system management utility that performs OS updates, base image rebases, and package layering, it requires permission to execute host commands (`rpm-ostree` / `ostree`) via Flatpak host portal permissions (`--talk-name=org.freedesktop.Flatpak`).

Flathub's security policies intentionally restrict apps requiring full host command access to maintain strict sandbox isolation. Because restricting host access would prevent performing core system operations, Atomic Basejump is packaged as a privileged system utility.

See [SECURITY.md](SECURITY.md) for details on permissions and privileges.

See [ARCHITECTURE.md](ARCHITECTURE.md) for why each operation uses D-Bus or
the host rpm-ostree CLI. In brief, read-only status and search use the system
bus in the sandbox, while mutations use the standard CLI because rpm-ostreed
transaction progress requires a private host peer socket.

---

## Installation

### Pre-built Flatpak (Releases)

```bash
flatpak install --user -y atomic-basejump.flatpak
flatpak run io.github.joshuaroman.AtomicBasejump
```

### Build from source

```bash
flatpak-builder --user --install-deps-from=flathub --repo=repo \
  --disable-rofiles-fuse --force-clean build-flatpak \
  io.github.joshuaroman.AtomicBasejump.yml
flatpak build-bundle repo atomic-basejump.flatpak io.github.joshuaroman.AtomicBasejump
flatpak --user install -y --reinstall atomic-basejump.flatpak
```

See [BUILD.md](BUILD.md) for Flatpak build and development workflows.

---

## Contributing

See [BUILD.md](BUILD.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
