# Building Atomic Basejump

How to build, install, run, and verify **Atomic Basejump** on Fedora Atomic / similar systems.

| | |
|--|--|
| **App ID** | `io.github.joshuaroman.AtomicBasejump` |
| **Binary** | `atomic-basejump` |
| **Flatpak runtime** | `org.kde.Platform//6.11` |
| **Status / deployments** | system D-Bus (`org.projectatomic.rpmostree1`) |
| **Mutations** | host `rpm-ostree` / `ostree` via `flatpak-spawn --host` when sandboxed; direct exec when native |

---

## Prerequisites

- Flatpak with Flathub remote (for the KDE SDK/Platform)
- `flatpak-builder`
- On Atomic hosts, `--disable-rofiles-fuse` is often required for `flatpak-builder`

The C/C++ toolchain, meson, ninja, and pkg-config used to build the bundled
GTK/libadwaita/PyGObject modules come from the `org.kde.Sdk` inside
flatpak-builder's build sandbox — nothing extra is needed on the host.

Install SDK/runtime as needed:

```bash
flatpak install -y flathub org.kde.Sdk//6.11 org.kde.Platform//6.11
```

Optional: a Fedora toolbox (e.g. `fedora-toolbox-44`) with build tools if you prefer not to install them on the host.

---

## Always reinstall the Flatpak after code changes

The app you run day-to-day is the **user Flatpak**. After any code, QML, or manifest change that should appear in the running app:

1. Rebuild and install the Flatpak (Option 1 below).
2. Fully quit Atomic Basejump (including the tray icon).
3. Start again with `flatpak run io.github.joshuaroman.AtomicBasejump`.
4. Confirm freshness with `flatpak info io.github.joshuaroman.AtomicBasejump` (Date/Commit) or the About page build time.

Treat **Flatpak rebuild + install as the default finish step** for UI/backend work.

