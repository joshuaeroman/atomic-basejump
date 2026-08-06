import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from basejump.core.rpm_ostree_dbus import RpmOstreeDBusClient


REFSPEC_RE = re.compile(r"^[A-Za-z0-9._:/@~-]+$")
CLI_FETCH_RE = re.compile(r"\[(\d+)/(\d+)\]")

# Typical share of total transaction time per step (percent). Chunk fetch
# dominates rebases; upgrades/installs only run the non-fetch phases.
# Non-fetch steps total 28% so that no-chunk runs scale to the full bar.
CLI_STEP_WEIGHTS = {
    "import": 2, "fetch": 72, "checkout-tree": 5, "rpm-md": 2, "resolve": 3,
    "relabel": 2, "checkout-packages": 4, "sysusers": 1, "pre": 2, "post": 2,
    "posttrans": 2, "write-rpmdb": 1, "write-commit": 1, "stage": 1,
}

# Initial "typical duration" guesses (seconds). Blended with measured
# durations from timestamped log lines and persisted, so weights track the
# real proportion of time over repeated runs.
CLI_DEFAULT_TYPICALS = {
    "import": 8, "checkout-tree": 25, "rpm-md": 12, "resolve": 20, "relabel": 30,
    "checkout-packages": 45, "sysusers": 5, "pre": 8, "post": 15, "posttrans": 8,
    "write-rpmdb": 10, "write-commit": 8, "stage": 3,
}

CLI_PHASE_PREFIXES = {
    "checkout-tree": "Checking out tree",
    "rpm-md": "Importing rpm-md",
    "resolve": "Resolving dependencies",
    "relabel": "Relabeling",
    "checkout-packages": "Checking out packages",
    "sysusers": "Running systemd-sysusers",
    "pre": "Running pre scripts",
    "post": "Running post scripts",
    "posttrans": "Running posttrans scripts",
    "write-rpmdb": "Writing rpmdb",
    "write-commit": "Writing OSTree commit",
    "stage": "Staging deployment",
}

PLASMA_PREP_SCRIPT = (
    "pkexec bash -c "
    "\"grep -q '^plasmalogin:' /etc/shadow || "
    "echo 'plasmalogin:!*:::::::' >> /etc/shadow; "
    "grep -q '^plasma-setup:' /etc/shadow || "
    "echo 'plasma-setup:!*:::::::' >> /etc/shadow; "
    "grep -q '^plasmalogin:' /etc/gshadow || "
    "echo 'plasmalogin:!*::' >> /etc/gshadow; "
    "grep -q '^plasma-setup:' /etc/gshadow || "
    "echo 'plasma-setup:!*::' >> /etc/gshadow; "
    "rm -f /etc/.fedora-kinoite-plasmalogin-workaround\""
)


def deployment_image_ref(dep):
    """Best-effort image/origin ref from a deployment dict."""
    if not dep:
        return ""
    return (
        dep.get("container-image-reference")
        or dep.get("ref")
        or dep.get("origin")
        or ""
    )


def desktop_family_from_ref(ref_or_image):
    """Classify a ref/image as gnome, plasma, other, or unknown.

    Pure helper (no I/O). Mirrors ImageRegistryService heuristics so status
    flags can be unit-tested without constructing the registry service.
    """
    hay = (ref_or_image or "").strip().lower()
    if not hay:
        return "unknown"
    if any(x in hay for x in ("bazzite-gnome", "silverblue", "bluefin")) or (
        "gnome" in hay and "kinoite" not in hay
    ):
        return "gnome"
    if any(x in hay for x in ("kinoite", "aurora", "bazzite")):
        return "plasma"
    if any(x in hay for x in ("sericea", "sway", "budgie", "onyx", "coreos")):
        return "other"
    return "unknown"


def plasma_login_repair_available(booted_dep, pending_dep):
    """True when a Plasma deployment is staged while booted on non-Plasma."""
    booted_family = desktop_family_from_ref(deployment_image_ref(booted_dep))
    staged_family = desktop_family_from_ref(deployment_image_ref(pending_dep))
    if not deployment_image_ref(pending_dep):
        return False
    return booted_family != "plasma" and staged_family == "plasma"


