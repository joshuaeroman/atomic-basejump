# Security

Atomic Basejump is a **system management utility**. It is not designed as a fully sandboxed end-user app.

## Privileges

When installed as a Flatpak (`io.github.joshuaroman.AtomicBasejump`), the application may:

| Access | Purpose |
|--------|---------|
| System bus → `org.projectatomic.rpmostree1` | Read deployments, status, package metadata |
| System bus → `org.freedesktop.login1` | Request reboot |
| `org.freedesktop.Flatpak` host portal | Run `rpm-ostree` / `ostree` on the host for upgrades, rebases, rollbacks, pins, and package layers |
| Network | Fetch OCI image tags from public registries (e.g. Quay, GHCR) |
| `pkexec` (host) | Optional Plasma login account prep when switching GNOME-family → Plasma-family bases |

Mutations use the same host tools a user would run in a terminal; they are not a separate privileged daemon inside the Flatpak.

## D-Bus and CLI Design

Status, deployment metadata, cached update state, rollback state, package
search, and reboot use permitted D-Bus APIs. rpm-ostree mutations use the
standard host CLI when running in the Flatpak. Although rpm-ostreed exposes
mutation methods on the system bus, each transaction must then be started and
monitored through a private peer socket under `/run`, which is not visible in
the sandbox. Atomic Basejump intentionally does not install a host-side bridge
script for that socket. Native development runs may use the D-Bus transaction
path directly.

Pinning remains `ostree admin pin` because libostree does not expose that
operation through rpm-ostreed D-Bus. Plasma account preparation remains a
static `pkexec` operation because it edits host account files.

The complete operation-by-operation rationale is documented in
[ARCHITECTURE.md](ARCHITECTURE.md).

## Distribution note

Primary distribution is **GitHub / self-built Flatpak**, not Flathub, because host command access is required for full functionality.

## Reporting issues

Please report security-relevant bugs via GitHub Issues or GitHub Security Advisories on the project repository:

https://github.com/joshuaroman/atomic-basejump

Include steps to reproduce, whether you used Flatpak or a native binary, and
relevant output from the in-app transaction log dialog. If the issue involves
a transaction failure, the full command output is retained in that log for the
session. Persistent application data (settings, overlay sets, progress stats)
lives under `~/.config/atomicbasejump/` and `~/.local/share/atomicbasejump/`.
