"""Feature-parity unit tests against shipped core and model wrappers.

No mocks of the units under test. Uses temp dirs for overlay persistence and
synthetic deployment dicts for status-derived flags.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Ensure project root is on path when run as `python3 test_parity.py`
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from basejump.core.ostree import (
    OstreeBackend,
    CliProgressEstimator,
    deployment_image_ref,
    desktop_family_from_ref,
    plasma_login_repair_available,
)
from basejump.core.overlays import OverlayService
from basejump.core.appinfo import AppInfo
from basejump.core.settings import SettingsManager
from basejump.core.registry import ImageRegistryService


class DesktopFamilyHelpersTest(unittest.TestCase):
    def test_desktop_family_from_ref_gnome(self):
        self.assertEqual(desktop_family_from_ref("ostree-image-signed:docker://ghcr.io/ublue-os/bluefin:stable"), "gnome")
        self.assertEqual(desktop_family_from_ref("quay.io/fedora/fedora-silverblue:42"), "gnome")
        self.assertEqual(desktop_family_from_ref("ghcr.io/ublue-os/bazzite-gnome:stable"), "gnome")

    def test_desktop_family_from_ref_plasma(self):
        self.assertEqual(desktop_family_from_ref("ghcr.io/ublue-os/aurora:stable"), "plasma")
        self.assertEqual(desktop_family_from_ref("quay.io/fedora/fedora-kinoite:42"), "plasma")
        self.assertEqual(desktop_family_from_ref("ghcr.io/ublue-os/bazzite:stable"), "plasma")

    def test_desktop_family_unknown_empty(self):
        self.assertEqual(desktop_family_from_ref(""), "unknown")
        self.assertEqual(desktop_family_from_ref("custom.local/mystery"), "unknown")
    def test_deployment_image_ref_prefers_container_ref(self):
        dep = {
            "container-image-reference": "ostree-image-signed:docker://ghcr.io/ublue-os/bluefin:gts",
            "origin": "fedora:42",
            "ref": "other",
        }
        self.assertIn("bluefin", deployment_image_ref(dep))

    def test_plasma_login_repair_available_true(self):
        booted = {"container-image-reference": "ghcr.io/ublue-os/bluefin:stable", "booted": True}
        pending = {"container-image-reference": "ghcr.io/ublue-os/aurora:stable", "staged": True}
        self.assertTrue(plasma_login_repair_available(booted, pending))

    def test_plasma_login_repair_available_false_same_family(self):
        booted = {"container-image-reference": "ghcr.io/ublue-os/aurora:stable", "booted": True}
        pending = {"container-image-reference": "ghcr.io/ublue-os/kinoite-main:stable", "staged": True}
        self.assertFalse(plasma_login_repair_available(booted, pending))

    def test_plasma_login_repair_available_false_no_pending(self):
        booted = {"container-image-reference": "ghcr.io/ublue-os/bluefin:stable"}
        self.assertFalse(plasma_login_repair_available(booted, {}))


class ImageRegistryTagClassificationTest(unittest.TestCase):
    def test_kinoite_build_tags_are_not_streams(self):
        tags = [
            "39",
            "42",
            "42.20250717.0014",
            "42.20250718.0016",
            "42-aarch64",
            "42-ppc64le",
            "42-x86_64",
            "43",
            "43.20250718.0",
            "43-x86_64",
            "latest",
            "rawhide",
        ]

        streams, versions = ImageRegistryService._classify_tags(tags)

        self.assertEqual(streams, ["latest", "rawhide"])
        self.assertEqual(versions, ["39", "42", "43"])


class OstreeDerivedFlagsTest(unittest.TestCase):
    def test_update_derived_status_flags_on_backend(self):
        backend = OstreeBackend(notify=lambda: None)
        backend.bootedDeployment = {
            "container-image-reference": "ostree-unverified-registry:ghcr.io/ublue-os/bluefin:stable",
            "booted": True,
        }
        backend.pendingDeployment = {
            "container-image-reference": "ostree-image-signed:docker://ghcr.io/ublue-os/bazzite:stable",
            "staged": True,
        }
        backend._update_derived_status_flags()
        self.assertEqual(backend.bootedDesktopFamily, "gnome")
        self.assertTrue(backend.plasmaLoginRepairAvailable)

    def test_needs_plasma_login_prep(self):
        backend = OstreeBackend(notify=lambda: None)
        backend.bootedDeployment = {
            "osname": "fedora",
            "ref": "ostree-image-signed:docker://ghcr.io/ublue-os/bluefin:stable",
        }
        self.assertTrue(backend.needsPlasmaLoginPrep("ostree-image-signed:docker://ghcr.io/ublue-os/aurora:stable"))
        self.assertFalse(backend.needsPlasmaLoginPrep("ostree-image-signed:docker://ghcr.io/ublue-os/bluefin-dx:stable"))

    def test_clear_transaction_log(self):
        backend = OstreeBackend(notify=lambda: None)
        backend.transactionLog = "hello"
        backend.statusBannerMessage = "Working"
        backend.lastError = "err"
        backend.transactionMessage = "msg"
        backend.clearTransactionLog()
        self.assertEqual(backend.transactionLog, "")
        self.assertEqual(backend.statusBannerMessage, "")
        self.assertEqual(backend.lastError, "")


class TransactionQueueTest(unittest.TestCase):
    def setUp(self):
        self.backend = OstreeBackend(notify=lambda: None)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.backend.transactionInProgress = False
        self.backend._queue.clear()

    def test_check_exit_77_means_up_to_date(self):
        # rpm-ostree upgrade --check implies --unchanged-exit-77: 77 is a
        # successful check (no updates), 0 means updates available.
        ok, note = self.backend._classify_result(["rpm-ostree", "upgrade", "--check"], 77)
        self.assertTrue(ok)
        self.assertIn("up to date", note)
        ok, _ = self.backend._classify_result(["rpm-ostree", "upgrade", "--check"], 0)
        self.assertTrue(ok)
        # 77 from a non-check command is still a real failure
        ok, _ = self.backend._classify_result(["rpm-ostree", "upgrade"], 77)
        self.assertFalse(ok)
        ok, _ = self.backend._classify_result(["rpm-ostree", "upgrade"], 1)
        self.assertFalse(ok)

    def test_cli_progress_chunk_fetch(self):
        backend = self.backend
        backend._update_cli_progress("[1/65] Fetching ostree chunk a0af4fb1d1bd47f795d (116.7 MB)...done")
        first = backend.transactionProgress
        self.assertGreaterEqual(first, 1)
        self.assertLess(first, 72)
        backend._update_cli_progress("[33/65] Fetching ostree chunk 5b83c2e3d41a8d0f7b2 (82.1 MB)...done")
        self.assertGreater(backend.transactionProgress, first)
        backend._update_cli_progress("[65/65] Fetching ostree chunk 73f5324de74e19927b4 (8.3 MB)...done")
        # fetch carries 72% of the transaction weight
        self.assertEqual(backend.transactionProgress, 72)
        self.assertIn("65/65", backend.transactionMessage)

    def test_cli_progress_rebase_full_log(self):
        # The complete phase sequence from a real rebase log, weighted by
        # typical time share: fetch 72 + phases to 99 (capped).
        backend = self.backend
        lines = [
            "[65/65] Fetching ostree chunk 73f5324de74e19927b4 (8.3 MB)...done",
            "Importing: ostree-image-signed:docker://quay.io/fedora/fedora-kinoite:latest (digest: sha256:b39c)",
            "Checking out tree 8cc1e14...done",
            "Importing rpm-md...done",
            "Resolving dependencies...done",
            "Relabeling...done",
            "Checking out packages...done",
            "Running systemd-sysusers...done",
            "Running pre scripts...done",
            "Running post scripts...done",
            "Running posttrans scripts...done",
            "Writing rpmdb...done",
            "Writing OSTree commit...done",
            "Staging deployment...done",
        ]
        for i, line in enumerate(lines):
            backend._update_cli_progress(line, elapsed=float(i))
        self.assertGreater(backend.transactionProgress, 90)
        self.assertLessEqual(backend.transactionProgress, 99)

    def test_cli_progress_no_chunk_phases_only(self):
        # upgrade/install output has no [n/N] lines; phases span the whole bar.
        backend = self.backend
        backend._update_cli_progress("Importing rpm-md...done")
        first = backend.transactionProgress
        self.assertGreaterEqual(first, 5)
        backend._update_cli_progress("Resolving dependencies...done")
        self.assertGreater(backend.transactionProgress, first)
        backend._update_cli_progress("Staging deployment...done")
        self.assertLessEqual(backend.transactionProgress, 99)

    def test_cli_progress_elapsed_partial_credit(self):
        backend = self.backend
        backend._update_cli_progress("Resolving dependencies", elapsed=0.0)
        p0 = backend.transactionProgress
        backend._update_cli_progress("Resolving dependencies", elapsed=10.0)
        p1 = backend.transactionProgress
        backend._update_cli_progress("Resolving dependencies...done", elapsed=20.0)
        p2 = backend.transactionProgress
        self.assertLessEqual(p0, p1)
        self.assertLess(p1, p2)

    def test_cli_progress_ignores_unmatched_lines(self):
        backend = self.backend
        backend._update_cli_progress("Pulling manifest: ostree-image-signed:docker://quay.io/fedora/fedora-kinoite:latest")
        self.assertEqual(backend.transactionProgress, 0)
        backend._update_cli_progress("[2/65] Fetching ostree chunk abc (12.3 MB)...done")
        pct = backend.transactionProgress
        backend._update_cli_progress("Upgraded:  linux-firmware 20260622-1.fc44 -> 20260810-1.fc44")
        self.assertEqual(backend.transactionProgress, pct)

    def test_cli_progress_self_calibrates_typical_durations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress_stats.json"
            est = CliProgressEstimator(stats_path=path)
            est.update("Relabeling", elapsed=0.0)
            est.update("Relabeling...done", elapsed=10.0)
            self.assertAlmostEqual(est._typicals["relabel"], (30 * 9 + 10) / 10)
            self.assertTrue(path.exists())
            # A fresh estimator loads the learned typical duration.
            est2 = CliProgressEstimator(stats_path=path)
            self.assertAlmostEqual(est2._typicals["relabel"], (30 * 9 + 10) / 10)

    def test_run_transaction_starts_when_free(self):
        started = []
        self.backend._run_cli_transaction = lambda cmd, task: started.append(task)
        self.backend.run_transaction(["echo", "a"], "Task A")
        self.assertEqual(started, ["Task A"])
        self.assertTrue(self.backend.transactionInProgress)

    def test_run_transaction_queues_when_busy(self):
        self.backend.transactionInProgress = True
        self.backend.run_transaction(["echo", "a"], "Task A")
        self.backend.run_transaction(["echo", "b"], "Task B")
        self.assertEqual([t for _, t in self.backend._queue], ["Task A", "Task B"])
        self.assertTrue(self.backend.transactionInProgress)

    def test_overlay_then_rebase_queued_in_order(self):
        # Regression: queueing an overlay set with a rebase must not silently
        # drop the rebase (the old guard returned early when busy).
        self.backend.transactionInProgress = True
        self.backend.run_transaction(["rpm-ostree", "install", "vim"], "Applying overlay set")
        self.backend.run_transaction(["rpm-ostree", "rebase", "aurora:stable"], "Rebasing to aurora:stable")
        tasks = [t for _, t in self.backend._queue]
        self.assertEqual(tasks, ["Applying overlay set", "Rebasing to aurora:stable"])


class OverlayServiceParityTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home = Path(self._tmp.name)
        self._home_patch = mock.patch.dict(os.environ, {"HOME": str(home)})
        self._home_patch.start()
        self.addCleanup(self._home_patch.stop)
        # OverlayService uses Path.home()
        data = home / ".local" / "share" / "atomicbasejump"
        data.mkdir(parents=True)

    def test_create_list_export_roundtrip(self):
        svc = OverlayService()
        set_id = svc.createOverlaySet(
            "Gaming",
            "steam + mangohud",
            ["steam", "mangohud"],
            [],
            ["firefox"],
        )
        self.assertTrue(set_id.startswith("overlay_"))
        self.assertEqual(len(svc.sets), 1)
        got = svc.getOverlaySet(set_id)
        self.assertEqual(got["layeredPackages"], ["steam", "mangohud"])
        self.assertEqual(got["removedPackages"], ["firefox"])

        exported = svc.exportJson()
        data = json.loads(exported)
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["name"], "Gaming")

        svc2 = OverlayService()
        # same file path under patched HOME
        self.assertEqual(len(svc2.sets), 1)
        self.assertEqual(svc2.sets[0]["id"], set_id)


class OverlayServiceModelPropertyTest(unittest.TestCase):
    """KDE QML reads overlaySets; model must expose it as alias of sets."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home = Path(self._tmp.name)
        self._home_patch = mock.patch.dict(os.environ, {"HOME": str(home)})
        self._home_patch.start()
        self.addCleanup(self._home_patch.stop)
        (home / ".local" / "share" / "atomicbasejump").mkdir(parents=True)

    def test_overlay_sets_alias_matches_sets(self):
        try:
            from basejump.ui_kde.models import OverlayServiceModel
        except Exception as exc:
            self.skipTest(f"PyQt6/models unavailable: {exc}")

        model = OverlayServiceModel()
        model.createOverlaySet("A", "d", ["vim"], [], [])
        sets_list = model.sets
        alias = model.overlaySets
        self.assertEqual(len(sets_list), 1)
        self.assertEqual(len(alias), 1)
        self.assertEqual(sets_list[0]["name"], alias[0]["name"])
        self.assertEqual(sets_list[0]["layeredPackages"], ["vim"])


class SettingsCheckNowTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home = Path(self._tmp.name)
        self._home_patch = mock.patch.dict(os.environ, {"HOME": str(home)})
        self._home_patch.start()
        self.addCleanup(self._home_patch.stop)
        (home / ".config" / "atomicbasejump").mkdir(parents=True)

    def test_check_for_updates_now_calls_backend(self):
        try:
            from basejump.ui_kde.models import SettingsManagerModel, OstreeBackendModel
        except Exception as exc:
            self.skipTest(f"PyQt6/models unavailable: {exc}")

        class FakeBackend:
            def __init__(self):
                self.called = False

            def checkForUpdates(self):
                self.called = True

        fake = FakeBackend()
        model = SettingsManagerModel(fake)
        before = model.lastCheckTime
        model.checkForUpdatesNow()
        self.assertTrue(fake.called)
        self.assertNotEqual(model.lastCheckTime, "Never")
        self.assertNotEqual(model.lastCheckTime, before if before != "Never" else "")

    def test_settings_manager_persists_last_check(self):
        sm = SettingsManager()
        sm.lastCheckTime = "2026-01-01 12:00:00"
        sm2 = SettingsManager()
        self.assertEqual(sm2.lastCheckTime, "2026-01-01 12:00:00")


class AppInfoTest(unittest.TestCase):
    def test_appinfo_fields(self):
        info = AppInfo()
        self.assertTrue(info.version)
        self.assertTrue(info.display_name)
        self.assertIn("github", info.homepage.lower())
        self.assertTrue(info.license)


class ImportModulesTest(unittest.TestCase):
    def test_import_core_and_gnome_pages(self):
        import basejump.core.ostree
        import basejump.core.overlays
        import basejump.core.settings
        import basejump.core.registry
        import basejump.core.appinfo
        # GNOME page modules import gi; require GTK available
        import basejump.ui_gnome.overview
        import basejump.ui_gnome.image_browser
        import basejump.ui_gnome.overlay_sets
        import basejump.ui_gnome.settings
        import basejump.ui_gnome.about
        import basejump.ui_gnome.window
        self.assertTrue(hasattr(basejump.ui_gnome.overview, "OverviewPage"))
        self.assertTrue(hasattr(basejump.ui_gnome.about, "AboutPage"))

    def test_import_kde_models(self):
        try:
            import basejump.ui_kde.models as models
        except Exception as exc:
            self.skipTest(f"PyQt6 unavailable: {exc}")
        self.assertTrue(hasattr(models.OverlayServiceModel, "overlaySets"))
        self.assertTrue(hasattr(models.SettingsManagerModel, "checkForUpdatesNow"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
