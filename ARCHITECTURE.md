# Architecture

Atomic Basejump prefers D-Bus when the operation can be completed through a
normal bus call. It uses the rpm-ostree CLI only where the Flatpak sandbox
cannot safely drive the daemon transaction lifecycle.

## Transport Choices

| Operation | Native execution | Flatpak execution | Reason |
|---|---|---|---|
| Deployment status and update state | D-Bus | D-Bus | Structured read-only properties are available on the system bus. |
| Package search | D-Bus | D-Bus | `OS.Search` is a synchronous read-only method. |
| Upgrade, rebase, rollback, update checks | D-Bus transaction (CLI fallback) | `flatpak-spawn --host` CLI | rpm-ostreed returns a private peer address at `/run/rpm-ostree-transaction.sock`; a client must connect to it and call `Transaction.Start()`. The host `/run` is not exposed to this sandbox. Native runs can drive the D-Bus transaction directly. |
| Overlay install/remove, override reset | CLI | CLI | Handled by `rpm-ostree install` / `override remove` / `reset` in both modes; no D-Bus transaction path is used. |
| Reboot | `login1` D-Bus | `login1` D-Bus | A normal system-bus method call; no private transaction socket is involved. |
| Pin and unpin | `ostree admin` CLI | `ostree admin` CLI | libostree has no equivalent daemon D-Bus API. |
| Plasma login preparation | `pkexec` static command | `pkexec` static command | This edits host account files and has no rpm-ostreed API. |

The application deliberately does not install a host-side helper or driver
script to bridge the transaction socket. That would add a host footprint and
would be more intrusive than the intended Flatpak model. The CLI is the
standard rpm-ostree client and already handles transaction startup, progress,
polkit, and cleanup correctly.

All CLI arguments are passed as argument vectors. User-provided image
references are validated and are never interpolated into shell source.

## D-Bus Data

The daemon's `Sysroot.Deployments` property contains the same deployment
metadata consumed by the existing UI: booted/staged/pinned state, checksums,
image references, versions, layered packages, local packages, and removals.
`OS.CachedUpdate` and `OS.RollbackDeployment` provide authoritative update and
rollback state without parsing command output.