The backend uses system-bus D-Bus for status, search, and reboot. Native runs
can drive rpm-ostreed transactions through D-Bus; the Flatpak uses the host
rpm-ostree CLI for mutations because transaction progress requires a private
host socket. See [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Option 1: Flatpak build and install (recommended)

```bash
flatpak-builder --disable-rofiles-fuse --force-clean --user --install \
  build-flatpak io.github.joshuaroman.AtomicBasejump.yml

flatpak run io.github.joshuaroman.AtomicBasejump
```

### Toolbox variant

```bash
toolbox run --container fedora-toolbox-44 flatpak-builder \
  --disable-rofiles-fuse --force-clean --user --install \
  build-flatpak io.github.joshuaroman.AtomicBasejump.yml
```

---

## Option 2: Direct local Python run (testing only)

Use this for a **fast check** while iterating, avoiding a full Flatpak rebuild. Note that certain host interactions like `flatpak-spawn --host` will fall back to local `pkexec` when not sandboxed.

> **Flatpak users can stop here.** The bundle ships its own Qt/PyQt (via the
> PyQt BaseApp), GTK4/libadwaita/PyGObject (manifest modules), and vendored
> Python deps — the host needs only `flatpak`. Everything below is for
> running the source tree natively, for development only.

### Dependencies (Fedora)

```bash
sudo dnf install -y \
    python3-pyqt6 qt6-qtbase-devel qt6-qtdeclarative-devel \
    kf6-kirigami-devel \
    gtk4 libadwaita python3-gobject \
    python3-requests python3-dasbus
```

All of these are in the **standard Fedora repositories** (fedora/updates),
the same repos an Atomic image ships with — none require RPM Fusion, a COPR,
or another extra repo. On Atomic hosts, layer them instead with
`rpm-ostree install` (e.g. `rpm-ostree install kf6-kirigami-devel …` then
reboot), or do both with `rpm-ostree install` in a toolbox.

### What the base images already ship

Verified against the Fedora 44 base Kinoite and Silverblue image commits
(2026-08): **every runtime dependency is already installed** in both base
images — `python3-pyqt6`, `qt6-qtbase`, `qt6-qtdeclarative`, `gtk4`,
`libadwaita`, `python3-gobject`, `python3-requests`, `python3-dasbus`. The
only runtime exception is **`kf6-kirigami` (the Kirigami QML module), which
is present in Kinoite but absent in Silverblue** — a Silverblue host running
the KDE frontend needs `rpm-ostree install kf6-kirigami`.

The `-devel` packages (`qt6-qtbase-devel`, `qt6-qtdeclarative-devel`,
`kf6-kirigami-devel`) are **not** in either base image; they are only needed
for development work, not to run the app.

### Run

```bash
./basejump-launcher.sh
```

---

## Option 3: Bundle for distribution

```bash
flatpak-builder --disable-rofiles-fuse --force-clean \
  build-flatpak io.github.joshuaroman.AtomicBasejump.yml

flatpak build-export repo build-flatpak
flatpak build-bundle repo atomic-basejump.flatpak \
  io.github.joshuaroman.AtomicBasejump

flatpak --user install -y --reinstall atomic-basejump.flatpak
```

---

## Makefile shortcuts

The repository ships a `Makefile` wrapping the common Flatpak flows (it
falls back to a toolbox if `flatpak-builder` is not on the host):

| Target | What it does |
|--------|--------------|
| `make build-flatpak` | Prune intermediates, then fresh build exported to local `repo/` |
| `make install-flatpak` | Build, bundle, and user-install |
| `make prune` | Remove all build outputs except `atomic-basejump.flatpak` |
| `make run` | `flatpak run io.github.joshuaroman.AtomicBasejump` |
| `make info` | Show installed Flatpak metadata |
| `make clean` | Prune, and remove the bundle too |

`make build-flatpak` (and therefore `install-flatpak`) starts by pruning
every intermediate — `build-flatpak/`, `.flatpak-builder/`, `repo/`,
`build-dir/`, `build/`, and Python bytecode — so the final bundle is the
only thing left after a build. Note that pruning also drops the
`.flatpak-builder` module cache, so each build rebuilds the bundled GTK /
libadwaita / PyGObject modules from source (slower, but always fresh).

The toolbox container name (`fedora-toolbox-44`) is set in the `Makefile`.

---

## Python dependencies

The Flatpak fetches pure-Python deps (`requests`, `dasbus`, and their
transitive deps) from PyPI **at build time** via the `basejump-deps.json`
module (generated by `flatpak-pip-generator.py` from flatpak-builder-tools),
which pins download URLs and SHA-256 checksums. PyQt6 and PyGObject are **not**
pip-installed — PyQt6 comes from the `com.riverbankcomputing.PyQt.BaseApp`
base, PyGObject from the bundled GTK module.

To refresh the pins after changing dependencies, regenerate and commit the
module (the stray wheels the generator drops in the working directory can be
discarded — the manifest fetches them itself):

```bash
# 1. List the pip-only runtime deps (requests and dasbus; PyQt6/PyGObject
#    are provided by the runtime/base, not PyPI):
printf 'requests\ndasbus\n' > /tmp/basejump-reqs.txt

# 2. Generate the flatpak module (downloads wheels for checksum pinning):
python3 flatpak-pip-generator.py --requirements-file=/tmp/basejump-reqs.txt \
  --output=basejump-deps

# 3. Commit basejump-deps.json; discard the downloaded *.whl files.
```

Then rebuild with `make install-flatpak` and confirm the new pins were
picked up. Building requires network access to PyPI.

---

## Verifying build freshness

### In-app

Open **About** in the sidebar and check **Version** (`0.9`) and **Build Time**.
The Flatpak build stamps the real build time into `appinfo.py`; direct local
runs (`./basejump-launcher.sh`) show the un-stamped placeholder (`Just now`).

### Command line

```bash
flatpak info io.github.joshuaroman.AtomicBasejump
```

---

## Cleaning build artifacts

`make prune` removes all build outputs except the final bundle
(`atomic-basejump.flatpak`) and runs automatically at the start of every
`make build-flatpak`. `make clean` does the same and also deletes the
bundle:

```bash
make prune   # keep atomic-basejump.flatpak
make clean   # remove everything, including the bundle
```
