# Contributing to Atomic Basejump

Thanks for your interest in improving Atomic Basejump.

## Development loop

1. Prefer a **Flatpak rebuild** after UI or backend changes you want to run for real (see [BUILD.md](BUILD.md)).
2. Use a **direct Python run** (`./basejump-launcher.sh`) for fast iteration on UI/backend logic; note that it runs unsandboxed and falls back to `pkexec` where the Flatpak would use `flatpak-spawn --host`.
3. Fully quit the tray icon before relaunching, or you may still see the old process.

## Running tests

The repository ships plain stdlib test scripts; run them from the repo root:

```bash
python3 test_parity.py   # main unit suite: overlays, progress estimation, status flags
python3 test_create.py   # overlay set creation smoke test
python3 test_qml.py      # QML engine smoke test
python3 test_style.py    # QtQuick style availability check
```

The three smoke scripts need the KDE frontend deps (`python3-qt6`,
`kf6-kirigami-devel`) installed; `test_parity.py` runs with stdlib only.
Each script exits non-zero on failure.

## Scope for 1.0-era work

- Bug fixes, UI polish, packaging, and docs are welcome.
- Large architecture changes (multi-DE frontends, core library splits) should be discussed first.
- UI is English-only for now; `qsTr` is fine, full `po/` catalogs can wait.

## Identity

- Display name: **Atomic Basejump**
- App ID: `io.github.joshuaroman.AtomicBasejump`
- Binary: `atomic-basejump`

## License

Contributions are accepted under **GPL-3.0-or-later** (see [LICENSE](LICENSE)).
