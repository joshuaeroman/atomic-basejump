"""Small Gio client for the rpm-ostreed D-Bus API.

The system-bus API is usable from the Flatpak sandbox. Transaction progress is
different: rpm-ostreed exposes it on a host-only peer socket, so callers that
cannot access that socket should keep using the standard rpm-ostree CLI.
"""

import threading

from gi.repository import Gio, GLib


SERVICE = "org.projectatomic.rpmostree1"
SYSROOT_PATH = "/org/projectatomic/rpmostree1/Sysroot"
SYSROOT_IFACE = f"{SERVICE}.Sysroot"
OS_IFACE = f"{SERVICE}.OS"
TRANSACTION_IFACE = f"{SERVICE}.Transaction"


def _unpack(value):
    if isinstance(value, GLib.Variant):
        return _unpack(value.unpack())
    if isinstance(value, dict):
        return {key: _unpack(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_unpack(item) for item in value)
    return value


def _vardict(values):
    return {key: GLib.Variant(value_type, value) for key, (value_type, value) in values.items()}


class RpmOstreeDBusClient:
    def __init__(self):
        self._bus = None
        self._os_path = None
        self._lock = threading.RLock()

    def _connect(self):
        with self._lock:
            if self._bus is None:
                self._bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
                try:
                    self._bus.call_sync(
                        SERVICE,
                        SYSROOT_PATH,
                        SYSROOT_IFACE,
                        "RegisterClient",
                        GLib.Variant("(a{sv})", (_vardict({"id": ("s", "atomic-basejump")} ),)),
                        GLib.VariantType.new("()"),
                        Gio.DBusCallFlags.NONE,
                        5000,
                        None,
                    )
                except GLib.Error:
                    # Registration is useful for daemon lifecycle tracking but
                    # must not prevent read-only operation on older daemons.
                    pass
            return self._bus

    def _call(self, path, interface, method, signature, args, result="()"):
        return _unpack(self._connect().call_sync(
            SERVICE, path, interface, method,
            GLib.Variant(signature, args) if signature else None,
            GLib.VariantType.new(result), Gio.DBusCallFlags.NONE, 30000, None,
        ))

    def _get_property(self, path, interface, name):
        result = self._call(
            path,
            "org.freedesktop.DBus.Properties",
            "Get",
            "(ss)",
            (interface, name),
            "(v)",
        )
        return _unpack(result[0]) if result else None

    def _os_path_for(self, deployments):
        if self._os_path:
            return self._os_path
        booted_path = self._get_property(SYSROOT_PATH, SYSROOT_IFACE, "Booted")
        if booted_path and booted_path != "/":
            self._os_path = booted_path
            return booted_path
        os_name = next((item.get("osname") for item in deployments if item.get("booted")), "")
        if os_name:
            self._os_path = self._call(SYSROOT_PATH, SYSROOT_IFACE, "GetOS", "(s)", (os_name,), "(o)")[0]
        return self._os_path

    def refresh(self):
        deployments = self._get_property(SYSROOT_PATH, SYSROOT_IFACE, "Deployments") or []
        deployments = [dict(item) for item in deployments]
        os_path = self._os_path_for(deployments)
        if not os_path:
            raise RuntimeError("rpm-ostreed has no booted OS")
        return {
            "deployments": deployments,
            "booted": self._get_property(os_path, OS_IFACE, "BootedDeployment") or {},
            "rollback": self._get_property(os_path, OS_IFACE, "RollbackDeployment") or {},
            "cached_update": self._get_property(os_path, OS_IFACE, "CachedUpdate") or {},
            "name": self._get_property(os_path, OS_IFACE, "Name") or "default",
            "policy": self._get_property(SYSROOT_PATH, SYSROOT_IFACE, "AutomaticUpdatePolicy") or "",
        }

    def search(self, term):
        os_path = self._os_path_for([])
        if not os_path:
            self.refresh()
            os_path = self._os_path
        return self._call(os_path, OS_IFACE, "Search", "(as)", ([term],), "(aa{sv})")[0]

    def transaction_call(self, method, signature, args):
        os_path = self._os_path_for([])
        if not os_path:
            self.refresh()
            os_path = self._os_path
        return self._call(os_path, OS_IFACE, method, signature, args, "(s)")[0]

    def check_for_updates(self):
        enabled, address = self._call(
            self._os_path_for([]), OS_IFACE, "AutomaticUpdateTrigger", "(a{sv})", (_vardict({
            "mode": ("s", "check"), "output-to-self": ("b", False)
            }),), "(bs)"
        )
        return address if enabled else ""

    def upgrade(self):
        return self.transaction_call("Upgrade", "(a{sv})", (_vardict({}),))

    def rebase(self, refspec):
        return self.transaction_call("Rebase", "(a{sv}s as)".replace(" ", ""), (_vardict({}), refspec, []))

    def rollback(self):
        return self.transaction_call("Rollback", "(a{sv})", (_vardict({}),))

    def reboot(self):
        self._connect().call_sync(
            "org.freedesktop.login1", "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager", "Reboot",
            GLib.Variant("(b)", (False,)), GLib.VariantType.new("()"),
            Gio.DBusCallFlags.NONE, 30000, None,
        )

    def run_transaction(self, address, on_message=None, on_progress=None):
        """Drive a native transaction on its private peer D-Bus socket."""
        connection = Gio.DBusConnection.new_for_address_sync(
            address, Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT, None, None
        )
        loop = GLib.MainLoop()
        result = {"success": False, "error": "Transaction did not finish"}

        def signal(_connection, _sender, _path, _interface, name, parameters, _data):
            values = parameters.unpack()
            if name == "Message" and on_message:
                on_message(values[0])
            elif name == "TaskBegin" and on_message:
                on_message(values[0])
            elif name == "PercentProgress" and on_progress:
                on_progress(values[0], values[1])
            elif name == "Finished":
                result["success"], result["error"] = values
                loop.quit()

        connection.signal_subscribe(None, TRANSACTION_IFACE, None, "/", None,
                                    Gio.DBusSignalFlags.NONE, signal, None)
        connection.call_sync(None, "/", TRANSACTION_IFACE, "Start", None,
                             GLib.VariantType.new("(b)"), Gio.DBusCallFlags.NONE,
                             30000, None)
        loop.run()
        connection.close_sync(None)
        if not result["success"]:
            raise RuntimeError(result["error"] or "rpm-ostree transaction failed")