class CliProgressEstimator:
    """Estimate transaction progress from rpm-ostree CLI output.

    The CLI suppresses its percent rendering on pipes, but prints ``[n/N]``
    chunk-fetch lines and ``...done`` phase lines. Each step carries a weight
    proportional to its typical share of total time; chunk fetch advances
    linearly with ``n/N``, and phases gain partial credit as elapsed time
    approaches the step's typical duration. Durations measured from the
    timestamped log lines are blended (EMA) into a persisted typical table,
    so the weights track real time proportions across runs.
    """

    def __init__(self, stats_path=None):
        if stats_path is None:
            stats_path = Path.home() / ".local" / "share" / "atomicbasejump" / "progress_stats.json"
        self._stats_path = Path(stats_path)
        self._typicals = dict(CLI_DEFAULT_TYPICALS)
        self._load_stats()
        self.reset()

    def reset(self):
        self._saw_chunks = False
        self._fetch_fraction = 0.0
        self._completed = 0.0
        self._done = set()
        self._current = None
        self._step_start = 0.0
        self._last = 0.0

    def _load_stats(self):
        try:
            data = json.loads(self._stats_path.read_text())
            for step, avg in data.get("typical", {}).items():
                if step in self._typicals and avg > 0:
                    self._typicals[step] = float(avg)
        except Exception:
            pass

    def _save_stats(self):
        try:
            self._stats_path.parent.mkdir(parents=True, exist_ok=True)
            self._stats_path.write_text(json.dumps({"typical": self._typicals}, indent=2))
        except Exception:
            pass

    def _denominator(self):
        total = sum(CLI_STEP_WEIGHTS.values())
        if not self._saw_chunks:
            total -= CLI_STEP_WEIGHTS["fetch"]
        return max(total, 1)

    def _weight(self, step):
        return CLI_STEP_WEIGHTS.get(step, 0)

    def _progress(self, elapsed):
        base = self._completed
        if self._saw_chunks:
            base += self._weight("fetch") * self._fetch_fraction
        if self._current and self._step_start is not None:
            spent = max(0.0, elapsed - self._step_start)
            typical = max(self._typicals.get(self._current, 1.0), 1.0)
            base += self._weight(self._current) * min(1.0, spent / typical)
        return min(0.99, base / self._denominator())

    def update(self, line, elapsed):
        """Feed one output line; return (progress 0..1, message or None)."""
        match = CLI_FETCH_RE.search(line)
        if match:
            n, total = int(match.group(1)), int(match.group(2))
            self._saw_chunks = True
            if total > 0:
                self._fetch_fraction = n / total
                self._last = self._progress(elapsed)
                return self._last, f"Fetching chunk {n}/{total}"

        if line.startswith("Importing: ") and "import" not in self._done:
            return self._complete_step("import", elapsed), None

        for step, prefix in CLI_PHASE_PREFIXES.items():
            if line.startswith(prefix):
                if step not in self._done and self._current != step:
                    self._current = step
                    self._step_start = elapsed
                if "...done" in line:
                    return self._complete_step(step, elapsed), None
                break

        self._last = max(self._last, self._progress(elapsed))
        return self._last, None

    def _complete_step(self, step, elapsed):
        if step in self._done:
            return self._last
        if self._current == step and self._step_start is not None:
            duration = max(0.0, elapsed - self._step_start)
            if duration > 0:
                self._typicals[step] = (
                    self._typicals.get(step, 0) * 9 + duration
                ) / 10
                self._save_stats()
        self._done.add(step)
        self._completed += self._weight(step)
        self._current = None
        self._step_start = None
        self._last = self._progress(elapsed)
        return self._last


class OstreeBackend:
    def __init__(self, notify=None):
        self.deployments = []
        self.bootedDeployment = {}
        self.pendingDeployment = {}
        self.rollbackDeployment = {}
        self.updateAvailable = False
        self.rebootRequired = False
        self.transactionInProgress = False
        self.transactionProgress = 0
        self.transactionMessage = ""
        self.currentTask = ""
        self.transactionLog = ""
        self.lastError = ""
        self.statusBannerMessage = ""
        self.statusBannerType = "info"
        self.currentOsName = "default"
        self.bootedDesktopFamily = "unknown"
        self.severeUpdateAvailable = False
        self.plasmaLoginRepairAvailable = False
        self._searchCache = {}
        self._notify = notify or (lambda: None)
        self._dbus = RpmOstreeDBusClient()
        self._queue = []
        self._queue_lock = threading.Lock()
        self._cli_estimator = CliProgressEstimator()

    def _reset_cli_progress(self):
        self._cli_estimator.reset()
        self.transactionProgress = 0
        self.transactionMessage = ""

    def _update_cli_progress(self, line, elapsed=0.0):
        progress, message = self._cli_estimator.update(line, elapsed)
        self.transactionProgress = int(round(progress * 100))
        if message:
            self.transactionMessage = message

    def _changed(self):
        try:
            self._notify()
        except Exception:
            pass

    @staticmethod
    def _normalise_deployment(dep):
        dep = dict(dep)
        dep.setdefault("ref", dep.get("container-image-reference") or dep.get("origin", ""))
        dep.setdefault("commit", dep.get("checksum", ""))
        return dep

    def _update_derived_status_flags(self):
        """Derive desktop-family and Plasma repair flags from current deployments."""
        self.bootedDesktopFamily = desktop_family_from_ref(
            deployment_image_ref(self.bootedDeployment)
        )
        self.plasmaLoginRepairAvailable = plasma_login_repair_available(
            self.bootedDeployment, self.pendingDeployment
        )

    def refresh_status(self):
        try:
            data = self._dbus.refresh()
            self.deployments = [self._normalise_deployment(dep) for dep in data["deployments"]]
            self.bootedDeployment = self._normalise_deployment(data["booted"])
            self.rollbackDeployment = self._normalise_deployment(data["rollback"])
            self.pendingDeployment = next(
                (dep for dep in self.deployments if dep.get("staged")), {}
            )
            self.updateAvailable = bool(data["cached_update"])
            self.currentOsName = data["name"]
            self.rebootRequired = bool(self.pendingDeployment)
            self._update_derived_status_flags()
            self._changed()
            return
        except Exception as dbus_error:
            print("D-Bus status unavailable, using rpm-ostree CLI:", dbus_error)

        try:
            cmd = ['rpm-ostree', 'status', '--json']
            if os.path.exists('/.flatpak-info'):
                cmd = ['flatpak-spawn', '--host'] + cmd
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
        except Exception as e:
            print("Failed to get rpm-ostree status:", e)
            return

        self.deployments = [self._normalise_deployment(dep) for dep in data.get("deployments", [])]
        
        self.bootedDeployment = {}
        self.pendingDeployment = {}
        self.rollbackDeployment = {}

        for dep in self.deployments:
            if dep.get("booted"):
                self.bootedDeployment = dep
            elif dep.get("staged"):
                self.pendingDeployment = dep

        self.rollbackDeployment = next(
            (dep for dep in self.deployments if not dep.get("booted") and not dep.get("staged")), {}
        )
                
        self.updateAvailable = False
        self.rebootRequired = bool(self.pendingDeployment)
        self._update_derived_status_flags()
        self._changed()

    def refreshStatus(self):
        self.refresh_status()

    def clearTransactionLog(self):
        self.transactionLog = ""
        self.statusBannerMessage = ""
        self.lastError = ""
        self.transactionMessage = ""
        self._changed()

    def run_transaction(self, cmd_args, task_name=""):
        with self._queue_lock:
            if self.transactionInProgress:
                self._queue.append((cmd_args, task_name))
                queued = True
            else:
                self.transactionInProgress = True
                queued = False
        if queued:
            self.statusBannerMessage = f"Queued: {task_name}..."
            self._changed()
            return
        self._run_cli_transaction(cmd_args, task_name)

    def _start_queued(self):
        with self._queue_lock:
            if self.transactionInProgress or not self._queue:
                return
            cmd_args, task_name = self._queue.pop(0)
            self.transactionInProgress = True
        self._run_cli_transaction(cmd_args, task_name)

    @staticmethod
    def _classify_result(cmd_args, returncode):
        """Return (success, note). rpm-ostree --check implies --unchanged-exit-77:
        exit 77 means the system is already up to date, i.e. a successful check."""
        if returncode == 0:
            return True, ""
        if returncode == 77 and "--check" in cmd_args:
            return True, " (up to date)"
        return False, f" (Code {returncode})"

    def _run_cli_transaction(self, cmd_args, task_name):
        stamp = time.strftime("%H:%M:%S")
        self.currentTask = task_name
        self.transactionLog = (
            f"[{stamp}] Starting: {task_name}\n[{stamp}] Command: {' '.join(cmd_args)}\n"
        )
        self.statusBannerMessage = f"Working: {task_name}..."
        self.statusBannerType = "info"
        self._reset_cli_progress()
        self._changed()

        def _thread_target():
            cmd = cmd_args
            if os.path.exists('/.flatpak-info'):
                cmd = ['flatpak-spawn', '--host'] + cmd

            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                start = time.monotonic()
                for line in iter(process.stdout.readline, ''):
                    self.transactionLog += f"[{time.strftime('%H:%M:%S')}] {line}"
                    self._update_cli_progress(line, time.monotonic() - start)
                    self._changed()
                process.stdout.close()
                process.wait()

                ok, note = self._classify_result(cmd_args, process.returncode)
                if ok:
                    self.statusBannerMessage = f"Completed: {task_name}{note}"
                    self.statusBannerType = "success"
                    self.transactionProgress = 100
                else:
                    self.statusBannerMessage = f"Failed: {task_name}{note}"
                    self.statusBannerType = "error"
                    self.lastError = self.transactionLog
            except Exception as e:
                self.statusBannerMessage = f"Error: {str(e)}"
                self.statusBannerType = "error"
                self.lastError = str(e)
            finally:
                with self._queue_lock:
                    self.transactionInProgress = False
                self.currentTask = ""
                self.refresh_status()
                self._changed()
                self._start_queued()

        threading.Thread(target=_thread_target, daemon=True).start()

    def checkForUpdates(self):
        if not os.path.exists('/.flatpak-info'):
            try:
                address = self._dbus.check_for_updates()
                if address:
                    self._run_dbus_transaction(address, "Checking for updates")
                else:
                    self.refresh_status()
                return
            except Exception as e:
                print("D-Bus update check unavailable:", e)
        self.run_transaction(["rpm-ostree", "upgrade", "--check"], "Checking for updates")
        
    def upgradeSystem(self):
        if not os.path.exists('/.flatpak-info'):
            try:
                self._run_dbus_transaction(self._dbus.upgrade(), "Upgrading system")
                return
            except Exception as e:
                print("D-Bus upgrade unavailable:", e)
        self.run_transaction(["rpm-ostree", "upgrade"], "Upgrading system")
        
    def rebootSystem(self):
        if not os.path.exists('/.flatpak-info'):
            try:
                self._dbus.reboot()
                return
            except Exception as e:
                print("D-Bus reboot unavailable:", e)
        cmd = ["systemctl", "reboot"]
        if os.path.exists('/.flatpak-info'):
            cmd = ['flatpak-spawn', '--host'] + cmd
        subprocess.run(cmd)
        
    def rollbackSystem(self):
        if not os.path.exists('/.flatpak-info'):
            try:
                self._run_dbus_transaction(self._dbus.rollback(), "Rolling back system")
                return
            except Exception as e:
                print("D-Bus rollback unavailable:", e)
        self.run_transaction(["rpm-ostree", "rollback"], "Rolling back system")
        
    def rebaseSystem(self, refspec, options=None):
        if not isinstance(refspec, str) or not REFSPEC_RE.fullmatch(refspec):
            self.statusBannerMessage = "Invalid image reference."
            self.lastError = "Image references may not contain whitespace or shell metacharacters."
            self._changed()
            return
        if options and options.get("prepPlasmaLogin"):
            script = PLASMA_PREP_SCRIPT + '\nrpm-ostree rebase "$1"'
            self.run_transaction(["bash", "-c", script, "basejump", refspec], f"Rebasing to {refspec} with Plasma Prep")
        elif not os.path.exists('/.flatpak-info'):
            try:
                self._run_dbus_transaction(self._dbus.rebase(refspec), f"Rebasing to {refspec}")
                return
            except Exception as e:
                print("D-Bus rebase unavailable:", e)
        else:
            self.run_transaction(["rpm-ostree", "rebase", refspec], f"Rebasing to {refspec}")

    def _run_dbus_transaction(self, address, task_name):
        with self._queue_lock:
            if self.transactionInProgress:
                queued = True
            else:
                self.transactionInProgress = True
                queued = False
        if queued:
            self.statusBannerMessage = f"Queued: {task_name}..."
            self._changed()
            threading.Thread(
                target=self._run_dbus_when_free, args=(address, task_name), daemon=True
            ).start()
            return
        self._run_dbus_transaction_now(address, task_name)

    def _run_dbus_when_free(self, address, task_name):
        while True:
            with self._queue_lock:
                if not self.transactionInProgress:
                    self.transactionInProgress = True
                    break
            time.sleep(0.1)
        self._run_dbus_transaction_now(address, task_name)

    def _run_dbus_transaction_now(self, address, task_name):
        self.currentTask = task_name
        self.transactionLog = f"Starting: {task_name}\n"
        self.statusBannerMessage = f"Working: {task_name}..."
        self.statusBannerType = "info"
        self._changed()

        def worker():
            try:
                self._dbus.run_transaction(
                    address,
                    on_message=lambda text: self._append_transaction(text),
                    on_progress=lambda text, percent: self._set_progress(text, percent),
                )
                self.statusBannerMessage = f"Completed: {task_name}"
                self.statusBannerType = "success"
            except Exception as e:
                self.statusBannerMessage = f"Failed: {task_name}"
                self.statusBannerType = "error"
                self.lastError = str(e)
                self.transactionLog += f"\n{e}\n"
            finally:
                with self._queue_lock:
                    self.transactionInProgress = False
                self.currentTask = ""
                self.refresh_status()
                self._changed()
                self._start_queued()

        threading.Thread(target=worker, daemon=True).start()

    def _append_transaction(self, text):
        self.transactionLog += f"[{time.strftime('%H:%M:%S')}] {text}\n"
        self.transactionMessage = str(text)
        self._changed()

    def _set_progress(self, text, percent):
        self.transactionMessage = str(text)
        self.transactionProgress = int(percent)
        self._changed()

    def pinDeployment(self, index):
        self.run_transaction(["ostree", "admin", "pin", str(index)], f"Pinning deployment {index}")

    def unpinDeployment(self, index):
        self.run_transaction(["ostree", "admin", "pin", "-u", str(index)], f"Unpinning deployment {index}")

    def applyOverlaySet(self, layered, local=None, removed=None):
        local = local or []
        removed = removed or []
        cmd = []
        if removed:
            cmd = ["rpm-ostree", "override", "remove"] + removed
            for p in layered + local:
                cmd.extend(["--install", p])
        elif layered or local:
            cmd = ["rpm-ostree", "install"] + layered + local
            
        if cmd:
            self.run_transaction(cmd, "Applying overlay set")
        else:
            self.statusBannerMessage = "Overlay set is empty."

    def resetOverlays(self):
        self.run_transaction(["rpm-ostree", "reset"], "Resetting overlays")
        
    def queuePendingOverlaySet(self, layered, local=None, removed=None):
        self.applyOverlaySet(layered, local, removed)
        
    def queuePendingOverlayReset(self):
        self.resetOverlays()
        
    def prepPlasmaLoginAccounts(self, includeStagedDeployment=False):
        self.run_transaction(["bash", "-c", PLASMA_PREP_SCRIPT], "Preparing Plasma login accounts")
        
    def needsPlasmaLoginPrep(self, targetRefOrImage):
        booted = self.bootedDeployment.get("osname", "") + " " + self.bootedDeployment.get("ref", "")
        target = targetRefOrImage.lower()
        booted = booted.lower()
        target_is_plasma = (
            ("kinoite" in target or "aurora" in target or "bazzite" in target)
            and "gnome" not in target
        )
        booted_is_gnome = "silverblue" in booted or "bluefin" in booted or "bazzite-gnome" in booted
        return bool(target_is_plasma and booted_is_gnome)

    def searchPackages(self, term):
        if term in self._searchCache:
            return self._searchCache[term]
        try:
            result = self._dbus.search(term)
            self._searchCache[term] = result[:50]
            return self._searchCache[term]
        except Exception as e:
            print("D-Bus package search unavailable:", e)
        import subprocess
        cmd = ['rpm-ostree', 'search', term]
        if os.path.exists('/.flatpak-info'):
            cmd = ['flatpak-spawn', '--host'] + cmd
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            pkgs = []
            for line in res.stdout.splitlines():
                if ' : ' in line and not line.startswith('='):
                    parts = line.split(' : ', 1)
                    pkgs.append({"name": parts[0].strip(), "summary": parts[1].strip()})
            result = pkgs[:50]
            self._searchCache[term] = result
            return result
        except Exception:
            return []

    def getDeploymentPackages(self):
        pkgs = set()
        pkgs.update(self.bootedDeployment.get("requested-packages", []))
        pkgs.update(self.bootedDeployment.get("packages", []))
        pkgs.update(self.bootedDeployment.get("requested-local-packages", []))
        return sorted(list(pkgs))
